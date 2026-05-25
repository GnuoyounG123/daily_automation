"""Configuration diagnostics used by the Streamlit UI and tests."""

from __future__ import annotations

from pathlib import Path


STATUS_LABELS = {
    "ok": "通过",
    "warning": "警告",
    "error": "错误",
}


def _check_writable(path: Path) -> tuple[bool, str]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True, str(path)
    except OSError as exc:
        return False, f"{path} 不可写：{exc}"


def _item(identifier: str, label: str, status: str, detail: str) -> dict[str, str]:
    return {
        "id": identifier,
        "label": label,
        "status": status,
        "status_label": STATUS_LABELS[status],
        "detail": detail,
    }


def diagnose_config(config: dict, project_root: Path, app_dir: Path, backend_script: Path | None = None) -> list[dict[str, str]]:
    backend = backend_script or project_root / "daily_assistant.py"
    diagnostics: list[dict[str, str]] = []

    if backend.exists():
        diagnostics.append(_item("backend", "后端入口", "ok", str(backend)))
    else:
        diagnostics.append(_item("backend", "后端入口", "error", f"找不到后端入口：{backend}"))

    writable, detail = _check_writable(app_dir)
    diagnostics.append(_item("runtime", "运行目录", "ok" if writable else "error", detail))

    data_writable, data_detail = _check_writable(app_dir / "data")
    diagnostics.append(_item("data", "输出目录", "ok" if data_writable else "error", data_detail))

    sources = config.get("news_sources", [])
    enabled_sources = [source for source in sources if source.get("enabled", True)]
    if not sources:
        diagnostics.append(_item("sources", "信息源", "error", "尚未配置任何信息源"))
    elif not enabled_sources:
        diagnostics.append(_item("sources", "信息源", "warning", "已配置信息源，但当前全部停用"))
    else:
        diagnostics.append(_item("sources", "信息源", "ok", f"已启用 {len(enabled_sources)} / {len(sources)} 个来源"))

    keywords = config.get("keywords", []) + config.get("keywords_cn", [])
    if keywords:
        diagnostics.append(_item("keywords", "关键词", "ok", f"已配置 {len(keywords)} 个关键词"))
    else:
        diagnostics.append(_item("keywords", "关键词", "warning", "未配置关键词，简报相关性会变弱"))

    city = str(config.get("weather_city", "")).strip()
    diagnostics.append(
        _item("weather", "天气城市", "ok" if city else "warning", city or "未配置天气城市，将无法生成天气建议")
    )

    email = config.get("email", {})
    if not email.get("enabled", False):
        diagnostics.append(_item("email", "邮件发送", "warning", "邮件未启用，只会生成本地文件"))
    else:
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
            diagnostics.append(_item("email", "邮件发送", "error", "缺少：" + "、".join(missing)))
        else:
            diagnostics.append(_item("email", "邮件发送", "ok", f"发送到 {email.get('receiver_email')}"))

    api_keys = config.get("api_keys", {})
    enabled_names = {source.get("name", "").lower() for source in enabled_sources}
    key_map = {
        "semantic scholar": "semantic_scholar",
        "openalex": "openalex",
        "core": "core",
    }
    missing_keys = [
        service for service, key in key_map.items()
        if any(service in name for name in enabled_names) and not api_keys.get(key)
    ]
    if missing_keys:
        diagnostics.append(_item("api_keys", "API Key", "warning", "部分启用来源缺少 Key：" + "、".join(missing_keys)))
    else:
        diagnostics.append(_item("api_keys", "API Key", "ok", "必要 Key 已配置或当前来源无需 Key"))

    return diagnostics


def diagnostic_counts(diagnostics: list[dict[str, str]]) -> dict[str, int]:
    counts = {"ok": 0, "warning": 0, "error": 0}
    for item in diagnostics:
        status = item.get("status", "")
        if status in counts:
            counts[status] += 1
    return counts
