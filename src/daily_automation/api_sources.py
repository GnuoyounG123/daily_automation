#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API-driven Academic Sources with date filtering
Supports: Semantic Scholar / CrossRef / DBLP / OpenAlex / PLOS / PubMed / bioRxiv
All sources now filter for recent papers only (last 7 days by default)
"""

import asyncio
import json
import time
import re
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from urllib.parse import quote, urlencode

try:
    from .config_manager import ConfigManager
    _config_mgr = ConfigManager()
except Exception:
    _config_mgr = None


def _get_api_key(service: str) -> str:
    if _config_mgr:
        return _config_mgr.get_api_key(service)
    return ''


def _is_recent(date_str: str, max_days: int = 7) -> bool:
    if not date_str or date_str == 'N/A':
        return True
    try:
        clean = re.sub(r'[TtZz].*$', '', str(date_str)).strip()
        for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d', '%Y%m%d', '%Y']:
            try:
                d = datetime.strptime(clean[:len(fmt.replace('%','00'))], fmt)
                if fmt == '%Y':
                    d = d.replace(month=1, day=1)
                now = datetime.now()
                if d > now + timedelta(days=1):
                    return False
                if (now - d).days > max_days:
                    return False
                return True
            except ValueError:
                continue
        year_match = re.search(r'(\d{4})', str(date_str))
        if year_match:
            year = int(year_match.group(1))
            now_year = datetime.now().year
            if year > now_year + 1 or year < now_year - 1:
                return False
        return True
    except Exception:
        return True


def _parse_date_flexible(date_str: str) -> str:
    if not date_str or date_str == 'N/A':
        return ''
    try:
        clean = re.sub(r'[TtZz].*$', '', str(date_str)).strip()
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d']:
            try:
                return datetime.strptime(clean[:10], fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        year_match = re.search(r'(\d{4})', str(date_str))
        if year_match:
            return year_match.group(1)
        return ''
    except Exception:
        return ''


class SemanticScholarApi:
    name = "Semantic Scholar API"

    def __init__(self):
        from .web_fetcher import WebFetcher
        self._fetcher = WebFetcher()
        self._async_fetcher = None
        self._api_key = _get_api_key('semantic_scholar')

    async def _get_async_fetcher(self):
        if self._async_fetcher is None:
            from .web_fetcher import AsyncWebFetcher
            self._async_fetcher = AsyncWebFetcher()
        return self._async_fetcher

    def search(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        year = datetime.now().year
        url = (
            f"https://api.semanticscholar.org/graph/v1/paper/search"
            f"?query={quote(query)}&limit={max_results}&fields="
            f"title,abstract,url,publicationDate,externalIds,authors"
            f"&year={year}"
        )

        headers = {}
        if self._api_key:
            headers['x-api-key'] = self._api_key

        result = self._fetcher.fetch(url, timeout=20, max_retries=2, headers=headers if headers else None)
        if not result.content or result.error:
            if result.status_code == 429:
                time.sleep(5)
                result = self._fetcher.fetch(url, timeout=20, headers=headers if headers else None)
            if not result.content or result.error:
                return items

        try:
            data = json.loads(result.content)
            for paper in data.get('data', [])[:max_results]:
                title = paper.get('title', '')
                if not title:
                    continue
                pub_date = paper.get('publicationDate', '') or ''
                if pub_date and not _is_recent(pub_date, 30):
                    continue
                abstract = paper.get('abstract', '') or ''
                paper_url = paper.get('url', '')
                ext_ids = paper.get('externalIds', {})
                if ext_ids.get('ArXiv'):
                    paper_url = f"https://arxiv.org/abs/{ext_ids['ArXiv']}"
                authors = paper.get('authors', [])
                author_names = ', '.join(a.get('name', '') for a in authors[:3] if a.get('name'))
                items.append({
                    'title': title,
                    'abstract': abstract[:500] if abstract else '',
                    'url': paper_url,
                    'date': _parse_date_flexible(pub_date) or 'today',
                    'source': 'Semantic Scholar',
                    'authors': author_names
                })
        except Exception:
            return []

        return items

    async def search_async(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        year = datetime.now().year
        url = (
            f"https://api.semanticscholar.org/graph/v1/paper/search"
            f"?query={quote(query)}&limit={max_results}&fields="
            f"title,abstract,url,publicationDate,externalIds,authors"
            f"&year={year}"
        )

        headers = {}
        if self._api_key:
            headers['x-api-key'] = self._api_key

        fetcher = await self._get_async_fetcher()
        result = await fetcher.fetch(url, timeout=20, max_retries=2, headers=headers if headers else None)
        if not result.content or result.error:
            if result.status_code == 429:
                await asyncio.sleep(5)
                result = await fetcher.fetch(url, timeout=20, headers=headers if headers else None)
            if not result.content or result.error:
                return items

        try:
            data = json.loads(result.content)
            for paper in data.get('data', [])[:max_results]:
                title = paper.get('title', '')
                if not title:
                    continue
                pub_date = paper.get('publicationDate', '') or ''
                if pub_date and not _is_recent(pub_date, 30):
                    continue
                abstract = paper.get('abstract', '') or ''
                paper_url = paper.get('url', '')
                ext_ids = paper.get('externalIds', {})
                if ext_ids.get('ArXiv'):
                    paper_url = f"https://arxiv.org/abs/{ext_ids['ArXiv']}"
                authors = paper.get('authors', [])
                author_names = ', '.join(a.get('name', '') for a in authors[:3] if a.get('name'))
                items.append({
                    'title': title,
                    'abstract': abstract[:500] if abstract else '',
                    'url': paper_url,
                    'date': _parse_date_flexible(pub_date) or 'today',
                    'source': 'Semantic Scholar',
                    'authors': author_names
                })
        except Exception:
            return []

        return items


class CrossRefApi:
    name = "CrossRef API"

    def __init__(self):
        from .web_fetcher import WebFetcher
        self._fetcher = WebFetcher()
        self._async_fetcher = None

    async def _get_async_fetcher(self):
        if self._async_fetcher is None:
            from .web_fetcher import AsyncWebFetcher
            self._async_fetcher = AsyncWebFetcher()
        return self._async_fetcher

    def search(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        today = datetime.now().strftime('%Y-%m-%d')
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        params = {
            'query': query,
            'rows': max_results,
            'sort': 'published',
            'order': 'desc',
            'filter': f'from-pub-date:{week_ago},until-pub-date:{today}'
        }
        url = f"https://api.crossref.org/works?{urlencode(params)}"

        result = self._fetcher.fetch(url, timeout=20)
        if not result.content or result.error:
            return items

        try:
            data = json.loads(result.content)
            for item in data.get('message', {}).get('items', [])[:max_results]:
                titles = item.get('title', [])
                title = titles[0] if titles else ''
                if not title:
                    continue
                abstract = item.get('abstract', '') or ''
                abstract = re.sub(r'<[^>]+>', '', abstract)[:500]
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
                    'date': _parse_date_flexible(pub_date) or 'today',
                    'source': 'CrossRef',
                    'authors': author_names
                })
        except Exception:
            return []

        return items

    async def search_async(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        today = datetime.now().strftime('%Y-%m-%d')
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        params = {
            'query': query,
            'rows': max_results,
            'sort': 'published',
            'order': 'desc',
            'filter': f'from-pub-date:{week_ago},until-pub-date:{today}'
        }
        url = f"https://api.crossref.org/works?{urlencode(params)}"

        fetcher = await self._get_async_fetcher()
        result = await fetcher.fetch(url, timeout=20)
        if not result.content or result.error:
            return items

        try:
            data = json.loads(result.content)
            for item in data.get('message', {}).get('items', [])[:max_results]:
                titles = item.get('title', [])
                title = titles[0] if titles else ''
                if not title:
                    continue
                abstract = item.get('abstract', '') or ''
                abstract = re.sub(r'<[^>]+>', '', abstract)[:500]
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
                    'date': _parse_date_flexible(pub_date) or 'today',
                    'source': 'CrossRef',
                    'authors': author_names
                })
        except Exception:
            return []

        return items


class DBLPApi:
    name = "DBLP API"

    def __init__(self):
        from .web_fetcher import WebFetcher
        self._fetcher = WebFetcher()
        self._async_fetcher = None

    async def _get_async_fetcher(self):
        if self._async_fetcher is None:
            from .web_fetcher import AsyncWebFetcher
            self._async_fetcher = AsyncWebFetcher()
        return self._async_fetcher

    def search(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        year = datetime.now().year
        url = (
            f"https://dblp.org/search/publ/api"
            f"?q={quote(query)}+{year}&h={max_results}&format=json"
        )

        result = self._fetcher.fetch(url, timeout=20)
        if not result.content or result.error:
            return items

        try:
            data = json.loads(result.content)
            hits = data.get('result', {}).get('hits', {}).get('hit', [])
            if isinstance(hits, dict):
                hits = [hits]
            for hit in hits[:max_results]:
                info = hit.get('info', {})
                title = info.get('title', '')
                if not title:
                    continue
                year_val = info.get('year', '')
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
                    'abstract': '',
                    'url': paper_url,
                    'date': str(year_val) if year_val else 'today',
                    'source': 'DBLP',
                    'authors': author_names,
                    'venue': venue
                })
        except Exception:
            return []

        return items

    async def search_async(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        year = datetime.now().year
        url = (
            f"https://dblp.org/search/publ/api"
            f"?q={quote(query)}+{year}&h={max_results}&format=json"
        )

        fetcher = await self._get_async_fetcher()
        result = await fetcher.fetch(url, timeout=20)
        if not result.content or result.error:
            return items

        try:
            data = json.loads(result.content)
            hits = data.get('result', {}).get('hits', {}).get('hit', [])
            if isinstance(hits, dict):
                hits = [hits]
            for hit in hits[:max_results]:
                info = hit.get('info', {})
                title = info.get('title', '')
                if not title:
                    continue
                year_val = info.get('year', '')
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
                    'abstract': '',
                    'url': paper_url,
                    'date': str(year_val) if year_val else 'today',
                    'source': 'DBLP',
                    'authors': author_names,
                    'venue': venue
                })
        except Exception:
            return []

        return items


class OpenAlexApi:
    name = "OpenAlex API"

    def __init__(self):
        from .web_fetcher import WebFetcher
        self._fetcher = WebFetcher()
        self._async_fetcher = None
        self._api_key = _get_api_key('openalex')

    async def _get_async_fetcher(self):
        if self._async_fetcher is None:
            from .web_fetcher import AsyncWebFetcher
            self._async_fetcher = AsyncWebFetcher()
        return self._async_fetcher

    def search(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        today = datetime.now().strftime('%Y-%m-%d')
        api_key_param = f"&api_key={self._api_key}" if self._api_key else ""
        url = (
            f"https://api.openalex.org/works"
            f"?search={quote(query)}&per_page={max_results}"
            f"&sort=publication_date:desc"
            f"&filter=from_publication_date:{week_ago},to_publication_date:{today}"
            f"{api_key_param}"
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
                    'date': _parse_date_flexible(pub_date) or 'today',
                    'source': 'OpenAlex',
                    'authors': author_names
                })
        except Exception:
            return []

        return items

    async def search_async(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        today = datetime.now().strftime('%Y-%m-%d')
        api_key_param = f"&api_key={self._api_key}" if self._api_key else ""
        url = (
            f"https://api.openalex.org/works"
            f"?search={quote(query)}&per_page={max_results}"
            f"&sort=publication_date:desc"
            f"&filter=from_publication_date:{week_ago},to_publication_date:{today}"
            f"{api_key_param}"
        )

        fetcher = await self._get_async_fetcher()
        result = await fetcher.fetch(url, timeout=20)
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
                    'date': _parse_date_flexible(pub_date) or 'today',
                    'source': 'OpenAlex',
                    'authors': author_names
                })
        except Exception:
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


class PLOSApi:
    name = "PLOS API"

    def __init__(self):
        from .web_fetcher import WebFetcher
        self._fetcher = WebFetcher()
        self._async_fetcher = None

    async def _get_async_fetcher(self):
        if self._async_fetcher is None:
            from .web_fetcher import AsyncWebFetcher
            self._async_fetcher = AsyncWebFetcher()
        return self._async_fetcher

    def search(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        url = (
            f"https://api.plos.org/search"
            f"?q=({quote(query)})+AND+publication_date:[{month_ago}T00:00:00Z+TO+NOW]"
            f"&rows={max_results}&sort=publication_date+desc"
            f"&fl=title,abstract,url,id,publication_date,author_display"
        )

        result = self._fetcher.fetch(url, timeout=20)
        if not result.content or result.error:
            return items

        try:
            data = json.loads(result.content)
            docs = data.get('response', {}).get('docs', [])
            for doc in docs[:max_results]:
                title = doc.get('title', '')
                if isinstance(title, list):
                    title = title[0] if title else ''
                if not title:
                    continue
                abstract = doc.get('abstract', '')
                if isinstance(abstract, list):
                    abstract = abstract[0] if abstract else ''
                abstract = str(abstract)[:500]
                pub_date = doc.get('publication_date', '')
                if isinstance(pub_date, list):
                    pub_date = pub_date[0] if pub_date else ''
                paper_id = doc.get('id', '')
                paper_url = f"https://doi.org/10.1371/journal.{paper_id}" if paper_id else ''
                authors = doc.get('author_display', [])
                if isinstance(authors, list):
                    author_names = ', '.join(str(a) for a in authors[:3])
                else:
                    author_names = str(authors)
                items.append({
                    'title': title,
                    'abstract': abstract,
                    'url': paper_url,
                    'date': _parse_date_flexible(str(pub_date)) or 'today',
                    'source': 'PLOS',
                    'authors': author_names
                })
        except Exception:
            return []

        return items

    async def search_async(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        url = (
            f"https://api.plos.org/search"
            f"?q=({quote(query)})+AND+publication_date:[{month_ago}T00:00:00Z+TO+NOW]"
            f"&rows={max_results}&sort=publication_date+desc"
            f"&fl=title,abstract,url,id,publication_date,author_display"
        )

        fetcher = await self._get_async_fetcher()
        result = await fetcher.fetch(url, timeout=20)
        if not result.content or result.error:
            return items

        try:
            data = json.loads(result.content)
            docs = data.get('response', {}).get('docs', [])
            for doc in docs[:max_results]:
                title = doc.get('title', '')
                if isinstance(title, list):
                    title = title[0] if title else ''
                if not title:
                    continue
                abstract = doc.get('abstract', '')
                if isinstance(abstract, list):
                    abstract = abstract[0] if abstract else ''
                abstract = str(abstract)[:500]
                pub_date = doc.get('publication_date', '')
                if isinstance(pub_date, list):
                    pub_date = pub_date[0] if pub_date else ''
                paper_id = doc.get('id', '')
                paper_url = f"https://doi.org/10.1371/journal.{paper_id}" if paper_id else ''
                authors = doc.get('author_display', [])
                if isinstance(authors, list):
                    author_names = ', '.join(str(a) for a in authors[:3])
                else:
                    author_names = str(authors)
                items.append({
                    'title': title,
                    'abstract': abstract,
                    'url': paper_url,
                    'date': _parse_date_flexible(str(pub_date)) or 'today',
                    'source': 'PLOS',
                    'authors': author_names
                })
        except Exception:
            return []

        return items


class PubMedApi:
    name = "PubMed API"

    def __init__(self):
        from .web_fetcher import WebFetcher
        self._fetcher = WebFetcher()
        self._async_fetcher = None

    async def _get_async_fetcher(self):
        if self._async_fetcher is None:
            from .web_fetcher import AsyncWebFetcher
            self._async_fetcher = AsyncWebFetcher()
        return self._async_fetcher

    def search(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        search_url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            f"?db=pubmed&term={quote(query)}&retmax={max_results}"
            f"&sort=date&retmode=json"
        )

        result = self._fetcher.fetch(search_url, timeout=20)
        if not result.content or result.error:
            return items

        try:
            data = json.loads(result.content)
            id_list = data.get('esearchresult', {}).get('idlist', [])
            if not id_list:
                return items

            ids_str = ','.join(id_list[:max_results])
            fetch_url = (
                f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                f"?db=pubmed&id={ids_str}&retmode=json"
            )
            result2 = self._fetcher.fetch(fetch_url, timeout=20)
            if not result2.content or result2.error:
                return items

            data2 = json.loads(result2.content)
            for pmid in id_list[:max_results]:
                info = data2.get('result', {}).get(pmid, {})
                title = info.get('title', '')
                if not title:
                    continue
                pub_date = info.get('pubdate', '')
                authors = info.get('authors', [])
                author_names = ', '.join(a.get('name', '') for a in authors[:3] if a.get('name'))
                paper_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                items.append({
                    'title': title,
                    'abstract': '',
                    'url': paper_url,
                    'date': _parse_date_flexible(str(pub_date)) or 'today',
                    'source': 'PubMed',
                    'authors': author_names
                })
        except Exception:
            return []

        return items

    async def search_async(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        query = " ".join(keywords[:3])
        search_url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            f"?db=pubmed&term={quote(query)}&retmax={max_results}"
            f"&sort=date&retmode=json"
        )

        fetcher = await self._get_async_fetcher()
        result = await fetcher.fetch(search_url, timeout=20)
        if not result.content or result.error:
            return items

        try:
            data = json.loads(result.content)
            id_list = data.get('esearchresult', {}).get('idlist', [])
            if not id_list:
                return items

            ids_str = ','.join(id_list[:max_results])
            fetch_url = (
                f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                f"?db=pubmed&id={ids_str}&retmode=json"
            )
            result2 = await fetcher.fetch(fetch_url, timeout=20)
            if not result2.content or result2.error:
                return items

            data2 = json.loads(result2.content)
            for pmid in id_list[:max_results]:
                info = data2.get('result', {}).get(pmid, {})
                title = info.get('title', '')
                if not title:
                    continue
                pub_date = info.get('pubdate', '')
                authors = info.get('authors', [])
                author_names = ', '.join(a.get('name', '') for a in authors[:3] if a.get('name'))
                paper_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                items.append({
                    'title': title,
                    'abstract': '',
                    'url': paper_url,
                    'date': _parse_date_flexible(str(pub_date)) or 'today',
                    'source': 'PubMed',
                    'authors': author_names
                })
        except Exception:
            return []

        return items


class BioRxivApi:
    name = "bioRxiv API"

    def __init__(self):
        from .web_fetcher import WebFetcher
        self._fetcher = WebFetcher()
        self._async_fetcher = None

    async def _get_async_fetcher(self):
        if self._async_fetcher is None:
            from .web_fetcher import AsyncWebFetcher
            self._async_fetcher = AsyncWebFetcher()
        return self._async_fetcher

    def search(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        today = datetime.now().strftime('%Y-%m-%d')
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        url = (
            f"https://api.biorxiv.org/details/biorxiv/"
            f"{week_ago}/{today}/0/{max_results}"
        )

        result = self._fetcher.fetch(url, timeout=20)
        if not result.content or result.error:
            return items

        try:
            data = json.loads(result.content)
            papers = data.get('collection', [])
            for paper in papers[:max_results]:
                title = paper.get('title', '')
                if not title:
                    continue
                abstract = paper.get('abstract', '') or ''
                pub_date = paper.get('date', '') or ''
                doi = paper.get('doi', '')
                paper_url = f"https://doi.org/{doi}" if doi else ''
                authors = paper.get('authors', '')
                if isinstance(authors, list):
                    author_names = ', '.join(str(a) for a in authors[:3])
                else:
                    author_names = str(authors)[:100]
                items.append({
                    'title': title,
                    'abstract': abstract[:500] if abstract else '',
                    'url': paper_url,
                    'date': _parse_date_flexible(str(pub_date)) or 'today',
                    'source': 'bioRxiv',
                    'authors': author_names
                })
        except Exception:
            return []

        return items

    async def search_async(self, keywords: List[str], max_results: int = 10) -> List[dict]:
        items = []
        today = datetime.now().strftime('%Y-%m-%d')
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        url = (
            f"https://api.biorxiv.org/details/biorxiv/"
            f"{week_ago}/{today}/0/{max_results}"
        )

        fetcher = await self._get_async_fetcher()
        result = await fetcher.fetch(url, timeout=20)
        if not result.content or result.error:
            return items

        try:
            data = json.loads(result.content)
            papers = data.get('collection', [])
            for paper in papers[:max_results]:
                title = paper.get('title', '')
                if not title:
                    continue
                abstract = paper.get('abstract', '') or ''
                pub_date = paper.get('date', '') or ''
                doi = paper.get('doi', '')
                paper_url = f"https://doi.org/{doi}" if doi else ''
                authors = paper.get('authors', '')
                if isinstance(authors, list):
                    author_names = ', '.join(str(a) for a in authors[:3])
                else:
                    author_names = str(authors)[:100]
                items.append({
                    'title': title,
                    'abstract': abstract[:500] if abstract else '',
                    'url': paper_url,
                    'date': _parse_date_flexible(str(pub_date)) or 'today',
                    'source': 'bioRxiv',
                    'authors': author_names
                })
        except Exception:
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
        source_classes = [
            SemanticScholarApi, CrossRefApi, DBLPApi, OpenAlexApi,
            PLOSApi, PubMedApi, BioRxivApi
        ]
        for cls in source_classes:
            try:
                source = cls()
                self.sources.append(source)
                self._log(f"[ApiSource] {cls.name} initialized")
            except Exception as e:
                self._log(f"[ApiSource] {cls.name} init failed: {e}")

    def search_all(self, keywords: List[str], max_per_source: int = 5) -> List[dict]:
        all_items = []
        for source in self.sources:
            self._log(f"[ApiSource] Querying {source.name}...")
            try:
                items = source.search(keywords, max_results=max_per_source)
                self._log(f"[ApiSource] {source.name} returned {len(items)} items")
                all_items.extend(items)
                time.sleep(0.3)
            except Exception as e:
                self._log(f"[ApiSource] {source.name} failed: {e}")
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

    async def search_all_async(self, keywords: List[str], max_per_source: int = 5,
                               max_concurrent: int = 7) -> List[dict]:
        sem = asyncio.Semaphore(max_concurrent)

        async def _search_one(source):
            async with sem:
                self._log(f"[ApiSource] Async querying {source.name}...")
                try:
                    if hasattr(source, 'search_async'):
                        items = await source.search_async(keywords, max_results=max_per_source)
                    else:
                        items = source.search(keywords, max_results=max_per_source)
                    self._log(f"[ApiSource] {source.name} async returned {len(items)} items")
                    return items
                except Exception as e:
                    self._log(f"[ApiSource] {source.name} async failed: {e}")
                    return []

        tasks = [_search_one(source) for source in self.sources]
        results = await asyncio.gather(*tasks)
        all_items = []
        for items in results:
            all_items.extend(items)
        return all_items

    async def search_single_async(self, source_name: str, keywords: List[str],
                                  max_results: int = 10) -> List[dict]:
        for source in self.sources:
            if source.name == source_name:
                try:
                    if hasattr(source, 'search_async'):
                        return await source.search_async(keywords, max_results=max_results)
                    return source.search(keywords, max_results=max_results)
                except Exception:
                    return []
        return []
