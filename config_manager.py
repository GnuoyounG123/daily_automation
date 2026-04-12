#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块 - Configuration Manager
提供配置的增删改查功能
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


def _get_app_dir() -> Path:
    """获取应用程序目录（兼容打包环境）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller打包环境：exe所在目录
        return Path(sys.executable).parent
    else:
        # 开发环境：源码目录
        return Path(__file__).parent


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: Path = None):
        if config_dir is None:
            config_dir = _get_app_dir()

        self.config_dir = config_dir
        self.config_file = config_dir / "config.json"
        self.schedule_file = config_dir / "schedule.json"
        self.weekly_tasks_file = config_dir / "weekly_tasks.json"

        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)

    # ========== 通用配置操作 ==========

    def load_json(self, file_path: Path) -> Dict:
        """加载JSON文件"""
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_json(self, file_path: Path, data: Dict) -> bool:
        """保存JSON文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存失败: {e}")
            return False

    def backup_config(self, file_path: Path) -> Optional[Path]:
        """备份配置文件"""
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

    # ========== 主配置 (config.json) ==========

    def get_config(self) -> Dict:
        """获取主配置"""
        return self.load_json(self.config_file)

    def save_config(self, config: Dict) -> bool:
        """保存主配置"""
        return self.save_json(self.config_file, config)

    # ========== 新闻源管理 ==========

    def get_news_sources(self) -> List[Dict]:
        """获取新闻源列表"""
        config = self.get_config()
        return config.get('news_sources', [])

    def add_news_source(self, name: str, url: str, source_type: str = "rss", enabled: bool = True) -> bool:
        """添加新闻源"""
        config = self.get_config()
        if 'news_sources' not in config:
            config['news_sources'] = []

        # 检查是否已存在
        for source in config['news_sources']:
            if source['name'] == name:
                return False

        config['news_sources'].append({
            'name': name,
            'url': url,
            'type': source_type,
            'enabled': enabled
        })
        return self.save_config(config)

    def update_news_source(self, index: int, name: str = None, url: str = None,
                           source_type: str = None, enabled: bool = None) -> bool:
        """更新新闻源"""
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
        """删除新闻源"""
        config = self.get_config()
        sources = config.get('news_sources', [])

        if index < 0 or index >= len(sources):
            return False

        sources.pop(index)
        config['news_sources'] = sources
        return self.save_config(config)

    # ========== 关键词管理 ==========

    def get_keywords(self) -> Dict[str, List[str]]:
        """获取关键词（英文和中文）"""
        config = self.get_config()
        return {
            'keywords': config.get('keywords', []),
            'keywords_cn': config.get('keywords_cn', [])
        }

    def update_keywords(self, keywords: List[str], keywords_cn: List[str]) -> bool:
        """更新关键词"""
        config = self.get_config()
        config['keywords'] = keywords
        config['keywords_cn'] = keywords_cn
        return self.save_config(config)

    # ========== 提醒管理 ==========

    def get_reminders(self) -> List[Dict]:
        """获取提醒列表"""
        config = self.get_config()
        return config.get('reminders', [])

    def add_reminder(self, time: str, title: str, description: str) -> bool:
        """添加提醒"""
        config = self.get_config()
        if 'reminders' not in config:
            config['reminders'] = []

        config['reminders'].append({
            'time': time,
            'title': title,
            'description': description
        })
        return self.save_config(config)

    def update_reminder(self, index: int, time: str = None, title: str = None,
                        description: str = None) -> bool:
        """更新提醒"""
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
        """删除提醒"""
        config = self.get_config()
        reminders = config.get('reminders', [])

        if index < 0 or index >= len(reminders):
            return False

        reminders.pop(index)
        config['reminders'] = reminders
        return self.save_config(config)

    # ========== 邮箱配置 ==========

    def get_email_config(self) -> Dict:
        """获取邮箱配置"""
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
        """更新邮箱配置"""
        config = self.get_config()
        config['email'] = email_config
        return self.save_config(config)


    # ========== API密钥配置 ==========

    API_KEY_INFO = {
        'semantic_scholar': {
            'name': 'Semantic Scholar',
            'required': False,
            'description': '无Key限流100次/5分钟，有Key可提升配额',
            'get_url': 'https://www.semanticscholar.org/product/api#api-key'
        },
        'openalex': {
            'name': 'OpenAlex',
            'required': False,
            'description': '无Key限速，有Key可提升速率',
            'get_url': 'https://docs.openalex.org/how-to-use-the-api/get-an-api-key'
        },
        'core': {
            'name': 'CORE',
            'required': True,
            'description': '必须配置API Key才能使用',
            'get_url': 'https://core.ac.uk/services/api'
        }
    }

    def get_api_keys(self) -> Dict:
        """获取API密钥配置"""
        config = self.get_config()
        return config.get('api_keys', {
            'semantic_scholar': '',
            'openalex': '',
            'core': ''
        })

    def get_api_key(self, service: str) -> str:
        """获取指定服务的API密钥"""
        keys = self.get_api_keys()
        return keys.get(service, '')

    def update_api_keys(self, api_keys: Dict) -> bool:
        """更新API密钥配置"""
        config = self.get_config()
        config['api_keys'] = api_keys
        return self.save_config(config)

    def check_missing_api_keys(self) -> List[Dict]:
        """检查缺失的API密钥，返回需要配置的列表"""
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

    # ========== 翻译配置 ==========

    def get_translation_config(self) -> Dict:
        """获取翻译配置"""
        config = self.get_config()
        return config.get('translation', {'enabled': False, 'target_lang': 'en'})

    def update_translation_config(self, enabled: bool, target_lang: str = 'en') -> bool:
        """更新翻译配置"""
        config = self.get_config()
        config['translation'] = {
            'enabled': enabled,
            'target_lang': target_lang
        }
        return self.save_config(config)

    # ========== 其他设置 ==========

    def get_output_settings(self) -> Dict:
        """获取输出设置"""
        config = self.get_config()
        return {
            'output_format': config.get('output_format', 'markdown'),
            'max_items_per_source': config.get('max_items_per_source', 5)
        }

    def update_output_settings(self, output_format: str = None, max_items: int = None) -> bool:
        """更新输出设置"""
        config = self.get_config()
        if output_format is not None:
            config['output_format'] = output_format
        if max_items is not None:
            config['max_items_per_source'] = max_items
        return self.save_config(config)

    # ========== 课程表管理 ==========

    def get_schedule(self) -> Dict:
        """获取课程表"""
        return self.load_json(self.schedule_file)

    def save_schedule(self, schedule: Dict) -> bool:
        """保存课程表"""
        return self.save_json(self.schedule_file, schedule)

    def get_week_schedule(self) -> Dict[str, List[Dict]]:
        """获取周课程表"""
        schedule = self.get_schedule()
        return schedule.get('week_schedule', {})

    def add_course(self, day: str, name: str, time: str, location: str,
                   teacher: str, note: str = "") -> bool:
        """添加课程"""
        schedule = self.get_schedule()
        if 'week_schedule' not in schedule:
            schedule['week_schedule'] = {}
        if day not in schedule['week_schedule']:
            schedule['week_schedule'][day] = []

        schedule['week_schedule'][day].append({
            'name': name,
            'time': time,
            'location': location,
            'teacher': teacher,
            'note': note
        })
        return self.save_schedule(schedule)

    def delete_course(self, day: str, index: int) -> bool:
        """删除课程"""
        schedule = self.get_schedule()
        week_schedule = schedule.get('week_schedule', {})

        if day not in week_schedule:
            return False
        if index < 0 or index >= len(week_schedule[day]):
            return False

        week_schedule[day].pop(index)
        return self.save_schedule(schedule)

    # ========== 每周任务管理 ==========

    def get_weekly_tasks(self) -> Dict:
        """获取每周任务"""
        return self.load_json(self.weekly_tasks_file)

    def save_weekly_tasks(self, tasks: Dict) -> bool:
        """保存每周任务"""
        return self.save_json(self.weekly_tasks_file, tasks)

    # ========== 导入导出 ==========

    def export_all_config(self) -> Dict:
        """导出所有配置"""
        return {
            'config': self.get_config(),
            'schedule': self.get_schedule(),
            'weekly_tasks': self.get_weekly_tasks(),
            'export_time': datetime.now().isoformat()
        }

    def import_all_config(self, data: Dict) -> bool:
        """导入所有配置"""
        try:
            if 'config' in data:
                self.save_config(data['config'])
            if 'schedule' in data:
                self.save_schedule(data['schedule'])
            if 'weekly_tasks' in data:
                self.save_weekly_tasks(data['weekly_tasks'])
            return True
        except Exception as e:
            print(f"导入失败: {e}")
            return False

    def reset_to_default(self) -> Dict:
        """重置为默认配置"""
        default_config = {
            "news_sources": [
                {"name": "arXiv AI", "url": "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL&sortBy=submittedDate&sortOrder=descending&max_results=10", "type": "rss", "enabled": True},
                {"name": "Semantic Scholar", "url": "https://www.semanticscholar.org/", "type": "web", "enabled": True},
                {"name": "AMiner", "url": "https://www.aminer.cn/", "type": "web", "enabled": True},
                {"name": "The Gradient", "url": "https://thegradient.pub/", "type": "web", "enabled": True}
            ],
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
                "core": ""
            }
        }
        self.save_config(default_config)
        return default_config
