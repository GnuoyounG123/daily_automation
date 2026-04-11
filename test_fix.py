#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Automation 修复测试脚本
测试打包环境兼容性和邮件发送功能
"""

import sys
import os
from pathlib import Path

def test_paths():
    """测试路径检测"""
    print("=" * 60)
    print("路径配置测试")
    print("=" * 60)

    # 测试是否在打包环境中
    is_frozen = getattr(sys, 'frozen', False)
    print(f"打包环境检测 (sys.frozen): {is_frozen}")

    if is_frozen:
        print(f"sys.executable: {sys.executable}")
        if hasattr(sys, '_MEIPASS'):
            print(f"sys._MEIPASS: {sys._MEIPASS}")

    # 测试当前目录下的config.json
    current_dir = Path(__file__).parent
    config_file = current_dir / "config.json"
    print(f"\n当前目录: {current_dir}")
    print(f"config.json 存在: {config_file.exists()}")

    # 测试release目录（如果存在）
    release_dir = current_dir / "release"
    if release_dir.exists():
        print(f"\nrelease目录存在: {release_dir}")
        release_config = release_dir / "config.json"
        print(f"release/config.json 存在: {release_config.exists()}")

    return config_file.exists()

def test_daily_assistant_import():
    """测试daily_assistant模块导入"""
    print("\n" + "=" * 60)
    print("模块导入测试")
    print("=" * 60)

    try:
        # 尝试直接导入
        import daily_assistant
        print("[OK] daily_assistant 模块导入成功")

        # 测试路径配置
        print(f"CONFIG_DIR: {daily_assistant.CONFIG_DIR}")
        print(f"CONFIG_FILE: {daily_assistant.CONFIG_FILE}")
        print(f"CONFIG_FILE 存在: {daily_assistant.CONFIG_FILE.exists()}")

        return True
    except ImportError as e:
        print(f"[ERROR] 导入失败: {e}")

        # 尝试从文件导入
        try:
            import importlib.util
            current_dir = Path(__file__).parent
            spec = importlib.util.spec_from_file_location(
                "daily_assistant",
                str(current_dir / "daily_assistant.py")
            )
            if spec and spec.loader:
                daily_assistant = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(daily_assistant)
                print("[OK] 从文件导入 daily_assistant 成功")
                return True
        except Exception as e2:
            print(f"[ERROR] 文件导入也失败: {e2}")

    return False

def test_email_config():
    """测试邮件配置"""
    print("\n" + "=" * 60)
    print("邮件配置测试")
    print("=" * 60)

    try:
        # 加载配置
        import json
        config_file = Path(__file__).parent / "config.json"
        if not config_file.exists():
            print("[ERROR] config.json 文件不存在")
            return False

        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        email_config = config.get('email', {})
        enabled = email_config.get('enabled', False)
        smtp_server = email_config.get('smtp_server', '')
        sender_email = email_config.get('sender_email', '')

        print(f"邮件功能启用: {enabled}")
        print(f"SMTP服务器: {smtp_server}")
        print(f"发件邮箱: {sender_email}")

        if enabled and smtp_server and sender_email:
            print("[OK] 邮件配置基本正常")
            return True
        else:
            print("[WARN] 邮件配置不完整")
            return False

    except Exception as e:
        print(f"[ERROR] 配置读取失败: {e}")
        return False

def main():
    """主测试函数"""
    print("Daily Automation 修复测试")
    print("=" * 60)

    results = []

    # 运行测试
    results.append(("路径配置", test_paths()))
    results.append(("模块导入", test_daily_assistant_import()))
    results.append(("邮件配置", test_email_config()))

    # 显示结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "[OK] 通过" if passed else "[ERROR] 失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] 所有测试通过！")
        print("建议重新打包测试：运行 build.bat 选择选项1")
    else:
        print("[WARN] 部分测试失败")
        print("需要进一步调试，请根据上方错误信息修复")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())