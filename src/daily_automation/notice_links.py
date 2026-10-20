"""Read bounded public link text; private/login pages require manual supplementation."""

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def _public_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ValueError("只读取公开 HTTPS 链接")
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(address[4][0]).is_global for address in addresses):
        raise ValueError("链接地址不是公开网络地址")


def fetch_notice_link(url: str) -> tuple[str, str]:
    session = requests.Session()
    try:
        for _ in range(5):
            _public_url(url)
            response = session.get(url, timeout=20, stream=True, allow_redirects=False)
            with response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    url = urljoin(url, response.headers.get("Location", ""))
                    continue
                response.raise_for_status()
                if "text/html" not in response.headers.get("Content-Type", ""):
                    raise ValueError("文件或非网页内容需补录原文")
                chunks, size = [], 0
                for chunk in response.iter_content(16384):
                    size += len(chunk)
                    if size > 1_000_000:
                        raise ValueError("链接内容过长，需要人工核对")
                    chunks.append(chunk)
                soup = BeautifulSoup(b"".join(chunks), "lxml")
                if soup.select_one("input[type=password]"):
                    raise ValueError("链接需要登录")
                title = soup.title.get_text(" ", strip=True) if soup.title else ""
                for node in soup.select("script,style,nav,footer,header,noscript"):
                    node.decompose()
                main = soup.select_one("article,main,#js_content,.article-content,.content") or soup.body or soup
                body = main.get_text("\n", strip=True)
                if len(body) < 100 or any(word in body[:300] for word in ("安全验证", "请先登录", "访问过于频繁")):
                    raise ValueError("链接正文未能确认")
                if len(body) > 20000:
                    raise ValueError("链接正文过长，需要补录相关段落")
                return title[:500], body
        raise ValueError("链接重定向过多")
    finally:
        session.close()
