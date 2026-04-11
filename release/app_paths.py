#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用程序路径管理 - 统一处理打包环境和开发环境的路径问题
"""

import sys
from pathlib import Path


def get_app_dir() -> Path:
    """
    获取应用程序工作目录

    - 打包环境：exe所在目录（用户配置文件位置）
    - 开发环境：源码目录

    注意：配置文件（config.json）应该在exe所在目录，
    而不是PyInstaller的临时解压目录（sys._MEIPASS）
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller打包环境
        # sys.executable 是exe的完整路径
        return Path(sys.executable).parent
    else:
        # 开发环境
        return Path(__file__).parent


def get_internal_dir() -> Path:
    """
    获取内部资源目录（PyInstaller临时目录）

    打包的静态资源（如图标、模板等）在这里
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller打包环境
        if hasattr(sys, '_MEIPASS'):
            return Path(sys._MEIPASS)
        else:
            return Path(sys.executable).parent
    else:
        # 开发环境：与源码目录相同
        return Path(__file__).parent


# 预定义常用路径
APP_DIR = get_app_dir()
CONFIG_FILE = APP_DIR / "config.json"
SCHEDULE_FILE = APP_DIR / "schedule.json"
WEEKLY_TASKS_FILE = APP_DIR / "weekly_tasks.json"
DATA_DIR = APP_DIR / "data"
LOG_DIR = APP_DIR / "logs"


def ensure_dirs():
    """确保必要目录存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
