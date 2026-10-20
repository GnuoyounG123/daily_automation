"""Readiness checks for the campus notice pipeline.

Every check is local: it does not touch the network, send mail, or connect to
DingTalk. Secret values are never returned; only whether a secret is present,
encrypted, and decryptable with the local key.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .campus_cas import TERM_TO_XQM
from .config_diagnostics import STATUS_LABELS, diagnostic_counts
from .notice_store import NoticeStore
from .password_crypto import PasswordCrypto

SHANGHAI = ZoneInfo("Asia/Shanghai")

SOURCE_CHECKS = (
    ("zdbk_public", "教务公开通知", 36),
    ("lms", "学在浙大", 36),
    ("zdbk_private", "教务个人页面", 36),
    ("zdbk_timetable", "课表", 36),
    ("deepseek", "摘要服务", 36),
    ("campus_email", "邮件发送", 72),
    ("dingtalk", "钉钉监听", None),
)


def _item(identifier: str, label: str, status: str, detail: str) -> dict[str, str]:
    return {
        "id": identifier,
        "label": label,
        "status": status,
        "status_label": STATUS_LABELS[status],
        "detail": detail,
    }


def _section(config: dict, key: str) -> dict:
    value = config.get(key)
    return value if isinstance(value, dict) else {}


def _secret_state(runtime_dir: Path, value: str) -> str:
    """Return missing, key_missing, key_invalid, key_unreadable, undecryptable, legacy, plaintext, or encrypted."""
    value = str(value or "")
    if not value:
        return "missing"
    if not value.startswith("fernet:"):
        return "legacy" if value.startswith("enc:") else "plaintext"
    key_file = runtime_dir / ".secret_key"
    if not key_file.exists():
        return "key_missing"
    try:
        key_data = key_file.read_bytes().strip()
    except OSError:
        return "key_unreadable"
    if len(key_data) != 44:
        return "key_invalid"
    try:
        decrypted = PasswordCrypto(runtime_dir).decrypt(value)
    except (OSError, ValueError):
        return "undecryptable"
    return "encrypted" if decrypted and decrypted != value else "undecryptable"


_KEY_ERRORS = {
    "key_missing": "缺少 runtime_local/.secret_key；请恢复密钥文件或重新保存凭证",
    "key_invalid": "runtime_local/.secret_key 格式无效；请恢复备份或重新保存凭证",
    "key_unreadable": "无法读取 runtime_local/.secret_key；请检查目录权限",
    "undecryptable": "请恢复 runtime_local/.secret_key 或重新保存凭证",
}


def _secret_blocker(state: str, identifier: str, label: str) -> dict[str, str] | None:
    if state == "missing":
        return _item(identifier, label, "error", "未配置")
    detail = _KEY_ERRORS.get(state)
    if detail:
        return _item(identifier, label, "error", "无法解密：" + detail)
    if state in {"legacy", "plaintext"}:
        return _item(identifier, label, "error",
                     "不是 Fernet 加密格式；请在配置页重新保存，程序才会使用该凭证")
    return None


def _check_deepseek(config: dict, runtime_dir: Path) -> dict[str, str]:
    settings = _section(config, "deepseek")
    state = _secret_state(runtime_dir, settings.get("api_key", ""))
    blocker = _secret_blocker(state, "deepseek_secret", "DeepSeek 摘要")
    if blocker:
        return blocker
    model = str(settings.get("model") or "").strip() or "deepseek-flash"
    return _item("deepseek_secret", "DeepSeek 摘要", "ok", f"Key 已加密保存；模型：{model}")


def _check_campus_login(config: dict, runtime_dir: Path) -> dict[str, str]:
    settings = _section(config, "campus")
    username = str(settings.get("username") or "").strip()
    stored = str(settings.get("password") or "")
    remember = bool(settings.get("remember_password"))
    label = "统一身份认证"
    if not username and not stored:
        return _item("campus_login", label, "warning",
                     "未填写学号；将只使用专用浏览器会话")
    if not username:
        return _item("campus_login", label, "error", "已保存密码但缺少学号")
    if not remember:
        detail = "学号已填写；未勾选记住密码，定时任务无法使用接口登录，仍可使用专用浏览器"
        if stored:
            detail += "；配置中残留密码，请在配置页重新保存以清除"
        return _item("campus_login", label, "warning", detail)
    state = _secret_state(runtime_dir, stored)
    if state == "missing":
        return _item("campus_login", label, "error", "已勾选记住密码但未保存密码")
    blocker = _secret_blocker(state, "campus_login", label)
    if blocker:
        return blocker
    return _item("campus_login", label, "ok", "学号已填写；密码已加密保存")


def _check_campus_term(config: dict) -> dict[str, str]:
    settings = _section(config, "campus")
    year = str(settings.get("academic_year") or "").strip()
    term = str(settings.get("term") or "").strip()
    label = "接口学年学期"
    if year and not re.fullmatch(r"20\d{2}", year):
        return _item("campus_term", label, "error", f"学年格式无效：{year}；应为四位起始年份")
    if term and term not in TERM_TO_XQM:
        return _item("campus_term", label, "error", f"学期无效：{term}；应为 秋、冬、春、夏 之一")
    if year and term:
        return _item("campus_term", label, "ok", f"{year} 学年 {term}季")
    if year or term:
        return _item("campus_term", label, "warning", "学年与学期需同时填写；当前将按日期推断未填写项")
    if str(settings.get("username") or "").strip():
        return _item("campus_term", label, "warning",
                     "未填写学年与学期；将按当前日期推断，跨学期时可能读错课表")
    return _item("campus_term", label, "ok", "未填写；未启用接口登录时不需要")


def _check_dingtalk(config: dict, runtime_dir: Path) -> list[dict[str, str]]:
    settings = _section(config, "dingtalk")
    client_id = str(settings.get("client_id") or "").strip()
    state = _secret_state(runtime_dir, settings.get("client_secret", ""))
    blocker = _secret_blocker(state, "dingtalk_credentials", "钉钉应用")
    if not client_id:
        credentials = _item("dingtalk_credentials", "钉钉应用", "error", "未配置 Client ID")
    elif blocker:
        credentials = blocker
    else:
        credentials = _item("dingtalk_credentials", "钉钉应用", "ok", "Client ID 与 Secret 已保存")

    allowed = [str(item).strip() for item in settings.get("allowed_sender_ids", []) if str(item).strip()]
    if allowed:
        allowlist = _item("dingtalk_allowlist", "钉钉发送人", "ok", f"已限制 {len(allowed)} 个 senderStaffId")
    else:
        allowlist = _item("dingtalk_allowlist", "钉钉发送人", "warning",
                          "未设置发送人白名单；任何能单聊该机器人的账号都可投递，建议填写 senderStaffId")
    return [credentials, allowlist]


def _check_email(config: dict, runtime_dir: Path) -> dict[str, str]:
    email = _section(config, "email")
    if not email.get("enabled"):
        return _item("email", "邮件发送", "warning", "邮件未启用；每日计划和临期提醒只在本地生成")
    missing = [
        label for key, label in (
            ("smtp_server", "SMTP 服务器"),
            ("smtp_port", "SMTP 端口"),
            ("sender_email", "发件邮箱"),
            ("sender_password", "授权码"),
            ("receiver_email", "收件邮箱"),
        )
        if not email.get(key)
    ]
    if missing:
        return _item("email", "邮件发送", "error", "缺少：" + "、".join(missing))
    state = _secret_state(runtime_dir, email.get("sender_password", ""))
    key_error = _KEY_ERRORS.get(state)
    if key_error:
        return _item("email", "邮件发送", "error", "授权码无法解密：" + key_error)
    if state in {"legacy", "plaintext"}:
        return _item("email", "邮件发送", "warning",
                     f"发送到 {email.get('receiver_email')}；授权码未加密保存，建议在配置页重新保存")
    return _item("email", "邮件发送", "ok", f"发送到 {email.get('receiver_email')}")


def _check_browser_profile(runtime_dir: Path) -> dict[str, str]:
    profile = runtime_dir / "campus_browser_profile"
    try:
        populated = profile.is_dir() and any(profile.iterdir())
    except OSError:
        populated = False
    if populated:
        return _item("browser_profile", "专用浏览器", "ok",
                     "配置目录已建立；登录是否有效以最近一次同步状态为准")
    return _item("browser_profile", "专用浏览器", "warning",
                 "尚未建立专用浏览器登录；请先在「校内事项」打开登录窗口")


def _check_semester(settings: dict, schedule: dict | None) -> dict[str, str]:
    weekly = (schedule or {}).get("week_schedule", {})
    courses = [
        course for group in weekly.values() if isinstance(group, list)
        for course in group if isinstance(course, dict)
    ]
    constrained = any(course.get("weeks") for course in courses)
    raw = str(settings.get("semester_start") or "").strip()
    if raw:
        try:
            value = date.fromisoformat(raw)
        except ValueError:
            return _item("semester_start", "课表周次", "error",
                         f"本学期第一周日期格式无效：{raw}；应为 YYYY-MM-DD")
        if value.weekday() != 0:
            return _item("semester_start", "课表周次", "error",
                         f"{raw} 不是周一；课表按第一周周一计算")
        return _item("semester_start", "课表周次", "ok", f"第一周周一：{raw}")
    if constrained:
        return _item("semester_start", "课表周次", "warning",
                     "课表含周次或单双周课程；请填写本学期第一周周一日期，否则这些课程不会进入当天安排")
    return _item("semester_start", "课表周次", "ok", "未填写；当前课表没有周次课程")


def _check_profile_fields(settings: dict) -> dict[str, str]:
    filled = [
        key for key in ("grade", "college", "major")
        if str(settings.get(key) or "").strip()
    ]
    if filled:
        return _item("profile_fields", "个人筛选信息", "ok", f"已填写 {len(filled)} / 3 项")
    return _item("profile_fields", "个人筛选信息", "warning",
                 "未填写年级、学院和专业；公开通知的相关性判断会变弱")


def _check_tasks_installed(runtime_dir: Path) -> dict[str, str]:
    path = runtime_dir / "tasks_installed.json"
    if not path.exists():
        return _item("tasks_installed", "Windows 计划任务", "warning",
                     "未检测到安装记录；每日 09:00 检查和登录监听可能尚未注册")
    try:
        record = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return _item("tasks_installed", "Windows 计划任务", "warning",
                     "安装记录无法读取；请重新运行安装脚本")
    tasks = record.get("tasks") if isinstance(record, dict) else None
    if not isinstance(tasks, list) or not tasks:
        return _item("tasks_installed", "Windows 计划任务", "warning",
                     "安装记录缺少任务名称；请重新运行安装脚本")
    installed = str(record.get("installed_at") or "").strip() or "时间未知"
    names = "、".join(str(task) for task in tasks[:4])
    return _item("tasks_installed", "Windows 计划任务", "ok", f"最近安装：{installed}；任务：{names}")


def _age(checked_at: str, now: datetime) -> timedelta | None:
    try:
        stamp = datetime.fromisoformat(str(checked_at))
    except (TypeError, ValueError):
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=SHANGHAI)
    return now - stamp


def _missing_source(source: str, label: str) -> dict[str, str]:
    detail = ("监听尚未启动；离线期间的消息需要补录"
              if source == "dingtalk" else "尚未检查")
    return _item(f"source_{source}", label, "warning", detail)


def _check_sources(runtime_dir: Path, now: datetime) -> list[dict[str, str]]:
    if not (runtime_dir / "campus_notices.sqlite3").exists():
        return [_missing_source(source, label) for source, label, _ in SOURCE_CHECKS]
    try:
        states = {row["source"]: row for row in NoticeStore(runtime_dir).source_states()}
    except Exception:
        return [_item("source_store", "来源状态", "error", "无法读取本地通知数据库；请检查 runtime_local 权限")]

    items = []
    for source, label, max_age_hours in SOURCE_CHECKS:
        row = states.get(source)
        if not row:
            items.append(_missing_source(source, label))
            continue
        status = row.get("status")
        detail = str(row.get("detail") or "")
        if status not in {"ok", "warning", "error"}:
            status, detail = "warning", detail or "状态未知"
        if status == "ok" and max_age_hours:
            age = _age(row.get("checked_at", ""), now)
            if age is None or age > timedelta(hours=max_age_hours):
                status = "warning"
                detail = (f"上次检查：{row.get('checked_at') or '未知'}；"
                          f"已超过 {max_age_hours} 小时")
        items.append(_item(f"source_{source}", label, status, detail or "无详情"))
    return items


def diagnose_campus(config: dict, runtime_dir: Path, schedule: dict | None = None,
                    now: datetime | None = None) -> list[dict[str, str]]:
    runtime_dir = Path(runtime_dir)
    settings = _section(config, "campus")
    now = now or datetime.now(SHANGHAI)
    if now.tzinfo is None:
        now = now.replace(tzinfo=SHANGHAI)

    enabled = bool(settings.get("enabled"))
    checks = [
        _item("campus_enabled", "校内检查", "ok" if enabled else "warning",
              "已启用" if enabled else "未启用；以下配置可提前准备，每日检查不会运行"),
        _check_deepseek(config, runtime_dir),
        _check_campus_login(config, runtime_dir),
        _check_campus_term(config),
        *_check_dingtalk(config, runtime_dir),
        _check_email(config, runtime_dir),
        _check_browser_profile(runtime_dir),
        _check_semester(settings, schedule),
        _check_profile_fields(settings),
        _check_tasks_installed(runtime_dir),
        *_check_sources(runtime_dir, now),
    ]
    return checks


def campus_diagnostic_counts(checks: list[dict[str, str]]) -> dict[str, int]:
    return diagnostic_counts(checks)
