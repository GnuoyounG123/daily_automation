#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Streamlit web UI for the local Daily Automation app."""

from __future__ import annotations

import base64
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

import streamlit as st

from .config_manager import ConfigManager
from .password_crypto import PasswordCrypto


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return _project_root() / "runtime_local"


def _daily_assistant_script() -> Path:
    return _project_root() / "daily_assistant.py"


def _decode_pwd(value: str) -> str:
    if not value:
        return ""
    if value.startswith("fernet:"):
        try:
            return PasswordCrypto(_app_dir()).decrypt(value)
        except Exception:
            return value
    if value.startswith("enc:"):
        try:
            return base64.b64decode(value[4:]).decode("utf-8")
        except Exception:
            return value
    return value


def _encode_pwd(value: str) -> str:
    if value and not value.startswith(("enc:", "fernet:")):
        try:
            return PasswordCrypto(_app_dir()).encrypt(value)
        except Exception:
            return "enc:" + base64.b64encode(value.encode("utf-8")).decode("utf-8")
    return value


def _latest_file(pattern: str) -> Path | None:
    data_dir = _app_dir() / "data"
    if not data_dir.exists():
        return None
    files = sorted(data_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _read_text(path: Path, limit: int = 20000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"读取失败：{exc}"
    return text[:limit]


def _line_tag(line: str) -> str:
    lower = line.lower()
    if any(token in lower for token in ("error", "failed", "exception", "traceback")):
        return "error"
    if any(token in line for token in ("错误", "失败", "异常", "严重")):
        return "error"
    if "warning" in lower or any(token in line for token in ("警告", "未配置", "未完成")):
        return "warning"
    return "info"


def _summarize_issues(lines: Iterable[str]) -> list[str]:
    issues: list[str] = []
    for line in lines:
        if _line_tag(line) in {"error", "warning"}:
            clean = line.strip()
            if clean and clean not in issues:
                issues.append(clean)
    return issues[:8]


def run_backend(mode: str) -> tuple[int, list[str], list[str]]:
    """Run backend task and stream progress into Streamlit."""
    app_dir = _app_dir()
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "logs").mkdir(exist_ok=True)

    cmd = [sys.executable, str(_daily_assistant_script()), mode]
    output_queue: queue.Queue[str | None] = queue.Queue()
    output_lines: list[str] = []

    def reader(pipe) -> None:
        try:
            for raw in iter(pipe.readline, ""):
                if not raw:
                    break
                output_queue.put(raw.rstrip("\r\n"))
        finally:
            output_queue.put(None)

    with st.status("任务已启动，正在生成输出。这个过程可能需要 1-5 分钟。", expanded=True) as status:
        st.caption("执行命令：" + " ".join(cmd))
        progress = st.progress(0)
        log_box = st.empty()
        heartbeat = st.empty()

        process = subprocess.Popen(
            cmd,
            cwd=str(_project_root()),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdout is not None
        threading.Thread(target=reader, args=(process.stdout,), daemon=True).start()

        start = time.monotonic()
        last_heartbeat = start
        reader_done = False

        while process.poll() is None or not reader_done:
            try:
                item = output_queue.get(timeout=1)
            except queue.Empty:
                item = "__heartbeat__"

            now = time.monotonic()
            elapsed = int(now - start)

            if item is None:
                reader_done = True
            elif item == "__heartbeat__":
                if now - last_heartbeat >= 10:
                    heartbeat.info(f"仍在运行，已用时 {elapsed} 秒。请不要重复点击。")
                    last_heartbeat = now
            else:
                output_lines.append(item)
                tail = "\n".join(output_lines[-80:])
                log_box.code(tail or "等待后端输出...", language="text")

            progress.progress(min(95, 10 + (elapsed % 85)))

        returncode = process.wait()
        progress.progress(100)

        issues = _summarize_issues(output_lines)
        if returncode == 0 and not issues:
            status.update(label="任务完成。", state="complete", expanded=False)
        elif returncode == 0:
            status.update(label="任务完成，但存在警告。", state="complete", expanded=True)
        else:
            status.update(label="任务失败。", state="error", expanded=True)

    return returncode, output_lines, issues


def render_briefing_home(config: dict) -> None:
    st.header("今日简报")

    sources = config.get("news_sources", [])
    enabled_sources = [s for s in sources if s.get("enabled", True)]
    email = config.get("email", {})
    latest_report = _latest_file("academic_briefing_*.md")
    latest_plan = _latest_file("daily_plan_*.html")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("最新简报", latest_report.name if latest_report else "未生成")
    col2.metric("启用来源", str(len(enabled_sources)))
    col3.metric("邮箱", "已配置" if email.get("enabled") else "未启用")
    col4.metric("运行目录", str(_app_dir().name))

    if st.button("生成并发送今日简报", type="primary", use_container_width=True):
        returncode, _lines, issues = run_backend("all")
        if returncode == 0 and not issues:
            st.success("生成完成。已刷新最新输出。")
            st.rerun()
        elif returncode == 0:
            st.warning("生成完成，但部分来源或步骤存在问题。")
            for issue in issues:
                st.write("- " + issue)
            st.rerun()
        else:
            st.error(f"生成失败，返回码：{returncode}")
            for issue in issues:
                st.write("- " + issue)

    st.subheader("简报预览")
    if latest_report:
        st.caption(f"文件：{latest_report}")
        st.markdown(_read_text(latest_report))
    else:
        st.info("还没有生成过简报。点击上方按钮开始第一次运行。")

    if latest_plan:
        with st.expander("查看今日计划 HTML 文件路径"):
            st.code(str(latest_plan), language="text")


def render_control_console() -> None:
    st.header("控制台")
    st.caption("这里用于手动执行任务，并实时显示后端输出。")

    col1, col2, col3 = st.columns(3)
    if col1.button("只生成学术简报", use_container_width=True):
        returncode, _lines, issues = run_backend("crawl")
        if returncode == 0 and not issues:
            st.success("学术简报生成完成。")
        elif returncode == 0:
            st.warning("学术简报生成完成，但存在警告。")
            for issue in issues:
                st.write("- " + issue)
        else:
            st.error(f"学术简报生成失败，返回码：{returncode}")

    if col2.button("只检查提醒", use_container_width=True):
        returncode, _lines, issues = run_backend("remind")
        if returncode == 0 and not issues:
            st.success("提醒检查完成。")
        elif returncode == 0:
            st.warning("提醒检查完成，但存在警告。")
            for issue in issues:
                st.write("- " + issue)
        else:
            st.error(f"提醒检查失败，返回码：{returncode}")

    if col3.button("刷新页面", use_container_width=True):
        st.rerun()

    st.subheader("运行路径")
    st.code(f"项目目录：{_project_root()}\n运行数据：{_app_dir()}", language="text")

    log_dir = _app_dir() / "logs"
    if log_dir.exists():
        logs = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if logs:
            selected = st.selectbox("查看日志", logs, format_func=lambda p: p.name)
            st.code(_read_text(selected), language="text")


def render_settings(manager: ConfigManager, config: dict) -> None:
    st.header("配置")

    with st.form("email_config"):
        st.subheader("邮箱")
        email = config.get("email", {})
        enabled = st.checkbox("启用邮件发送", value=bool(email.get("enabled", False)))
        smtp_server = st.text_input("SMTP 服务器", value=email.get("smtp_server", "smtp.qq.com"))
        smtp_port = st.number_input("SMTP 端口", min_value=1, max_value=65535, value=int(email.get("smtp_port", 465)))
        sender_email = st.text_input("发件邮箱", value=email.get("sender_email", ""))
        sender_password = st.text_input("授权码", value=_decode_pwd(email.get("sender_password", "")), type="password")
        receiver_email = st.text_input("收件邮箱", value=email.get("receiver_email", ""))
        subject_prefix = st.text_input("邮件主题前缀", value=email.get("subject_prefix", "[学术简报]"))
        weather_city = st.text_input("天气城市", value=config.get("weather_city", "Beijing"))

        if st.form_submit_button("保存邮箱和天气配置", type="primary"):
            manager.update_email_config({
                "enabled": enabled,
                "smtp_server": smtp_server,
                "smtp_port": int(smtp_port),
                "sender_email": sender_email,
                "sender_password": _encode_pwd(sender_password),
                "receiver_email": receiver_email,
                "subject_prefix": subject_prefix,
            })
            manager.update_weather_city(weather_city)
            st.success("配置已保存。")

    with st.form("api_config"):
        st.subheader("API 密钥")
        api_keys = config.get("api_keys", {})
        semantic = st.text_input("Semantic Scholar API Key", value=api_keys.get("semantic_scholar", ""), type="password")
        openalex = st.text_input("OpenAlex API Key", value=api_keys.get("openalex", ""), type="password")
        core = st.text_input("CORE API Key", value=api_keys.get("core", ""), type="password")
        qweather = st.text_input("QWeather / 和风天气 API Key", value=api_keys.get("qweather", ""), type="password")

        if st.form_submit_button("保存 API 密钥"):
            api_keys.update({
                "semantic_scholar": semantic,
                "openalex": openalex,
                "core": core,
                "qweather": qweather,
            })
            manager.update_api_keys(api_keys)
            st.success("API 密钥已保存。")

    st.subheader("信息源概览")
    sources = config.get("news_sources", [])
    if not sources:
        st.info("尚未配置新闻源。")
    else:
        for source in sources:
            state = "启用" if source.get("enabled", True) else "停用"
            st.write(f"- {state} | {source.get('name', '未命名')} | {source.get('type', '')}")


def main() -> None:
    st.set_page_config(page_title="Daily Automation", layout="wide")
    st.title("Daily Automation")
    st.caption("本地网页端：先看今日简报，再进入控制台和配置。")

    manager = ConfigManager()
    manager.ensure_default_config()
    manager.ensure_default_schedule()
    config = manager.get_config()

    tab_briefing, tab_console, tab_settings = st.tabs(["今日简报", "控制台", "配置"])
    with tab_briefing:
        render_briefing_home(config)
    with tab_console:
        render_control_console()
    with tab_settings:
        render_settings(manager, config)


if __name__ == "__main__":
    main()
