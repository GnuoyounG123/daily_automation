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
    except:
        pass
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
    log_entry = f"[{timestamp}] [{level}] {message}\n"
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

class InfoCrawler:
    """学术信息爬取器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0',
            'Accept': 'application/json, application/xml, text/xml, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        self.results = []

    def fetch_content(self, url, timeout=15):
        """获取内容"""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content_type = response.headers.get('Content-Type', '')
                data = response.read()

                # 尝试解码
                try:
                    return data.decode('utf-8')
                except:
                    try:
                        return data.decode('gbk')
                    except:
                        return data.decode('latin-1')
        except urllib.error.HTTPError as e:
            log_message(f"HTTP错误 {e.code}: {url}", "ERROR")
            return None
        except Exception as e:
            log_message(f"获取失败 {url}: {str(e)}", "ERROR")
            return None

    def parse_arxiv_rss(self, xml_content):
        """解析arXiv RSS"""
        items = []
        try:
            root = ET.fromstring(xml_content)
            # 处理命名空间
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
                        'source': 'arXiv'
                    })
        except Exception as e:
            log_message(f"解析arXiv RSS失败: {str(e)}", "ERROR")
        return items

    def parse_generic_rss(self, xml_content, source_name):
        """解析通用RSS"""
        items = []
        try:
            root = ET.fromstring(xml_content)

            # 查找item元素（可能在channel下，也可能直接在root下）
            channel = root.find('.//channel')
            if channel is not None:
                item_list = channel.findall('item')
            else:
                item_list = root.findall('.//item')

            for item in item_list[:10]:  # 最多取10条
                title = item.find('title')
                desc = item.find('description')
                link = item.find('link')
                pub_date = item.find('pubDate')

                if title is not None and title.text:
                    items.append({
                        'title': title.text.strip(),
                        'abstract': desc.text.strip() if desc is not None and desc.text else '',
                        'url': link.text.strip() if link is not None and link.text else '',
                        'date': '今日',
                        'source': source_name
                    })
        except Exception as e:
            log_message(f"解析RSS失败 {source_name}: {str(e)}", "ERROR")
        return items

    def parse_paperswithcode(self, json_content):
        """解析PapersWithCode API"""
        items = []
        try:
            data = json.loads(json_content)
            results = data.get('results', [])

            for paper in results[:10]:
                items.append({
                    'title': paper.get('title', '无标题'),
                    'abstract': paper.get('abstract', ''),
                    'url': paper.get('url', ''),
                    'date': paper.get('published', datetime.now().strftime('%Y-%m-%d')),
                    'source': 'PapersWithCode',
                    'github': paper.get('github_url', '')
                })
        except Exception as e:
            log_message(f"解析PapersWithCode失败: {str(e)}", "ERROR")
        return items

    def crawl_source(self, source):
        """爬取单个来源"""
        source_name = source['name']
        source_url = source['url']
        source_type = source.get('type', 'web')

        log_message(f"正在爬取: {source_name}")

        content = self.fetch_content(source_url)
        if not content:
            return []

        items = []
        if source_type == 'rss':
            if 'arxiv' in source_url.lower():
                items = self.parse_arxiv_rss(content)
            else:
                items = self.parse_generic_rss(content, source_name)
        elif source_type == 'json':
            # 通用JSON处理
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    for item in data[:10]:
                        items.append({
                            'title': item.get('title', '无标题'),
                            'abstract': item.get('abstract', item.get('summary', '')),
                            'url': item.get('url', item.get('link', '')),
                            'date': item.get('date', '今日'),
                            'source': source_name
                        })
            except Exception as e:
                log_message(f"解析JSON失败 {source_name}: {str(e)}", "ERROR")
        elif source_type == 'web':
            # 根据域名选择解析方法
            if 'semanticscholar.org' in source_url.lower():
                items = self.parse_semantic_scholar(content, source_name)
            elif 'aminer.cn' in source_url.lower():
                items = self.parse_aminer(content, source_name)
            elif 'thegradient.pub' in source_url.lower():
                items = self.parse_the_gradient(content, source_name)
            else:
                # 通用网页解析
                items = self.parse_generic_web(content, source_name, source_url)

        log_message(f"{source_name} 获取 {len(items)} 条")
        return items

    def parse_semantic_scholar(self, html, source_name):
        """解析Semantic Scholar网页"""
        items = []
        try:
            # 尝试多种可能的标题链接模式
            patterns = [
                # 文章卡片模式
                r'<a[^>]*href="(/paper/[^"]+)"[^>]*data-test-id="paper-title"[^>]*>(.*?)</a>',
                r'<a[^>]*href="(/paper/[^"]+)"[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</a>',
                # 通用文章链接
                r'<h[23][^>]*>.*?<a[^>]*href="(/paper/[^"]+)"[^>]*>(.*?)</a>.*?</h[23]>',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
                for match in matches[:8]:
                    if isinstance(match, tuple):
                        link, title = match
                    else:
                        continue

                    # 清理标题
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    if not title or len(title) < 10:
                        continue

                    # 确保链接完整
                    if link.startswith('/'):
                        link = 'https://www.semanticscholar.org' + link

                    items.append({
                        'title': title,
                        'abstract': '',
                        'url': link,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'source': source_name
                    })

            # 去重
            seen = set()
            unique_items = []
            for item in items:
                if item['url'] not in seen:
                    seen.add(item['url'])
                    unique_items.append(item)

            return unique_items[:5]
        except Exception as e:
            log_message(f"解析Semantic Scholar失败: {str(e)}", "ERROR")
            return []

    def parse_aminer(self, html, source_name):
        """解析AMiner网页"""
        items = []
        try:
            # AMiner常见文章模式
            patterns = [
                # 论文标题链接
                r'<a[^>]*href="(/pub/[^"]+)"[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</a>',
                r'<a[^>]*href="(/pub/[^"]+)"[^>]*target="_blank"[^>]*>([^<]+)</a>',
                # 通用链接模式
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
                        'title': title,
                        'abstract': '',
                        'url': link,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'source': source_name
                    })

            # 去重
            seen = set()
            unique_items = []
            for item in items:
                if item['url'] not in seen:
                    seen.add(item['url'])
                    unique_items.append(item)

            return unique_items[:5]
        except Exception as e:
            log_message(f"解析AMiner失败: {str(e)}", "ERROR")
            return []

    def parse_the_gradient(self, html, source_name):
        """解析The Gradient网页"""
        items = []
        try:
            # The Gradient是博客网站，文章通常在列表中
            patterns = [
                # 文章标题链接模式
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

                    # 过滤导航链接
                    if any(x in link.lower() for x in ['about', 'contact', 'subscribe', 'wp-content']):
                        continue

                    # 确保链接完整
                    if link.startswith('/'):
                        link = 'https://thegradient.pub' + link

                    items.append({
                        'title': title,
                        'abstract': '',
                        'url': link,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'source': source_name
                    })

            # 去重
            seen = set()
            unique_items = []
            for item in items:
                if item['url'] not in seen:
                    seen.add(item['url'])
                    unique_items.append(item)

            return unique_items[:5]
        except Exception as e:
            log_message(f"解析The Gradient失败: {str(e)}", "ERROR")
            return []

    def parse_generic_web(self, html, source_name, base_url):
        """通用网页解析 - 提取可能的学术文章"""
        items = []
        try:
            # 通用模式：查找所有可能的标题链接
            # 匹配2-5个单词的标题（可能是文章标题）
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

                    # 过滤条件
                    if len(title) < 20 or len(title) > 200:
                        continue
                    if any(x in title.lower() for x in ['javascript', 'css', 'login', 'signup', 'home', 'about']):
                        continue
                    if title.count(' ') > 20:  # 太长的可能是段落而非标题
                        continue

                    # 确保链接完整
                    if link.startswith('/'):
                        parsed = urlparse(base_url)
                        link = f"{parsed.scheme}://{parsed.netloc}{link}"
                    elif not link.startswith('http'):
                        continue

                    items.append({
                        'title': title,
                        'abstract': '',
                        'url': link,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'source': source_name
                    })

            # 去重
            seen = set()
            unique_items = []
            for item in items:
                if item['url'] not in seen:
                    seen.add(item['url'])
                    unique_items.append(item)

            return unique_items[:5]
        except Exception as e:
            log_message(f"通用解析失败 {source_name}: {str(e)}", "ERROR")
            return []

    def crawl_all(self, sources):
        """爬取所有启用的来源"""
        enabled_sources = [s for s in sources if s.get('enabled', True)]
        log_message(f"开始爬取 {len(enabled_sources)} 个学术信息源...")

        all_items = []
        for source in enabled_sources:
            items = self.crawl_source(source)
            all_items.extend(items)
            time.sleep(1.5)  # 礼貌延迟

        log_message(f"爬取完成，共获取 {len(all_items)} 条学术资讯")
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
                entry += f"**Code**: [GitHub]({item['github']})\n"
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
                entry += f"**代码实现**：[GitHub]({item['github']})\n"

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
                report += f"- **{src}**: {bar} ({count} papers)\n"

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
                report += f"- **{src}**: {bar} ({count}篇)\n"

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
        self.sender_password = config.get('sender_password', '')
        self.receiver_email = config.get('receiver_email', '')
        self.subject_prefix = config.get('subject_prefix', '[学术简报]')
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
                f.write(f"[{datetime.now().isoformat()}] 提醒: {current['title']} - {current['description']}\n")


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
        # 1. 爬取学术信息
        crawler = InfoCrawler()
        items = crawler.crawl_all(config['news_sources'])

        # 2. 处理信息
        processor = InfoProcessor(config['keywords'])
        report = processor.generate_academic_report(
            items,
            max_items=config.get('max_items_per_source', 10)
        )

        # 3. 保存报告
        report_file = processor.save_report(report)
        log_message(f"学术简报已生成: {report_file}")

        # 4. 发送邮件
        email_config = config.get('email', {})
        if email_config.get('enabled', False):
            email_sender = EmailSender(email_config)
            email_sender.send_report(report, report_file)

        # 5. 显示简报预览
        safe_print("\n" + "="*60)
        safe_print("简报预览（前3条）:")
        safe_print("="*60)
        # 提取前3条显示
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
