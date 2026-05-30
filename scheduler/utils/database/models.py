from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class UserSession:
    username: str
    session_cookies: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    is_valid: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'username': self.username,
            'session_cookies': json.dumps(self.session_cookies),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_valid': self.is_valid
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSession':
        return cls(
            username=data['username'],
            session_cookies=json.loads(data['session_cookies']) if isinstance(data['session_cookies'], str) else data['session_cookies'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            is_valid=data.get('is_valid', True)
        )


@dataclass
class ScheduleCache:
    username: str
    year: int
    semester: str
    courses_data: str
    created_at: datetime
    expires_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'username': self.username,
            'year': self.year,
            'semester': self.semester,
            'courses_data': self.courses_data,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduleCache':
        return cls(
            username=data['username'],
            year=data['year'],
            semester=data['semester'],
            courses_data=data['courses_data'],
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=datetime.fromisoformat(data['expires_at'])
        )
    
    @property
    def cache_key(self) -> str:
        return f"{self.username}_{self.year}_{self.semester}"


@dataclass
class CacheStats:
    total_entries: int
    valid_entries: int
    expired_entries: int
    oldest_entry: Optional[datetime]
    newest_entry: Optional[datetime]