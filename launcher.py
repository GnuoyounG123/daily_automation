#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Automation 启动器
整合配置界面和运行功能
"""

import os
import sys
import subprocess
import webbrowser
import threading
import time
from pathlib import Path

# 获取程序目录
APP_DIR = Path(__file__).parent


def start_streamlit():
    """启动 Streamlit 配置界面"""
    os.chdir(APP_DIR)
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "app.py",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--server.port", "8501"
    ])


def open_browser():
    """延迟打开浏览器"""
    time.sleep(2)
    webbrowser.open("http://localhost:8501")


def run_daily_task():
    """运行一次日常任务"""
    os.chdir(APP_DIR)
    subprocess.run([sys.executable, "daily_assistant.py"])


def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║          📚 Daily Automation - 学术自动化助手                    ║
╠════════════════════════════════════════════════════════════════╣
║  1. 打开配置界面 (Web)                                          ║
║  2. 运行一次爬取任务                                            ║
║  3. 退出                                                       ║
╚════════════════════════════════════════════════════════════════╝
""")

    while True:
        try:
            choice = input("请选择 [1-3]: ").strip()

            if choice == "1":
                print("\n正在启动配置界面...")
                print("浏览器将自动打开 http://localhost:8501")
                print("按 Ctrl+C 停止服务\n")

                # 启动浏览器
                browser_thread = threading.Thread(target=open_browser)
                browser_thread.daemon = True
                browser_thread.start()

                # 启动 Streamlit
                start_streamlit()

            elif choice == "2":
                print("\n正在运行爬取任务...\n")
                run_daily_task()
                print("\n任务完成！\n")

            elif choice == "3":
                print("\n再见！")
                break
            else:
                print("无效选择，请输入 1-3")

        except KeyboardInterrupt:
            print("\n\n已退出")
            break
        except Exception as e:
            print(f"错误: {e}")


if __name__ == "__main__":
    main()
