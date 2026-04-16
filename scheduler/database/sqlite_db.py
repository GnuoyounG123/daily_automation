"""
SQLite数据库实现
用于本地存储会话和课表缓存
"""
import sqlite3
import os
from typing import Optional
from datetime import datetime
from .base import DatabaseInterface
from .models import UserSession, ScheduleCache, CacheStats


class SQLiteDatabase(DatabaseInterface):
    """SQLite数据库操作类"""
    
    def __init__(self, db_path: str = "data/zju_schedule.db"):
        """初始化：设置数据库路径，自动创建目录"""
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self._ensure_directory()
    
    def _ensure_directory(self):
        dir_path = os.path.dirname(self.db_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
    
    def connect(self) -> bool:
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self._create_tables()
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False
    
    def disconnect(self) -> bool:
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                return True
            except Exception:
                return False
        return True
    
    def is_connected(self) -> bool:
        return self.connection is not None
    
    def _create_tables(self):
        cursor = self.connection.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                username TEXT PRIMARY KEY,
                session_cookies TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT,
                is_valid INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedule_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                year INTEGER NOT NULL,
                semester TEXT NOT NULL,
                courses_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                UNIQUE(username, year, semester)
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cache_expires 
            ON schedule_cache(expires_at)
        ''')
        
        self.connection.commit()
    
    def save_user_session(self, session: UserSession) -> bool:
        try:
            cursor = self.connection.cursor()
            data = session.to_dict()
            cursor.execute('''
                INSERT OR REPLACE INTO user_sessions 
                (username, session_cookies, created_at, updated_at, expires_at, is_valid)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data['username'],
                data['session_cookies'],
                data['created_at'],
                data['updated_at'],
                data['expires_at'],
                int(data['is_valid'])
            ))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error saving user session: {e}")
            return False
    
    def get_user_session(self, username: str) -> Optional[UserSession]:
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT * FROM user_sessions WHERE username = ?
            ''', (username,))
            row = cursor.fetchone()
            if row:
                return UserSession.from_dict(dict(row))
            return None
        except Exception as e:
            print(f"Error getting user session: {e}")
            return None
    
    def delete_user_session(self, username: str) -> bool:
        try:
            cursor = self.connection.cursor()
            cursor.execute('DELETE FROM user_sessions WHERE username = ?', (username,))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error deleting user session: {e}")
            return False
    
    def update_session_validity(self, username: str, is_valid: bool) -> bool:
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                UPDATE user_sessions 
                SET is_valid = ?, updated_at = ?
                WHERE username = ?
            ''', (int(is_valid), datetime.now().isoformat(), username))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error updating session validity: {e}")
            return False
    
    def save_schedule_cache(self, cache: ScheduleCache) -> bool:
        try:
            cursor = self.connection.cursor()
            data = cache.to_dict()
            cursor.execute('''
                INSERT OR REPLACE INTO schedule_cache 
                (username, year, semester, courses_data, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data['username'],
                data['year'],
                data['semester'],
                data['courses_data'],
                data['created_at'],
                data['expires_at']
            ))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error saving schedule cache: {e}")
            return False
    
    def get_schedule_cache(self, username: str, year: int, semester: str) -> Optional[ScheduleCache]:
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT * FROM schedule_cache 
                WHERE username = ? AND year = ? AND semester = ?
            ''', (username, year, semester))
            row = cursor.fetchone()
            if row:
                return ScheduleCache.from_dict(dict(row))
            return None
        except Exception as e:
            print(f"Error getting schedule cache: {e}")
            return None
    
    def delete_schedule_cache(self, username: str, year: int, semester: str) -> bool:
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                DELETE FROM schedule_cache 
                WHERE username = ? AND year = ? AND semester = ?
            ''', (username, year, semester))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error deleting schedule cache: {e}")
            return False
    
    def delete_expired_caches(self) -> int:
        try:
            cursor = self.connection.cursor()
            now = datetime.now().isoformat()
            cursor.execute('DELETE FROM schedule_cache WHERE expires_at < ?', (now,))
            deleted = cursor.rowcount
            self.connection.commit()
            return deleted
        except Exception as e:
            print(f"Error deleting expired caches: {e}")
            return 0
    
    def get_cache_stats(self) -> CacheStats:
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT COUNT(*) FROM schedule_cache')
            total = cursor.fetchone()[0]
            
            now = datetime.now().isoformat()
            cursor.execute('SELECT COUNT(*) FROM schedule_cache WHERE expires_at >= ?', (now,))
            valid = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM schedule_cache WHERE expires_at < ?', (now,))
            expired = cursor.fetchone()[0]
            
            cursor.execute('SELECT MIN(created_at) FROM schedule_cache')
            oldest = cursor.fetchone()[0]
            oldest_dt = datetime.fromisoformat(oldest) if oldest else None
            
            cursor.execute('SELECT MAX(created_at) FROM schedule_cache')
            newest = cursor.fetchone()[0]
            newest_dt = datetime.fromisoformat(newest) if newest else None
            
            return CacheStats(
                total_entries=total,
                valid_entries=valid,
                expired_entries=expired,
                oldest_entry=oldest_dt,
                newest_entry=newest_dt
            )
        except Exception as e:
            print(f"Error getting cache stats: {e}")
            return CacheStats(0, 0, 0, None, None)
    
    def clear_all(self) -> bool:
        try:
            cursor = self.connection.cursor()
            cursor.execute('DELETE FROM user_sessions')
            cursor.execute('DELETE FROM schedule_cache')
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error clearing all: {e}")
            return False
    
    def cleanup(self):
        self.delete_expired_caches()
        if self.connection:
            self.connection.commit()