import re
import json
from typing import Tuple, Optional
import requests
from utils.crypto import RSAEncryptor


class SSOService:
    """浙大统一身份认证服务"""
    
    def __init__(self, timeout: int = 30):
        """初始化：创建新session对象"""
        self.session = requests.Session()
        self.timeout = timeout
        self.base_url = 'https://zjuam.zju.edu.cn/cas'
    
    def login(self, username: str, password: str, service_url: str = None) -> bool:
        """
        SSO登录
        参数：username=学号，password=密码，service_url=回调URL(如教务系统地址)
        流程：1.获取execution参数 2.获取RSA公钥 3.加密密码 4.提交登录
        返回：True表示成功，session中已含认证cookies
        """
        login_url = f'{self.base_url}/login'
        if service_url:
            login_url = f'{login_url}?service={service_url}'
        
        # 获取execution参数
        resp = self.session.get(login_url, timeout=self.timeout)
        match = re.search(r'name="execution" value="([^"]+)"', resp.text)
        if not match:
            raise Exception('获取execution失败')
        execution = match.group(1)
        
        # 获取RSA公钥并加密密码
        modulus, exponent = self.get_rsa_public_key()
        encrypted_pwd = RSAEncryptor.encrypt(password, modulus, exponent)
        
        # 提交登录表单
        data = {
            'username': username,
            'password': encrypted_pwd,
            'execution': execution,
            '_eventId': 'submit',
            'rememberMe': 'true'
        }
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        resp = self.session.post(
            login_url, data=data, headers=headers,
            allow_redirects=True, timeout=self.timeout
        )
        
        # 检查登录成功：session中有JSESSIONID和route
        return 'JSESSIONID' in self.session.cookies and 'route' in self.session.cookies
    
    def get_rsa_public_key(self) -> Tuple[str, str]:
        """获取RSA公钥参数，返回(modulus, exponent)"""
        url = f'{self.base_url}/v2/getPubKey'
        resp = self.session.get(url, timeout=self.timeout)
        data = resp.json()
        return data['modulus'], data['exponent']
    
    def get_session(self) -> requests.Session:
        """返回已认证的session对象"""
        return self.session