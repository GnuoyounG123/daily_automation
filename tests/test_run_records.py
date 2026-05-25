from pathlib import Path

from daily_automation.run_records import (
    begin_run,
    detect_new_outputs,
    finish_run,
    list_output_files,
    list_run_records,
)


def test_run_record_roundtrip(tmp_path: Path):
    record = begin_run(tmp_path, "crawl", ["python", "daily_assistant.py", "crawl"])
    finished = finish_run(
        tmp_path,
        record,
        status="warning",
        returncode=0,
        issues=["WARNING: one source failed"],
        outputs=["report.md"],
        log_lines=["start", "WARNING: one source failed"],
    )

    records = list_run_records(tmp_path)

    assert len(records) == 1
    assert records[0]["run_id"] == finished["run_id"]
    assert records[0]["status"] == "warning"
    assert records[0]["issues"] == ["WARNING: one source failed"]
    assert records[0]["duration_seconds"] is not None


def test_detect_new_outputs(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    old_report = data_dir / "academic_briefing_20260524.md"
    old_report.write_text("old", encoding="utf-8")
    before = list_output_files(tmp_path)

    new_report = data_dir / "academic_briefing_20260525.md"
    new_report.write_text("new", encoding="utf-8")

    assert detect_new_outputs(tmp_path, before) == [str(new_report)]
