"""Read-only campus readiness checks; no network, mail, or bot traffic."""

import json
import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from daily_automation.campus_diagnostics import campus_diagnostic_counts, diagnose_campus
from daily_automation.notice_store import NoticeStore
from daily_automation.password_crypto import PasswordCrypto

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _token(label: str) -> str:
    return f"{label}-{secrets.token_urlsafe(12)}"


def _config(runtime_dir):
    crypto = PasswordCrypto(runtime_dir)
    return {
        "campus": {
            "enabled": True, "grade": "2024", "college": "计算机学院", "major": "人工智能",
            "semester_start": "2026-09-21",
            "username": "student", "password": crypto.encrypt(_token("cas")),
            "remember_password": True, "academic_year": "2026", "term": "秋",
        },
        "deepseek": {"api_key": crypto.encrypt(_token("deepseek")), "model": "deepseek-chat"},
        "dingtalk": {
            "client_id": "ding-client",
            "client_secret": crypto.encrypt(_token("bot")),
            "allowed_sender_ids": ["staff-1"],
        },
        "email": {
            "enabled": True, "smtp_server": "smtp.example.com", "smtp_port": 465,
            "sender_email": "sender@example.com", "sender_password": crypto.encrypt(_token("mail")),
            "receiver_email": "receiver@example.com",
        },
    }


def _mark_all_sources_ok(runtime_dir):
    store = NoticeStore(runtime_dir)
    for source in ("zdbk_public", "lms", "zdbk_private", "zdbk_timetable",
                   "deepseek", "campus_email", "dingtalk"):
        store.set_source_state(source, "ok", "checked", 1)


def _write_marker(runtime_dir):
    (runtime_dir / "tasks_installed.json").write_text(json.dumps({
        "installed_at": "2026-10-20T00:00:00Z",
        "tasks": ["DailyAutomation_CampusDaily", "DailyAutomation_DingTalkListener"],
    }), encoding="utf-8")


def test_fully_configured_pipeline_has_no_warnings(tmp_path):
    config = _config(tmp_path)
    profile = tmp_path / "campus_browser_profile"
    profile.mkdir()
    (profile / "Preferences").write_text("{}", encoding="utf-8")
    _mark_all_sources_ok(tmp_path)
    _write_marker(tmp_path)
    schedule = {"week_schedule": {"Monday": [{"name": "课程", "weeks": [1, 2]}]}}

    checks = diagnose_campus(config, tmp_path, schedule)
    counts = campus_diagnostic_counts(checks)

    assert counts == {"ok": 18, "warning": 0, "error": 0}
    assert {item["id"] for item in checks} == {
        "campus_enabled", "deepseek_secret", "campus_login", "campus_term",
        "dingtalk_credentials", "dingtalk_allowlist",
        "email", "browser_profile", "semester_start", "profile_fields", "tasks_installed",
        "source_zdbk_public", "source_lms", "source_zdbk_private", "source_zdbk_timetable",
        "source_deepseek", "source_campus_email", "source_dingtalk",
    }


def test_missing_local_key_blocks_all_encrypted_credentials(tmp_path):
    config = _config(tmp_path)
    (tmp_path / ".secret_key").unlink()

    checks = diagnose_campus(config, tmp_path)
    by_id = {item["id"]: item for item in checks}

    assert by_id["deepseek_secret"]["status"] == "error"
    assert by_id["dingtalk_credentials"]["status"] == "error"
    assert by_id["email"]["status"] == "error"
    assert by_id["campus_login"]["status"] == "error"
    assert "secret_key" in by_id["deepseek_secret"]["detail"]
    rendered = json.dumps(checks, ensure_ascii=False)
    assert "fernet:" not in rendered
    assert "Authorization" not in rendered


def test_non_fernet_credentials_are_reported_without_echoing_values(tmp_path):
    config = _config(tmp_path)
    plaintext = {
        "deepseek": _token("deepseek-plain"),
        "bot": _token("bot-plain"),
        "mail": _token("mail-plain"),
        "cas": _token("cas-plain"),
    }
    config["deepseek"]["api_key"] = plaintext["deepseek"]
    config["dingtalk"]["client_secret"] = plaintext["bot"]
    config["email"]["sender_password"] = plaintext["mail"]
    config["campus"]["password"] = plaintext["cas"]

    checks = diagnose_campus(config, tmp_path)
    by_id = {item["id"]: item for item in checks}

    assert by_id["deepseek_secret"]["status"] == "error"
    assert by_id["dingtalk_credentials"]["status"] == "error"
    assert by_id["email"]["status"] == "warning"
    assert by_id["campus_login"]["status"] == "error"
    rendered = json.dumps(checks, ensure_ascii=False)
    for value in plaintext.values():
        assert value not in rendered


def test_invalid_local_key_is_reported_without_being_rewritten(tmp_path):
    config = _config(tmp_path)
    key_file = tmp_path / ".secret_key"
    damaged = b"damaged-local-key"
    key_file.write_bytes(damaged)

    checks = diagnose_campus(config, tmp_path)
    by_id = {item["id"]: item for item in checks}

    assert by_id["deepseek_secret"]["status"] == "error"
    assert "格式无效" in by_id["deepseek_secret"]["detail"]
    assert key_file.read_bytes() == damaged


def test_diagnostics_do_not_create_runtime_database(tmp_path):
    checks = diagnose_campus({}, tmp_path)
    assert not (tmp_path / "campus_notices.sqlite3").exists()
    assert any(item["id"] == "source_dingtalk" and item["status"] == "warning" for item in checks)


def test_stale_sources_and_unreadable_marker_are_warnings(tmp_path):
    config = _config(tmp_path)
    _mark_all_sources_ok(tmp_path)
    (tmp_path / "tasks_installed.json").write_text("{not-json", encoding="utf-8")
    later = datetime.now(SHANGHAI) + timedelta(hours=48)

    checks = diagnose_campus(config, tmp_path, now=later)
    by_id = {item["id"]: item for item in checks}

    assert by_id["source_lms"]["status"] == "warning"
    assert "超过 36 小时" in by_id["source_lms"]["detail"]
    assert by_id["source_campus_email"]["status"] == "ok"
    assert by_id["tasks_installed"]["status"] == "warning"
    assert campus_diagnostic_counts(checks)["error"] == 0
