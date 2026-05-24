#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a clean source-style release folder for manual testing."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELEASE_DIR = ROOT / "artifacts" / "release" / "manual"

INCLUDE_FILES = [
    "README.md",
    "requirements.txt",
    "config.example.json",
    "weekly_tasks_template.json",
    "app.py",
    "launcher.py",
    "daily_assistant.py",
    "gui_app.py",
    "config_manager.py",
    "schedule_manager.py",
    "password_crypto.py",
    "api_sources.py",
    "web_fetcher.py",
    "html_parser.py",
    "app_paths.py",
]

INCLUDE_DIRS = [
    "src",
    "scripts",
    "docs",
]


def copy_file(name: str) -> None:
    source = ROOT / name
    if source.exists():
        shutil.copy2(source, RELEASE_DIR / name)


def copy_dir(name: str) -> None:
    source = ROOT / name
    target = RELEASE_DIR / name
    if source.exists():
        shutil.copytree(
            source,
            target,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "user_guides",
            ),
        )


def create_release_package() -> Path:
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    RELEASE_DIR.mkdir(parents=True)

    for name in INCLUDE_FILES:
        copy_file(name)
    for name in INCLUDE_DIRS:
        copy_dir(name)

    exe = ROOT / "artifacts" / "manual_exe" / "DailyAutomation.exe"
    if exe.exists():
        shutil.copy2(exe, RELEASE_DIR / "DailyAutomation.exe")

    (RELEASE_DIR / "客户试跑说明.md").write_text(
        """# Daily Automation 客户试跑说明

推荐启动网页端：

```text
scripts\\windows\\启动网页端.bat
```

浏览器会打开：

```text
http://localhost:8501
```

首次运行会在当前目录生成 `runtime_local\\`，其中包含本机配置、密钥、日志和输出。
这些运行文件不应提交到 GitHub。
""",
        encoding="utf-8",
    )

    return RELEASE_DIR


if __name__ == "__main__":
    path = create_release_package()
    print(f"Release package created: {path}")
