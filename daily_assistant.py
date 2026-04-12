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
from password_crypto import PasswordCrypto
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
    else:
        return Path(__file__).parent

def get_config_dir():
    return get_base_dir()

CONFIG_DIR = get_config_dir()
DATA_DIR = CONFIG_DIR / "data"
LOG_DIR = CONFIG_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config():
    from config_manager import ConfigManager
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

from web_fetcher import WebFetcher, FetchResult
from html_parser import HtmlParser
from api_sources import ApiSourceManager


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

    def generate_academic_report(self, items, max_items=10):
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
        crawler = InfoCrawler()
        all_keywords = config.get('keywords', []) + config.get('keywords_cn', [])
        items = crawler.crawl_all(config['news_sources'], keywords=all_keywords)

        processor = InfoProcessor(config['keywords'])
        report = processor.generate_academic_report(
            items,
            max_items=config.get('max_items_per_source', 10)
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
            email_sender.send_report(report, report_file)

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


if __name__ == "__main__":
    main()
