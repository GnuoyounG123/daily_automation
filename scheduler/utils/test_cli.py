#!/usr/bin/env python3
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import SQLiteDatabase
from services.cache import CacheService
from services.sso import SSOService
from services.zdbk import ZdbkService
from models.course import Course
from utils.timetable import TimetableGrid
from utils.ical_exporter import ICalExporter
from config import Config
from prettytable import PrettyTable
import requests

DB_PATH = 'data/test_cli.db'


def test_timetable_grid():
    print("\n=== 测试课表网格解析 ===")
    
    test_courses = [
        Course(name='高等数学', time='周一 1-2节', location='东1-201', teacher='张老师', exam_time='2025年06月15日(09:00-11:00)'),
        Course(name='大学物理', time='周三 3-4节', location='东2-301', teacher='李老师', exam_time='未安排'),
        Course(name='程序设计', time='周五 6-8节', location='西1-401', teacher='王老师', exam_time='2025年06月20日(14:00-16:00)'),
        Course(name='线性代数', time='周二 1节', location='东3-101', teacher='赵老师', exam_time='2025年06月18日(09:00-11:00)'),
    ]
    
    grid = TimetableGrid()
    grid.load_courses(test_courses)
    
    print("课表内容:")
    table = PrettyTable()
    table.field_names = ['节次', '时间', '周一', '周二', '周三', '周四', '周五', '周六', '周日']
    
    for i, (slot_name, time_range) in enumerate(TimetableGrid.TIMESLOTS, 1):
        row = [slot_name, time_range]
        for day in TimetableGrid.WEEKDAYS:
            cell = grid.get_cell_content(day, i)
            row.append(cell if cell else '')
        table.add_row(row)
    
    print(table)
    
    print("\n考试信息:")
    exams = grid.get_all_exam_info()
    for exam in exams:
        print(f"  {exam['name']}: {exam['exam_time']}")
    
    return True


def test_ical_export():
    print("\n=== 测试iCal导出 ===")
    
    test_exams = [
        {'name': '高等数学', 'exam_time': '2025年06月15日(09:00-11:00)', 'location': '东1-201', 'teacher': '张老师'},
        {'name': '程序设计', 'exam_time': '2025年06月20日(14:00-16:00)', 'location': '西1-401', 'teacher': '王老师'},
        {'name': '线性代数', 'exam_time': '2025年06月18日(09:00-11:00)', 'location': '东3-101', 'teacher': '赵老师'},
    ]
    
    output_path = str(Config.OUTPUT_DIR / 'test_exams.ics')
    
    try:
        count = ICalExporter.export_exams(test_exams, output_path, "2025春夏")
        print(f"✓ 导出成功: {count} 门考试")
        print(f"  文件路径: {output_path}")
        
        with open(output_path, 'rb') as f:
            content = f.read()
            print(f"  文件大小: {len(content)} bytes")
        
        return True
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        return False


def test_real_schedule():
    print("\n=== 测试真实课表获取 ===")
    
    db = SQLiteDatabase(DB_PATH)
    if not db.connect():
        print("❌ 数据库连接失败")
        return False
    
    cache = CacheService(db)
    
    import json
    with open(Config.CREDENTIALS_FILE, 'r') as f:
        creds = json.load(f)
    
    username = creds['username']
    password = creds['password']
    
    cached = cache.get_cached_courses(username, Config.CURRENT_YEAR, Config.CURRENT_SEMESTER)
    if cached:
        print(f"✓ 使用缓存: {len(cached)} 门课程")
        courses = cached
    else:
        print("登录获取新课表...")
        
        sso = SSOService()
        service_url = 'https://zdbk.zju.edu.cn/jwglxt/xtgl/login_ssologin.html'
        if not sso.login(username, password, service_url):
            print("❌ 登录失败")
            db.disconnect()
            return False
        
        print("✓ SSO登录成功")
        
        cookies = sso.get_session().cookies.get_dict()
        cache.save_session(username, cookies)
        
        zdbk = ZdbkService(session=sso.get_session())
        raw_courses = zdbk.get_timetable(Config.CURRENT_YEAR, Config.CURRENT_SEMESTER)
        courses = [Course.from_zdbk_dict(c) for c in raw_courses]
        
        cache.cache_courses(username, Config.CURRENT_YEAR, Config.CURRENT_SEMESTER, courses)
        print(f"✓ 获取并缓存: {len(courses)} 门课程")
    
    grid = TimetableGrid()
    grid.load_courses(courses)
    
    print("\n课表展示 (前5节):")
    table = PrettyTable()
    table.field_names = ['节次', '周一', '周二', '周三', '周四', '周五']
    
    for i in range(1, 6):
        row = [f"第{i}节"]
        for day in ['周一', '周二', '周三', '周四', '周五']:
            cell = grid.get_cell_content(day, i)
            if cell:
                cell = cell[:15] + '...' if len(cell) > 15 else cell
            row.append(cell if cell else '')
        table.add_row(row)
    
    print(table)
    
    exams = grid.get_all_exam_info()
    print(f"\n考试安排: {len(exams)} 门")
    for exam in exams[:5]:
        print(f"  {exam['name']}: {exam['exam_time']}")
    
    if exams:
        output_path = str(Config.OUTPUT_DIR / f'exams_{Config.CURRENT_YEAR}_{Config.CURRENT_SEMESTER.replace("|", "_")}.ics')
        count = ICalExporter.export_exams(exams, output_path)
        print(f"\n✓ 已导出考试到: {output_path}")
    
    db.disconnect()
    return True


def main():
    print("=" * 70)
    print("浙江大学课表CLI - 功能测试")
    print("=" * 70)
    
    tests = [
        ("课表网格解析", test_timetable_grid),
        ("iCal导出", test_ical_export),
        ("真实课表获取", test_real_schedule),
    ]
    
    results = []
    for name, func in tests:
        try:
            result = func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} 失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 70)
    print("测试结果:")
    print("=" * 70)
    for name, result in results:
        status = "✓ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    print("\n提示: 运行 cli.py 进入交互式界面")


if __name__ == '__main__':
    main()