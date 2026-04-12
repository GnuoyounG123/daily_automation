#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API驱动学术源 - API-based Academic Sources
使用公开API获取学术信息，无需网页爬取，稳定性最高
支持: Semantic Scholar API / CrossRef API / DBLP API / OpenAlex API / CORE API
"""

import json
import time
from typing import List, Optional, Dict
from datetime import datetime
from urllib.parse import quote, urlencode

try:
    from config_manager import ConfigManager
    _config_mgr = ConfigManager()
except Exception:
    _config_mgr = None


def _get_api_key(service: str) -> str:
    if _config_mgr:
        return _config_mgr.get_api_key(service)
    return ''



class SemanticScholarApi:
    name = "Semantic Scholar API"

    def __init__(self):
        from web_fetcher import WebFetcher
        self._fetcher = WebFetcher()
        self._api_key = _get_api_key('semantic_scholar')

    def search(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        url = (
            f"https://api.semanticscholar.org/graph/v1/paper/search"
            f"?query={quote(query)}&limit={max_results}&fields="
            f"title,abstract,url,publicationDate,externalIds,authors"
        )

        headers = {}
        if self._api_key:
            headers['x-api-key'] = self._api_key

        result = self._fetcher.fetch(url, timeout=20, max_retries=3, headers=headers if headers else None)
        if not result.content or result.error:
            if result.status_code == 429:
                if not self._api_key:
                    self._log("Semantic Scholar API 限流(429)，建议配置API Key: https://www.semanticscholar.org/product/api#api-key")
                time.sleep(3)
                result = self._fetcher.fetch(url, timeout=20, headers=headers if headers else None)
            if not result.content or result.error:
                return items

        try:
            data = json.loads(result.content)
            for paper in data.get('data', [])[:max_results]:
                title = paper.get('title', '')
                if not title:
                    continue
                abstract = paper.get('abstract', '') or ''
                pub_date = paper.get('publicationDate', '') or ''
                paper_url = paper.get('url', '')

                ext_ids = paper.get('externalIds', {})
                if ext_ids.get('ArXiv'):
                    paper_url = f"https://arxiv.org/abs/{ext_ids['ArXiv']}"

                authors = paper.get('authors', [])
                author_names = ', '.join(
                    a.get('name', '') for a in authors[:3] if a.get('name')
                )

                items.append({
                    'title': title,
                    'abstract': abstract[:500] if abstract else '',
                    'url': paper_url,
                    'date': pub_date[:10] if pub_date else '今日',
                    'source': 'Semantic Scholar',
                    'authors': author_names
                })
        except Exception as e:
            self._log(f"API请求异常: {e}")
            return []

        return items


class CrossRefApi:
    name = "CrossRef API"

    def __init__(self):
        from web_fetcher import WebFetcher
        self._fetcher = WebFetcher()

    def search(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        params = {
            'query': query,
            'rows': max_results,
            'sort': 'published',
            'order': 'desc'
        }
        url = f"https://api.crossref.org/works?{urlencode(params)}"

        result = self._fetcher.fetch(url, timeout=20)
        if not result.content or result.error:
            return items

        try:
            data = json.loads(result.content)
            messages = data.get('message', {})
            for item in messages.get('items', [])[:max_results]:
                titles = item.get('title', [])
                title = titles[0] if titles else ''
                if not title:
                    continue

                abstract = item.get('abstract', '') or ''
                abstract = abstract.replace('<jats:p>', '').replace('</jats:p>', '').replace('<jats:title>', '').replace('</jats:title>', '')
                abstract = abstract[:500]

                dates = item.get('published-print', item.get('published-online', {}))
                date_parts = dates.get('date-parts', [[]])
                pub_date = ''
                if date_parts and date_parts[0]:
                    parts = date_parts[0]
                    pub_date = '-'.join(str(p) for p in parts[:3])

                doi = item.get('DOI', '')
                paper_url = f"https://doi.org/{doi}" if doi else ''

                authors = item.get('author', [])
                author_names = ', '.join(
                    f"{a.get('given', '')} {a.get('family', '')}".strip()
                    for a in authors[:3]
                )

                items.append({
                    'title': title,
                    'abstract': abstract,
                    'url': paper_url,
                    'date': pub_date or '今日',
                    'source': 'CrossRef',
                    'authors': author_names
                })
        except Exception as e:
            self._log(f"API请求异常: {e}")
            return []

        return items


class DBLPApi:
    name = "DBLP API"

    def __init__(self):
        from web_fetcher import WebFetcher
        self._fetcher = WebFetcher()

    def search(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        url = (
            f"https://dblp.org/search/publ/api"
            f"?q={quote(query)}&h={max_results}&format=json"
        )

        result = self._fetcher.fetch(url, timeout=20)
        if not result.content or result.error:
            return items

        try:
            data = json.loads(result.content)
            hits = data.get('result', {}).get('hits', {}).get('hit', [])
            for hit in hits[:max_results]:
                info = hit.get('info', {})
                title = info.get('title', '')
                if not title:
                    continue

                abstract = ''
                year = info.get('year', '')
                venue = info.get('venue', '')
                paper_url = info.get('url', '')

                authors = info.get('authors', {}).get('author', [])
                if isinstance(authors, dict):
                    authors = [authors]
                author_names = ', '.join(
                    a.get('text', '') for a in authors[:3] if isinstance(a, dict)
                )

                items.append({
                    'title': title,
                    'abstract': abstract,
                    'url': paper_url,
                    'date': year or '今日',
                    'source': 'DBLP',
                    'authors': author_names,
                    'venue': venue
                })
        except Exception as e:
            self._log(f"API请求异常: {e}")
            return []

        return items


class OpenAlexApi:
    name = "OpenAlex API"

    def __init__(self):
        from web_fetcher import WebFetcher
        self._fetcher = WebFetcher()
        self._api_key = _get_api_key('openalex')

    def search(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        api_key_param = f"&api_key={self._api_key}" if self._api_key else ""
        url = (
            f"https://api.openalex.org/works"
            f"?search={quote(query)}&per_page={max_results}"
            f"&sort=publication_date:desc{api_key_param}"
        )

        result = self._fetcher.fetch(url, timeout=20)
        if not result.content or result.error:
            return items

        try:
            data = json.loads(result.content)
            for work in data.get('results', [])[:max_results]:
                title = work.get('title', '')
                if not title:
                    continue

                abstract_inverted = work.get('abstract_inverted_index', {})
                abstract = self._reconstruct_abstract(abstract_inverted)

                pub_date = work.get('publication_date', '') or ''
                paper_url = work.get('id', '')

                authorships = work.get('authorships', [])
                author_names = ', '.join(
                    a.get('author', {}).get('display_name', '')
                    for a in authorships[:3]
                    if a.get('author', {}).get('display_name')
                )

                items.append({
                    'title': title,
                    'abstract': abstract[:500] if abstract else '',
                    'url': paper_url,
                    'date': pub_date[:10] if pub_date else '今日',
                    'source': 'OpenAlex',
                    'authors': author_names
                })
        except Exception as e:
            self._log(f"API请求异常: {e}")
            return []

        return items

    @staticmethod
    def _reconstruct_abstract(inverted_index: dict) -> str:
        if not inverted_index:
            return ''
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort(key=lambda x: x[0])
        return ' '.join(w for _, w in word_positions)


class CoreApi:
    name = "CORE API"

    def __init__(self):
        from web_fetcher import WebFetcher
        self._fetcher = WebFetcher()
        self._api_key = _get_api_key('core')

    def search(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        if not self._api_key:
            self._log("CORE API 需要API Key，请在config.json中配置api_keys.core")
            self._log("获取API Key: https://core.ac.uk/services/api")
            return items
        query = " ".join(keywords[:3])
        url = (
            f"https://api.core.ac.uk/v3/search/works"
            f"?q={quote(query)}&limit={max_results}&offset=0"
        )

        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self._api_key}'
        }
        result = self._fetcher.fetch(url, timeout=20, headers=headers)
        if not result.content or result.error:
            return items

        try:
            data = json.loads(result.content)
            for work in data.get('results', [])[:max_results]:
                title = work.get('title', '')
                if not title:
                    continue

                abstract = work.get('abstract', '') or ''
                abstract = abstract[:500]

                pub_date = work.get('publishedDate', '') or ''
                paper_url = work.get('downloadUrl', work.get('sourceFulltextUrls', [''])[0] if work.get('sourceFulltextUrls') else '')

                authors = work.get('authors', [])
                author_names = ', '.join(
                    a.get('name', '') for a in authors[:3] if isinstance(a, dict) and a.get('name')
                )

                items.append({
                    'title': title,
                    'abstract': abstract,
                    'url': paper_url if isinstance(paper_url, str) else '',
                    'date': pub_date[:10] if pub_date else '今日',
                    'source': 'CORE',
                    'authors': author_names
                })
        except Exception as e:
            self._log(f"API请求异常: {e}")
            return []

        return items


class ApiSourceManager:
    def __init__(self):
        self.sources: List[object] = []
        self._log_messages = []
        self._init_sources()

    def _log(self, msg: str):
        self._log_messages.append(msg)

    def get_logs(self) -> List[str]:
        return self._log_messages

    def _init_sources(self):
        source_classes = [SemanticScholarApi, CrossRefApi, DBLPApi, OpenAlexApi, CoreApi]
        for cls in source_classes:
            try:
                source = cls()
                self.sources.append(source)
                self._log(f"[ApiSource] {cls.name} 初始化成功")
            except Exception as e:
                self._log(f"[ApiSource] {cls.name} 初始化失败: {e}")

    def search_all(self, keywords: List[str], max_per_source: int = 5) -> List[dict]:
        all_items = []
        for source in self.sources:
            self._log(f"[ApiSource] 查询 {source.name}...")
            try:
                items = source.search(keywords, max_results=max_per_source)
                self._log(f"[ApiSource] {source.name} 返回 {len(items)} 条")
                all_items.extend(items)
                time.sleep(0.5)
            except Exception as e:
                self._log(f"[ApiSource] {source.name} 查询失败: {e}")
        return all_items

    def search_single(self, source_name: str, keywords: List[str],
                      max_results: int = 10) -> List[dict]:
        for source in self.sources:
            if source.name == source_name:
                try:
                    return source.search(keywords, max_results=max_results)
                except Exception:
                    return []
        return []
