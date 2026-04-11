# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 - 启动器版本
打包命令行启动器，包含所有必要文件
"""

import sys
from pathlib import Path

block_cipher = None

current_dir = Path(SPECPATH)

a = Analysis(
    ['launcher.py'],
    pathex=[str(current_dir)],
    binaries=[],
    datas=[
        # 包含所有Python脚本和数据文件
        ('app.py', '.'),
        ('config_manager.py', '.'),
        ('daily_assistant.py', '.'),
        ('schedule_manager.py', '.'),
        ('config.json', '.'),
        ('schedule.json', '.'),
        ('weekly_tasks.json', '.'),
        ('weekly_tasks_template.json', '.'),
    ],
    hiddenimports=[
        'streamlit',
        'streamlit.runtime.scriptrunner',
        'streamlit.runtime.caching',
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
    name='DailyAutomation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
