#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Manager - with categorized academic sources
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


def _get_app_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2] / "runtime_local"


SOURCE_CATEGORIES = {
    "cs_ai": "AI/ML/NLP",
    "cs_cv": "Computer Vision",
    "cs_security": "Cybersecurity",
    "cs_ml_stat": "Statistics/ML",
    "general_academic": "General Academic",
    "life_science": "Life Sciences",
    "nature_science": "Nature/Science",
    "tech_blog": "Tech Blogs",
}


DEFAULT_NEWS_SOURCES = [
    {"name": "arXiv AI/ML/NLP", "url": "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL&sortBy=submittedDate&sortOrder=descending&max_results=10", "type": "rss", "enabled": True, "category": "cs_ai", "desc": "AI, ML, NLP - arXiv latest preprints"},
    {"name": "arXiv CV", "url": "http://export.arxiv.org/api/query?search_query=cat:cs.CV&sortBy=submittedDate&sortOrder=descending&max_results=10", "type": "rss", "enabled": True, "category": "cs_cv", "desc": "Computer Vision - image recognition, generation"},
    {"name": "arXiv Security", "url": "http://export.arxiv.org/api/query?search_query=cat:cs.CR&sortBy=submittedDate&sortOrder=descending&max_results=10", "type": "rss", "enabled": True, "category": "cs_security", "desc": "Cryptography, security, privacy"},
    {"name": "arXiv Stat.ML", "url": "http://export.arxiv.org/api/query?search_query=cat:stat.ML&sortBy=submittedDate&sortOrder=descending&max_results=10", "type": "rss", "enabled": True, "category": "cs_ml_stat", "desc": "Statistical ML theory and methods"},
    {"name": "arXiv Robotics", "url": "http://export.arxiv.org/api/query?search_query=cat:cs.RO&sortBy=submittedDate&sortOrder=descending&max_results=10", "type": "rss", "enabled": False, "category": "cs_ai", "desc": "Robotics - control, planning, perception"},
    {"name": "arXiv HCI", "url": "http://export.arxiv.org/api/query?search_query=cat:cs.HC&sortBy=submittedDate&sortOrder=descending&max_results=10", "type": "rss", "enabled": False, "category": "cs_ai", "desc": "Human-Computer Interaction"},
    {"name": "arXiv SE", "url": "http://export.arxiv.org/api/query?search_query=cat:cs.SE&sortBy=submittedDate&sortOrder=descending&max_results=10", "type": "rss", "enabled": False, "category": "cs_security", "desc": "Software Engineering"},
    {"name": "Semantic Scholar", "url": "https://api.semanticscholar.org/graph/v1/paper/search", "type": "api", "enabled": True, "category": "cs_ai", "desc": "AI academic paper search engine"},
    {"name": "DBLP", "url": "https://dblp.org/search/publ/api", "type": "api", "enabled": True, "category": "general_academic", "desc": "CS bibliography database"},
    {"name": "OpenAlex", "url": "https://api.openalex.org/works", "type": "api", "enabled": True, "category": "general_academic", "desc": "Open academic metadata - all fields"},
    {"name": "CrossRef", "url": "https://api.crossref.org/works", "type": "api", "enabled": True, "category": "general_academic", "desc": "DOI metadata - cross-publisher"},
    {"name": "PubMed", "url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/", "type": "api", "enabled": False, "category": "life_science", "desc": "Biomedical & life sciences literature"},
    {"name": "PLOS", "url": "https://api.plos.org/search", "type": "api", "enabled": False, "category": "life_science", "desc": "Public Library of Science - open access"},
    {"name": "bioRxiv", "url": "https://api.biorxiv.org/details/biorxiv", "type": "api", "enabled": False, "category": "life_science", "desc": "Biology preprints - very slow, enable only if needed"},
    {"name": "Nature RSS", "url": "https://www.nature.com/nature.rss", "type": "rss", "enabled": True, "category": "nature_science", "desc": "Nature journal - top-tier research"},
    {"name": "Science RSS", "url": "https://www.science.org/rss/express.xml", "type": "rss", "enabled": True, "category": "nature_science", "desc": "Science journal - breakthrough research"},
    {"name": "The Gradient", "url": "https://thegradient.pub/", "type": "web", "enabled": True, "category": "tech_blog", "desc": "ML/AI research explanations and perspectives"},
    {"name": "Distill", "url": "https://distill.pub/", "type": "web", "enabled": True, "category": "tech_blog", "desc": "Interactive ML research visualizations"},
]


DEFAULT_TIME_SLOTS = [
    {"label": "1-2节", "start": "08:00", "end": "09:40"},
    {"label": "3-4节", "start": "10:00", "end": "11:40"},
    {"label": "5-6节", "start": "14:00", "end": "15:40"},
    {"label": "7-8节", "start": "16:00", "end": "17:40"},
    {"label": "9-10节", "start": "19:00", "end": "20:40"},
]

WEEKDAY_CN_TO_EN = {
    '周一': 'Monday', '周二': 'Tuesday', '周三': 'Wednesday',
    '周四': 'Thursday', '周五': 'Friday', '周六': 'Saturday', '周日': 'Sunday',
    '星期一': 'Monday', '星期二': 'Tuesday', '星期三': 'Wednesday',
    '星期四': 'Thursday', '星期五': 'Friday', '星期六': 'Saturday', '星期日': 'Sunday',
    '周1': 'Monday', '周2': 'Tuesday', '周3': 'Wednesday',
    '周4': 'Thursday', '周5': 'Friday', '周6': 'Saturday', '周7': 'Sunday',
}


def _normalize_day(day: str) -> str:
    """将中文星期/英文缩写统一转为英文全称 Monday-Sunday"""
    if not day:
        return 'Monday'
    # 如果是中文，直接映射
    if day in WEEKDAY_CN_TO_EN:
        return WEEKDAY_CN_TO_EN[day]
    # 检查是否包含中文关键词
    for cn, en in WEEKDAY_CN_TO_EN.items():
        if cn in day:
            return en
    # 已经是英文：首字母大写
    return day.capitalize()


class ConfigManager:

    def __init__(self, config_dir: Path = None):
        if config_dir is None:
            config_dir = _get_app_dir()

        self.config_dir = config_dir
        self.config_file = config_dir / "config.json"
        self.schedule_file = config_dir / "schedule.json"
        self.weekly_tasks_file = config_dir / "weekly_tasks.json"

        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_json(self, file_path: Path) -> Dict:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_json(self, file_path: Path, data: Dict) -> bool:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Save failed: {e}")
            return False

    def backup_config(self, file_path: Path) -> Optional[Path]:
        if not file_path.exists():
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = file_path.with_suffix(f".backup_{timestamp}.json")
        try:
            data = self.load_json(file_path)
            self.save_json(backup_file, data)
            return backup_file
        except Exception:
            return None

    def get_config(self) -> Dict:
        return self.load_json(self.config_file)

    def save_config(self, config: Dict) -> bool:
        return self.save_json(self.config_file, config)

    def get_news_sources(self) -> List[Dict]:
        config = self.get_config()
        return config.get('news_sources', [])

    def add_news_source(self, name: str, url: str, source_type: str = "rss", enabled: bool = True) -> bool:
        config = self.get_config()
        if 'news_sources' not in config:
            config['news_sources'] = []
        for source in config['news_sources']:
            if source['name'] == name:
                return False
        config['news_sources'].append({
            'name': name, 'url': url, 'type': source_type, 'enabled': enabled
        })
        return self.save_config(config)

    def update_news_source(self, index: int, name: str = None, url: str = None,
                           source_type: str = None, enabled: bool = None) -> bool:
        config = self.get_config()
        sources = config.get('news_sources', [])
        if index < 0 or index >= len(sources):
            return False
        if name is not None:
            sources[index]['name'] = name
        if url is not None:
            sources[index]['url'] = url
        if source_type is not None:
            sources[index]['type'] = source_type
        if enabled is not None:
            sources[index]['enabled'] = enabled
        return self.save_config(config)

    def delete_news_source(self, index: int) -> bool:
        config = self.get_config()
        sources = config.get('news_sources', [])
        if index < 0 or index >= len(sources):
            return False
        sources.pop(index)
        config['news_sources'] = sources
        return self.save_config(config)

    def get_keywords(self) -> Dict[str, List[str]]:
        config = self.get_config()
        return {
            'keywords': config.get('keywords', []),
            'keywords_cn': config.get('keywords_cn', [])
        }

    def update_keywords(self, keywords: List[str], keywords_cn: List[str]) -> bool:
        config = self.get_config()
        config['keywords'] = keywords
        config['keywords_cn'] = keywords_cn
        return self.save_config(config)

    def get_reminders(self) -> List[Dict]:
        config = self.get_config()
        return config.get('reminders', [])

    def add_reminder(self, time: str, title: str, description: str) -> bool:
        config = self.get_config()
        if 'reminders' not in config:
            config['reminders'] = []
        config['reminders'].append({
            'time': time, 'title': title, 'description': description
        })
        return self.save_config(config)

    def update_reminder(self, index: int, time: str = None, title: str = None,
                        description: str = None) -> bool:
        config = self.get_config()
        reminders = config.get('reminders', [])
        if index < 0 or index >= len(reminders):
            return False
        if time is not None:
            reminders[index]['time'] = time
        if title is not None:
            reminders[index]['title'] = title
        if description is not None:
            reminders[index]['description'] = description
        return self.save_config(config)

    def delete_reminder(self, index: int) -> bool:
        config = self.get_config()
        reminders = config.get('reminders', [])
        if index < 0 or index >= len(reminders):
            return False
        reminders.pop(index)
        config['reminders'] = reminders
        return self.save_config(config)

    def get_email_config(self) -> Dict:
        config = self.get_config()
        return config.get('email', {
            'enabled': False,
            'smtp_server': 'smtp.qq.com',
            'smtp_port': 587,
            'sender_email': '',
            'sender_password': '',
            'receiver_email': '',
            'subject_prefix': '[学术简报]'
        })

    def update_email_config(self, email_config: Dict) -> bool:
        config = self.get_config()
        config['email'] = email_config
        return self.save_config(config)

    API_KEY_INFO = {
        'semantic_scholar': {
            'name': 'Semantic Scholar',
            'required': False,
            'description': 'No key: 100 req/5min; with key: higher quota',
            'get_url': 'https://www.semanticscholar.org/product/api#api-key'
        },
        'openalex': {
            'name': 'OpenAlex',
            'required': False,
            'description': 'No key: rate limited; with key: faster',
            'get_url': 'https://docs.openalex.org/how-to-use-the-api/get-an-api-key'
        },
        'core': {
            'name': 'CORE',
            'required': True,
            'description': 'API Key required',
            'get_url': 'https://core.ac.uk/services/api'
        },
        'qweather': {
            'name': 'QWeather',
            'required': False,
            'description': 'Optional weather provider key',
            'get_url': 'https://dev.qweather.com/'
        }
    }

    def get_api_keys(self) -> Dict:
        config = self.get_config()
        return config.get('api_keys', {
            'semantic_scholar': '',
            'openalex': '',
            'core': '',
            'qweather': ''
        })

    def get_api_key(self, service: str) -> str:
        keys = self.get_api_keys()
        return keys.get(service, '')

    def update_api_keys(self, api_keys: Dict) -> bool:
        config = self.get_config()
        config['api_keys'] = api_keys
        return self.save_config(config)

    def check_missing_api_keys(self) -> List[Dict]:
        keys = self.get_api_keys()
        missing = []
        for key_name, info in self.API_KEY_INFO.items():
            if not keys.get(key_name, ''):
                missing.append({
                    'key_name': key_name,
                    'name': info['name'],
                    'required': info['required'],
                    'description': info['description'],
                    'get_url': info['get_url']
                })
        return missing

    def get_translation_config(self) -> Dict:
        config = self.get_config()
        return config.get('translation', {'enabled': False, 'target_lang': 'en'})

    def update_translation_config(self, enabled: bool, target_lang: str = 'en') -> bool:
        config = self.get_config()
        config['translation'] = {'enabled': enabled, 'target_lang': target_lang}
        return self.save_config(config)

    def get_output_settings(self) -> Dict:
        config = self.get_config()
        return {
            'output_format': config.get('output_format', 'markdown'),
            'max_items_per_source': config.get('max_items_per_source', 5)
        }

    def update_output_settings(self, output_format: str = None, max_items: int = None) -> bool:
        config = self.get_config()
        if output_format is not None:
            config['output_format'] = output_format
        if max_items is not None:
            config['max_items_per_source'] = max_items
        return self.save_config(config)

    def get_weather_city(self) -> str:
        config = self.get_config()
        return config.get('weather_city', 'Beijing')

    def update_weather_city(self, city: str) -> bool:
        config = self.get_config()
        config['weather_city'] = city
        return self.save_config(config)

    def get_user_info(self) -> Dict[str, str]:
        config = self.get_config()
        return {
            'university': config.get('university', ''),
            'grade': config.get('grade', ''),
            'weather_city': config.get('weather_city', 'Beijing')
        }

    def update_user_info(self, university: str = None, grade: str = None, weather_city: str = None) -> bool:
        config = self.get_config()
        if university is not None:
            config['university'] = university
        if grade is not None:
            config['grade'] = grade
        if weather_city is not None:
            config['weather_city'] = weather_city
        return self.save_config(config)

    def get_time_slots(self) -> List[Dict]:
        config = self.get_config()
        return config.get('time_slots', DEFAULT_TIME_SLOTS)

    def save_time_slots(self, time_slots: List[Dict]) -> bool:
        config = self.get_config()
        config['time_slots'] = time_slots
        return self.save_config(config)

    def get_schedule(self) -> Dict:
        return self.load_json(self.schedule_file)

    def save_schedule(self, schedule: Dict) -> bool:
        return self.save_json(self.schedule_file, schedule)

    def get_week_schedule(self) -> Dict[str, List[Dict]]:
        schedule = self.get_schedule()
        week_schedule = schedule.get('week_schedule', {})
        normalized = {}
        for day, courses in week_schedule.items():
            normalized[_normalize_day(day)] = courses
        return normalized

    def add_course(self, day: str, name: str, time: str, location: str,
                   teacher: str, note: str = "") -> bool:
        day = _normalize_day(day)
        schedule = self.get_schedule()
        if 'week_schedule' not in schedule:
            schedule['week_schedule'] = {}
        if day not in schedule['week_schedule']:
            schedule['week_schedule'][day] = []
        schedule['week_schedule'][day].append({
            'name': name, 'time': time, 'location': location,
            'teacher': teacher, 'note': note
        })
        return self.save_schedule(schedule)

    def delete_course(self, day: str, index: int) -> bool:
        day = _normalize_day(day)
        schedule = self.get_schedule()
        week_schedule = schedule.get('week_schedule', {})
        if day not in week_schedule:
            return False
        if index < 0 or index >= len(week_schedule[day]):
            return False
        week_schedule[day].pop(index)
        return self.save_schedule(schedule)

    def get_weekly_tasks(self) -> Dict:
        return self.load_json(self.weekly_tasks_file)

    def save_weekly_tasks(self, tasks: Dict) -> bool:
        return self.save_json(self.weekly_tasks_file, tasks)

    def export_all_config(self) -> Dict:
        return {
            'config': self.get_config(),
            'schedule': self.get_schedule(),
            'weekly_tasks': self.get_weekly_tasks(),
            'export_time': datetime.now().isoformat()
        }

    def import_all_config(self, data: Dict) -> bool:
        try:
            if 'config' in data:
                self.save_config(data['config'])
            if 'schedule' in data:
                self.save_schedule(data['schedule'])
            if 'weekly_tasks' in data:
                self.save_weekly_tasks(data['weekly_tasks'])
            return True
        except Exception as e:
            print(f"Import failed: {e}")
            return False

    def reset_to_default(self) -> Dict:
        default_config = {
            "news_sources": DEFAULT_NEWS_SOURCES,
            "time_slots": DEFAULT_TIME_SLOTS,
            "reminders": [
                {"time": "09:00", "title": "学术早报", "description": "今日最新学术资讯已整理完毕，请查阅。"},
                {"time": "22:00", "title": "晚间复盘", "description": "今日工作告一段落，回顾一下收获。"}
            ],
            "keywords": ["artificial intelligence", "machine learning", "big data", "public governance", "digital governance"],
            "keywords_cn": ["人工智能", "大数据", "公共治理", "数字治理"],
            "output_format": "markdown",
            "translation": {"enabled": False, "target_lang": "en"},
            "max_items_per_source": 5,
            "email": {
                "enabled": False,
                "smtp_server": "smtp.qq.com",
                "smtp_port": 587,
                "sender_email": "",
                "sender_password": "",
                "receiver_email": "",
                "subject_prefix": "[学术简报]"
            },
            "api_keys": {
                "semantic_scholar": "",
                "openalex": "",
                "core": "",
                "qweather": ""
            },
            "weather_city": "Beijing",
            "university": "",
            "grade": ""
        }
        self.save_config(default_config)
        return default_config

    def ensure_default_config(self) -> bool:
        created = False
        if not self.config_file.exists():
            self.reset_to_default()
            return True
        config = self.get_config()
        if 'time_slots' not in config:
            config['time_slots'] = DEFAULT_TIME_SLOTS
            self.save_config(config)
            created = True
        return created

    def ensure_default_schedule(self) -> bool:
        if not self.schedule_file.exists():
            default = {
                "semester": "",
                "week_schedule": {
                    "Monday": [], "Tuesday": [], "Wednesday": [],
                    "Thursday": [], "Friday": [], "Saturday": [], "Sunday": []
                },
                "review_tasks": {},
                "daily_routine": {}
            }
            self.save_schedule(default)
            return True
        return False
