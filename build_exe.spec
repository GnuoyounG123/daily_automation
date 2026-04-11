# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 - 桌面GUI版本
打包成单个exe文件，用户双击即用
"""

import sys
from pathlib import Path

block_cipher = None

current_dir = Path(SPECPATH)

a = Analysis(
    ['gui_app.py'],
    pathex=[str(current_dir)],
    binaries=[],
    datas=[
        # 包含数据文件
        ('config.json', '.'),
        ('schedule.json', '.'),
        ('weekly_tasks.json', '.'),
    ],
    hiddenimports=[
        'config_manager',
        'daily_assistant',
        'schedule_manager',
        'app_paths',
        'feedparser',
        'requests',
        'bs4',
        'smtplib',
        'email.mime.text',
        'email.mime.multipart',
        'email.header',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块，减小体积
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'PIL', 'cv2', 'IPython', 'jupyter',
        'torch', 'tensorflow', 'keras',
    ],
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
    console=False,  # 无控制台窗口，纯GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
