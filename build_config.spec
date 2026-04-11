# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置
用于打包配置中心界面
"""

import sys
from pathlib import Path

block_cipher = None

# 获取当前目录
current_dir = Path(SPECPATH)

a = Analysis(
    ['app.py'],
    pathex=[str(current_dir)],
    binaries=[],
    datas=[
        # 包含配置文件模板
        ('config.json', '.'),
        ('schedule.json', '.'),
        ('weekly_tasks.json', '.'),
    ],
    hiddenimports=[
        'streamlit',
        'streamlit.runtime.scriptrunner',
        'streamlit.runtime.caching',
        'config_manager',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DailyAutomationConfig',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保持控制台以查看日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加图标文件
)
