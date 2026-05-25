from pathlib import Path

from daily_automation.config_diagnostics import diagnose_config, diagnostic_counts


def test_diagnostics_pass_core_checks(tmp_path: Path):
    backend = tmp_path / "daily_assistant.py"
    backend.write_text("print('ok')", encoding="utf-8")
    config = {
        "news_sources": [{"name": "CrossRef", "type": "api", "enabled": True}],
        "keywords": ["ai"],
        "keywords_cn": ["人工智能"],
        "weather_city": "Hangzhou",
        "email": {"enabled": False},
        "api_keys": {},
    }

    diagnostics = diagnose_config(config, tmp_path, tmp_path / "runtime_local", backend)
    counts = diagnostic_counts(diagnostics)

    assert counts["error"] == 0
    assert any(item["id"] == "email" and item["status"] == "warning" for item in diagnostics)
    assert any(item["id"] == "sources" and item["status"] == "ok" for item in diagnostics)


def test_diagnostics_detect_email_errors(tmp_path: Path):
    backend = tmp_path / "daily_assistant.py"
    backend.write_text("print('ok')", encoding="utf-8")
    config = {
        "news_sources": [{"name": "Semantic Scholar", "type": "api", "enabled": True}],
        "keywords": [],
        "keywords_cn": [],
        "weather_city": "",
        "email": {
            "enabled": True,
            "smtp_server": "smtp.qq.com",
            "smtp_port": 465,
            "sender_email": "sender@example.com",
            "sender_password": "",
            "receiver_email": "",
        },
        "api_keys": {},
    }

    diagnostics = diagnose_config(config, tmp_path, tmp_path / "runtime_local", backend)
    counts = diagnostic_counts(diagnostics)

    assert counts["error"] == 1
    assert any(item["id"] == "email" and "授权码" in item["detail"] for item in diagnostics)
    assert any(item["id"] == "api_keys" and item["status"] == "warning" for item in diagnostics)
