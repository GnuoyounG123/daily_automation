"""CLI for authenticated campus collection and bot intake."""

from __future__ import annotations

import argparse
import getpass
import json
import logging
import sys

from .app_paths import APP_DIR
from .campus_cas import CampusError, probe_account, resolve_term
from .campus_diagnostics import campus_diagnostic_counts, diagnose_campus
from .campus_service import CampusService
from .campus_sources import CampusBrowser
from .config_manager import ConfigManager
from .dingtalk_listener import listen
from .password_crypto import PasswordCrypto


def _run(argv=None) -> int:
    parser = argparse.ArgumentParser(description="校内通知与个人计划")
    parser.add_argument("command", choices=("login", "sync", "daily", "listen", "status", "doctor", "api-check"))
    parser.add_argument("--json", action="store_true", help="以 JSON 输出 doctor、status 或 api-check 结果")
    args = parser.parse_args(argv)
    manager = ConfigManager(APP_DIR)
    manager.ensure_default_config()
    config = manager.get_config()
    if args.command == "doctor":
        checks = diagnose_campus(config, APP_DIR, manager.get_schedule())
        counts = campus_diagnostic_counts(checks)
        if args.json:
            print(json.dumps({"checks": checks, "counts": counts}, ensure_ascii=False, indent=2))
        else:
            print("校内接入自检（本地检查，不访问网络、不发送消息）")
            for check in checks:
                print(f"[{check['status_label']}] {check['label']}：{check['detail']}")
            print(f"通过 {counts['ok']} / 警告 {counts['warning']} / 错误 {counts['error']}")
        return 1 if counts["error"] else 0
    if args.command == "api-check":
        campus = config.get("campus", {})
        username = str(campus.get("username") or "").strip()
        password = ""
        stored = str(campus.get("password") or "")
        if campus.get("remember_password") and stored.startswith("fernet:"):
            key_file = APP_DIR / ".secret_key"
            try:
                if key_file.exists() and len(key_file.read_bytes().strip()) == 44:
                    password = PasswordCrypto(APP_DIR).decrypt(stored)
            except OSError:
                password = ""
            if password.startswith(("fernet:", "enc:")):
                password = ""
        if not username:
            username = input("学号：").strip()
        if not password:
            password = getpass.getpass("统一身份认证密码（不保存）：")
        if not username or not password:
            print("学号或密码为空，已退出。")
            return 2
        try:
            year, term = resolve_term(campus)
        except CampusError as exc:
            print(f"学年学期配置无效：{exc}")
            return 2
        result = probe_account(username, password, year, term)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    if args.command == "login":
        with CampusBrowser(APP_DIR, headless=False) as browser:
            landing = browser.login_interactive()
        if landing:
            config = manager.get_config()
            campus = config.setdefault("campus", {})
            if "lms" in landing:
                campus["lms_url"] = landing["lms"]
            if "zdbk_private" in landing:
                campus["zdbk_url"] = landing["zdbk_private"]
            if "timetable_url" in landing:
                campus["timetable_url"] = landing["timetable_url"]
            ConfigManager(APP_DIR).save_config(config)
        print("登录入口已记录：" + ", ".join(landing or ["无；请确认已登录"]))
        print("请运行 sync 检查会话与页面覆盖情况。")
        return 0 if {"lms", "zdbk_private"}.issubset(landing) else 1
    if args.command == "listen":
        listen(APP_DIR, config)
        return 0
    service = CampusService(APP_DIR, config)
    if args.command == "sync":
        result = service.sync()
    elif args.command == "daily":
        result = service.run_daily()
    else:
        result = {"sources": service.store.source_states(),
                  "pending": len(service.store.list_notices(review_state="pending")),
                  "review": len(service.store.list_notices(review_state="review"))}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result.get("warnings") else 1


def main(argv=None) -> int:
    # pythonw scheduled runs have no console; retain outcome without credentials.
    log_dir = APP_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("daily_automation.campus_cli")
    if not logger.handlers:
        handler = logging.FileHandler(log_dir / "campus_monitor.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    command = (argv or sys.argv[1:] or ["unknown"])[0]
    try:
        result = _run(argv)
        logger.info("command=%s exit=%s", command, result)
        return result
    except Exception as exc:
        logger.error("command=%s failed=%s", command, type(exc).__name__)
        print(f"校内任务未完成：{type(exc).__name__}；请核对来源状态、登录及接入配置。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
