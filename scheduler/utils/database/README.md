# 数据库接口使用说明

## 架构设计

采用抽象接口模式，支持轻松扩展到MySQL、Redis等数据库。

```
database/
├── base.py        # 抽象接口 DatabaseInterface
├── models.py      # 数据模型 UserSession, ScheduleCache
├── sqlite_db.py   # SQLite实现
└── __init__.py
```

## 核心组件

### 1. 数据库接口 (DatabaseInterface)

抽象基类定义以下方法：
- `save_user_session()` / `get_user_session()` / `delete_user_session()` - 会话管理
- `save_schedule_cache()` / `get_schedule_cache()` / `delete_schedule_cache()` - 课表缓存
- `delete_expired_caches()` - 清理过期缓存
- `get_cache_stats()` - 获取统计信息

### 2. 数据模型

**UserSession** - 用户会话
```python
username: str              # 用户名
session_cookies: dict      # Session cookies
created_at: datetime       # 创建时间
updated_at: datetime       # 更新时间
expires_at: datetime       # 过期时间
is_valid: bool            # 是否有效
```

**ScheduleCache** - 课表缓存
```python
username: str              # 用户名
year: int                 # 学年
semester: str             # 学期
courses_data: str         # 课程JSON数据
created_at: datetime      # 创建时间
expires_at: datetime      # 过期时间
```

### 3. 缓存服务 (CacheService)

高级封装，简化使用：

```python
from database import SQLiteDatabase
from services.cache import CacheService

# 初始化
db = SQLiteDatabase('data/zju_schedule.db')
db.connect()
cache = CacheService(db, cache_duration_hours=24)

# 保存会话（无需存储密码）
cache.save_session('username', cookies_dict, expires_hours=24)

# 获取会话
cookies = cache.get_session('username')  # 自动检查过期

# 缓存课表
cache.cache_courses('username', 2025, '2|夏', courses_list)

# 获取缓存课表
courses = cache.get_cached_courses('username', 2025, '2|夏')

# 检查会话有效性
if cache.is_session_valid('username'):
    # 使用缓存会话
    pass
```

## 扩展到其他数据库

实现 `DatabaseInterface` 即可：

```python
from database.base import DatabaseInterface

class MySQLDatabase(DatabaseInterface):
    def __init__(self, host, user, password, database):
        # MySQL连接
        pass
    
    def save_user_session(self, session):
        # MySQL实现
        pass
    
    # ... 实现其他方法
```

## 测试

运行完整测试：
```bash
python3 test_db.py
```

测试覆盖：
- 数据库基本CRUD操作
- 会话缓存与过期机制
- 课表缓存与过期清理
- 真实登录流程集成
- 缓存统计功能