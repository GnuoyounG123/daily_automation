# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path.cwd()
block_cipher = None

added_files = [
    (str(ROOT / 'config.example.json'), '.'),
]

a = Analysis([str(ROOT / 'gui_app.py')],
             pathex=[str(ROOT), str(ROOT / 'src')],
             binaries=[],
             datas=added_files,
             hiddenimports=[
                 'daily_automation.config_manager',
                 'daily_automation.daily_assistant',
                 'daily_automation.schedule_manager',
                 'daily_automation.app_paths',
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[
                 'PyQt5',
                 'PyQt6',
                 'PySide2',
                 'PySide6',
             ],
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
