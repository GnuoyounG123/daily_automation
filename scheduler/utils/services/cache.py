"""
缓存服务层
封装数据库操作，提供会话和课表缓存管理
"""
import json
import pickle
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import requests
from database import DatabaseInterface, UserSession, ScheduleCache
from models.course import Course


class CacheService:
    """缓存管理服务"""
    
    DEFAULT_CACHE_DURATION_HOURS = 24
    
    def __init__(self, db: DatabaseInterface, cache_duration_hours: int = None):
        """初始化：接收数据库接口，设置默认缓存时长"""
        self.db = db
        self.cache_duration = timedelta(hours=cache_duration_hours or self.DEFAULT_CACHE_DURATION_HOURS)
    
    def save_session(self, username: str, cookies, expires_hours: int = 24) -> bool:
        """
        保存用户会话到数据库
        参数cookies可以是dict或RequestsCookieJar
        使用pickle序列化完整cookie信息（含domain/path等）
        """
        now = datetime.now()
        expires_at = now + timedelta(hours=expires_hours)
        
        # 序列化cookie jar
        if isinstance(cookies, requests.cookies.RequestsCookieJar):
            cookies_dict = pickle.dumps(cookies)
        else:
            cookies_dict = pickle.dumps(cookies)
        
        # base64编码存储
        cookies_b64 = base64.b64encode(cookies_dict).decode('utf-8')
        
        session = UserSession(
            username=username, session_cookies={'pickle_b64': cookies_b64},
            created_at=now, updated_at=now,
            expires_at=expires_at, is_valid=True
        )
        
        return self.db.save_user_session(session)
    
    def get_session(self, username: str) -> Optional[requests.cookies.RequestsCookieJar]:
        """
        获取用户会话，自动检查过期
        返回RequestsCookieJar对象（可直接用于session.cookies.update）
        """
        session = self.db.get_user_session(username)
        if not session:
            return None
        
        # 过期检查
        if session.expires_at and datetime.now() > session.expires_at:
            self.db.update_session_validity(username, False)
            return None
        
        if not session.is_valid:
            return None
        
        # 反序列化cookies
        try:
            cookies_data = session.session_cookies
            if isinstance(cookies_data, dict) and 'pickle_b64' in cookies_data:
                cookies_bytes = base64.b64decode(cookies_data['pickle_b64'])
                return pickle.loads(cookies_bytes)
            else:
                # 兼容旧格式
                return cookies_data
        except Exception:
            return None
    
    def invalidate_session(self, username: str) -> bool:
        """标记会话无效"""
        return self.db.update_session_validity(username, False)
    
    def cache_courses(self, username: str, year: int, semester: str, 
                      courses: List[Course], duration_hours: int = None) -> bool:
        """缓存课表数据"""
        now = datetime.now()
        duration = timedelta(hours=duration_hours) if duration_hours else self.cache_duration
        expires_at = now + duration
        
        courses_data = json.dumps([course.to_dict() for course in courses])
        
        cache = ScheduleCache(
            username=username, year=year, semester=semester,
            courses_data=courses_data, created_at=now, expires_at=expires_at
        )
        
        return self.db.save_schedule_cache(cache)
    
    def get_cached_courses(self, username: str, year: int, semester: str) -> Optional[List[Course]]:
        """获取缓存课表，过期返回None"""
        cache = self.db.get_schedule_cache(username, year, semester)
        if not cache:
            return None
        
        if datetime.now() > cache.expires_at:
            return None
        
        try:
            courses_data = json.loads(cache.courses_data)
            return [Course.from_dict(data) for data in courses_data]
        except Exception:
            return None
    
    def invalidate_cache(self, username: str, year: int, semester: str) -> bool:
        return self.db.delete_schedule_cache(username, year, semester)
    
    def cleanup_expired(self) -> int:
        return self.db.delete_expired_caches()
    
    def get_stats(self) -> Dict[str, Any]:
        stats = self.db.get_cache_stats()
        return {
            'total_entries': stats.total_entries,
            'valid_entries': stats.valid_entries,
            'expired_entries': stats.expired_entries,
            'oldest_entry': stats.oldest_entry.isoformat() if stats.oldest_entry else None,
            'newest_entry': stats.newest_entry.isoformat() if stats.newest_entry else None
        }