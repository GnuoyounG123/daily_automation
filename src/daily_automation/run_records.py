"""Persistent task run records for the local web UI."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable


FINAL_STATUSES = {"success", "warning", "failed", "timeout", "startup_failed"}


def utc_now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def runs_dir(app_dir: Path) -> Path:
    return app_dir / "runs"


def data_dir(app_dir: Path) -> Path:
    return app_dir / "data"


def list_output_files(app_dir: Path) -> dict[str, float]:
    directory = data_dir(app_dir)
    if not directory.exists():
        return {}
    patterns = ("academic_briefing_*.md", "daily_plan_*.html")
    files: dict[str, float] = {}
    for pattern in patterns:
        for path in directory.glob(pattern):
            try:
                files[str(path)] = path.stat().st_mtime
            except OSError:
                continue
    return files


def detect_new_outputs(app_dir: Path, before: dict[str, float]) -> list[str]:
    after = list_output_files(app_dir)
    changed = [
        path for path, mtime in after.items()
        if path not in before or mtime > before[path]
    ]
    return sorted(changed, key=lambda p: after[p], reverse=True)


def begin_run(app_dir: Path, mode: str, command: Iterable[str]) -> dict:
    started_at = utc_now_iso()
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    record = {
        "run_id": run_id,
        "mode": mode,
        "command": list(command),
        "started_at": started_at,
        "ended_at": None,
        "duration_seconds": None,
        "status": "running",
        "returncode": None,
        "issues": [],
        "outputs": [],
        "log_tail": [],
        "error": "",
    }
    write_run_record(app_dir, record)
    return record


def finish_run(
    app_dir: Path,
    record: dict,
    *,
    status: str,
    returncode: int | None,
    issues: Iterable[str] = (),
    outputs: Iterable[str] = (),
    log_lines: Iterable[str] = (),
    error: str = "",
) -> dict:
    ended_at = utc_now_iso()
    started_at = datetime.fromisoformat(record["started_at"])
    ended = datetime.fromisoformat(ended_at)
    record.update({
        "ended_at": ended_at,
        "duration_seconds": round((ended - started_at).total_seconds(), 1),
        "status": status,
        "returncode": returncode,
        "issues": list(issues)[:12],
        "outputs": list(outputs)[:10],
        "log_tail": list(log_lines)[-120:],
        "error": error,
    })
    write_run_record(app_dir, record)
    return record


def write_run_record(app_dir: Path, record: dict) -> Path:
    directory = runs_dir(app_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{record['run_id']}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_run_records(app_dir: Path, limit: int = 20) -> list[dict]:
    directory = runs_dir(app_dir)
    if not directory.exists():
        return []
    records: list[dict] = []
    for path in sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
        if len(records) >= limit:
            break
    return records


def latest_run_record(app_dir: Path) -> dict | None:
    records = list_run_records(app_dir, limit=1)
    return records[0] if records else None
