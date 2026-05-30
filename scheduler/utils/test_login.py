#!/usr/bin/env python3
"""
CLI登录态检测测试
验证：进入程序检测、登录流程、数据抓取
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database import SQLiteDatabase
from services.cache import CacheService
from services.sso import SSOService
from services.zdbk import ZdbkService
from models.course import Course
from config import Config
import json


def test_login_check():
    """测试登录态检测逻辑"""
    print("\n=== 测试登录态检测 ===")
    
    db = SQLiteDatabase('data/test_login.db')
    db.connect()
    cache = CacheService(db)
    
    # 情况1：无缓存会话
    cookies = cache.get_session('test_user')
    if cookies is None:
        print("✓ 无缓存会话时返回None")
    
    # 情况2：有缓存会话但过期
    cache.save_session('test_user', {'test': 'value'}, expires_hours=-1)
    cookies = cache.get_session('test_user')
    if cookies is None:
        print("✓ 过期会话返回None")
    
    db.disconnect()
    return True


def test_real_login_flow():
    """测试完整登录流程"""
    print("\n=== 测试真实登录流程 ===")
    
    with open(Config.CREDENTIALS_FILE, 'r') as f:
        creds = json.load(f)
    username = creds['username']
    password = creds['password']
    
    db = SQLiteDatabase('data/test_login.db')
    db.connect()
    cache = CacheService(db)
    
    # 步骤1：清除旧缓存
    db.delete_user_session(username)
    print("清除旧缓存...")
    
    # 步骤2：执行SSO登录
    print(f"登录用户: {username}")
    service_url = 'https://zdbk.zju.edu.cn/jwglxt/xtgl/login_ssologin.html'
    sso = SSOService()
    
    if not sso.login(username, password, service_url):
        print("❌ SSO登录失败")
        db.disconnect()
        return False
    
    print("✓ SSO登录成功")
    
    # 步骤3：保存session（使用完整cookie jar）
    session = sso.get_session()
    cache.save_session(username, session.cookies, expires_hours=24)
    print(f"✓ 保存session，cookies: {list(session.cookies.keys())}")
    
    # 步骤4：使用session获取课表
    print("获取课表...")
    zdbk = ZdbkService(session=session)
    
    try:
        raw_courses = zdbk.get_timetable(Config.CURRENT_YEAR, Config.CURRENT_SEMESTER)
        courses = [Course.from_zdbk_dict(c) for c in raw_courses]
        print(f"✓ 获取课表成功: {len(courses)} 门课程")
        
        # 步骤5：验证缓存恢复
        cached_cookies = cache.get_session(username)
        if cached_cookies:
            print(f"✓ 缓存恢复成功")
            
            # 用缓存cookies创建新session并测试
            import requests
            new_session = requests.Session()
            new_session.cookies.update(cached_cookies)
            
            new_zdbk = ZdbkService(session=new_session)
            raw_courses2 = new_zdbk.get_timetable(Config.CURRENT_YEAR, Config.CURRENT_SEMESTER)
            print(f"✓ 缓存会话可用，获取: {len(raw_courses2)} 门课程")
        
        return True
    except Exception as e:
        print(f"❌ 获取课表失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    db.disconnect()


def test_cli_check_login_status():
    """测试CLI的check_login_status方法"""
    print("\n=== 测试CLI登录态检测方法 ===")
    
    import requests
    from cli import ScheduleCLI
    
    cli = ScheduleCLI()
    cli.init_db()
    
    # 模拟已有缓存
    with open(Config.CREDENTIALS_FILE, 'r') as f:
        creds = json.load(f)
    username = creds['username']
    password = creds['password']
    
    # 先登录获取真实session
    service_url = 'https://zdbk.zju.edu.cn/jwglxt/xtgl/login_ssologin.html'
    sso = SSOService()
    if sso.login(username, password, service_url):
        cli.cache.save_session(username, sso.get_session().cookies, expires_hours=24)
        cli.username = username
        
        # 测试检测方法
        print(f"开始检测登录态...")
        print(f"  username已设置: {cli.username}")
        
        cached = cli.cache.get_session(username)
        print(f"  缓存cookies获取: {cached is not None}")
        
        if cli.check_login_status():
            print(f"✓ 登录态检测返回True")
            print(f"  session已设置: {cli.session is not None}")
            print(f"  is_logged_in: {cli.is_logged_in}")
        else:
            print("❌ 登录态检测返回False")
            print(f"  可能原因: cookies过期或课表获取失败")
    
    cli.close_db()
    return True


def main():
    print("=" * 60)
    print("CLI登录态检测测试")
    print("=" * 60)
    
    tests = [
        ("缓存会话过期检测", test_login_check),
        ("真实登录流程", test_real_login_flow),
        ("CLI登录态检测方法", test_cli_check_login_status),
    ]
    
    results = []
    for name, func in tests:
        try:
            result = func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name}出错: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("测试结果:")
    for name, result in results:
        status = "✓ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")


if __name__ == '__main__':
    main()