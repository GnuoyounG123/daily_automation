"""
数据库抽象接口
定义标准操作方法，支持扩展到MySQL/Redis等
"""
from abc import ABC, abstractmethod
from typing import Optional
from .models import UserSession, ScheduleCache, CacheStats


class DatabaseInterface(ABC):
    """数据库操作抽象基类"""
    
    @abstractmethod
    def connect(self) -> bool:
        """连接数据库"""
    
    @abstractmethod
    def disconnect(self) -> bool:
        """断开连接"""
    
    @abstractmethod
    def save_user_session(self, session: UserSession) -> bool:
        """保存用户会话"""
    
    @abstractmethod
    def get_user_session(self, username: str) -> Optional[UserSession]:
        """获取用户会话"""
    
    @abstractmethod
    def delete_user_session(self, username: str) -> bool:
        """删除用户会话"""
    
    @abstractmethod
    def update_session_validity(self, username: str, is_valid: bool) -> bool:
        """更新会话有效性"""
    
    @abstractmethod
    def save_schedule_cache(self, cache: ScheduleCache) -> bool:
        """保存课表缓存"""
    
    @abstractmethod
    def get_schedule_cache(self, username: str, year: int, semester: str) -> Optional[ScheduleCache]:
        """获取课表缓存"""
    
    @abstractmethod
    def delete_schedule_cache(self, username: str, year: int, semester: str) -> bool:
        """删除课表缓存"""
    
    @abstractmethod
    def delete_expired_caches(self) -> int:
        """删除过期缓存，返回删除数量"""
    
    @abstractmethod
    def get_cache_stats(self) -> CacheStats:
        """获取缓存统计"""