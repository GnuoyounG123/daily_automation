#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Automation Assistant - with concurrent crawling and date filtering
"""

import os
import sys
import json
import time
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, quote
import urllib.request
import urllib.error
import smtplib
from concurrent.futures import ThreadPoolExecutor, as_completed
from .password_crypto import PasswordCrypto
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

if sys.platform == 'win32':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    if sys.stdout:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]

def get_config_dir():
    if getattr(sys, 'frozen', False):
        return get_base_dir()
    return get_base_dir() / "runtime_local"

CONFIG_DIR = get_config_dir()
DATA_DIR = CONFIG_DIR / "data"
LOG_DIR = CONFIG_DIR / "logs"

CONFIG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config():
    from .config_manager import ConfigManager
    cm = ConfigManager(CONFIG_DIR)
    config = cm.get_config()
    if not config:
        config = cm.reset_to_default()
    return config


def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def log_message(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y%m%d')}.log"
    log_entry = f"[{timestamp}] [{level}] {message}" + "\n"
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    safe_print(log_entry.strip())


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        safe_text = text.encode('gbk', errors='replace').decode('gbk')
        print(safe_text)


# ============ Date Filtering ============

def is_recent_article(date_str, max_days=7):
    if not date_str or date_str in ('N/A', 'today', ''):
        return True
    try:
        clean = re.sub(r'[TtZz].*$', '', str(date_str)).strip()
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d']:
            try:
                d = datetime.strptime(clean[:10], fmt)
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


def filter_recent_items(items, max_days=7):
    recent = []
    for item in items:
        date_str = item.get('date', '')
        if is_recent_article(date_str, max_days):
            recent.append(item)
    return recent


# ============ Weather API ============

class WeatherAPI:
    FREE_API_URL = "https://wttr.in/{city}?format=j1"

    @staticmethod
    def get_weather(city="Beijing"):
        try:
            url = WeatherAPI.FREE_API_URL.format(city=city)
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            return WeatherAPI._parse_weather_data(data)
        except Exception as e:
            log_message(f"Weather API failed: {e}", "WARNING")
            return None

    @staticmethod
    def _parse_temperature(value):
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _get_clothing_advice(temp_C):
        temp = WeatherAPI._parse_temperature(temp_C)
        if temp is None:
            return "暂无穿衣建议"
        if temp < 10:
            return "天气较凉，建议穿厚外套"
        if temp < 20:
            return "天气温和，适合正常穿着"
        if temp < 28:
            return "天气暖和，适合轻便穿着"
        return "天气炎热，注意防晒补水"

    @staticmethod
    def _parse_weather_data(data):
        try:
            current = data.get('current_condition', [{}])[0]
            weather_desc = current.get('weatherDesc', [{}])[0].get('value', '未知')
            temp_C = current.get('temp_C', '?')
            feelsLike_C = current.get('FeelsLikeC', '?')
            humidity = current.get('humidity', '?')
            wind_speed = current.get('windspeedKmph', '?')
            wind_dir = current.get('winddir16Point', '?')
            uv_index = current.get('uvIndex', '?')

            穿衣建议 = WeatherAPI._get_clothing_advice(temp_C)

            tomorrow = data.get('weather', [{}])[1] if len(data.get('weather', [])) > 1 else {}
            tomorrow_desc = ""
            if tomorrow:
                tomorrow_desc = tomorrow.get('weatherDesc', [{}])[0].get('value', '')

            return {
                'desc': weather_desc,
                'temp': temp_C,
                'feels_like': feelsLike_C,
                'humidity': humidity,
                'wind_speed': wind_speed,
                'wind_dir': wind_dir,
                'uv_index': uv_index,
                '穿衣建议': 穿衣建议,
                'tomorrow_desc': tomorrow_desc
            }
        except Exception as e:
            log_message(f"Weather parse failed: {e}", "WARNING")
            return None

    @staticmethod
    def format_weather_section(weather):
        if not weather:
            return ""
        return f"""
## 今日天气

| 项目 | 详情 |
|------|------|
| 天气 | {weather['desc']} |
| 温度 | {weather['temp']}°C (体感 {weather['feels_like']}°C) |
| 湿度 | {weather['humidity']}% |
| 风速 | {weather['wind_speed']} km/h ({weather['wind_dir']}) |
| UV指数 | {weather['uv_index']} |
| 穿衣建议 | {weather['穿衣建议']} |

> 明日天气: {weather.get('tomorrow_desc', '暂无预报')}

"""

    @staticmethod
    def format_weather_html(weather):
        if not weather:
            return ""
        emoji_map = {
            'Sunny': '☀️', 'Clear': '☀️', 'Partly cloudy': '⛅', 'Cloudy': '☁️',
            'Overcast': '☁️', 'Mist': '🌫️', 'Fog': '🌫️', 'Light rain': '🌧️',
            'Moderate rain': '🌧️', 'Heavy rain': '⛈️', 'Thunderstorm': '⛈️',
            'Snow': '❄️', 'Light snow': '🌨️', 'Sleet': '🌨️'
        }
        emoji = emoji_map.get(weather['desc'], '🌤️')
        return f"""
<div class="weather-section">
    <div class="section-title"><span class="section-icon">🌤️</span>今日天气</div>
    <div class="weather-card">
        <div class="weather-main">
            <span class="weather-emoji">{emoji}</span>
            <span class="weather-temp">{weather['temp']}°C</span>
            <span class="weather-desc">{weather['desc']}</span>
        </div>
        <div class="weather-details">
            <span>💧 湿度 {weather['humidity']}%</span>
            <span>💨 风速 {weather['wind_speed']} km/h</span>
            <span>☀️ UV指数 {weather['uv_index']}</span>
        </div>
        <div class="weather-advice">👔 {weather['穿衣建议']}</div>
        <div class="weather-tomorrow">📅 明日: {weather.get('tomorrow_desc', '暂无预报')}</div>
    </div>
</div>
"""


# ============ Translator ============

class Translator:
    enabled = True

    TERM_DICT = {
        "artificial intelligence": "人工智能",
        "machine learning": "机器学习",
        "deep learning": "深度学习",
        "neural network": "神经网络",
        "natural language processing": "自然语言处理",
        "computer vision": "计算机视觉",
        "reinforcement learning": "强化学习",
        "supervised learning": "监督学习",
        "unsupervised learning": "无监督学习",
        "generative model": "生成模型",
        "transformer": "Transformer架构",
        "large language model": "大语言模型",
        "artificial general intelligence": "通用人工智能",
        "algorithm": "算法",
        "dataset": "数据集",
        "training": "训练",
        "inference": "推理",
        "optimization": "优化",
        "big data": "大数据",
        "data mining": "数据挖掘",
        "data governance": "数据治理",
        "data privacy": "数据隐私",
        "public governance": "公共治理",
        "digital governance": "数字治理",
        "e-government": "电子政务",
        "smart city": "智慧城市",
        "urban governance": "城市治理",
        "policy": "政策",
        "regulation": "监管",
        "transparency": "透明度",
        "accountability": "问责制",
        "citizen participation": "公民参与",
        "empirical study": "实证研究",
        "case study": "案例研究",
        "comparative analysis": "比较分析",
        "quantitative research": "定量研究",
        "qualitative research": "定性研究",
        "literature review": "文献综述",
        "framework": "框架",
        "methodology": "方法论",
        "abstract": "摘要",
        "introduction": "引言",
        "conclusion": "结论",
        "results": "结果",
        "discussion": "讨论",
        "implications": "启示",
        "challenges": "挑战",
        "opportunities": "机遇",
        "innovation": "创新",
        "sustainable": "可持续的"
    }

    @classmethod
    def translate_text(cls, text):
        if not text or not isinstance(text, str):
            return text
        if not cls.enabled:
            return text
        translated = text.lower()
        for en_term, cn_term in sorted(cls.TERM_DICT.items(), key=lambda x: -len(x[0])):
            translated = translated.replace(en_term.lower(), cn_term)
        if translated == text.lower() and not any(cn in translated for cn in cls.TERM_DICT.values()):
            return f"{text} [待译]"
        return translated.capitalize() if text[0].isupper() else translated

    @classmethod
    def translate_title(cls, title):
        if not title:
            return title
        translated = cls.translate_text(title)
        redundant = ["a ", "an ", "the ", "study on ", "research on ", "analysis of ", "towards ", "for "]
        result = translated
        for r in redundant:
            result = result.replace(r, "")
            result = result.replace(r.capitalize(), "")
        return result.strip()

    @classmethod
    def extract_essence(cls, text, max_length=200):
        if not text:
            return "No abstract available" if not cls.enabled else "暂无摘要"
        if not cls.enabled:
            if len(text) <= max_length:
                return text
            truncated = text[:max_length]
            last_period = truncated.rfind('.')
            if last_period > max_length * 0.7:
                return truncated[:last_period + 1] + ".."
            return truncated + "..."
        translated = cls.translate_text(text)
        sentences = re.split(r'[.!?。！？]+', translated)
        essence = []
        for sent in sentences[:2]:
            sent = sent.strip()
            if len(sent) > 20:
                essence.append(sent)
            if sum(len(s) for s in essence) >= max_length:
                break
        result = '。'.join(essence)
        if len(result) > max_length:
            result = result[:max_length] + "..."
        return result if result else translated[:max_length] + "..."


# ============ Crawler ============

from .web_fetcher import WebFetcher, FetchResult
from .html_parser import HtmlParser
from .api_sources import ApiSourceManager


class InfoCrawler:

    JS_REQUIRED_DOMAINS = [
        'semanticscholar.org', 'aminer.cn', 'scholar.google.com',
        'connectedpapers.com', 'researchgate.net',
    ]

    API_DOMAIN_MAP = {
        'semanticscholar.org': 'Semantic Scholar API',
        'dblp.org': 'DBLP API',
        'openalex.org': 'OpenAlex API',
        'crossref.org': 'CrossRef API',
        'plos.org': 'PLOS API',
        'ncbi.nlm.nih.gov': 'PubMed API',
        'biorxiv.org': 'bioRxiv API',
    }

    def __init__(self):
        self.fetcher = WebFetcher()
        self.parser = HtmlParser()
        self.api_manager = ApiSourceManager()
        self.failed_sources = []
        self._crawl_logs = []

        for log_msg in self.fetcher.get_logs():
            log_message(log_msg, "INFO")
        for log_msg in self.parser.get_logs():
            log_message(log_msg, "INFO")
        for log_msg in self.api_manager.get_logs():
            log_message(log_msg, "INFO")

    def _log(self, msg, level="INFO"):
        self._crawl_logs.append(f"[{level}] {msg}")
        log_message(msg, level)

    def get_failed_sources(self):
        return self.failed_sources

    def _needs_js(self, url):
        domain = urlparse(url).netloc.lower()
        return any(d in domain for d in self.JS_REQUIRED_DOMAINS)

    def _has_api(self, url):
        domain = urlparse(url).netloc.lower()
        for api_domain, api_name in self.API_DOMAIN_MAP.items():
            if api_domain in domain:
                return api_name
        return None

    def _try_api_fallback(self, source, keywords):
        api_name = self._has_api(source['url'])
        if not api_name:
            return []
        self._log(f"[API] Trying {api_name} for {source['name']}")
        try:
            items = self.api_manager.search_single(api_name, keywords, max_results=10)
            if items:
                self._log(f"[API] {api_name} got {len(items)} items")
                return items
        except Exception as e:
            self._log(f"[API] {api_name} failed: {e}", "WARNING")
        return []

    def _try_static_crawl(self, source):
        self._log(f"[Static] Fetching {source['name']}")
        result = self.fetcher.fetch(source['url'], timeout=15)

        if not result.content or result.error:
            self._log(f"[Static] All backends failed: {result.error}", "WARNING")
            return []

        content = result.content
        source_type = source.get('type', 'web')
        items = []

        if source_type == 'rss':
            is_arxiv = 'arxiv' in source['url'].lower()
            items = self.parser.parse_rss(content, source['name'], is_arxiv=is_arxiv)
        elif source_type == 'json':
            items = self.parser.parse_json(content, source['name'])
        elif source_type == 'web':
            items = self.parser.parse(content, source['url'], source['name'])

        if items:
            self._log(f"[Static] Parsed {len(items)} items")
        else:
            self._log(f"[Static] No valid results", "WARNING")

        return items

    def _try_js_crawl(self, source):
        self._log(f"[JS] Trying Selenium for {source['name']}")
        try:
            result = self.fetcher.fetch_with_js(source['url'], timeout=30, wait_seconds=5)
            if not result.content or result.error:
                self._log(f"[JS] Selenium failed: {result.error}", "WARNING")
                return []
            items = self.parser.parse(result.content, source['url'], source['name'])
            if items:
                self._log(f"[JS] Parsed {len(items)} items")
            else:
                self._log(f"[JS] No valid results", "WARNING")
            return items
        except Exception as e:
            self._log(f"[JS] Exception: {e}", "ERROR")
            return []

    def _mark_failed(self, source, reason=""):
        failed_info = {
            'name': source['name'],
            'url': source['url'],
            'type': source.get('type', 'web'),
            'reason': reason,
            'suggestion': self._get_manual_suggestion(source)
        }
        self.failed_sources.append(failed_info)
        self._log(f"[FAIL] {source['name']}: {reason}", "ERROR")

    def _get_manual_suggestion(self, source):
        domain = urlparse(source['url']).netloc.lower()
        suggestions = {
            'semanticscholar.org': 'Semantic Scholar has a public API, consider configuring an API Key',
            'aminer.cn': 'AMiner requires JS rendering, consider changing source type to "api"',
            'thegradient.pub': 'Consider checking if the RSS feed is available',
        }
        for d, s in suggestions.items():
            if d in domain:
                return s
        return 'Check URL or manually input academic information'

    def crawl_source(self, source, keywords=None):
        source_name = source['name']
        source_url = source['url']
        source_type = source.get('type', 'web')

        self._log(f"Crawling: {source_name} ({source_url})")

        if keywords is None:
            keywords = []

        items = []

        if source_type == 'api':
            self._log(f"[API] Using API mode for {source_name}")
            api_name = self._has_api(source_url)
            if api_name:
                items = self.api_manager.search_single(api_name, keywords, max_results=10)
            else:
                items = self.api_manager.search_all(keywords, max_per_source=5)
            if items:
                self._log(f"{source_name} API got {len(items)} items")
                return items
            self._log(f"[API] No results, trying other strategies", "WARNING")
            return items

        if source_type == 'rss':
            items = self._try_static_crawl(source)
            if items:
                self._log(f"{source_name} got {len(items)} items")
                return items
            self._mark_failed(source, "RSS parse failed")
            return []

        if source_type == 'json':
            items = self._try_static_crawl(source)
            if items:
                self._log(f"{source_name} got {len(items)} items")
                return items
            self._mark_failed(source, "JSON parse failed")
            return []

        if source_type == 'web':
            if self._has_api(source_url):
                items = self._try_api_fallback(source, keywords)
                if items:
                    self._log(f"{source_name} API fallback got {len(items)} items")
                    return items

            items = self._try_static_crawl(source)
            if items:
                self._log(f"{source_name} static got {len(items)} items")
                return items

            if self._needs_js(source_url):
                items = self._try_js_crawl(source)
                if items:
                    self._log(f"{source_name} JS got {len(items)} items")
                    return items

            self._mark_failed(source, "All strategies failed")
            return []

        self._mark_failed(source, f"Unknown type: {source_type}")
        return []

    def crawl_all(self, sources, keywords=None):
        enabled_sources = [s for s in sources if s.get('enabled', True)]
        log_message(f"Starting crawl of {len(enabled_sources)} sources...")

        if keywords is None:
            keywords = []

        all_items = []
        max_workers = min(4, len(enabled_sources))

        if max_workers <= 1 or len(enabled_sources) <= 2:
            for source in enabled_sources:
                items = self.crawl_source(source, keywords=keywords)
                all_items.extend(items)
                time.sleep(0.5)
        else:
            def _crawl_one(source):
                try:
                    return self.crawl_source(source, keywords=keywords)
                except Exception as e:
                    self._log(f"Error crawling {source['name']}: {e}", "ERROR")
                    return []

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_source = {
                    executor.submit(_crawl_one, source): source
                    for source in enabled_sources
                }
                for future in as_completed(future_to_source):
                    source = future_to_source[future]
                    try:
                        items = future.result()
                        all_items.extend(items)
                    except Exception as e:
                        self._log(f"Error getting results from {source['name']}: {e}", "ERROR")

        all_items = filter_recent_items(all_items, max_days=7)

        failed_count = len(self.failed_sources)
        log_message(f"Crawl complete: {len(all_items)} recent articles")
        if failed_count > 0:
            log_message(f"WARNING: {failed_count} sources failed", "WARNING")

        return all_items

    async def crawl_source_async(self, source, keywords=None):
        source_name = source['name']
        source_url = source['url']
        source_type = source.get('type', 'web')

        self._log(f"[Async] Crawling: {source_name} ({source_url})")

        if keywords is None:
            keywords = []

        items = []

        if source_type == 'api':
            self._log(f"[Async] Using API mode for {source_name}")
            api_name = self._has_api(source_url)
            if api_name:
                items = await self.api_manager.search_single_async(api_name, keywords, max_results=10)
            else:
                items = await self.api_manager.search_all_async(keywords, max_per_source=5)
            if items:
                self._log(f"{source_name} async API got {len(items)} items")
                return items
            self._log(f"[Async] API no results", "WARNING")
            return items

        if source_type in ('rss', 'json', 'web'):
            items = await self._try_static_crawl_async(source)
            if items:
                self._log(f"{source_name} async got {len(items)} items")
                return items
            if source_type in ('rss', 'json'):
                self._mark_failed(source, f"{source_type.upper()} parse failed")
                return []

        if source_type == 'web':
            if self._has_api(source_url):
                items = await self._try_api_fallback_async(source, keywords)
                if items:
                    self._log(f"{source_name} async API fallback got {len(items)} items")
                    return items

            self._mark_failed(source, "All strategies failed")
            return []

        self._mark_failed(source, f"Unknown type: {source_type}")
        return []

    async def _try_static_crawl_async(self, source):
        self._log(f"[Async] Fetching {source['name']}")
        from .web_fetcher import AsyncWebFetcher
        async_fetcher = AsyncWebFetcher()
        result = await async_fetcher.fetch(source['url'], timeout=15)

        if not result.content or result.error:
            self._log(f"[Async] Fetch failed: {result.error}", "WARNING")
            return []

        content = result.content
        source_type = source.get('type', 'web')
        items = []

        if source_type == 'rss':
            is_arxiv = 'arxiv' in source['url'].lower()
            items = self.parser.parse_rss(content, source['name'], is_arxiv=is_arxiv)
        elif source_type == 'json':
            items = self.parser.parse_json(content, source['name'])
        elif source_type == 'web':
            items = self.parser.parse(content, source['url'], source['name'])

        if items:
            self._log(f"[Async] Parsed {len(items)} items")
        else:
            self._log(f"[Async] No valid results", "WARNING")

        return items

    async def _try_api_fallback_async(self, source, keywords):
        api_name = self._has_api(source['url'])
        if not api_name:
            return []
        self._log(f"[Async] API {api_name} for {source['name']}")
        try:
            items = await self.api_manager.search_single_async(api_name, keywords, max_results=10)
            if items:
                self._log(f"[Async] {api_name} got {len(items)} items")
                return items
        except Exception as e:
            self._log(f"[Async] {api_name} failed: {e}", "WARNING")
        return []

    async def crawl_all_async(self, sources, keywords=None):
        enabled_sources = [s for s in sources if s.get('enabled', True)]
        log_message(f"[Async] Starting crawl of {len(enabled_sources)} sources...")

        if keywords is None:
            keywords = []

        sem = asyncio.Semaphore(4)

        async def _crawl_one(source):
            async with sem:
                try:
                    return await self.crawl_source_async(source, keywords=keywords)
                except Exception as e:
                    self._log(f"Error async crawling {source['name']}: {e}", "ERROR")
                    return []

        tasks = [_crawl_one(source) for source in enabled_sources]
        results = await asyncio.gather(*tasks)

        all_items = []
        for items in results:
            all_items.extend(items)

        all_items = filter_recent_items(all_items, max_days=7)

        failed_count = len(self.failed_sources)
        log_message(f"[Async] Crawl complete: {len(all_items)} recent articles")
        if failed_count > 0:
            log_message(f"WARNING: {failed_count} sources failed", "WARNING")

        return all_items


# ============ Info Processor ============

class InfoProcessor:

    def __init__(self, keywords):
        self.keywords = [k.lower() for k in keywords]

    def calculate_relevance(self, item):
        title = item.get('title', '').lower()
        abstract = item.get('abstract', '').lower()
        combined = title + ' ' + abstract

        score = 0
        matched = []

        for kw in self.keywords:
            if kw in title:
                score += 3
                matched.append(kw)
            elif kw in abstract:
                score += 1
                matched.append(kw)

        return score, list(set(matched))

    def filter_and_rank(self, items):
        scored_items = []

        for item in items:
            score, matched = self.calculate_relevance(item)
            if score > 0:
                item['relevance_score'] = score
                item['matched_keywords'] = matched
                scored_items.append(item)
            else:
                item['relevance_score'] = 0
                item['matched_keywords'] = []
                scored_items.append(item)

        scored_items.sort(key=lambda x: x['relevance_score'], reverse=True)
        return scored_items

    def format_paper_entry(self, item, index):
        is_english = not Translator.enabled

        if is_english:
            title_display = item.get('title', 'No Title')
            essence = Translator.extract_essence(item.get('abstract', ''), max_length=250)
            keywords_matched = item.get('matched_keywords', [])
        else:
            title_display = Translator.translate_title(item.get('title', '无标题'))
            essence = Translator.extract_essence(item.get('abstract', ''), max_length=250)
            keywords_matched = [Translator.translate_text(k) for k in item.get('matched_keywords', [])]

        if is_english:
            entry = f"""### {index}. {title_display}

**Source**: {item.get('source', 'Unknown')} | **Date**: {item.get('date', 'Unknown')}

**Abstract**:
{essence}

**Keywords**: {', '.join(keywords_matched) if keywords_matched else 'General'}

**Link**: [View Paper]({item.get('url', '#')})
"""
            if item.get('github'):
                entry += f"**Code**: [GitHub]({item['github']})" + "\n"
        else:
            entry = f"""### {index}. {title_display}

**来源**：{item.get('source', '未知')} | **日期**：{item.get('date', '未知')}

**核心要点**：
{essence}

**相关领域**：{', '.join(keywords_matched) if keywords_matched else '综合'}

**原文链接**：[点击查看]({item.get('url', '#')})
"""
            if item.get('github'):
                entry += f"**代码实现**：[GitHub]({item['github']})" + "\n"

        entry += "\n---\n\n"
        return entry

    def generate_academic_report(self, items, max_items=10, weather=None):
        is_english = not Translator.enabled

        if is_english:
            today = datetime.now().strftime("%Y-%m-%d")
            now = datetime.now().strftime("%H:%M:%S")

            ranked_items = self.filter_and_rank(items)

            report = f"""# Daily Academic Briefing - {today}

> Generated at: {now}
> Your academic assistant has curated today's latest research

---

## Overview

| Metric | Value |
|--------|-------|
| Sources | {len(set(item.get('source') for item in items))} databases |
| Total Papers | {len(items)} |
| Relevant Papers | {len([i for i in ranked_items if i.get('relevance_score', 0) > 0])} |
| Featured | {min(max_items, len(ranked_items))} |

---

{WeatherAPI.format_weather_section(weather) if weather else ""}
## Featured Papers

"""

            if ranked_items:
                for i, item in enumerate(ranked_items[:max_items], 1):
                    report += self.format_paper_entry(item, i)
            else:
                report += """> No papers found today.

---

"""

            report += """## Source Distribution

"""

            source_counts = {}
            for item in ranked_items[:20]:
                src = item.get('source', 'Other')
                source_counts[src] = source_counts.get(src, 0) + 1

            for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
                bar = '█' * count
                report += f"- **{src}**: {bar} ({count} papers)" + "\n"

            report += """
---

*This briefing was automatically generated*

"""
        else:
            today = datetime.now().strftime("%Y年%m月%d日")
            now = datetime.now().strftime("%H:%M:%S")

            ranked_items = self.filter_and_rank(items)

            report = f"""# 每日学术简报 - {today}

> 生成时间：{now}
> 您的学术助手已为您筛选今日最新研究动态

---

## 数据概览

| 指标 | 数值 |
|------|------|
| 爬取来源 | {len(set(item.get('source') for item in items))}个数据库 |
| 总文献数 | {len(items)} 篇 |
| 相关文献 | {len([i for i in ranked_items if i.get('relevance_score', 0) > 0])} 篇 |
| 精选推荐 | {min(max_items, len(ranked_items))} 篇 |

---

{WeatherAPI.format_weather_section(weather) if weather else ""}
## 重点推荐

"""

            if ranked_items:
                for i, item in enumerate(ranked_items[:max_items], 1):
                    report += self.format_paper_entry(item, i)
            else:
                report += """> 今日暂无最新文献。

---

"""

            report += f"""## 领域分布

基于关键词匹配结果：

"""
            source_counts = {}
            for item in ranked_items[:20]:
                src = item.get('source', '其他')
                source_counts[src] = source_counts.get(src, 0) + 1

            for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
                bar = '█' * count
                report += f"- **{src}**: {bar} ({count}篇)" + "\n"

            report += f"""
---

*本简报由您的学术助手自动生成*

"""

        return report

    def generate_failed_sources_report(self, failed_sources):
        is_english = not Translator.enabled

        if is_english:
            report = f"""
---

## Failed Sources

| Source | URL | Reason | Suggestion |
|--------|-----|--------|------------|
"""
            for fs in failed_sources:
                report += f"| {fs['name']} | {fs['url'][:50]}... | {fs['reason']} | {fs['suggestion']} |" + "\n"
        else:
            report = f"""
---

## 爬取失败源

| 来源 | URL | 失败原因 | 建议 |
|------|-----|----------|------|
"""
            for fs in failed_sources:
                report += f"| {fs['name']} | {fs['url'][:50]}... | {fs['reason']} | {fs['suggestion']} |" + "\n"

        return report

    def save_report(self, report):
        date_str = datetime.now().strftime("%Y%m%d")
        filename = DATA_DIR / f"academic_briefing_{date_str}.md"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)

        log_message(f"Report saved: {filename}")
        return filename


# ============ Email ============

class EmailSender:

    def __init__(self, config):
        self.enabled = config.get('enabled', False)
        self.smtp_server = config.get('smtp_server', 'smtp.qq.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.sender_email = config.get('sender_email', '')
        self.sender_password = self._decode_pwd(config.get('sender_password', ''))
        self.receiver_email = config.get('receiver_email', '')
        self.subject_prefix = config.get('subject_prefix', '[学术简报]')

    @staticmethod
    def _decode_pwd(value: str) -> str:
        if not value:
            return ""
        import base64
        if value.startswith("fernet:"):
            try:
                crypto = PasswordCrypto(Path(__file__).parent)
                return crypto.decrypt(value)
            except Exception:
                return value
        if value.startswith("enc:"):
            try:
                return base64.b64decode(value[4:]).decode('utf-8')
            except Exception:
                return value
        return value

    def send_report(self, report_content, report_file=None):
        if not self.enabled:
            log_message("Email disabled, skipping")
            return False

        if not self.sender_email or not self.sender_password:
            log_message("Email config incomplete", "WARNING")
            return False

        try:
            msg = MIMEMultipart('alternative')
            today = datetime.now().strftime("%Y年%m月%d日")
            msg['Subject'] = Header(f"{self.subject_prefix} {today} 每日学术简报", 'utf-8')
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_email

            html_content = self._convert_markdown_to_html(report_content)

            text_part = MIMEText(report_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')

            msg.attach(text_part)
            msg.attach(html_part)

            log_message(f"Connecting to {self.smtp_server}:{self.smtp_port}...")

            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()

            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.receiver_email, msg.as_string())
            server.quit()

            log_message(f"Email sent to {self.receiver_email}")
            return True

        except Exception as e:
            log_message(f"Email failed: {str(e)}", "ERROR")
            return False

    def _convert_markdown_to_html(self, markdown_content):
        html = markdown_content

        html = html.replace('&', '&amp;')
        html = html.replace('<', '&lt;')
        html = html.replace('>', '&gt;')

        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', html)
        html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html)
        html = re.sub(r'\*(.+?)\*', r'<i>\1</i>', html)

        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

        html = re.sub(r'^---+$', r'<hr>', html, flags=re.MULTILINE)

        html = html.replace('\n', '<br>\n')

        full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; border-bottom: 2px solid #bdc3c7; padding-bottom: 8px; margin-top: 30px; }}
        h3 {{ color: #7f8c8d; margin-top: 25px; }}
        a {{ color: #3498db; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        hr {{ border: none; border-top: 1px solid #ddd; margin: 20px 0; }}
        blockquote {{ border-left: 4px solid #3498db; margin: 0; padding-left: 15px; color: #666; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .content {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
    </style>
</head>
<body>
    <div class="content">
        {html}
    </div>
</body>
</html>"""
        return full_html

    def create_combined_email(self, report, weather, schedule_info, config):
        today = datetime.now().strftime("%Y年%m月%d日")
        greeting = self._get_greeting()

        report_html = self._convert_markdown_to_html(report)
        weather_html = WeatherAPI.format_weather_html(weather) if weather else ""
        schedule_html = self._format_schedule_html(schedule_info)

        combined = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{today} 每日简报</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 700px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 35px 30px;
            text-align: center;
        }}
        .greeting {{
            font-size: 26px;
            font-weight: bold;
            margin-bottom: 8px;
        }}
        .date {{
            font-size: 16px;
            opacity: 0.9;
        }}
        .content {{ padding: 25px 30px; }}
        .report-content {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .report-content h1 {{
            color: #2c3e50;
            font-size: 22px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }}
        .report-content h2 {{
            color: #34495e;
            font-size: 18px;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 8px;
            margin: 20px 0 12px;
        }}
        .report-content h3 {{
            color: #7f8c8d;
            font-size: 15px;
            margin-top: 18px;
        }}
        .report-content a {{ color: #3498db; text-decoration: none; }}
        .report-content table {{
            border-collapse: collapse;
            width: 100%;
            margin: 12px 0;
            font-size: 14px;
        }}
        .report-content th, .report-content td {{
            border: 1px solid #ddd;
            padding: 6px 10px;
            text-align: left;
        }}
        .report-content th {{ background-color: #f2f2f2; }}
        .weather-section .section-title {{
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .weather-card {{
            background: linear-gradient(135deg, #667eea20 0%, #764ba220 100%);
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 20px;
            border: 1px solid #667eea40;
        }}
        .weather-main {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 12px;
        }}
        .weather-emoji {{ font-size: 42px; }}
        .weather-temp {{ font-size: 36px; font-weight: bold; color: #333; }}
        .weather-desc {{ font-size: 18px; color: #666; }}
        .weather-details {{
            display: flex;
            gap: 20px;
            font-size: 14px;
            color: #555;
            margin-bottom: 10px;
        }}
        .weather-advice {{
            font-size: 14px;
            color: #667eea;
            font-weight: bold;
        }}
        .weather-tomorrow {{ font-size: 13px; color: #888; margin-top: 8px; }}
        .schedule-section .section-title {{
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .course-item {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 14px;
            margin-bottom: 10px;
            display: flex;
            gap: 12px;
            align-items: center;
            border-left: 4px solid #667eea;
        }}
        .course-time {{
            background: #667eea;
            color: white;
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: bold;
            white-space: nowrap;
        }}
        .course-name {{ font-size: 15px; font-weight: bold; color: #333; }}
        .course-location {{ font-size: 13px; color: #666; }}
        .empty {{ text-align: center; color: #999; padding: 20px; font-style: italic; }}
        .footer {{
            background: #f8f9fa;
            padding: 18px 30px;
            text-align: center;
            color: #888;
            font-size: 13px;
        }}
        .footer .heart {{ color: #e74c3c; }}
        @media (max-width: 600px) {{
            body {{ padding: 10px; }}
            .content {{ padding: 15px; }}
            .weather-details {{ flex-direction: column; gap: 8px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="greeting">{greeting}</div>
            <div class="date">{today}</div>
        </div>
        <div class="content">
            {weather_html}
            {schedule_html}
            <div class="report-content">
                {report_html}
            </div>
        </div>
        <div class="footer">
            <p>由 Daily Automation 为您生成 <span class="heart">♥</span></p>
        </div>
    </div>
</body>
</html>"""
        return combined

    def _get_greeting(self):
        import random
        greetings = [
            "早安，主人～ 今日份简报已备好",
            "新的一天，新的发现～",
            "为您整理好了今日资讯",
            "今日学术动态，一文掌握"
        ]
        return random.choice(greetings)

    def _format_schedule_html(self, schedule_info):
        if not schedule_info:
            return ""
        courses = schedule_info.get('courses', [])
        weekday_cn = {
            "Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
            "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"
        }
        weekday = schedule_info.get('weekday', '')
        date = schedule_info.get('date', '')
        courses_html = ""
        if courses:
            for course in courses:
                courses_html += f"""
                <div class="course-item">
                    <div class="course-time">{course.get('time', '')}</div>
                    <div>
                        <div class="course-name">{course.get('name', '')}</div>
                        <div class="course-location">📍 {course.get('location', '')}</div>
                    </div>
                </div>
                """
        else:
            courses_html = '<div class="empty">今天没有课程安排～</div>'

        return f"""
<div class="schedule-section">
    <div class="section-title"><span>📚</span>今日课程 ({weekday_cn.get(weekday, weekday)})</div>
    {courses_html}
</div>
"""

    def send_combined_email(self, html_content, report_file=None):
        if not self.enabled:
            log_message("Email disabled, skipping")
            return False

        if not self.sender_email or not self.sender_password:
            log_message("Email config incomplete", "WARNING")
            return False

        try:
            msg = MIMEMultipart('alternative')
            today = datetime.now().strftime("%Y年%m月%d日")
            msg['Subject'] = Header(f"{self.subject_prefix} {today} 每日简报", 'utf-8')
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_email

            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            log_message(f"Connecting to {self.smtp_server}:{self.smtp_port}...")

            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()

            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.receiver_email, msg.as_string())
            server.quit()

            log_message(f"Combined email sent to {self.receiver_email}")
            return True

        except Exception as e:
            log_message(f"Email failed: {str(e)}", "ERROR")
            return False


# ============ Reminders ============

class ReminderSystem:

    def __init__(self, reminders):
        self.reminders = reminders

    def check_reminders(self):
        current_time = datetime.now().strftime("%H:%M")
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute

        current = None
        upcoming = []

        for reminder in self.reminders:
            reminder_time = reminder['time']
            reminder_hour = int(reminder_time.split(':')[0])
            reminder_minute = int(reminder_time.split(':')[1])

            if reminder_time == current_time:
                current = reminder

            if reminder_hour > current_hour or (reminder_hour == current_hour and reminder_minute > current_minute):
                if reminder_hour < current_hour + 2 or (reminder_hour == current_hour + 2 and reminder_minute <= current_minute):
                    upcoming.append(reminder)

        return current, upcoming

    def generate_reminder_output(self, current, upcoming):
        output = []

        if current:
            output.append("""
+--------------------------------------------------------------+
|  Reminder
+--------------------------------------------------------------+
""")
            desc = current['description']
            title = current['title']

            output.append(f"  {title}")
            output.append(f"  {desc}")
            output.append("+--------------------------------------------------------------+")

        if upcoming:
            output.append("""
+--------------------------------------------------------------+
|  Upcoming
+--------------------------------------------------------------+
""")
            for r in upcoming[:3]:
                output.append(f"  {r['time']} - {r['title']}")
            output.append("+--------------------------------------------------------------+")

        return '\n'.join(output) if output else ""

    def save_reminder_log(self, current):
        if current:
            date_str = datetime.now().strftime("%Y%m%d")
            log_file = LOG_DIR / f"reminders_{date_str}.log"

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().isoformat()}] Reminder: {current['title']} - {current['description']}" + "\n")


# ============ Main ============

def main(mode=None):
    log_message("=" * 60)
    log_message("Daily Automation Assistant starting")
    log_message("=" * 60)

    config = load_config()
    log_message("Config loaded")

    translation_config = config.get('translation', {})
    Translator.enabled = translation_config.get('enabled', False)
    log_message(f"Translation: {'on' if Translator.enabled else 'off'}")

    if mode is None:
        mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    log_message(f"Mode: {mode}")

    if mode in ["crawl", "all"]:
        weather = None
        weather_city = config.get('weather_city', 'Beijing')
        try:
            weather = WeatherAPI.get_weather(weather_city)
            if weather:
                log_message(f"Weather: {weather['desc']}, {weather['temp']}°C")
        except Exception as e:
            log_message(f"Weather fetch failed: {e}", "WARNING")

        crawler = InfoCrawler()
        all_keywords = config.get('keywords', []) + config.get('keywords_cn', [])
        items = crawler.crawl_all(config['news_sources'], keywords=all_keywords)

        processor = InfoProcessor(config['keywords'])
        schedule_info = None
        schedule_data = None
        try:
            from .schedule_manager import load_schedule, get_today_schedule
            schedule_data = load_schedule()
            week_tasks = {}
            try:
                tasks_file = CONFIG_DIR / "weekly_tasks.json"
                if tasks_file.exists():
                    with open(tasks_file, 'r', encoding='utf-8') as f:
                        week_tasks = json.load(f)
            except Exception:
                pass
            daily_tasks = week_tasks.get("daily_tasks", {})
            schedule_info = get_today_schedule(schedule_data, daily_tasks)
        except Exception as e:
            log_message(f"Schedule load failed: {e}", "WARNING")

        report = processor.generate_academic_report(
            items,
            max_items=config.get('max_items_per_source', 10),
            weather=weather
        )

        failed_sources = crawler.get_failed_sources()
        if failed_sources:
            failed_report = processor.generate_failed_sources_report(failed_sources)
            report += failed_report

        report_file = processor.save_report(report)
        log_message(f"Report generated: {report_file}")

        email_config = config.get('email', {})
        if email_config.get('enabled', False):
            email_sender = EmailSender(email_config)
            combined_html = email_sender.create_combined_email(
                report=report,
                weather=weather,
                schedule_info=schedule_info,
                config=config
            )
            email_sender.send_combined_email(combined_html, report_file)

        safe_print("\n" + "=" * 60)
        safe_print("Briefing preview (first 3):")
        safe_print("=" * 60)
        lines = report.split('\n')
        preview_lines = []
        count = 0
        for line in lines:
            if line.startswith('###'):
                count += 1
                if count > 3:
                    break
            preview_lines.append(line)
        safe_print('\n'.join(preview_lines))
        safe_print("\n" + "=" * 60)

        if failed_sources:
            safe_print("\n" + "=" * 60)
            safe_print(f"WARNING: {len(failed_sources)} sources failed:")
            for fs in failed_sources:
                safe_print(f"  - {fs['name']}: {fs['reason']}")
            safe_print("=" * 60)

    if mode in ["remind", "all"]:
        reminder_sys = ReminderSystem(config['reminders'])
        current, upcoming = reminder_sys.check_reminders()

        reminder_output = reminder_sys.generate_reminder_output(current, upcoming)
        if reminder_output:
            safe_print(reminder_output)

        reminder_sys.save_reminder_log(current)

    log_message("=" * 60)
    log_message("Daily Automation Assistant complete")
    log_message("=" * 60)


async def main_async(mode=None):
    log_message("=" * 60)
    log_message("Daily Automation Assistant (Async mode) starting")
    log_message("=" * 60)

    config = load_config()
    log_message("Config loaded")

    translation_config = config.get('translation', {})
    Translator.enabled = translation_config.get('enabled', False)
    log_message(f"Translation: {'on' if Translator.enabled else 'off'}")

    if mode is None:
        idx = 1
        if len(sys.argv) > idx and sys.argv[idx] == "--async":
            idx = 2
        mode = sys.argv[idx] if len(sys.argv) > idx else "all"

    log_message(f"Mode: {mode} (async)")

    if mode in ["crawl", "all"]:
        weather = None
        weather_city = config.get('weather_city', 'Beijing')
        try:
            weather = WeatherAPI.get_weather(weather_city)
            if weather:
                log_message(f"Weather: {weather['desc']}, {weather['temp']}°C")
        except Exception as e:
            log_message(f"Weather fetch failed: {e}", "WARNING")

        crawler = InfoCrawler()
        all_keywords = config.get('keywords', []) + config.get('keywords_cn', [])
        items = await crawler.crawl_all_async(config['news_sources'], keywords=all_keywords)

        processor = InfoProcessor(config['keywords'])
        schedule_info = None
        schedule_data = None
        try:
            from .schedule_manager import load_schedule, get_today_schedule
            schedule_data = load_schedule()
            week_tasks = {}
            try:
                tasks_file = CONFIG_DIR / "weekly_tasks.json"
                if tasks_file.exists():
                    with open(tasks_file, 'r', encoding='utf-8') as f:
                        week_tasks = json.load(f)
            except Exception:
                pass
            daily_tasks = week_tasks.get("daily_tasks", {})
            schedule_info = get_today_schedule(schedule_data, daily_tasks)
        except Exception as e:
            log_message(f"Schedule load failed: {e}", "WARNING")

        report = processor.generate_academic_report(
            items,
            max_items=config.get('max_items_per_source', 10),
            weather=weather
        )

        failed_sources = crawler.get_failed_sources()
        if failed_sources:
            failed_report = processor.generate_failed_sources_report(failed_sources)
            report += failed_report

        report_file = processor.save_report(report)
        log_message(f"Report generated: {report_file}")

        email_config = config.get('email', {})
        if email_config.get('enabled', False):
            email_sender = EmailSender(email_config)
            combined_html = email_sender.create_combined_email(
                report=report,
                weather=weather,
                schedule_info=schedule_info,
                config=config
            )
            email_sender.send_combined_email(combined_html, report_file)

        safe_print("\n" + "=" * 60)
        safe_print("Briefing preview (first 3):")
        safe_print("=" * 60)
        lines = report.split('\n')
        preview_lines = []
        count = 0
        for line in lines:
            if line.startswith('###'):
                count += 1
                if count > 3:
                    break
            preview_lines.append(line)
        safe_print('\n'.join(preview_lines))
        safe_print("\n" + "=" * 60)

        if failed_sources:
            safe_print("\n" + "=" * 60)
            safe_print(f"WARNING: {len(failed_sources)} sources failed:")
            for fs in failed_sources:
                safe_print(f"  - {fs['name']}: {fs['reason']}")
            safe_print("=" * 60)

    if mode in ["remind", "all"]:
        reminder_sys = ReminderSystem(config['reminders'])
        current, upcoming = reminder_sys.check_reminders()

        reminder_output = reminder_sys.generate_reminder_output(current, upcoming)
        if reminder_output:
            safe_print(reminder_output)

        reminder_sys.save_reminder_log(current)

    log_message("=" * 60)
    log_message("Daily Automation Assistant (Async mode) complete")
    log_message("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--async":
        asyncio.run(main_async())
    else:
        main()
