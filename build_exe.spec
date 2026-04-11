# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

added_files = [
    ('config.json', '.'),
    ('schedule.json', '.'),
    ('weekly_tasks.json', '.'),
    ('data', 'data'),
    ('logs', 'logs')
]

a = Analysis(['gui_app.py'],
             pathex=['C:\\Users\\lenovo\\Projects\\daily_automation'],
             binaries=[],
             datas=added_files,
             hiddenimports=['config_manager', 'daily_assistant', 'schedule_manager', 'app_paths'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz,
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
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )
