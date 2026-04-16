#!/usr/bin/env python3
"""
浙江大学教务系统课表抓取测试
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
    print("浙江大学教务系统课表抓取")
    print("=" * 60)
    print(f"学期: {Config.CURRENT_YEAR}-{Config.CURRENT_YEAR+1}学年 {Config.CURRENT_SEMESTER}")
    
    try:
        sso = SSOService(timeout=Config.REQUEST_TIMEOUT)
        username, password = sso.load_credentials(str(Config.CREDENTIALS_FILE))
        print(f"账号: {username}")
        
        service_url = 'https://zdbk.zju.edu.cn/jwglxt/xtgl/login_ssologin.html'
        print("登录SSO...")
        if not sso.login(username, password, service_url):
            print("登录失败")
            return
        
        zdbk = ZdbkService(sso.get_session(), timeout=Config.REQUEST_TIMEOUT)
        
        print("抓取课表...")
        raw_courses = zdbk.get_timetable(Config.CURRENT_YEAR, Config.CURRENT_SEMESTER)
        courses = [Course.from_zdbk_dict(c) for c in raw_courses]
        
        csv_filename = f'timetable_{Config.CURRENT_YEAR}_{Config.CURRENT_SEMESTER.replace("|", "_")}.csv'
        csv_path = Config.OUTPUT_DIR / csv_filename
        CourseExporter.to_csv(courses, csv_path)
        
        print(f"\n成功！共 {len(courses)} 门课程")
        print(f"CSV: {csv_path}")
        print("=" * 60)
        
        for i, course in enumerate(courses, 1):
            print(f"{i}. {course.name}")
            print(f"   时间: {course.time}")
            print(f"   地点: {course.location}")
            print(f"   教师: {course.teacher}")
            print(f"   考试: {course.exam_time}")
        
    except CaptchaError as e:
        print(f"需要验证码: {e}")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()