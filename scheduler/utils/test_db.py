import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import json
from database import SQLiteDatabase, UserSession, ScheduleCache
from services.cache import CacheService
from services.sso import SSOService
from services.zdbk import ZdbkService
from models.course import Course
from config import config

TEST_DB_PATH = 'data/test_zju_schedule.db'

def test_database_basic():
    print("\n=== 测试数据库基本操作 ===")
    
    db = SQLiteDatabase(TEST_DB_PATH)
    if not db.connect():
        print("❌ 数据库连接失败")
        return False
    print("✓ 数据库连接成功")
    
    print("\n--- 测试用户会话存储 ---")
    test_cookies = {
        'JSESSIONID': 'test_session_id_12345',
        'route': 'test_route_value'
    }
    
    session = UserSession(
        username='test_user',
        session_cookies=test_cookies,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=24),
        is_valid=True
    )
    
    if db.save_user_session(session):
        print("✓ 用户会话保存成功")
    else:
        print("❌ 用户会话保存失败")
        return False
    
    retrieved = db.get_user_session('test_user')
    if retrieved and retrieved.session_cookies == test_cookies:
        print(f"✓ 用户会话读取成功: {retrieved.username}")
        print(f"  - Cookies: {retrieved.session_cookies}")
        print(f"  - 有效期至: {retrieved.expires_at}")
    else:
        print("❌ 用户会话读取失败")
        return False
    
    print("\n--- 测试课表缓存 ---")
    test_courses_data = json.dumps([
        {'name': '测试课程1', 'teacher': '教师A'},
        {'name': '测试课程2', 'teacher': '教师B'}
    ])
    
    cache = ScheduleCache(
        username='test_user',
        year=2025,
        semester='2|夏',
        courses_data=test_courses_data,
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=24)
    )
    
    if db.save_schedule_cache(cache):
        print("✓ 课表缓存保存成功")
    else:
        print("❌ 课表缓存保存失败")
        return False
    
    cached = db.get_schedule_cache('test_user', 2025, '2|夏')
    if cached and cached.courses_data == test_courses_data:
        print(f"✓ 课表缓存读取成功")
        print(f"  - 用户: {cached.username}")
        print(f"  - 学年学期: {cached.year} {cached.semester}")
        print(f"  - 过期时间: {cached.expires_at}")
    else:
        print("❌ 课表缓存读取失败")
        return False
    
    print("\n--- 测试缓存统计 ---")
    stats = db.get_cache_stats()
    print(f"缓存统计:")
    print(f"  - 总条目数: {stats.total_entries}")
    print(f"  - 有效条目: {stats.valid_entries}")
    print(f"  - 过期条目: {stats.expired_entries}")
    
    print("\n--- 测试清理功能 ---")
    if db.clear_all():
        print("✓ 数据清理成功")
    
    db.disconnect()
    print("✓ 数据库断开连接")
    return True


def test_cache_service():
    print("\n=== 测试缓存服务 ===")
    
    db = SQLiteDatabase(TEST_DB_PATH)
    db.connect()
    
    cache_service = CacheService(db, cache_duration_hours=24)
    
    print("\n--- 测试会话缓存 ---")
    test_cookies = {
        'JSESSIONID': 'session_abc123',
        'route': 'route_xyz789'
    }
    
    if cache_service.save_session('test_user_2', test_cookies, expires_hours=24):
        print("✓ 会话保存成功")
    
    retrieved_cookies = cache_service.get_session('test_user_2')
    if retrieved_cookies == test_cookies:
        print("✓ 会话读取成功")
        print(f"  Cookies: {retrieved_cookies}")
    
    if cache_service.is_session_valid('test_user_2'):
        print("✓ 会话有效性验证通过")
    
    print("\n--- 测试课表缓存 ---")
    test_courses = [
        Course(
            name='高等数学',
            time='周一 1-2节',
            location='东1-201',
            teacher='张老师',
            exam_time='2025-06-15(09:00-11:00)'
        ),
        Course(
            name='大学物理',
            time='周三 3-4节',
            location='东2-301',
            teacher='李老师',
            exam_time='未安排'
        )
    ]
    
    if cache_service.cache_courses('test_user_2', 2025, '2|夏', test_courses):
        print("✓ 课表缓存保存成功")
    
    cached_courses = cache_service.get_cached_courses('test_user_2', 2025, '2|夏')
    if cached_courses:
        print(f"✓ 课表缓存读取成功，共 {len(cached_courses)} 门课程:")
        for i, course in enumerate(cached_courses, 1):
            print(f"  {i}. {course.name} - {course.teacher} @ {course.location}")
    
    print("\n--- 测试缓存统计 ---")
    stats = cache_service.get_stats()
    print(f"缓存统计: {stats}")
    
    db.clear_all()
    db.disconnect()
    return True


def test_real_login_with_cache():
    print("\n=== 测试真实登录与会话缓存 ===")
    
    credentials_file = config['default'].CREDENTIALS_FILE
    if not credentials_file.exists():
        print("❌ 凭证文件不存在")
        return False
    
    with open(credentials_file, 'r') as f:
        creds = json.load(f)
    
    username = creds['username']
    password = creds['password']
    
    db = SQLiteDatabase(TEST_DB_PATH)
    db.connect()
    cache_service = CacheService(db)
    
    print(f"\n--- 测试用户: {username} ---")
    
    print("\n步骤1: 检查是否有缓存会话...")
    cached_session = cache_service.get_session(username)
    
    if cached_session:
        print("✓ 发现缓存会话")
        print(f"  Cookies: {list(cached_session.keys())}")
        
        print("\n步骤2: 使用缓存会话获取课表...")
        import requests
        session = requests.Session()
        session.cookies.update(cached_session)
        zdbk = ZdbkService(session=session)
        
        try:
            raw_courses = zdbk.get_timetable(2025, '2|夏')
            courses = [Course.from_zdbk_dict(c) for c in raw_courses]
            if courses:
                print(f"✓ 成功获取课表: {len(courses)} 门课程")
            else:
                print("⚠ 课表为空，会话可能已过期")
                cached_session = None
        except Exception as e:
            print(f"⚠ 使用缓存会话失败: {e}")
            cached_session = None
    
    if not cached_session:
        print("\n步骤3: 执行完整登录流程...")
        
        sso = SSOService()
        service_url = 'https://zdbk.zju.edu.cn/jwglxt/xtgl/login_ssologin.html'
        if not sso.login(username, password, service_url):
            print("❌ SSO登录失败")
            db.disconnect()
            return False
        print("✓ SSO登录成功")
        
        zdbk = ZdbkService(session=sso.get_session())
        
        print("\n步骤4: 保存会话到缓存...")
        cookies_dict = sso.get_session().cookies.get_dict()
        if cache_service.save_session(username, cookies_dict, expires_hours=24):
            print("✓ 会话已缓存，有效期24小时")
        
        print("\n步骤5: 获取课表并缓存...")
        raw_courses = zdbk.get_timetable(2025, '2|夏')
        courses = [Course.from_zdbk_dict(c) for c in raw_courses]
        if courses:
            print(f"✓ 获取课表成功: {len(courses)} 门课程")
            
            if cache_service.cache_courses(username, 2025, '2|夏', courses):
                print("✓ 课表已缓存")
    
    print("\n步骤6: 验证课表缓存...")
    cached_courses = cache_service.get_cached_courses(username, 2025, '2|夏')
    if cached_courses:
        print(f"✓ 课表缓存验证成功: {len(cached_courses)} 门课程")
        for i, course in enumerate(cached_courses[:3], 1):
            print(f"  {i}. {course.name} - {course.teacher}")
        if len(cached_courses) > 3:
            print(f"  ... 还有 {len(cached_courses) - 3} 门课程")
    
    print("\n步骤7: 查看缓存统计...")
    stats = cache_service.get_stats()
    print(f"当前缓存状态:")
    print(f"  - 总条目: {stats['total_entries']}")
    print(f"  - 有效条目: {stats['valid_entries']}")
    print(f"  - 过期条目: {stats['expired_entries']}")
    
    db.disconnect()
    return True


def test_cache_expiration():
    print("\n=== 测试缓存过期机制 ===")
    
    db = SQLiteDatabase(TEST_DB_PATH)
    db.connect()
    cache_service = CacheService(db)
    
    print("\n--- 创建即将过期的会话 ---")
    test_cookies = {'test': 'cookies'}
    
    if cache_service.save_session('expiring_user', test_cookies, expires_hours=0):
        print("✓ 创建过期时间为0小时的会话")
    
    import time
    time.sleep(1)
    
    result = cache_service.get_session('expiring_user')
    if result is None:
        print("✓ 过期会话正确返回None")
    else:
        print("❌ 过期会话未正确处理")
    
    print("\n--- 测试过期缓存清理 ---")
    test_courses = [Course(name='测试', time='测试', location='测试', teacher='测试', exam_time='未安排')]
    cache_service.cache_courses('expiring_user', 2025, '2|夏', test_courses, duration_hours=-1)
    
    deleted = cache_service.cleanup_expired()
    print(f"✓ 清理了 {deleted} 条过期缓存")
    
    db.clear_all()
    db.disconnect()
    return True


def main():
    print("=" * 60)
    print("浙江大学教务系统 - 数据库与缓存测试")
    print("=" * 60)
    
    tests = [
        ("数据库基本操作", test_database_basic),
        ("缓存服务", test_cache_service),
        ("真实登录与会话缓存", test_real_login_with_cache),
        ("缓存过期机制", test_cache_expiration)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 出错: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    for name, result in results:
        status = "✓ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    print("=" * 60)
    
    if os.path.exists(TEST_DB_PATH):
        print(f"\n测试数据库文件: {TEST_DB_PATH}")
        print(f"文件大小: {os.path.getsize(TEST_DB_PATH)} bytes")


if __name__ == '__main__':
    main()