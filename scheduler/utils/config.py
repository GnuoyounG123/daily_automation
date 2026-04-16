import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    CREDENTIALS_FILE = BASE_DIR / 'credentials.json'
    
    SSO_BASE_URL = 'https://zjuam.zju.edu.cn/cas'
    ZDBK_BASE_URL = 'https://zdbk.zju.edu.cn/jwglxt'
    
    CURRENT_YEAR = 2025
    CURRENT_SEMESTER = '2|夏'
    
    REQUEST_TIMEOUT = 30
    MAX_RETRY = 3
    
    OUTPUT_DIR = BASE_DIR / 'output'
    OUTPUT_DIR.mkdir(exist_ok=True)

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}