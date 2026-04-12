#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多后端HTTP获取器 - Multi-backend Web Fetcher
支持 urllib / requests / httpx / selenium 四种后端自动降级
当一种后端失败时，自动尝试下一种
"""

import time
from dataclasses import dataclass
from typing import Optional, List
from urllib.parse import urlparse


@dataclass
class FetchResult:
    url: str
    content: Optional[str] = None
    status_code: int = 0
    encoding: str = "utf-8"
    error: Optional[str] = None
    backend_used: str = ""
    elapsed: float = 0.0
    is_js_rendered: bool = False


class UrllibBackend:
    name = "urllib"

    def __init__(self):
        import urllib.request
        import urllib.error
        self._urllib = urllib.request
        self._urllib_error = urllib.error

    def fetch(self, url: str, timeout: int = 15, headers: dict = None) -> FetchResult:
        start = time.time()
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'identity',
        }
        if headers:
            default_headers.update(headers)

        try:
            req = self._urllib.Request(url, headers=default_headers)
            with self._urllib.urlopen(req, timeout=timeout) as response:
                data = response.read()
                content_type = response.headers.get('Content-Type', '')
                status_code = response.status

                charset = 'utf-8'
                if 'charset=' in content_type:
                    charset = content_type.split('charset=')[-1].split(';')[0].strip()

                content = self._decode_content(data, charset)
                return FetchResult(
                    url=url, content=content, status_code=status_code,
                    encoding=charset, backend_used=self.name,
                    elapsed=time.time() - start
                )
        except self._urllib_error.HTTPError as e:
            return FetchResult(
                url=url, status_code=e.code, error=f"HTTP {e.code}",
                backend_used=self.name, elapsed=time.time() - start
            )
        except Exception as e:
            return FetchResult(
                url=url, error=str(e),
                backend_used=self.name, elapsed=time.time() - start
            )

    @staticmethod
    def _decode_content(data: bytes, preferred: str = 'utf-8') -> str:
        for enc in [preferred, 'utf-8', 'gbk', 'gb2312', 'latin-1']:
            try:
                return data.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return data.decode('latin-1', errors='replace')


class RequestsBackend:
    name = "requests"

    def __init__(self):
        import requests
        self._requests = requests

    def fetch(self, url: str, timeout: int = 15, headers: dict = None) -> FetchResult:
        start = time.time()
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        if headers:
            default_headers.update(headers)

        try:
            resp = self._requests.get(
                url, headers=default_headers, timeout=timeout, allow_redirects=True
            )
            resp.encoding = resp.apparent_encoding or 'utf-8'
            return FetchResult(
                url=url, content=resp.text, status_code=resp.status_code,
                encoding=resp.encoding, backend_used=self.name,
                elapsed=time.time() - start
            )
        except Exception as e:
            return FetchResult(
                url=url, error=str(e),
                backend_used=self.name, elapsed=time.time() - start
            )


class HttpxBackend:
    name = "httpx"

    def __init__(self):
        import httpx
        self._httpx = httpx

    def fetch(self, url: str, timeout: int = 15, headers: dict = None) -> FetchResult:
        start = time.time()
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        if headers:
            default_headers.update(headers)

        try:
            with self._httpx.Client(
                headers=default_headers, timeout=timeout, follow_redirects=True
            ) as client:
                resp = client.get(url)
                return FetchResult(
                    url=url, content=resp.text, status_code=resp.status_code,
                    encoding=resp.encoding or 'utf-8', backend_used=self.name,
                    elapsed=time.time() - start
                )
        except Exception as e:
            return FetchResult(
                url=url, error=str(e),
                backend_used=self.name, elapsed=time.time() - start
            )


class SeleniumBackend:
    name = "selenium"

    def __init__(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        self._webdriver = webdriver
        self._options = Options

    def fetch(self, url: str, timeout: int = 30, headers: dict = None,
              wait_seconds: int = 5) -> FetchResult:
        start = time.time()
        driver = None
        try:
            options = self._options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_argument(
                'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0'
            )

            try:
                driver = self._webdriver.Chrome(options=options)
            except Exception:
                try:
                    from selenium.webdriver.edge.options import Options as EdgeOptions
                    edge_opts = EdgeOptions()
                    edge_opts.add_argument('--headless')
                    edge_opts.add_argument('--no-sandbox')
                    edge_opts.add_argument('--disable-dev-shm-usage')
                    driver = self._webdriver.Edge(options=edge_opts)
                except Exception:
                    return FetchResult(
                        url=url, error="No Chrome/Edge driver available",
                        backend_used=self.name, elapsed=time.time() - start
                    )

            driver.set_page_load_timeout(timeout)
            driver.get(url)
            time.sleep(wait_seconds)

            content = driver.page_source
            return FetchResult(
                url=url, content=content, status_code=200,
                encoding='utf-8', backend_used=self.name,
                elapsed=time.time() - start, is_js_rendered=True
            )
        except Exception as e:
            return FetchResult(
                url=url, error=str(e),
                backend_used=self.name, elapsed=time.time() - start
            )
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass  # driver.quit()失败可忽略


class WebFetcher:
    def __init__(self, prefer_js: bool = False):
        self._log_messages = []
        self.backends: List[object] = []
        self._init_backends(prefer_js)

    def _log(self, msg: str):
        self._log_messages.append(msg)

    def get_logs(self) -> List[str]:
        return self._log_messages

    def _init_backends(self, prefer_js: bool):
        if prefer_js:
            backend_classes = [SeleniumBackend, RequestsBackend, HttpxBackend, UrllibBackend]
        else:
            backend_classes = [RequestsBackend, HttpxBackend, UrllibBackend, SeleniumBackend]

        for cls in backend_classes:
            try:
                backend = cls()
                self.backends.append(backend)
                self._log(f"[WebFetcher] 后端 {cls.name} 初始化成功")
            except ImportError:
                self._log(f"[WebFetcher] 后端 {cls.name} 不可用（未安装）")
            except Exception as e:
                self._log(f"[WebFetcher] 后端 {cls.name} 初始化失败: {e}")

        if not self.backends:
            try:
                backend = UrllibBackend()
                self.backends.append(backend)
                self._log("[WebFetcher] 回退到 urllib 后端")
            except Exception as e:
                self._log(f"[WebFetcher] 严重：无可用后端: {e}")

    def fetch(self, url: str, timeout: int = 15, headers: dict = None,
              max_retries: int = 1) -> FetchResult:
        errors = []
        for backend in self.backends:
            for attempt in range(max_retries):
                self._log(f"[WebFetcher] 尝试 {backend.name} 获取 {url} (第{attempt+1}次)")
                result = backend.fetch(url, timeout=timeout, headers=headers)

                if result.content and not result.error:
                    self._log(
                        f"[WebFetcher] {backend.name} 成功获取 {url} "
                        f"({result.elapsed:.2f}s, {len(result.content)} chars)"
                    )
                    return result

                error_msg = f"{backend.name}: {result.error or 'empty content'}"
                errors.append(error_msg)
                self._log(f"[WebFetcher] {backend.name} 失败: {error_msg}")

                if result.status_code in (403, 429):
                    self._log(f"[WebFetcher] 状态码 {result.status_code}，等待后重试...")
                    time.sleep(2 * (attempt + 1))

        self._log(f"[WebFetcher] 所有后端均失败: {url}")
        return FetchResult(
            url=url,
            error="; ".join(errors),
            backend_used="all_failed"
        )

    def fetch_with_js(self, url: str, timeout: int = 30,
                      wait_seconds: int = 5) -> FetchResult:
        for backend in self.backends:
            if isinstance(backend, SeleniumBackend):
                self._log(f"[WebFetcher] 使用 Selenium JS渲染获取 {url}")
                result = backend.fetch(url, timeout=timeout, wait_seconds=wait_seconds)
                if result.content and not result.error:
                    return result
                self._log(f"[WebFetcher] Selenium 失败: {result.error}")

        self._log(f"[WebFetcher] JS渲染后端不可用，尝试普通获取: {url}")
        return self.fetch(url, timeout=timeout)
