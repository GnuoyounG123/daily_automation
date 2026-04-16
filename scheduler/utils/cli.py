#!/usr/bin/env python3
"""
浙江大学课表CLI - 交互式课表管理系统
"""
import sys
import os
import json
import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from prettytable import PrettyTable
import requests

from database import SQLiteDatabase
from services.cache import CacheService
from services.sso import SSOService
from services.zdbk import ZdbkService, CaptchaError
from models.course import Course
from utils.timetable import TimetableGrid
from utils.ical_exporter import ICalExporter
from config import Config

DB_PATH = 'data/zju_schedule.db'


class ScheduleCLI:
    """CLI主控制器"""
    
    def __init__(self):
        """初始化CLI，设置数据库、缓存和用户状态"""
        self.db = None
        self.cache = None
        self.username = None
        self.session = None  # 当前活跃的session对象
        self.is_logged_in = False
    
    def init_db(self) -> bool:
        """连接SQLite数据库并初始化缓存服务"""
        self.db = SQLiteDatabase(DB_PATH)
        if not self.db.connect():
            print("❌ 数据库连接失败")
            return False
        self.cache = CacheService(self.db)
        return True
    
    def close_db(self):
        """断开数据库连接"""
        if self.db:
            self.db.disconnect()
    
    def clear_screen(self):
        """清屏"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def print_header(self, title: str):
        """显示页面标题"""
        self.clear_screen()
        print("=" * 70)
        print(f"  浙江大学教务系统 - {title}")
        print("=" * 70)
        print()
    
    def check_login_status(self) -> bool:
        """
        检查当前登录态有效性
        通过尝试获取课表来验证session是否有效
        返回True表示已登录且有效，False表示需要重新登录
        """
        if not self.username:
            return False
        
        cached_cookies = self.cache.get_session(self.username)
        if not cached_cookies:
            return False
        
        session = requests.Session()
        session.cookies.update(cached_cookies)
        
        zdbk = ZdbkService(session=session)
        try:
            raw_courses = zdbk.get_timetable(Config.CURRENT_YEAR, Config.CURRENT_SEMESTER)
            if raw_courses and len(raw_courses) > 0:
                self.session = session
                self.is_logged_in = True
                return True
        except Exception:
            pass
        
        return False
    
    def prompt_credentials(self) -> tuple:
        """
        提示用户输入学号和密码
        返回 或 None
        """
        print("\n请输入登录信息：")
        print("(输入后回车确认)")
        
        username = input("学号: ").strip()
        if not username:
            print("❌ 学号不能为空")
            return None
        
        password = getpass.getpass("密码: ").strip()
        if not password:
            print("❌ 密码不能为空")
            return None
        
        return username, password
    
    def do_login(self) -> bool:
        """
        执行SSO登录流程
        1. 提示输入学号密码
        2. SSO认证
        3. 保存session到缓存
        返回True表示登录成功
        """
        creds = self.prompt_credentials()
        if not creds:
            return False
        
        username, password = creds
        self.username = username
        
        print(f"\n正在登录 SSO...")
        service_url = 'https://zdbk.zju.edu.cn/jwglxt/xtgl/login_ssologin.html'
        
        sso = SSOService()
        if not sso.login(username, password, service_url):
            print("❌ SSO登录失败")
            return False
        
        print("✓ SSO登录成功")
        
        self.session = sso.get_session()
        
        # 保存完整的cookie jar（含domain/path等信息）
        if self.cache.save_session(username, self.session.cookies, expires_hours=24):
            print("✓ 会话已缓存(24小时)")
        
        self.is_logged_in = True
        return True
    
    def fetch_schedule(self) -> list:
        """
        获取课表数据
        优先使用缓存课表，否则从服务器获取
        返回Course对象列表
        """
        if not self.is_logged_in:
            print("⚠ 请先登录")
            return []
        
        cached = self.cache.get_cached_courses(self.username, Config.CURRENT_YEAR, Config.CURRENT_SEMESTER)
        if cached:
            print(f"✓ 使用缓存课表({len(cached)}门)")
            return cached
        
        print("\n正在从服务器获取课表...")
        
        zdbk = ZdbkService(session=self.session)
        
        try:
            raw_courses = zdbk.get_timetable(Config.CURRENT_YEAR, Config.CURRENT_SEMESTER)
            courses = [Course.from_zdbk_dict(c) for c in raw_courses]
            
            if courses:
                self.cache.cache_courses(self.username, Config.CURRENT_YEAR, 
                                         Config.CURRENT_SEMESTER, courses)
                print(f"✓ 获取成功({len(courses)}门)")
            
            return courses
        except CaptchaError:
            print("❌ 需要验证码，请稍后重试")
            return []
        except Exception as e:
            print(f"❌ 获取失败: {e}")
            return []
    
    def display_schedule(self, courses: list):
        """
        显示课表表格
        格式：13节×7天，含课程名称和地点
        """
        self.print_header(f"课表({Config.CURRENT_YEAR}-{Config.CURRENT_YEAR+1} {Config.CURRENT_SEMESTER})")
        
        if not courses:
            print("暂无课表数据")
            return
        
        grid = TimetableGrid()
        grid.load_courses(courses)
        
        table = PrettyTable()
        table.field_names = ['节次', '时间', '周一', '周二', '周三', '周四', '周五', '周六', '周日']
        table.align = 'c'
        
        for i, (slot_name, time_range) in enumerate(TimetableGrid.TIMESLOTS, 1):
            row = [slot_name, time_range]
            for day in TimetableGrid.WEEKDAYS:
                content = grid.get_cell_content(day, i)
                row.append(content if content else '')
            table.add_row(row)
        
        print(table)
        print(f"\n共{len(courses)}条课程记录")
    
    def display_exams(self, courses: list):
        """
        显示考试安排列表
        格式：课程名称、考试时间、地点
        """
        self.print_header("考试安排")
        
        if not courses:
            print("暂无课表数据")
            return
        
        grid = TimetableGrid()
        grid.load_courses(courses)
        
        exams = grid.get_all_exam_info()
        
        if not exams:
            print("暂无考试安排")
            return
        
        print(f"{'课程名称':<30} {'考试时间':<25} {'地点':<20}")
        print("-" * 75)
        
        for exam in exams:
            name = exam['name'][:28] if len(exam['name']) > 28 else exam['name']
            print(f"{name:<30} {exam['exam_time']:<25} {exam['location']:<20}")
        
        print(f"\n共{len(exams)}门考试")
    
    def export_ical(self, courses: list):
        """
        导出考试信息到iCal文件
        文件保存到output目录，可导入日历应用
        """
        if not courses:
            print("暂无课表数据")
            return
        
        grid = TimetableGrid()
        grid.load_courses(courses)
        
        exams = grid.get_all_exam_info()
        
        if not exams:
            print("暂无考试安排")
            return
        
        output_path = Config.OUTPUT_DIR / f'exams_{Config.CURRENT_YEAR}_{Config.CURRENT_SEMESTER.replace("|", "_")}.ics'
        
        try:
            count = ICalExporter.export_exams(exams, str(output_path))
            print(f"✓ 已导出{count}门考试到: {output_path}")
        except Exception as e:
            print(f"❌ 导出失败: {e}")
    
    def clear_cache_menu(self):
        """
        清除缓存菜单
        提供：清除会话、清除课表、清除所有选项
        """
        self.print_header("清除缓存")
        
        if not self.username:
            print("请先登录")
            return
        
        print(f"当前用户: {self.username}")
        print("\n1. 清除会话缓存")
        print("2. 清除课表缓存")
        print("3. 清除所有缓存")
        print("0. 返回")
        
        choice = input("\n请选择: ").strip()
        
        if choice == '1':
            self.db.delete_user_session(self.username)
            self.is_logged_in = False
            self.session = None
            print("✓ 会话缓存已清除")
        elif choice == '2':
            self.db.delete_schedule_cache(self.username, Config.CURRENT_YEAR, Config.CURRENT_SEMESTER)
            print("✓ 课表缓存已清除")
        elif choice == '3':
            self.db.delete_user_session(self.username)
            self.db.delete_expired_caches()
            self.is_logged_in = False
            self.session = None
            print("✓ 所有缓存已清除")
        
        input("\n按回车键继续...")
    
    def show_stats(self):
        """
        显示缓存统计信息
        包括：总条目数、有效/过期条目、时间范围
        """
        self.print_header("缓存统计")
        
        stats = self.cache.get_stats()
        
        print(f"总缓存条目: {stats['total_entries']}")
        print(f"有效条目: {stats['valid_entries']}")
        print(f"过期条目: {stats['expired_entries']}")
        
        if stats['oldest_entry']:
            print(f"最早缓存: {stats['oldest_entry']}")
        if stats['newest_entry']:
            print(f"最新缓存: {stats['newest_entry']}")
        
        input("\n按回车键继续...")
    
    def run(self):
        """
        CLI主循环
        进入时检测登录态，无效则跳转登录菜单
        """
        if not self.init_db():
            return
        
        if self.check_login_status():
            print(f"✓ 已登录: {self.username}")
        else:
            print("⚠ 未登录或会话过期")
            print("\n跳转到登录...")
            if not self.do_login():
                print("登录失败，程序退出")
                return
        
        try:
            while True:
                self.print_header("主菜单")
                
                status = "已登录" if self.is_logged_in else "未登录"
                print(f"状态: {status} | 用户: {self.username or '未知'}")
                print()
                
                print("1. 查看课表")
                print("2. 查看考试安排")
                print("3. 导出考试到日历(iCal)")
                print("4. 重新登录")
                print("5. 清除缓存")
                print("6. 查看缓存统计")
                print("0. 退出")
                print()
                
                choice = input("请选择: ").strip()
                
                if choice == '1':
                    courses = self.fetch_schedule()
                    self.display_schedule(courses)
                    input("\n按回车键继续...")
                
                elif choice == '2':
                    courses = self.fetch_schedule()
                    self.display_exams(courses)
                    input("\n按回车键继续...")
                
                elif choice == '3':
                    courses = self.fetch_schedule()
                    self.export_ical(courses)
                    input("\n按回车键继续...")
                
                elif choice == '4':
                    if self.do_login():
                        print("\n✓ 登录成功")
                    input("\n按回车键继续...")
                
                elif choice == '5':
                    self.clear_cache_menu()
                
                elif choice == '6':
                    self.show_stats()
                
                elif choice == '0':
                    print("\n再见！")
                    break
                
                else:
                    print("\n无效选择")
                    input("按回车键继续...")
        
        finally:
            self.close_db()


def main():
    """CLI入口点"""
    cli = ScheduleCLI()
    cli.run()


if __name__ == '__main__':
    main()