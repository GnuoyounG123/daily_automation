#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日自动化助手 - Daily Automation Assistant
功能：学术信息爬取、智能翻译、精华提取、日程提醒
作者：Claude Code
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
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# 设置Windows控制台UTF-8编码（必须在其他输出之前）
if sys.platform == 'win32':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)  # UTF-8
        kernel32.SetConsoleCP(65001)
    except Exception:
        pass  # Windows控制台编码设置失败可忽略
    # 同时设置Python的stdout编码
    if sys.stdout:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ============ 配置区域 ============
# 处理PyInstaller打包环境
def get_base_dir():
    """获取基础目录（exe所在目录，兼容打包环境）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller打包环境：exe所在目录
        return Path(sys.executable).parent
    else:
        # 开发环境：脚本所在目录
        return Path(__file__).parent

def get_config_dir():
    """获取配置文件目录"""
    # 直接使用exe所在目录（打包环境）或源码目录（开发环境）
    # 这确保我们读取用户修改的配置文件，而不是打包时的旧配置
    return get_base_dir()

CONFIG_DIR = get_config_dir()
DATA_DIR = CONFIG_DIR / "data"
LOG_DIR = CONFIG_DIR / "logs"

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config():
    """加载配置文件"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # 创建默认配置
        default_config = {
            "news_sources": [
                {"name": "arXiv AI", "url": "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL&sortBy=submittedDate&sortOrder=descending&max_results=10", "type": "rss", "enabled": True},
                {"name": "Semantic Scholar", "url": "https://www.semanticscholar.org/", "type": "web", "enabled": True},
                {"name": "AMiner", "url": "https://www.aminer.cn/", "type": "web", "enabled": True},
                {"name": "The Gradient", "url": "https://thegradient.pub/", "type": "web", "enabled": True}
            ],
            "reminders": [{"time": "09:00", "title": "学术早报", "description": "主人，您不在的时候，喵去打探了一下外面的世界喵。今日最新学术资讯已整理完毕，请查阅。"}],
            "keywords": ["artificial intelligence", "big data", "public governance", "digital governance"],
            "keywords_cn": ["人工智能", "大数据", "公共治理", "数字治理"],
            "output_format": "markdown",
            "max_items_per_source": 5
        }
        save_config(default_config)
        return default_config


def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def log_message(message, level="INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y%m%d')}.log"
    log_entry = f"[{timestamp}] [{level}] {message}" + "\n"
    # 写入日志文件（UTF-8编码，支持emoji）
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    # 控制台输出（处理GBK编码问题）
    safe_print(log_entry.strip())


def safe_print(text):
    """安全打印，处理Windows控制台编码问题"""
    try:
        print(text)
    except UnicodeEncodeError:
        # 替换无法编码的字符为问号
        safe_text = text.encode('gbk', errors='replace').decode('gbk')
        print(safe_text)


# ============ 翻译模块 ============

class Translator:
    """简易翻译器 - 使用术语词典 + 简单翻译规则"""

    enabled = True  # 全局翻译开关

    # 学术术语词典
    TERM_DICT = {
        # AI/ML术语
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
        # 数据相关
        "big data": "大数据",
        "data mining": "数据挖掘",
        "data governance": "数据治理",
        "data privacy": "数据隐私",
        # 治理术语
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
        # 研究方法
        "empirical study": "实证研究",
        "case study": "案例研究",
        "comparative analysis": "比较分析",
        "quantitative research": "定量研究",
        "qualitative research": "定性研究",
        "literature review": "文献综述",
        "framework": "框架",
        "methodology": "方法论",
        # 一般学术词汇
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
        """翻译文本 - 优先匹配术语，其余保持原样"""
        if not text or not isinstance(text, str):
            return text

        # 如果翻译被禁用，直接返回原文
        if not cls.enabled:
            return text

        # 先进行术语替换（长词优先）
        translated = text.lower()
        for en_term, cn_term in sorted(cls.TERM_DICT.items(), key=lambda x: -len(x[0])):
            translated = translated.replace(en_term.lower(), cn_term)

        # 如果没有被翻译，可能是专有名词，添加[待译]标记
        if translated == text.lower() and not any(cn in translated for cn in cls.TERM_DICT.values()):
            return f"{text} [待译]"

        return translated.capitalize() if text[0].isupper() else translated

    @classmethod
    def translate_title(cls, title):
        """翻译标题 - 提取核心概念"""
        if not title:
            return title

        # 先翻译术语
        translated = cls.translate_text(title)

        # 移除常见的冗余词汇
        redundant = ["a ", "an ", "the ", "study on ", "research on ", "analysis of ", "towards ", "for "]
        result = translated
        for r in redundant:
            result = result.replace(r, "")
            result = result.replace(r.capitalize(), "")

        return result.strip()

    @classmethod
    def extract_essence(cls, text, max_length=200):
        """提取精华 - 关键信息摘要"""
        if not text:
            return "No abstract available" if not cls.enabled else "暂无摘要"

        # 如果翻译被禁用，直接返回原文截断
        if not cls.enabled:
            if len(text) <= max_length:
                return text
            # 尝试在句子边界截断
            truncated = text[:max_length]
            last_period = truncated.rfind('.')
            if last_period > max_length * 0.7:
                return truncated[:last_period + 1] + ".."
            return truncated + "..."

        # 翻译文本
        translated = cls.translate_text(text)

        # 提取关键句（通常第一句最重要）
        sentences = re.split(r'[.!?。！？]+', translated)
        essence = []

        for sent in sentences[:2]:  # 取前两句
            sent = sent.strip()
            if len(sent) > 20:  # 过滤太短的句子
                essence.append(sent)
            if sum(len(s) for s in essence) >= max_length:
                break

        result = '。'.join(essence)
        if len(result) > max_length:
            result = result[:max_length] + "..."

        return result if result else translated[:max_length] + "..."


# ============ 信息爬取模块 ============

from web_fetcher import WebFetcher, FetchResult
from html_parser import HtmlParser
from api_sources import ApiSourceManager


class InfoCrawler:
    """学术信息爬取器 - 多架构自动降级版

    爬取策略降级链:
    1. API优先 - 使用公开API获取数据（最稳定）
    2. 静态爬取 - 多后端HTTP获取 + 多策略HTML解析
    3. JS渲染 - Selenium无头浏览器渲染后解析
    4. 标记失败 - 记录无法爬取的来源，提示用户手动输入
    """

    JS_REQUIRED_DOMAINS = [
        'semanticscholar.org', 'aminer.cn', 'scholar.google.com',
        'connectedpapers.com', 'researchgate.net',
    ]

    API_DOMAIN_MAP = {
        'semanticscholar.org': 'Semantic Scholar API',
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

        self._log(f"[策略1-API] 尝试 {api_name} 获取 {source['name']}")
        try:
            items = self.api_manager.search_single(api_name, keywords, max_results=10)
            if items:
                self._log(f"[策略1-API] {api_name} 成功获取 {len(items)} 条")
                return items
        except Exception as e:
            self._log(f"[策略1-API] {api_name} 失败: {e}", "WARNING")

        return []

    def _try_static_crawl(self, source):
        self._log(f"[策略2-静态] 尝试多后端获取 {source['name']}")
        result = self.fetcher.fetch(source['url'], timeout=15)

        if not result.content or result.error:
            self._log(f"[策略2-静态] 所有HTTP后端获取失败: {result.error}", "WARNING")
            return []

        self._log(f"[策略2-静态] {result.backend_used} 获取成功，尝试多策略解析")
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
            self._log(f"[策略2-静态] 解析成功: {len(items)} 条")
        else:
            self._log(f"[策略2-静态] 所有解析策略均未获得有效结果", "WARNING")

        return items

    def _try_js_crawl(self, source):
        self._log(f"[策略3-JS渲染] 尝试Selenium获取 {source['name']}")
        try:
            result = self.fetcher.fetch_with_js(source['url'], timeout=30, wait_seconds=5)
            if not result.content or result.error:
                self._log(f"[策略3-JS渲染] Selenium获取失败: {result.error}", "WARNING")
                return []

            self._log(f"[策略3-JS渲染] 获取成功，尝试解析")
            items = self.parser.parse(result.content, source['url'], source['name'])
            if items:
                self._log(f"[策略3-JS渲染] 解析成功: {len(items)} 条")
            else:
                self._log(f"[策略3-JS渲染] 解析未获得有效结果", "WARNING")
            return items
        except Exception as e:
            self._log(f"[策略3-JS渲染] 异常: {e}", "ERROR")
            return []

    def _mark_failed(self, source, reason=""):
        api_key_url = self._get_api_key_url(source)
        failed_info = {
            'name': source['name'],
            'url': source['url'],
            'type': source.get('type', 'web'),
            'reason': reason,
            'suggestion': self._get_manual_suggestion(source)
        }
        if api_key_url:
            failed_info['api_key_url'] = api_key_url
        self.failed_sources.append(failed_info)
        self._log(f"[失败] {source['name']} 所有策略均失败: {reason}", "ERROR")

    def _get_api_key_url(self, source):
        domain = urlparse(source['url']).netloc.lower()
        domain_key_map = {
            'semanticscholar.org': 'semantic_scholar',
            'openalex.org': 'openalex',
            'core.ac.uk': 'core',
        }
        for d, key_name in domain_key_map.items():
            if d in domain:
                return self.API_KEY_URLS.get(key_name, '')
        return ''

    API_KEY_URLS = {
        'semantic_scholar': 'https://www.semanticscholar.org/product/api#api-key',
        'openalex': 'https://docs.openalex.org/how-to-use-the-api/get-an-api-key',
        'core': 'https://core.ac.uk/services/api',
    }

    def _get_manual_suggestion(self, source):
        domain = urlparse(source['url']).netloc.lower()
        suggestions = {
            'semanticscholar.org': 'Semantic Scholar有公开API，建议配置API Key以提升配额\n申请链接: https://www.semanticscholar.org/product/api#api-key',
            'aminer.cn': 'AMiner需要JS渲染，建议将源类型改为"api"或手动输入感兴趣的论文信息',
            'thegradient.pub': '建议检查RSS源是否可用，或将源类型改为"rss"',
            'scholar.google.com': 'Google Scholar有反爬机制，建议使用Semantic Scholar API替代\n申请链接: https://www.semanticscholar.org/product/api#api-key',
        }
        for d, s in suggestions.items():
            if d in domain:
                return s
        return '建议检查URL是否正确，或手动输入该源的学术信息'

    def crawl_source(self, source, keywords=None):
        """爬取单个来源 - 多策略自动降级"""
        source_name = source['name']
        source_url = source['url']
        source_type = source.get('type', 'web')

        self._log(f"开始爬取: {source_name} ({source_url})")

        if keywords is None:
            keywords = []

        items = []

        if source_type == 'api':
            self._log(f"[策略1-API] 使用API模式获取 {source_name}")
            api_name = self._has_api(source_url)
            if api_name:
                items = self.api_manager.search_single(api_name, keywords, max_results=10)
            else:
                items = self.api_manager.search_all(keywords, max_per_source=5)
            if items:
                self._log(f"{source_name} API获取 {len(items)} 条")
                return items
            self._log(f"[策略1-API] API未返回结果，尝试其他策略", "WARNING")

        if source_type == 'rss':
            items = self._try_static_crawl(source)
            if items:
                self._log(f"{source_name} 获取 {len(items)} 条")
                return items
            items = self._try_js_crawl(source)
            if items:
                self._log(f"{source_name} JS渲染获取 {len(items)} 条")
                return items
            self._mark_failed(source, "RSS解析失败")
            return []

        if source_type == 'json':
            items = self._try_static_crawl(source)
            if items:
                self._log(f"{source_name} 获取 {len(items)} 条")
                return items
            self._mark_failed(source, "JSON解析失败")
            return []

        if source_type == 'web':
            if self._has_api(source_url):
                items = self._try_api_fallback(source, keywords)
                if items:
                    self._log(f"{source_name} API回退获取 {len(items)} 条")
                    return items

            items = self._try_static_crawl(source)
            if items:
                self._log(f"{source_name} 静态爬取获取 {len(items)} 条")
                return items

            if self._needs_js(source_url):
                items = self._try_js_crawl(source)
                if items:
                    self._log(f"{source_name} JS渲染获取 {len(items)} 条")
                    return items

            self._mark_failed(source, "所有爬取策略均失败")
            return []

        self._mark_failed(source, f"未知的源类型: {source_type}")
        return []

    def crawl_all(self, sources, keywords=None):
        """爬取所有启用的来源"""
        enabled_sources = [s for s in sources if s.get('enabled', True)]
        log_message(f"开始爬取 {len(enabled_sources)} 个学术信息源...")

        if keywords is None:
            keywords = []

        all_items = []
        for source in enabled_sources:
            items = self.crawl_source(source, keywords=keywords)
            all_items.extend(items)
            time.sleep(1.5)

        failed_count = len(self.failed_sources)
        log_message(f"爬取完成，共获取 {len(all_items)} 条学术资讯")
        if failed_count > 0:
            log_message(f"⚠️ {failed_count} 个源爬取失败，需要人工介入", "WARNING")
            for fs in self.failed_sources:
                log_message(f"  失败源: {fs['name']} - {fs['reason']}", "WARNING")
                log_message(f"  建议: {fs['suggestion']}", "WARNING")

        return all_items


# ============ 信息处理模块 ============

class InfoProcessor:
    """学术信息处理器"""

    def __init__(self, keywords):
        self.keywords = [k.lower() for k in keywords]

    def calculate_relevance(self, item):
        """计算文章相关度分数"""
        title = item.get('title', '').lower()
        abstract = item.get('abstract', '').lower()
        combined = title + ' ' + abstract

        score = 0
        matched = []

        for kw in self.keywords:
            if kw in title:
                score += 3  # 标题匹配权重高
                matched.append(kw)
            elif kw in abstract:
                score += 1
                matched.append(kw)

        return score, list(set(matched))

    def filter_and_rank(self, items):
        """过滤并排序文章"""
        scored_items = []

        for item in items:
            score, matched = self.calculate_relevance(item)
            if score > 0:
                item['relevance_score'] = score
                item['matched_keywords'] = matched
                scored_items.append(item)

        # 按相关度降序排序
        scored_items.sort(key=lambda x: x['relevance_score'], reverse=True)
        return scored_items

    def format_paper_entry(self, item, index):
        """格式化单篇论文条目"""
        # 判断是否为英文输出
        is_english = not Translator.enabled

        # 翻译和提取精华
        if is_english:
            title_display = item.get('title', 'No Title')
            essence = Translator.extract_essence(item.get('abstract', ''), max_length=250)
            keywords_matched = item.get('matched_keywords', [])
        else:
            title_display = Translator.translate_title(item.get('title', '无标题'))
            essence = Translator.extract_essence(item.get('abstract', ''), max_length=250)
            keywords_matched = [Translator.translate_text(k) for k in item.get('matched_keywords', [])]

        # 根据语言选择标签
        if is_english:
            entry = f"""### {index}. {title_display}

**Source**: {item.get('source', 'Unknown')} | **Date**: {item.get('date', 'Unknown')}

**Abstract**:
{essence}

**Keywords**: {', '.join(keywords_matched) if keywords_matched else 'General'}

**Link**: [View Paper]({item.get('url', '#')})
"""
            # 如果有GitHub链接
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
            # 如果有GitHub链接
            if item.get('github'):
                entry += f"**代码实现**：[GitHub]({item['github']})" + "\n"

        entry += "\n---\n\n"
        return entry

    def generate_academic_report(self, items, max_items=10):
        """生成学术简报"""
        is_english = not Translator.enabled

        if is_english:
            today = datetime.now().strftime("%Y-%m-%d")
            now = datetime.now().strftime("%H:%M:%S")

            # 过滤和排序
            ranked_items = self.filter_and_rank(items)

            # 英文报告头部
            report = f"""# 📚 Daily Academic Briefing - {today}

> ⏰ Generated at: {now}
> 🤖 Your academic assistant has curated today's latest research

---

## 📊 Overview

| Metric | Value |
|--------|-------|
| Sources | {len(set(item.get('source') for item in items))} academic databases |
| Total Papers | {len(items)} |
| Relevant Papers | {len(ranked_items)} |
| Featured | {min(max_items, len(ranked_items))} |

---

## 🔥 Featured Papers

"""

            # 添加精选文章
            if ranked_items:
                for i, item in enumerate(ranked_items[:max_items], 1):
                    report += self.format_paper_entry(item, i)
            else:
                report += """> No highly relevant papers found today. Consider expanding your keywords.

---

"""

            # 添加统计信息
            report += """## 📈 Source Distribution

Based on keyword matching results:

"""
            # 统计各来源数量
            source_counts = {}
            for item in ranked_items[:20]:
                src = item.get('source', 'Other')
                source_counts[src] = source_counts.get(src, 0) + 1

            for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
                bar = '█' * count
                report += f"- **{src}**: {bar} ({count} papers)" + "\n"

            report += """
---

## 💡 Recommendations

1. **Priority**: Papers with relevance score ≥3 (keywords in title)
2. **Code Available**: GitHub links indicate open-source implementations
3. **Save for Later**: Bookmark interesting papers for future reading

---

*This briefing was automatically generated | May knowledge light your path 🌟*
"""

        else:
            # 中文报告
            today = datetime.now().strftime("%Y年%m月%d日")
            now = datetime.now().strftime("%H:%M:%S")

            # 过滤和排序
            ranked_items = self.filter_and_rank(items)

            # 报告头部
            report = f"""# 📚 每日学术简报 - {today}

> ⏰ 生成时间：{now}
> 🤖 您的专属学术助手已为您筛选今日最新研究动态

---

## 📊 数据概览

| 指标 | 数值 |
|------|------|
| 爬取来源 | {len(set(item.get('source') for item in items))}个学术数据库 |
| 总文献数 | {len(items)} 篇 |
| 相关文献 | {len(ranked_items)} 篇 |
| 精选推荐 | {min(max_items, len(ranked_items))} 篇 |

---

## 🔥 重点推荐

"""

            # 添加精选文章
            if ranked_items:
                for i, item in enumerate(ranked_items[:max_items], 1):
                    report += self.format_paper_entry(item, i)
            else:
                report += """> 今日暂无高度相关的最新文献，建议扩大关键词范围或查看全部爬取结果。

---

"""

            # 添加统计信息
            report += f"""## 📈 领域分布

基于关键词匹配结果：

"""
            # 统计各来源数量
            source_counts = {}
            for item in ranked_items[:20]:
                src = item.get('source', '其他')
                source_counts[src] = source_counts.get(src, 0) + 1

            for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
                bar = '█' * count
                report += f"- **{src}**: {bar} ({count}篇)" + "\n"

            report += f"""
---

## 💡 使用建议

1. **优先阅读**相关度评分 ≥3 的文献（标题含关键词）
2. **GitHub链接**表示有开源代码实现，便于复现研究
3. **建议收藏**感兴趣但暂时无暇阅读的文献链接

---

*本简报由您的学术助手自动生成 | 愿知识照亮前路 🌟*
"""

        return report

    def generate_failed_sources_report(self, failed_sources):
        """生成失败源报告 - 提示用户手动输入"""
        is_english = not Translator.enabled

        if is_english:
            report = f"""
---

## ⚠️ Failed Sources - Manual Input Required

The following {len(failed_sources)} source(s) could not be automatically crawled.
You can manually add information from these sources.

| Source | URL | Reason | Suggestion |
|--------|-----|--------|------------|
"""
            for fs in failed_sources:
                api_key_note = ""
                if fs.get('api_key_url'):
                    api_key_note = f" [Get API Key]({fs['api_key_url']})"
                report += f"| {fs['name']} | {fs['url'][:50]}... | {fs['reason']} | {fs['suggestion']}{api_key_note} |" + "\n"

            report += """
### How to Help

1. **Visit the URL manually** and find relevant academic papers
2. **Add papers manually** by editing the config or using the GUI
3. **Switch to API mode** if the source has a public API
4. **Get an API Key** if the source requires one (links provided above)
5. **Report the issue** so we can improve the crawler

---
*Failed sources require manual intervention | Your input helps improve automation 🤝*
"""
        else:
            report = f"""
---

## ⚠️ 爬取失败源 - 需要人工输入

以下 {len(failed_sources)} 个源无法自动爬取，您可以手动补充这些源的信息。

| 来源 | URL | 失败原因 | 建议 |
|------|-----|----------|------|
"""
            for fs in failed_sources:
                api_key_note = ""
                if fs.get('api_key_url'):
                    api_key_note = f" [获取API Key]({fs['api_key_url']})"
                report += f"| {fs['name']} | {fs['url'][:50]}... | {fs['reason']} | {fs['suggestion']}{api_key_note} |" + "\n"

            report += """
### 如何帮助改进

1. **手动访问URL**，查找相关学术论文
2. **手动添加论文** - 通过GUI界面或编辑配置文件
3. **切换为API模式** - 如果该源有公开API
4. **申请API Key** - 如果该源需要密钥（上方已提供链接）
4. **反馈问题** - 帮助我们改进爬取器

---
*失败源需要人工介入 | 您的输入有助于改进自动化 🤝*
"""

        return report

    def save_report(self, report):
        """保存报告"""
        date_str = datetime.now().strftime("%Y%m%d")
        filename = DATA_DIR / f"academic_briefing_{date_str}.md"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)

        log_message(f"学术简报已保存: {filename}")
        return filename


# ============ 邮件发送模块 ============

class EmailSender:
    """邮件发送器"""

    def __init__(self, config):
        self.smtp_server = config.get('smtp_server', 'smtp.qq.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.sender_email = config.get('sender_email', '')
        self.sender_password = self._decode_pwd(config.get('sender_password', ''))
        self.receiver_email = config.get('receiver_email', '')
        self.subject_prefix = config.get('subject_prefix', '[学术简报]')

    @staticmethod
    def _decode_pwd(value: str) -> str:
        if value and value.startswith("enc:"):
            try:
                return base64.b64decode(value[4:]).decode('utf-8')
            except Exception:
                return value
        return value

        self.enabled = config.get('enabled', False)

    def send_report(self, report_content, report_file=None):
        """发送学术简报邮件"""
        if not self.enabled:
            log_message("邮件功能已禁用，跳过发送")
            return False

        if not self.sender_email or not self.sender_password:
            log_message("邮件配置不完整，请检查config.json中的邮箱设置", "WARNING")
            return False

        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            today = datetime.now().strftime("%Y年%m月%d日")
            msg['Subject'] = Header(f"{self.subject_prefix} {today} 每日学术简报", 'utf-8')
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_email

            # 邮件正文（HTML格式）
            html_content = self._convert_markdown_to_html(report_content)

            # 添加纯文本版本
            text_part = MIMEText(report_content, 'plain', 'utf-8')
            # 添加HTML版本
            html_part = MIMEText(html_content, 'html', 'utf-8')

            msg.attach(text_part)
            msg.attach(html_part)

            # 连接SMTP服务器并发送
            log_message(f"正在连接邮件服务器 {self.smtp_server}:{self.smtp_port}...")

            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()

            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.receiver_email, msg.as_string())
            server.quit()

            log_message(f"邮件发送成功！收件人：{self.receiver_email}")
            return True

        except Exception as e:
            log_message(f"邮件发送失败: {str(e)}", "ERROR")
            return False

    def _convert_markdown_to_html(self, markdown_content):
        """简单将Markdown转换为HTML"""
        html = markdown_content

        # 转义HTML特殊字符
        html = html.replace('&', '&amp;')
        html = html.replace('<', '&lt;')
        html = html.replace('>', '&gt;')

        # 标题转换
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # 粗体和斜体
        html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', html)
        html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html)
        html = re.sub(r'\*(.+?)\*', r'<i>\1</i>', html)

        # 链接
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

        # 分隔线
        html = re.sub(r'^---+$', r'<hr>', html, flags=re.MULTILINE)

        # 换行
        html = html.replace('\n', '<br>\n')

        # 包装在HTML文档中
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


# ============ 提醒系统 ============

class ReminderSystem:
    """日程提醒系统"""

    def __init__(self, reminders):
        self.reminders = reminders

    def check_reminders(self):
        """检查当前时间是否有需要提醒的事项"""
        current_time = datetime.now().strftime("%H:%M")
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute

        current = None
        upcoming = []

        for reminder in self.reminders:
            reminder_time = reminder['time']
            reminder_hour = int(reminder_time.split(':')[0])
            reminder_minute = int(reminder_time.split(':')[1])

            # 精确匹配当前时间（允许1分钟误差）
            if reminder_time == current_time:
                current = reminder

            # 未来2小时内的提醒
            if reminder_hour > current_hour or (reminder_hour == current_hour and reminder_minute > current_minute):
                if reminder_hour < current_hour + 2 or (reminder_hour == current_hour + 2 and reminder_minute <= current_minute):
                    upcoming.append(reminder)

        return current, upcoming

    def generate_reminder_output(self, current, upcoming):
        """生成提醒输出"""
        output = []

        if current:
            output.append("""
╔════════════════════════════════════════════════════════════════╗
║  ⏰ 日程提醒                                                    ║
╠════════════════════════════════════════════════════════════════╣
""")
            # 处理换行描述
            desc = current['description']
            title = current['title']

            output.append(f"║  📌 {title:<55} ║")
            output.append("║                                                                ║")

            # 分割长描述为多行
            words = desc
            line = "║  📝 "
            for char in words:
                if len(line.encode('gbk', errors='ignore')) >= 58:
                    output.append(f"{line:<63} ║")
                    line = "║      " + char
                else:
                    line += char
            if line != "║      ":
                output.append(f"{line:<63} ║")

            output.append("╚════════════════════════════════════════════════════════════════╝")

        if upcoming:
            output.append("""
╔════════════════════════════════════════════════════════════════╗
║  📅 即将开始                                                    ║
╠════════════════════════════════════════════════════════════════╣
""")
            for r in upcoming[:3]:
                output.append(f"║  {r['time']} - {r['title']:<50} ║")
            output.append("╚════════════════════════════════════════════════════════════════╝")

        return '\n'.join(output) if output else ""

    def save_reminder_log(self, current):
        """保存提醒记录"""
        if current:
            date_str = datetime.now().strftime("%Y%m%d")
            log_file = LOG_DIR / f"reminders_{date_str}.log"

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().isoformat()}] 提醒: {current['title']} - {current['description']}" + "\n")


# ============ 主程序 ============

def main(mode=None):
    """主程序入口

    Args:
        mode: 运行模式，可选 'crawl', 'remind', 'all'。默认从sys.argv获取。
    """
    log_message("="*60)
    log_message("学术自动化助手启动")
    log_message("="*60)

    # 加载配置
    config = load_config()
    log_message(f"配置加载完成")

    # 设置翻译开关
    translation_config = config.get('translation', {})
    Translator.enabled = translation_config.get('enabled', False)
    log_message(f"翻译功能: {'开启' if Translator.enabled else '关闭 (纯英文输出)'}")

    # 解析命令行参数（如果没有传入mode）
    if mode is None:
        mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    log_message(f"运行模式: {mode}")

    # 执行模式
    if mode in ["crawl", "all"]:
        # 1. 爬取学术信息（使用多架构自动降级）
        crawler = InfoCrawler()
        all_keywords = config.get('keywords', []) + config.get('keywords_cn', [])
        items = crawler.crawl_all(config['news_sources'], keywords=all_keywords)

        # 2. 处理信息
        processor = InfoProcessor(config['keywords'])
        report = processor.generate_academic_report(
            items,
            max_items=config.get('max_items_per_source', 10)
        )

        # 3. 添加失败源报告
        failed_sources = crawler.get_failed_sources()
        if failed_sources:
            failed_report = processor.generate_failed_sources_report(failed_sources)
            report += failed_report

        # 4. 保存报告
        report_file = processor.save_report(report)
        log_message(f"学术简报已生成: {report_file}")

        # 5. 发送邮件
        email_config = config.get('email', {})
        if email_config.get('enabled', False):
            email_sender = EmailSender(email_config)
            email_sender.send_report(report, report_file)

        # 6. 显示简报预览
        safe_print("\n" + "="*60)
        safe_print("简报预览（前3条）:")
        safe_print("="*60)
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
        safe_print("\n" + "="*60)

        # 7. 显示失败源摘要
        if failed_sources:
            safe_print("\n" + "="*60)
            safe_print(f"⚠️ {len(failed_sources)} 个源爬取失败，需要人工介入:")
            for fs in failed_sources:
                safe_print(f"  - {fs['name']}: {fs['reason']}")
                safe_print(f"    建议: {fs['suggestion']}")
                if fs.get('api_key_url'):
                    safe_print(f"    🔑 获取API Key: {fs['api_key_url']}")
            safe_print("="*60)

    if mode in ["remind", "all"]:
        # 5. 检查日程提醒
        reminder_sys = ReminderSystem(config['reminders'])
        current, upcoming = reminder_sys.check_reminders()

        reminder_output = reminder_sys.generate_reminder_output(current, upcoming)
        if reminder_output:
            safe_print(reminder_output)

        reminder_sys.save_reminder_log(current)

    log_message("="*60)
    log_message("学术自动化助手执行完毕")
    log_message("="*60)


if __name__ == "__main__":
    main()
