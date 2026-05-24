#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多策略HTML解析器 - Multi-strategy HTML Parser
支持 regex / BeautifulSoup / lxml / feedparser 四种解析策略自动降级
当一种策略失败时，自动尝试下一种
"""

import re
import json
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict
from datetime import datetime
from urllib.parse import urlparse
from dataclasses import dataclass, field


class RegexParser:
    name = "regex"

    def parse(self, html: str, url: str, source_name: str) -> List[dict]:
        items = []
        try:
            domain = urlparse(url).netloc.lower()

            if 'semanticscholar.org' in domain:
                items = self._parse_semantic_scholar(html, source_name)
            elif 'aminer.cn' in domain:
                items = self._parse_aminer(html, source_name)
            elif 'thegradient.pub' in domain:
                items = self._parse_the_gradient(html, source_name)
            else:
                items = self._parse_generic(html, source_name, url)
        except Exception as e:
            self._log(f"解析异常: {e}")
            return []

        return items

    def _parse_semantic_scholar(self, html, source_name):
        items = []
        patterns = [
            r'<a[^>]*href="(/paper/[^"]+)"[^>]*data-test-id="paper-title"[^>]*>(.*?)</a>',
            r'<a[^>]*href="(/paper/[^"]+)"[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</a>',
            r'<h[23][^>]*>.*?<a[^>]*href="(/paper/[^"]+)"[^>]*>(.*?)</a>.*?</h[23]>',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for match in matches[:8]:
                if isinstance(match, tuple):
                    link, title = match
                else:
                    continue
                title = re.sub(r'<[^>]+>', '', title).strip()
                if not title or len(title) < 10:
                    continue
                if link.startswith('/'):
                    link = 'https://www.semanticscholar.org' + link
                items.append({
                    'title': title, 'abstract': '', 'url': link,
                    'date': datetime.now().strftime('%Y-%m-%d'), 'source': source_name
                })
        seen = set()
        unique = []
        for item in items:
            if item['url'] not in seen:
                seen.add(item['url'])
                unique.append(item)
        return unique[:5]

    def _parse_aminer(self, html, source_name):
        items = []
        patterns = [
            r'<a[^>]*href="(/pub/[^"]+)"[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</a>',
            r'<a[^>]*href="(/pub/[^"]+)"[^>]*target="_blank"[^>]*>([^<]+)</a>',
            r'<h[23][^>]*>.*?<a[^>]*href="(/pub/[^"]+)"[^>]*>(.*?)</a>.*?</h[23]>',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for match in matches[:8]:
                if isinstance(match, tuple):
                    link, title = match
                else:
                    continue
                title = re.sub(r'<[^>]+>', '', title).strip()
                if not title or len(title) < 10:
                    continue
                if link.startswith('/'):
                    link = 'https://www.aminer.cn' + link
                items.append({
                    'title': title, 'abstract': '', 'url': link,
                    'date': datetime.now().strftime('%Y-%m-%d'), 'source': source_name
                })
        seen = set()
        unique = []
        for item in items:
            if item['url'] not in seen:
                seen.add(item['url'])
                unique.append(item)
        return unique[:5]

    def _parse_the_gradient(self, html, source_name):
        items = []
        patterns = [
            r'<a[^>]*href="(https://thegradient\.pub/[^"]+/)"[^>]*class="[^"]*post[^"]*"[^>]*>(.*?)</a>',
            r'<h[123][^>]*>.*?<a[^>]*href="(/[^"]+/)"[^>]*>(.*?)</a>.*?</h[123]>',
            r'<a[^>]*rel="bookmark"[^>]*href="(/[^"]+/)"[^>]*>(.*?)</a>',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for match in matches[:8]:
                if isinstance(match, tuple):
                    link, title = match
                else:
                    continue
                title = re.sub(r'<[^>]+>', '', title).strip()
                if not title or len(title) < 10:
                    continue
                if any(x in link.lower() for x in ['about', 'contact', 'subscribe', 'wp-content']):
                    continue
                if link.startswith('/'):
                    link = 'https://thegradient.pub' + link
                items.append({
                    'title': title, 'abstract': '', 'url': link,
                    'date': datetime.now().strftime('%Y-%m-%d'), 'source': source_name
                })
        seen = set()
        unique = []
        for item in items:
            if item['url'] not in seen:
                seen.add(item['url'])
                unique.append(item)
        return unique[:5]

    def _parse_generic(self, html, source_name, base_url):
        items = []
        patterns = [
            r'<a[^>]*href="([^"]+)"[^>]*>([^<]{30,150})</a>',
            r'<h[234][^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>.*?</h[234]>',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for match in matches[:10]:
                if isinstance(match, tuple):
                    link, title = match
                else:
                    continue
                title = re.sub(r'<[^>]+>', '', title).strip()
                if len(title) < 20 or len(title) > 200:
                    continue
                if any(x in title.lower() for x in ['javascript', 'css', 'login', 'signup', 'home', 'about']):
                    continue
                if title.count(' ') > 20:
                    continue
                if link.startswith('/'):
                    parsed = urlparse(base_url)
                    link = f"{parsed.scheme}://{parsed.netloc}{link}"
                elif not link.startswith('http'):
                    continue
                items.append({
                    'title': title, 'abstract': '', 'url': link,
                    'date': datetime.now().strftime('%Y-%m-%d'), 'source': source_name
                })
        seen = set()
        unique = []
        for item in items:
            if item['url'] not in seen:
                seen.add(item['url'])
                unique.append(item)
        return unique[:5]


class BeautifulSoupParser:
    name = "beautifulsoup"

    def __init__(self):
        from bs4 import BeautifulSoup
        self._bs = BeautifulSoup

    def parse(self, html: str, url: str, source_name: str) -> List[dict]:
        items = []
        try:
            soup = self._bs(html, 'html.parser')
            domain = urlparse(url).netloc.lower()

            article_containers = soup.find_all(['article', 'div'],
                class_=re.compile(r'(post|article|paper|card|item|entry|result)', re.I))

            if not article_containers:
                article_containers = soup.find_all(['li'],
                    class_=re.compile(r'(post|article|paper|card|item|entry|result)', re.I))

            if not article_containers:
                article_containers = []
                for heading in soup.find_all(['h2', 'h3', 'h4']):
                    parent = heading.find_parent(['article', 'div', 'li', 'section'])
                    if parent:
                        article_containers.append(parent)

            for container in article_containers[:10]:
                title_tag = container.find(['h1', 'h2', 'h3', 'h4'])
                link_tag = None
                if title_tag:
                    link_tag = title_tag.find('a')
                if not link_tag:
                    link_tag = container.find('a', href=True)

                if not title_tag or not link_tag:
                    continue

                title = title_tag.get_text(strip=True)
                link = link_tag.get('href', '')

                if not title or len(title) < 10:
                    continue

                abstract = ''
                desc_tag = container.find(['p', 'div'],
                    class_=re.compile(r'(abstract|summary|desc|excerpt|snippet)', re.I))
                if desc_tag:
                    abstract = desc_tag.get_text(strip=True)[:500]
                else:
                    p_tags = container.find_all('p')
                    if p_tags:
                        abstract = p_tags[0].get_text(strip=True)[:500]

                if link.startswith('/'):
                    parsed = urlparse(url)
                    link = f"{parsed.scheme}://{parsed.netloc}{link}"
                elif not link.startswith('http'):
                    continue

                items.append({
                    'title': title, 'abstract': abstract, 'url': link,
                    'date': datetime.now().strftime('%Y-%m-%d'), 'source': source_name
                })

        except Exception as e:
            self._log(f"解析异常: {e}")
            return []

        return items


class LxmlParser:
    name = "lxml"

    def __init__(self):
        from lxml import html as lxml_html
        self._lxml_html = lxml_html

    def parse(self, html_content: str, url: str, source_name: str) -> List[dict]:
        items = []
        try:
            tree = self._lxml_html.fromstring(html_content)
            tree.make_links_absolute(url)

            articles = tree.xpath(
                '//*[contains(@class, "post") or contains(@class, "article") '
                'or contains(@class, "paper") or contains(@class, "card") '
                'or contains(@class, "item") or contains(@class, "entry") '
                'or contains(@class, "result")]'
            )

            if not articles:
                articles = tree.xpath('//article')

            for article in articles[:10]:
                title_elems = article.xpath('.//h2//a | .//h3//a | .//h4//a | .//h1//a')
                if not title_elems:
                    title_elems = article.xpath('.//a[contains(@class, "title")]')

                if not title_elems:
                    continue

                title = title_elems[0].text_content().strip()
                link = title_elems[0].get('href', '')

                if not title or len(title) < 10:
                    continue

                abstract = ''
                desc_elems = article.xpath(
                    './/*[contains(@class, "abstract") or contains(@class, "summary") '
                    'or contains(@class, "desc") or contains(@class, "excerpt")]'
                )
                if desc_elems:
                    abstract = desc_elems[0].text_content().strip()[:500]
                else:
                    p_elems = article.xpath('.//p')
                    if p_elems:
                        abstract = p_elems[0].text_content().strip()[:500]

                if not link or not link.startswith('http'):
                    continue

                items.append({
                    'title': title, 'abstract': abstract, 'url': link,
                    'date': datetime.now().strftime('%Y-%m-%d'), 'source': source_name
                })

        except Exception as e:
            self._log(f"解析异常: {e}")
            return []

        return items


class FeedparserParser:
    name = "feedparser"

    def __init__(self):
        import feedparser
        self._feedparser = feedparser

    def parse_rss(self, xml_content: str, source_name: str) -> List[dict]:
        items = []
        try:
            feed = self._feedparser.parse(xml_content)
            for entry in feed.entries[:10]:
                title = entry.get('title', '')
                abstract = entry.get('summary', entry.get('description', ''))
                link = entry.get('link', '')
                date = entry.get('published', entry.get('updated', datetime.now().strftime('%Y-%m-%d')))

                if not title:
                    continue

                abstract = re.sub(r'<[^>]+>', '', abstract).strip()[:500]

                items.append({
                    'title': title, 'abstract': abstract, 'url': link,
                    'date': date[:10] if len(date) >= 10 else date,
                    'source': source_name
                })
        except Exception as e:
            self._log(f"解析异常: {e}")
            return []

        return items


class ArxivXmlParser:
    name = "arxiv_xml"

    def parse(self, xml_content: str, source_name: str = 'arXiv') -> List[dict]:
        items = []
        try:
            root = ET.fromstring(xml_content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            for entry in root.findall('.//atom:entry', ns):
                title = entry.find('atom:title', ns)
                summary = entry.find('atom:summary', ns)
                link = entry.find('atom:link', ns)
                published = entry.find('atom:published', ns)

                if title is not None:
                    items.append({
                        'title': title.text.strip() if title.text else '无标题',
                        'abstract': summary.text.strip() if summary is not None and summary.text else '',
                        'url': link.get('href') if link is not None else '',
                        'date': published.text[:10] if published is not None else datetime.now().strftime('%Y-%m-%d'),
                        'source': source_name
                    })
        except Exception as e:
            self._log(f"解析异常: {e}")
            return []

        return items


class HtmlParser:
    def __init__(self):
        self.parsers: List[object] = []
        self._log_messages = []
        self._init_parsers()

    def _log(self, msg: str):
        self._log_messages.append(msg)

    def get_logs(self) -> List[str]:
        return self._log_messages

    def _init_parsers(self):
        parser_classes = [BeautifulSoupParser, LxmlParser, RegexParser]
        for cls in parser_classes:
            try:
                parser = cls()
                self.parsers.append(parser)
                self._log(f"[HtmlParser] 解析器 {cls.name} 初始化成功")
            except ImportError:
                self._log(f"[HtmlParser] 解析器 {cls.name} 不可用（未安装）")
            except Exception as e:
                self._log(f"[HtmlParser] 解析器 {cls.name} 初始化失败: {e}")

        if not self.parsers:
            try:
                parser = RegexParser()
                self.parsers.append(parser)
                self._log("[HtmlParser] 回退到 regex 解析器")
            except Exception as e:
                self._log(f"[HtmlParser] 严重：无可用解析器: {e}")

    def parse(self, html: str, url: str, source_name: str,
              min_results: int = 1) -> List[dict]:
        errors = []
        for parser in self.parsers:
            self._log(f"[HtmlParser] 尝试 {parser.name} 解析 {url}")
            try:
                items = parser.parse(html, url, source_name)
                if len(items) >= min_results:
                    self._log(f"[HtmlParser] {parser.name} 成功解析 {url} ({len(items)} 条)")
                    return items
                else:
                    errors.append(f"{parser.name}: only {len(items)} items (need {min_results})")
                    self._log(f"[HtmlParser] {parser.name} 结果不足: {len(items)} 条")
            except Exception as e:
                errors.append(f"{parser.name}: {str(e)}")
                self._log(f"[HtmlParser] {parser.name} 解析失败: {e}")

        self._log(f"[HtmlParser] 所有解析器均未能有效解析: {url}")
        return []

    def parse_rss(self, xml_content: str, source_name: str,
                  is_arxiv: bool = False) -> List[dict]:
        if is_arxiv:
            arxiv_parser = ArxivXmlParser()
            items = arxiv_parser.parse(xml_content, source_name)
            if items:
                self._log(f"[HtmlParser] arXiv XML解析成功 ({len(items)} 条)")
                return items

        try:
            fp_parser = FeedparserParser()
            items = fp_parser.parse_rss(xml_content, source_name)
            if items:
                self._log(f"[HtmlParser] feedparser解析成功 ({len(items)} 条)")
                return items
        except ImportError:
            self._log("[HtmlParser] feedparser不可用")
        except Exception as e:
            self._log(f"[HtmlParser] feedparser解析失败: {e}")

        try:
            arxiv_parser = ArxivXmlParser()
            items = arxiv_parser.parse(xml_content, source_name)
            if items:
                self._log(f"[HtmlParser] arXiv XML回退解析成功 ({len(items)} 条)")
                return items
        except Exception as e:
            self._log(f"解析异常: {e}")
            return []

        self._log(f"[HtmlParser] RSS解析全部失败: {source_name}")
        return []

    def parse_json(self, json_content: str, source_name: str) -> List[dict]:
        items = []
        try:
            data = json.loads(json_content)
            results = data.get('results', data) if isinstance(data, dict) else data
            if isinstance(results, list):
                for item in results[:10]:
                    items.append({
                        'title': item.get('title', '无标题'),
                        'abstract': item.get('abstract', item.get('summary', '')),
                        'url': item.get('url', item.get('link', '')),
                        'date': item.get('date', item.get('published', '今日')),
                        'source': source_name
                    })
        except Exception as e:
            self._log(f"解析异常: {e}")
            return []
        return items
