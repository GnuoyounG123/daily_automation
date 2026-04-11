#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证release文件夹完整性
检查所有必需文件是否存在
"""

import os
import sys
from pathlib import Path

def verify_release():
    """验证release文件夹"""
    release_dir = Path(__file__).parent / "release"

    if not release_dir.exists():
        print("[ERROR] release文件夹不存在")
        return False

    print("=" * 60)
    print("验证release文件夹完整性")
    print("=" * 60)

    # 必需文件列表
    required_files = [
        ("DailyAutomation.exe", "主程序"),
        ("daily_assistant.py", "邮件发送核心"),
        ("config_manager.py", "配置管理核心"),
        ("config.json", "配置文件"),
        ("schedule.json", "日程配置"),
        ("weekly_tasks.json", "周任务配置"),
        ("create_desktop_shortcut.ps1", "快捷方式脚本"),
        ("一键安装.bat", "安装脚本"),
        ("添加快捷方式.bat", "快捷方式管理"),
        ("README.md", "说明文档"),
    ]

    all_ok = True
    for filename, description in required_files:
        filepath = release_dir / filename
        exists = filepath.exists()
        status = "[OK]" if exists else "[ERROR]"
        print(f"{status} {filename:25} - {description}")

        if not exists:
            all_ok = False
            if filename in ["daily_assistant.py", "config_manager.py", "config.json"]:
                print(f"     [严重] {filename} 是必需文件，缺失将导致功能失效")

    # 检查文件大小
    print("\n" + "=" * 60)
    print("文件大小检查")
    print("=" * 60)

    exe_path = release_dir / "DailyAutomation.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"DailyAutomation.exe: {size_mb:.1f} MB")
        if size_mb < 1:
            print("  [警告] EXE文件大小异常小，可能打包不完整")

    # 检查.py文件内容
    print("\n" + "=" * 60)
    print("Python文件内容检查")
    print("=" * 60)

    py_files = ["daily_assistant.py", "config_manager.py"]
    for py_file in py_files:
        filepath = release_dir / py_file
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                print(f"{py_file}: 第一行 - {first_line[:50]}")
            except Exception as e:
                print(f"{py_file}: [错误] 读取失败 - {e}")
        else:
            print(f"{py_file}: [缺失]")

    print("\n" + "=" * 60)
    if all_ok:
        print("[SUCCESS] release文件夹完整性验证通过")
        print("建议：运行 release\\DailyAutomation.exe 测试功能")
    else:
        print("[ERROR] release文件夹缺失必需文件")
        print("需要重新打包或手动补充缺失文件")

    return all_ok

if __name__ == "__main__":
    success = verify_release()
    sys.exit(0 if success else 1)