#!/usr/bin/env python3
"""
独立测试脚本 - 抓取当前学期课表并保存为CSV
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from services.sso import SSOService
from services.zdbk import ZdbkService, CaptchaError
from models.course import Course, CourseExporter


def main():
    print("=" * 60)
    print("浙江大学教务系统课表抓取测试")
    print("=" * 60)
    
    print(f"\n当前学期: {Config.CURRENT_YEAR}-{Config.CURRENT_YEAR+1}学年 {Config.CURRENT_SEMESTER}")
    print(f"凭证文件: {Config.CREDENTIALS_FILE}")
    print(f"输出目录: {Config.OUTPUT_DIR}")
    
    try:
        print("\n[1/4] 初始化SSO服务...")
        sso = SSOService(timeout=Config.REQUEST_TIMEOUT)
        
        print("[2/4] 加载登录凭证...")
        username, password = sso.load_credentials(str(Config.CREDENTIALS_FILE))
        print(f"      学号: {username}")
        
        print("[3/4] 登录统一身份认证...")
        if sso.login(username, password):
            print("      ✓ 登录成功")
        else:
            print("      ✗ 登录失败")
            return
        
        print("[4/4] 获取课表数据...")
        zdbk = ZdbkService(sso.get_session(), timeout=Config.REQUEST_TIMEOUT)
        
        if not zdbk.access_main_page():
            print("      ✗ 访问教务系统失败")
            return
        
        raw_courses = zdbk.get_timetable(Config.CURRENT_YEAR, Config.CURRENT_SEMESTER)
        print(f"      ✓ 获取到 {len(raw_courses)} 门课程")
        
        courses = [Course.from_zdbk_dict(c) for c in raw_courses]
        
        csv_filename = f'timetable_{Config.CURRENT_YEAR}_{Config.CURRENT_SEMESTER.replace("|", "_")}.csv'
        csv_path = Config.OUTPUT_DIR / csv_filename
        CourseExporter.to_csv(courses, csv_path)
        
        print(f"\n{'=' * 60}")
        print(f"✓ 成功！课表已保存到: {csv_path}")
        print(f"{'=' * 60}")
        
        print("\n课程列表:")
        print("-" * 60)
        for i, course in enumerate(courses, 1):
            print(f"{i}. {course.name}")
            print(f"   时间: {course.time}")
            print(f"   地点: {course.location}")
            print(f"   教师: {course.teacher}")
            print(f"   考试: {course.exam_time}")
        
    except CaptchaError as e:
        print(f"\n✗ 需要验证码: {e}")
        print("提示: 请通过Web API获取验证码")
    except FileNotFoundError as e:
        print(f"\n✗ 文件未找到: {e}")
        print(f"提示: 请确保 {Config.CREDENTIALS_FILE} 文件存在")
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()