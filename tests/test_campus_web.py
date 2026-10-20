"""Exercise actual Streamlit controls with isolated local data."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from daily_automation import web_app
from daily_automation.campus_service import CampusService
from daily_automation.config_manager import ConfigManager


def test_campus_ui_plan_preview_and_completion(tmp_path, monkeypatch):
    manager = ConfigManager(tmp_path)
    manager.ensure_default_config()
    manager.ensure_default_schedule()
    monkeypatch.setattr(web_app, "ConfigManager", lambda *args: manager)
    monkeypatch.setattr(web_app, "_app_dir", lambda: tmp_path)
    service = CampusService(tmp_path, manager.get_config())
    notice_id, _ = service.ingest("manual", "作业通知", "2026年10月3日提交论文")
    service.store.set_analysis(notice_id, summary="提交论文", action="提交论文", due_at="2026-10-03", suggested_date="2026-09-30")
    task_id = service.store.list_tasks()[0]["id"]
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=20)
    assert not app.exception
    app.button(key=f"task_add_{task_id}").click().run(timeout=20)
    assert not app.exception
    assert service.store.list_tasks()[0]["planned_date"] == "2026-09-30"
    next(button for button in app.button if button.label == "预览今日计划").click().run(timeout=20)
    assert not app.exception
    app.button(key=f"task_done_{task_id}").click().run(timeout=20)
    assert not app.exception
    assert service.store.list_tasks()[0]["completed_at"]
