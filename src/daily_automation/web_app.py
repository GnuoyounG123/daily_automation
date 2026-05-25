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
from pathlib import Path
from typing import Iterable

import streamlit as st

from .config_diagnostics import diagnose_config, diagnostic_counts
from .config_manager import ConfigManager
from .password_crypto import PasswordCrypto
from .run_records import (
    begin_run,
    detect_new_outputs,
    finish_run,
    latest_run_record,
    list_output_files,
    list_run_records,
)


TASK_LABELS = {
    "all": "生成并发送今日简报",
    "crawl": "只生成学术简报",
    "remind": "只检查提醒",
    "test-email": "发送测试邮件",
}

STATUS_LABELS = {
    "running": "运行中",
    "success": "成功",
    "warning": "有警告",
    "failed": "失败",
    "timeout": "超时",
    "startup_failed": "未启动",
}


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


def _status_from_result(returncode: int | None, issues: list[str], timed_out: bool) -> str:
    if timed_out:
        return "timeout"
    if returncode is None:
        return "startup_failed"
    if returncode != 0:
        return "failed"
    if issues:
        return "warning"
    return "success"


def _render_completion(status_name: str, returncode: int | None, issues: list[str], record: dict) -> None:
    status_text = STATUS_LABELS.get(status_name, status_name)
    if status_name == "success":
        st.success(f"{status_text}。输出已更新。")
        st.toast("任务完成。", icon=None)
    elif status_name == "warning":
        st.warning(f"{status_text}。任务已结束，但存在需要查看的问题。")
        st.toast("任务完成，但存在警告。", icon=None)
    else:
        code = "" if returncode is None else f"返回码：{returncode}。"
        st.error(f"{status_text}。{code}请查看下方运行详情。")
        st.toast("任务失败或未执行。", icon=None)

    if issues:
        with st.expander("问题摘要", expanded=True):
            for issue in issues:
                st.write("- " + issue)
    if record.get("outputs"):
        with st.expander("本次输出文件", expanded=True):
            for output in record["outputs"]:
                st.code(output, language="text")


def run_backend(mode: str, timeout_seconds: int = 600) -> tuple[int | None, list[str], list[str], dict]:
    """Run a backend task, stream progress, and persist a run record."""
    app_dir = _app_dir()
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "logs").mkdir(exist_ok=True)

    cmd = [sys.executable, str(_daily_assistant_script()), mode]
    output_queue: queue.Queue[str | None] = queue.Queue()
    output_lines: list[str] = []
    before_outputs = list_output_files(app_dir)
    record = begin_run(app_dir, mode, cmd)

    def reader(pipe) -> None:
        try:
            for raw in iter(pipe.readline, ""):
                if not raw:
                    break
                output_queue.put(raw.rstrip("\r\n"))
        finally:
            output_queue.put(None)

    task_label = TASK_LABELS.get(mode, mode)
    with st.status(f"{task_label}已启动，正在等待后端输出。", expanded=True) as status_box:
        st.caption("执行命令：" + " ".join(cmd))
        progress = st.progress(0)
        log_box = st.empty()
        heartbeat = st.empty()

        try:
            process = subprocess.Popen(
                cmd,
                cwd=str(_project_root()),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            issue = f"后端进程未启动：{exc}"
            output_lines.append(issue)
            record = finish_run(
                app_dir,
                record,
                status="startup_failed",
                returncode=None,
                issues=[issue],
                log_lines=output_lines,
                error=str(exc),
            )
            status_box.update(label="后端进程未启动。", state="error", expanded=True)
            progress.progress(100)
            return None, output_lines, [issue], record

        assert process.stdout is not None
        threading.Thread(target=reader, args=(process.stdout,), daemon=True).start()

        start = time.monotonic()
        last_heartbeat = start
        reader_done = False
        timed_out = False

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
                if elapsed >= timeout_seconds and process.poll() is None:
                    timed_out = True
                    process.kill()
                    output_lines.append(f"ERROR: task timed out after {timeout_seconds} seconds")
                    break
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
        outputs = detect_new_outputs(app_dir, before_outputs)
        status_name = _status_from_result(returncode, issues, timed_out)
        record = finish_run(
            app_dir,
            record,
            status=status_name,
            returncode=returncode,
            issues=issues,
            outputs=outputs,
            log_lines=output_lines,
        )

        if status_name == "success":
            status_box.update(label="任务完成。", state="complete", expanded=False)
        elif status_name == "warning":
            status_box.update(label="任务完成，但存在警告。", state="complete", expanded=True)
        elif status_name == "timeout":
            status_box.update(label="任务超时，已停止后端进程。", state="error", expanded=True)
        else:
            status_box.update(label="任务失败。", state="error", expanded=True)

    return returncode, output_lines, issues, record


def render_briefing_home(config: dict) -> None:
    st.header("今日简报")

    diagnostics = diagnose_config(config, _project_root(), _app_dir(), _daily_assistant_script())
    counts = diagnostic_counts(diagnostics)
    sources = config.get("news_sources", [])
    enabled_sources = [s for s in sources if s.get("enabled", True)]
    email = config.get("email", {})
    latest_report = _latest_file("academic_briefing_*.md")
    latest_plan = _latest_file("daily_plan_*.html")
    latest_run = latest_run_record(_app_dir())

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("最新简报", latest_report.name if latest_report else "未生成")
    col2.metric("启用来源", str(len(enabled_sources)))
    col3.metric("邮箱", "已启用" if email.get("enabled") else "未启用")
    col4.metric("配置问题", f"{counts['error']} 错误 / {counts['warning']} 警告")
    col5.metric("最近运行", STATUS_LABELS.get(latest_run.get("status", ""), "无") if latest_run else "无")

    if counts["error"]:
        st.error("当前配置存在错误，任务可能无法执行。先查看“配置检查”可以更快定位问题。")
    elif counts["warning"]:
        st.warning("当前配置可以尝试运行，但部分功能可能不可用。")

    if st.button("生成并发送今日简报", type="primary", use_container_width=True):
        returncode, _lines, issues, record = run_backend("all")
        _render_completion(record["status"], returncode, issues, record)

    st.subheader("简报预览")
    if latest_report:
        st.caption(f"文件：{latest_report}")
        st.markdown(_read_text(latest_report))
    else:
        st.info("还没有生成过简报。点击上方按钮开始第一次运行。")

    if latest_plan:
        with st.expander("查看今日计划 HTML 文件路径"):
            st.code(str(latest_plan), language="text")

    render_recent_runs(compact=True)


def render_diagnostics(config: dict) -> None:
    st.header("配置检查")
    diagnostics = diagnose_config(config, _project_root(), _app_dir(), _daily_assistant_script())
    counts = diagnostic_counts(diagnostics)

    col1, col2, col3 = st.columns(3)
    col1.metric("通过", counts["ok"])
    col2.metric("警告", counts["warning"])
    col3.metric("错误", counts["error"])

    rows = [
        {"项目": item["label"], "状态": item["status_label"], "说明": item["detail"]}
        for item in diagnostics
    ]
    st.table(rows)

    if counts["error"]:
        st.error("存在错误项时，后端任务可能无法启动或无法输出。")
    elif counts["warning"]:
        st.warning("存在警告项时，任务可以运行，但结果可能不完整。")
    else:
        st.success("关键配置检查通过。")

    st.subheader("运行数据目录")
    st.code(str(_app_dir()), language="text")


def render_recent_runs(compact: bool = False) -> None:
    records = list_run_records(_app_dir(), limit=8 if compact else 20)
    if compact:
        st.subheader("最近运行")
    else:
        st.header("运行记录")

    if not records:
        st.info("还没有运行记录。")
        return

    rows = []
    for record in records:
        rows.append({
            "开始时间": record.get("started_at", ""),
            "任务": TASK_LABELS.get(record.get("mode", ""), record.get("mode", "")),
            "状态": STATUS_LABELS.get(record.get("status", ""), record.get("status", "")),
            "耗时": "" if record.get("duration_seconds") is None else f"{record['duration_seconds']}s",
            "问题数": len(record.get("issues", [])),
            "输出数": len(record.get("outputs", [])),
        })
    st.table(rows)

    selected = st.selectbox(
        "查看运行详情",
        records,
        format_func=lambda r: f"{r.get('started_at', '')} | {TASK_LABELS.get(r.get('mode', ''), r.get('mode', ''))} | {STATUS_LABELS.get(r.get('status', ''), r.get('status', ''))}",
    )
    if selected:
        st.code("\n".join(selected.get("log_tail", [])) or "无日志输出", language="text")
        if selected.get("issues"):
            with st.expander("问题摘要", expanded=True):
                for issue in selected["issues"]:
                    st.write("- " + issue)
        if selected.get("outputs"):
            with st.expander("输出文件", expanded=True):
                for output in selected["outputs"]:
                    st.code(output, language="text")


def _run_task_button(column, label: str, mode: str) -> None:
    if column.button(label, use_container_width=True):
        returncode, _lines, issues, record = run_backend(mode)
        _render_completion(record["status"], returncode, issues, record)


def render_control_console() -> None:
    st.header("控制台")
    st.caption("这里用于手动执行任务，并实时显示后端输出。每次点击都会写入运行记录。")

    col1, col2, col3, col4 = st.columns(4)
    _run_task_button(col1, "完整流程", "all")
    _run_task_button(col2, "只生成简报", "crawl")
    _run_task_button(col3, "只检查提醒", "remind")
    _run_task_button(col4, "发送测试邮件", "test-email")

    st.subheader("运行路径")
    st.code(f"项目目录：{_project_root()}\n运行数据：{_app_dir()}", language="text")

    render_recent_runs(compact=False)

    log_dir = _app_dir() / "logs"
    if log_dir.exists():
        logs = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if logs:
            selected = st.selectbox("查看日志文件", logs, format_func=lambda p: p.name)
            st.code(_read_text(selected), language="text")


def render_settings(manager: ConfigManager, config: dict) -> None:
    st.header("配置")

    with st.form("email_config"):
        st.subheader("邮箱与天气")
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

    with st.form("briefing_config"):
        st.subheader("简报偏好")
        keywords = st.text_area("英文关键词，每行一个", value="\n".join(config.get("keywords", [])), height=120)
        keywords_cn = st.text_area("中文关键词，每行一个", value="\n".join(config.get("keywords_cn", [])), height=120)
        max_items = st.number_input(
            "每次最多展示条目",
            min_value=1,
            max_value=50,
            value=int(config.get("max_items_per_source", 5)),
        )

        if st.form_submit_button("保存简报偏好"):
            config["keywords"] = [line.strip() for line in keywords.splitlines() if line.strip()]
            config["keywords_cn"] = [line.strip() for line in keywords_cn.splitlines() if line.strip()]
            config["max_items_per_source"] = int(max_items)
            manager.save_config(config)
            st.success("简报偏好已保存。")

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

    with st.form("sources_config"):
        st.subheader("信息源开关")
        sources = [dict(source) for source in config.get("news_sources", [])]
        if not sources:
            st.info("尚未配置新闻源。")
        for index, source in enumerate(sources):
            label = f"{source.get('name', '未命名')} | {source.get('type', '')}"
            source["enabled"] = st.checkbox(label, value=bool(source.get("enabled", True)), key=f"source_enabled_{index}")
        if st.form_submit_button("保存信息源开关"):
            config["news_sources"] = sources
            manager.save_config(config)
            st.success("信息源配置已保存。")


def main() -> None:
    st.set_page_config(page_title="Daily Automation", layout="wide")
    st.title("Daily Automation")
    st.caption("本地网页端：先看今日简报，再进入配置检查、控制台和配置。")

    manager = ConfigManager()
    manager.ensure_default_config()
    manager.ensure_default_schedule()
    config = manager.get_config()

    tab_briefing, tab_diagnostics, tab_console, tab_settings = st.tabs(["今日简报", "配置检查", "控制台", "配置"])
    with tab_briefing:
        render_briefing_home(config)
    with tab_diagnostics:
        render_diagnostics(config)
    with tab_console:
        render_control_console()
    with tab_settings:
        render_settings(manager, config)


if __name__ == "__main__":
    main()
