#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Launcher for the local Daily Automation web UI and backend tasks."""

from __future__ import annotations

import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]


def start_web(port: int = 8501) -> int:
    root = project_root()
    app_file = root / "app.py"
    if not app_file.exists():
        print(f"[ERROR] Missing Streamlit entry: {app_file}")
        return 1

    url = f"http://localhost:{port}"
    print(f"[INFO] Starting local web UI: {url}")
    print("[INFO] Press Ctrl+C in this window to stop the server.")

    try:
        import streamlit  # noqa: F401
    except ModuleNotFoundError:
        print("[ERROR] Streamlit is not installed.")
        print("[FIX] Run: python -m pip install -r requirements.txt")
        return 1

    def open_when_ready() -> None:
        time.sleep(2)
        webbrowser.open(url)

    threading.Thread(target=open_when_ready, daemon=True).start()
    return subprocess.call([
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_file),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
        "--server.port",
        str(port),
    ], cwd=str(root))


def run_task(mode: str = "all") -> int:
    root = project_root()
    script = root / "daily_assistant.py"
    return subprocess.call([sys.executable, str(script), mode], cwd=str(root))


def main() -> int:
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command in {"web", "serve", "start"}:
            port = int(sys.argv[2]) if len(sys.argv) > 2 else 8501
            return start_web(port)
        if command in {"all", "crawl", "remind"}:
            return run_task(command)

    print("Daily Automation")
    print("1. 启动网页端")
    print("2. 运行完整任务")
    print("3. 只生成学术简报")
    print("4. 只检查提醒")
    print("5. 退出")

    while True:
        choice = input("请选择 [1-5]: ").strip()
        if choice == "1":
            return start_web()
        if choice == "2":
            return run_task("all")
        if choice == "3":
            return run_task("crawl")
        if choice == "4":
            return run_task("remind")
        if choice == "5":
            return 0
        print("无效选择，请输入 1-5。")


if __name__ == "__main__":
    raise SystemExit(main())
