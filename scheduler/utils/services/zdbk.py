import re
import json
from typing import List, Dict, Optional
import requests


class ZdbkService:
    """教务系统服务，负责课表数据抓取"""
    
    def __init__(self, session: requests.Session, timeout: int = 30):
        """初始化：接收已认证的session对象"""
        self.session = session
        self.timeout = timeout
        self.base_url = 'https://zdbk.zju.edu.cn/jwglxt'
        self.captcha = ''
    
    def get_timetable(self, year: int, semester: str) -> List[Dict]:
        """
        获取课表原始数据
        参数：year=学年(如2025)，semester=学期(如"2|夏")
        返回：课表字典列表，含kcb字段
        异常：CaptchaError表示需要验证码
        """
        url = f'{self.base_url}/kbcx/xskbcx_cxXsKb.html'
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        data = {
            'xnm': year,
            'xqm': semester,
            'captcha_value': self.captcha
        }
        
        resp = self.session.post(url, data=data, headers=headers, timeout=self.timeout)
        
        if 'captcha_error' in resp.text:
            raise CaptchaError('需要验证码')
        
        timetable_json = re.search(r'(?<="kbList":)\[(.*?)\](?=,"xh")', resp.text)
        
        if not timetable_json:
            raise Exception('解析课表数据失败')
        
        courses = json.loads(f'[{timetable_json.group(1)}]')
        
        # 过滤有效课程：有kcb字段且非JS课程
        filtered = [c for c in courses if c.get('kcb') and c.get('sfyjskc') != '1']
        
        return filtered


class CaptchaError(Exception):
    """验证码错误异常"""
    pass