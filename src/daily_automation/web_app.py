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
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

import streamlit as st

from .config_diagnostics import diagnose_config, diagnostic_counts
from .config_manager import ConfigManager
from .campus_diagnostics import campus_diagnostic_counts, diagnose_campus
from .campus_cas import TERM_TO_XQM, default_academic_year, default_term, probe_account
from .campus_service import CampusService, SHANGHAI
from .notice_processing import parse_user_deadline
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

    with st.form("campus_config"):
        st.subheader("校内通知与个人信息")
        campus = config.get("campus", {})
        enabled = st.checkbox("启用每天一次校内检查", value=bool(campus.get("enabled", False)))

        st.markdown("**统一身份认证接口登录**")
        username = st.text_input("学号", value=campus.get("username", ""))
        remember_password = st.checkbox(
            "记住密码（使用本地 Fernet 密钥加密保存）",
            value=bool(campus.get("remember_password", False)))
        password = st.text_input("统一身份认证密码（留空保持现有；仅勾选记住时保存）", type="password")
        current_password = str(campus.get("password") or "")
        if remember_password and current_password.startswith("fernet:"):
            st.caption("已保存加密密码；留空会保持不变。")
        elif current_password and not remember_password:
            st.caption("当前未记住密码；保存配置会清除残留密码。")
        year_default = str(campus.get("academic_year") or default_academic_year())
        term_default = str(campus.get("term") or default_term())
        term_options = list(TERM_TO_XQM)
        year = st.text_input("学年起始年（例如 2025）", value=year_default, max_chars=4)
        term = st.selectbox("学期", term_options,
                            index=term_options.index(term_default) if term_default in term_options else 0)
        st.caption("接口登录失败会自动回退到专用浏览器会话；验证码、账号锁定和限流不会被绕过。"
                   "未保存密码时，定时任务无法使用接口登录。")

        grade = st.text_input("年级（用于筛选公开通知）", value=campus.get("grade", ""))
        college = st.text_input("学院", value=campus.get("college", ""))
        major = st.text_input("专业", value=campus.get("major", ""))
        timetable_url = st.text_input("教务课表页面地址（自动发现失败时填写）", value=campus.get("timetable_url", ""))
        lms_extra = st.text_area("学在浙大作业或公告页面地址（可选，每行一个）", value="\n".join(campus.get("lms_extra_urls", [])))
        semester_start = st.text_input("本学期第一周周一日期（课表有周次时填写）", value=campus.get("semester_start", ""), placeholder="YYYY-MM-DD")
        deepseek = config.get("deepseek", {})
        model = st.text_input("DeepSeek 模型", value=deepseek.get("model", "deepseek-flash"))
        key = st.text_input("DeepSeek API Key（留空保持现有值）", type="password")
        dingtalk = config.get("dingtalk", {})
        client_id = st.text_input("钉钉应用 Client ID", value=dingtalk.get("client_id", ""))
        client_secret = st.text_input("钉钉 Client Secret（留空保持现有值）", type="password")
        allowed = st.text_area("允许转发的钉钉 senderStaffId（每行一个；留空则允许机器人单聊用户）",
                               value="\n".join(dingtalk.get("allowed_sender_ids", [])))
        save_submitted = st.form_submit_button("保存校内接入配置")
        test_submitted = st.form_submit_button("测试统一身份认证（不保存）")

        if test_submitted:
            typed = password.strip()
            if not typed and remember_password and current_password.startswith("fernet:"):
                typed = _decode_pwd(current_password)
                if typed.startswith(("fernet:", "enc:")):
                    typed = ""
            if not username.strip() or not typed:
                st.error("测试登录需要填写学号和密码；测试不会保存任何内容。")
            else:
                test_year = year.strip() or default_academic_year()
                try:
                    with st.spinner("正在验证 CAS、教务和学在浙大接口..."):
                        result = probe_account(username.strip(), typed, test_year, term)
                except Exception as exc:
                    st.error(f"测试未完成：{type(exc).__name__}")
                    return
                if result["cas"] != "ok":
                    st.error("统一身份认证未通过：" + "；".join(result["messages"]))
                else:
                    st.success(
                        f"统一身份认证通过；教务课表 {result['zdbk_courses']} 条，"
                        f"学在浙大待办 {result['lms_todos']} 条。")
                    for message in result["messages"]:
                        st.warning(message)
                    if not result["ok"]:
                        st.info("至少一个服务接口未通过；保存后仍会尝试浏览器回退。")
                st.caption("本次测试不保存密码、cookie 或会话。")
        elif save_submitted:
            year = year.strip()
            term = term.strip()
            old_username = str(campus.get("username") or "").strip()
            if year and not (year.isdigit() and len(year) == 4 and year.startswith("20")):
                st.error("学年应填写四位起始年份，例如 2025。")
                return
            if term not in TERM_TO_XQM:
                st.error("学期应为 秋、冬、春、夏 之一。")
                return
            if semester_start.strip():
                try:
                    if date.fromisoformat(semester_start.strip()).weekday() != 0:
                        raise ValueError("第一周日期必须为周一")
                except ValueError:
                    st.error("请使用 YYYY-MM-DD 格式填写本学期第一周的周一日期。")
                    return
            if remember_password and not password.strip() and old_username and old_username != username.strip():
                st.error("更换学号时请重新填写密码。")
                return
            campus.update({"enabled": enabled, "username": username.strip(),
                           "remember_password": remember_password,
                           "academic_year": year, "term": term,
                           "grade": grade.strip(),
                           "college": college.strip(), "major": major.strip(), "timetable_url": timetable_url.strip(),
                           "lms_extra_urls": [x.strip() for x in lms_extra.splitlines() if x.strip()],
                           "semester_start": semester_start.strip()})
            deepseek["model"] = model.strip() or "deepseek-flash"
            dingtalk["client_id"] = client_id.strip()
            dingtalk["allowed_sender_ids"] = [x.strip() for x in allowed.splitlines() if x.strip()]
            try:
                crypto = PasswordCrypto(_app_dir())
                if remember_password:
                    if password.strip():
                        campus["password"] = crypto.encrypt(password.strip())
                    elif not str(campus.get("password") or "").startswith("fernet:"):
                        st.error("勾选记住密码时请填写密码。")
                        return
                else:
                    campus["password"] = ""
                if key:
                    deepseek["api_key"] = crypto.encrypt(key.strip())
                if client_secret:
                    dingtalk["client_secret"] = crypto.encrypt(client_secret.strip())
                if (key and not deepseek["api_key"].startswith("fernet:")) or (client_secret and not dingtalk["client_secret"].startswith("fernet:")):
                    raise RuntimeError("缺少 cryptography，无法加密保存密钥")
                if remember_password and not str(campus.get("password") or "").startswith("fernet:"):
                    raise RuntimeError("缺少 cryptography，无法加密保存密码")
            except Exception as exc:
                st.error(f"密钥加密失败：{type(exc).__name__}")
                return
            config.update({"campus": campus, "deepseek": deepseek, "dingtalk": dingtalk})
            manager.save_config(config)
            schedule = manager.get_schedule()
            schedule["semester_start"] = semester_start.strip()
            manager.save_schedule(schedule)
            if remember_password:
                st.success("配置已保存；定时任务可使用统一身份认证接口登录。")
            else:
                st.success("配置已保存；未保存密码，定时任务将只使用专用浏览器会话。")


def render_campus(manager: ConfigManager, config: dict) -> None:
    st.header("校内事项")
    service = CampusService(_app_dir(), config)
    st.caption("每天 09:00 的任务需通过安装脚本设置；钉钉机器人只在本机监听程序运行时收件。")

    checks = diagnose_campus(config, _app_dir(), manager.get_schedule())
    counts = campus_diagnostic_counts(checks)
    col_ok, col_warn, col_error = st.columns(3)
    col_ok.metric("自检通过", counts["ok"])
    col_warn.metric("警告", counts["warning"])
    col_error.metric("错误", counts["error"])
    with st.expander("接入自检明细", expanded=bool(counts["error"])):
        st.table([{"项目": item["label"], "状态": item["status_label"], "说明": item["detail"]}
                  for item in checks])
        st.caption("自检读取本地配置与状态，不访问校内网站、不发送邮件、不连接钉钉。"
                   "命令行可运行 python campus_monitor.py doctor。")
    if counts["error"]:
        st.error("存在阻塞项；请按自检说明修复后再运行同步或发送。")
    elif counts["warning"]:
        st.warning("基础流程可用，但自检存在警告；未完成项可能影响收件或提醒。")

    left, right = st.columns(2)
    if left.button("打开校内登录窗口", use_container_width=True):
        command = [sys.executable, str(_project_root() / "campus_monitor.py"), "login"]
        try:
            flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            subprocess.Popen(command, cwd=_project_root(), creationflags=flags)
            st.info("请在新窗口完成两个平台的登录，并回到命令窗口按 Enter。")
        except OSError as exc:
            st.error(f"无法打开登录窗口：{exc}")
    if right.button("现在检查校内通知", use_container_width=True):
        with st.spinner("正在检查来源并整理新事项..."):
            result = service.sync()
        st.json(result)

    bot, automation = st.columns(2)
    if bot.button("启动钉钉监听", use_container_width=True):
        settings = config.get("dingtalk", {})
        if not settings.get("client_id") or not settings.get("client_secret", "").startswith("fernet:"):
            st.error("请先在配置页保存钉钉应用凭证。")
        else:
            log_path = _app_dir() / "logs" / "dingtalk_listener.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as log:
                subprocess.Popen([sys.executable, str(_project_root() / "campus_monitor.py"), "listen"],
                                 cwd=_project_root(), stdout=log, stderr=log,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            st.info("监听已启动；以来源状态和机器人确认回复核对连接。")
    if automation.button("安装每日检查与登录启动任务", use_container_width=True):
        ready = config.get("campus", {}).get("enabled") and config.get("deepseek", {}).get("api_key", "").startswith("fernet:") and config.get("dingtalk", {}).get("client_secret", "").startswith("fernet:") and config.get("dingtalk", {}).get("client_id")
        if not ready:
            st.error("请先启用校内检查，并保存 DeepSeek 和钉钉应用凭证。")
        else:
            result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                     str(_project_root() / "scripts/windows/setup_campus_tasks.ps1"),
                                     "-PythonPath", sys.executable], cwd=_project_root(),
                                    capture_output=True, timeout=30,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode == 0:
                st.success("每日 09:00 检查和登录后监听任务已安装。")
            else:
                st.error("计划任务安装失败，请在 PowerShell 运行 README 中的安装命令查看原因。")

    states = service.store.source_states()
    if states:
        st.subheader("来源状态")
        st.dataframe(states, use_container_width=True, hide_index=True)
    courses = [{"星期": day, "课程": course["name"], "节次": course.get("time", ""),
                "周次": ",".join(map(str, course.get("weeks", []))) or course.get("weeks_note") or "每周/待核对"}
               for day, group in manager.get_schedule().get("week_schedule", {}).items()
               for course in group]
    if courses:
        with st.expander("查看已保存课表"):
            st.dataframe(courses, use_container_width=True, hide_index=True)

    with st.form("manual_notice"):
        st.subheader("补录通知")
        title = st.text_input("标题（可选）")
        body = st.text_area("通知文字或链接", height=130)
        if st.form_submit_button("保存并摘要"):
            if not body.strip():
                st.error("请先填写通知内容。")
            else:
                service.ingest("manual", title, body)
                service.process_pending()
                st.success("已加入收件箱。")

    st.subheader("个人计划与待办")
    tasks = service.store.list_tasks()
    active = [task for task in tasks if task["relevance"] and not task["completed_at"]]
    show_completed = st.checkbox("显示已完成事项", value=False)
    planned_tasks = [task for task in active if task["planned_date"]]
    if planned_tasks:
        st.dataframe([{"开始日期": t["planned_date"], "事项": t["action"], "截止": t["due_at"] or "待确认"}
                      for t in sorted(planned_tasks, key=lambda t: t["planned_date"])], hide_index=True, use_container_width=True)
    if st.button("预览今日计划"):
        st.components.v1.html(service.build_daily_plan(), height=700, scrolling=True)
    visible_tasks = [t for t in tasks if t["relevance"] and (show_completed or not t["completed_at"])]
    for task in visible_tasks[:60]:
        state = "已完成" if task["completed_at"] else ("待核对" if task["review_state"] != "ready" else "待办")
        with st.expander(f"{state} · {task['action']} · {task['due_at'] or '未确认截止'}"):
            st.write(task["summary"])
            st.caption(f"来源：{task['title']}　建议开始：{task['suggested_date'] or '待确定'}")
            if task["url"]:
                st.link_button("查看原通知", task["url"])
            with st.expander("查看收件箱原文"):
                original = service.store.get_notice(task["notice_id"])
                st.text(original["body"] if original else "原文未找到")
            if task["deadline_evidence"]:
                st.text("日期依据：" + task["deadline_evidence"])
            action = st.text_input("事项", value=task["action"], key=f"task_action_{task['id']}")
            deadline = st.text_input("确认或修改截止日期", value=task["due_at"] or "",
                                     placeholder="2026-09-30 或 2026-09-30 23:59", key=f"task_due_{task['id']}")
            if st.button("保存核对结果", key=f"task_review_{task['id']}"):
                try:
                    if not action.strip():
                        raise ValueError("事项不能为空")
                    service.store.review_task(task["id"], action, parse_user_deadline(deadline))
                    st.rerun()
                except ValueError:
                    st.error("请填写事项，并使用 YYYY-MM-DD 或 YYYY-MM-DD HH:MM 格式的日期。")
            value = task["planned_date"] or task["suggested_date"]
            start = date.fromisoformat(value) if value else datetime.now(SHANGHAI).date()
            planned = st.date_input("计划开始日", value=start, key=f"task_plan_{task['id']}")
            col_plan, col_done = st.columns(2)
            if col_plan.button("加入个人计划", key=f"task_add_{task['id']}"):
                service.store.plan_task(task["id"], planned.isoformat())
                st.rerun()
            if col_done.button("重新打开" if task["completed_at"] else "标记完成", key=f"task_done_{task['id']}"):
                service.store.complete_task(task["id"], not bool(task["completed_at"]))
                st.rerun()
            if task["planned_date"] and st.button("撤出计划", key=f"task_unplan_{task['id']}"):
                service.store.plan_task(task["id"], None)
                st.rerun()

    st.subheader("通知收件箱")
    if st.button("重试未完成的摘要"):
        with st.spinner("正在整理..."):
            processed = service.process_pending()
        st.info(f"本次完成 {processed} 条摘要。")
    rows = service.store.list_notices(limit=60)
    if not rows:
        st.info("尚无校内通知。先完成登录并检查来源，或补录一条通知。")
    for row in rows:
        label = row["summary"] or row["title"]
        state = "待核对" if row["review_state"] != "ready" else "已整理"
        with st.expander(f"{state} · {label[:90]} · {row['source']}"):
            st.write(row["summary"] or row["title"])
            st.caption(f"来源：{row['source']}")
            if row["url"]:
                st.link_button("打开原通知", row["url"])
            st.text_area("原文", value=row["body"], height=120, disabled=True, key=f"raw_{row['id']}")
            supplement = st.text_area("补充或替换原文", key=f"supplement_{row['id']}")
            if st.button("保存补充原文并重新摘要", key=f"supplement_save_{row['id']}"):
                if supplement.strip():
                    service.ingest(row["source"], row["title"], supplement, row["url"],
                                   external_id=row["external_id"], published_at=row["published_at"])
                    service.process_pending()
                    st.rerun()
                else:
                    st.error("请填写补充内容。")
            relevance = st.checkbox("与我有关", value=bool(row["relevance"]), key=f"relevant_{row['id']}")
            if relevance != bool(row["relevance"]):
                service.store.set_relevance(row["id"], relevance)
                st.rerun()
            if not any(task["notice_id"] == row["id"] for task in tasks):
                action = st.text_input("本人需要做的事", value=row["action"], key=f"action_{row['id']}")
                deadline = st.text_input("人工确认的截止日期（可留空）", key=f"due_{row['id']}", placeholder="YYYY-MM-DD HH:MM")
                if st.button("确认事项", key=f"confirm_{row['id']}"):
                    try:
                        service.store.set_analysis(row["id"], summary=row["summary"] or row["title"],
                                                   action=action, evidence="用户人工确认", due_at=parse_user_deadline(deadline),
                                                   review_state="ready", relevance=bool(row["relevance"]))
                        st.rerun()
                    except ValueError:
                        st.error("日期格式无效，请使用 YYYY-MM-DD 或 YYYY-MM-DD HH:MM。")
            revisions = service.store.revisions(row["id"])
            if len(revisions) > 1:
                with st.expander(f"查看 {len(revisions)-1} 次变更记录"):
                    for revision in revisions:
                        st.caption(revision["captured_at"] + " · " + revision["title"])
                        st.text(revision["body"])


def main() -> None:
    st.set_page_config(page_title="Daily Automation", layout="wide")
    st.title("Daily Automation")
    st.caption("本地网页端：先看今日简报，再进入配置检查、控制台和配置。")

    manager = ConfigManager()
    manager.ensure_default_config()
    manager.ensure_default_schedule()
    config = manager.get_config()

    tab_briefing, tab_campus, tab_diagnostics, tab_console, tab_settings = st.tabs(
        ["今日简报", "校内事项", "配置检查", "控制台", "配置"])
    with tab_briefing:
        render_briefing_home(config)
    with tab_campus:
        render_campus(manager, config)
    with tab_diagnostics:
        render_diagnostics(config)
    with tab_console:
        render_control_console()
    with tab_settings:
        render_settings(manager, config)


if __name__ == "__main__":
    main()
