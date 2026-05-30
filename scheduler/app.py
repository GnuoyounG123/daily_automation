from flask import Flask, jsonify, Response
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from services.sso import SSOService
from services.zdbk import ZdbkService, CaptchaError
from models.course import Course, CourseExporter

app = Flask(__name__)
app.config.from_object(Config)


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({'status': 'ok'})


@app.route('/api/timetable/current', methods=['GET'])
def get_current_timetable():
    """
    获取当前学期课表
    
    Returns:
        JSON格式的课表数据
    """
    try:
        sso = SSOService(timeout=Config.REQUEST_TIMEOUT)
        username, password = sso.load_credentials(str(Config.CREDENTIALS_FILE))
        
        service_url = 'https://zdbk.zju.edu.cn/jwglxt/xtgl/login_ssologin.html'
        if not sso.login(username, password, service_url):
            return jsonify({'error': '登录失败'}), 401
        
        zdbk = ZdbkService(sso.get_session(), timeout=Config.REQUEST_TIMEOUT)
        
        year = Config.CURRENT_YEAR
        semester = Config.CURRENT_SEMESTER
        
        raw_courses = zdbk.get_timetable(year, semester)
        courses = [Course.from_zdbk_dict(c) for c in raw_courses]
        
        csv_path = Config.OUTPUT_DIR / f'timetable_{year}_{semester.replace("|", "_")}.csv'
        CourseExporter.to_csv(courses, csv_path)
        
        return jsonify({
            'success': True,
            'year': year,
            'semester': semester,
            'count': len(courses),
            'courses': CourseExporter.to_dict_list(courses),
            'csv_file': str(csv_path)
        })
    
    except CaptchaError as e:
        return jsonify({'error': str(e), 'need_captcha': True}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/timetable/<int:year>/<semester>', methods=['GET'])
def get_timetable(year: int, semester: str):
    """
    获取指定学年学期的课表
    
    Args:
        year: 学年
        semester: 学期
    
    Returns:
        JSON格式的课表数据
    """
    try:
        sso = SSOService(timeout=Config.REQUEST_TIMEOUT)
        username, password = sso.load_credentials(str(Config.CREDENTIALS_FILE))
        
        service_url = 'https://zdbk.zju.edu.cn/jwglxt/xtgl/login_ssologin.html'
        if not sso.login(username, password, service_url):
            return jsonify({'error': '登录失败'}), 401
        
        zdbk = ZdbkService(sso.get_session(), timeout=Config.REQUEST_TIMEOUT)
        
        raw_courses = zdbk.get_timetable(year, semester)
        courses = [Course.from_zdbk_dict(c) for c in raw_courses]
        
        csv_path = Config.OUTPUT_DIR / f'timetable_{year}_{semester.replace("|", "_")}.csv'
        CourseExporter.to_csv(courses, csv_path)
        
        return jsonify({
            'success': True,
            'year': year,
            'semester': semester,
            'count': len(courses),
            'courses': CourseExporter.to_dict_list(courses),
            'csv_file': str(csv_path)
        })
    
    except CaptchaError as e:
        return jsonify({'error': str(e), 'need_captcha': True}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/captcha', methods=['GET'])
def get_captcha():
    """
    获取验证码图片
    
    Returns:
        验证码图片
    """
    try:
        sso = SSOService(timeout=Config.REQUEST_TIMEOUT)
        username, password = sso.load_credentials(str(Config.CREDENTIALS_FILE))
        
        if not sso.login(username, password):
            return jsonify({'error': '登录失败'}), 401
        
        zdbk = ZdbkService(sso.get_session(), timeout=Config.REQUEST_TIMEOUT)
        zdbk.access_main_page()
        
        captcha_bytes = zdbk.get_captcha()
        
        return Response(captcha_bytes, mimetype='image/jpeg')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)