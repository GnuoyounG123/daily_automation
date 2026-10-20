"""Acceptance checks use isolated state and mocked transport; never send real mail."""

from datetime import date, datetime, timedelta
from unittest.mock import Mock

import pytest

from daily_automation import campus_service as service_module
from daily_automation.campus_cas import CampusCredentialError
from daily_automation.campus_service import CampusService
from daily_automation.campus_sources import CampusBrowser, SourceError, collect_public_zdbk, parse_timetable_html
from daily_automation.dingtalk_listener import record_message, _reply, create_stream_client
from daily_automation.notice_processing import (
    DeepSeekSummarizer, parse_deadline_evidence, parse_user_deadline,
    suggest_start_date, validate_analysis, SHANGHAI,
)
from daily_automation.notice_store import NoticeStore
from daily_automation.password_crypto import PasswordCrypto
from daily_automation.runtime_lock import runtime_lock


TODAY = date(2026, 9, 30)


@pytest.mark.parametrize(("evidence", "expected"), [
    ("2026年10月3日23:59截止", "2026-10-03T23:59+08:00"),
    ("10月3日截止", "2026-10-03"),
    ("2026-10-03 24:00", "2026-10-04T00:00+08:00"),
    ("2026-10-03 25:61", None),
    ("2026年2月30日", None),
    ("下周五前", None),
    ("10月1日或10月3日", None),
    ("8月1日", None),
    ("10月3日下午3点30分", "2026-10-03T15:30+08:00"),
    ("10月3日9:00至17:00", None),
    ("10月3日至5日", None),
    ("暂定10月3日", None),
])
def test_evidence_dates(evidence, expected):
    assert parse_deadline_evidence(evidence, "2026-09-29", TODAY) == expected


def test_new_year_and_explicit_time():
    assert parse_deadline_evidence("1月3日", "2026-12-30", TODAY) == "2027-01-03"
    assert parse_user_deadline("2026-10-03 09:00") == "2026-10-03T09:00+08:00"


def test_model_dates_require_original_evidence_and_untruncated_input():
    notice = {"title": "作业", "body": "第一项10月3日截止，第二项下周提交。", "published_at": "2026-09-30"}
    result = {"summary": "完成两项作业", "relevant": True, "tasks": [
        {"action": "提交第一项", "deadline_evidence": "10月3日", "estimated_minutes": 120},
        {"action": "提交第二项", "deadline_evidence": "10月5日"},
    ]}
    analysis = validate_analysis(notice, result, today=TODAY)
    assert analysis["tasks"][0]["due_at"] == "2026-10-03"
    assert analysis["tasks"][1]["due_at"] is None
    assert analysis["review_state"] == "review"
    result["_truncated"] = True
    assert all(t["due_at"] is None for t in validate_analysis(notice, result, today=TODAY)["tasks"])


def test_model_cannot_hide_uncertainty_by_quoting_date_only():
    notice = {"title": "作业通知", "body": "暂定10月3日提交作业，具体另行通知。"}
    result = {"summary": "提交作业", "relevant": True, "tasks": [{"action": "提交作业", "deadline_evidence": "10月3日"}]}
    assert validate_analysis(notice, result, today=TODAY)["tasks"][0]["due_at"] is None


def test_failed_config_save_preserves_previous_valid_file(tmp_path):
    from daily_automation.config_manager import ConfigManager
    manager = ConfigManager(tmp_path)
    assert manager.save_config({"campus": {"enabled": False}})
    assert not manager.save_config({"bad": object()})
    assert manager.get_config() == {"campus": {"enabled": False}}


def test_suggestion_respects_existing_weekly_load():
    # Sep 30 is Wednesday; heavy Wednesday moves the suggestion to Thursday.
    schedule = {"week_schedule": {"Wednesday": [{"name": "课"}] * 6}}
    assert suggest_start_date("2026-10-07", 60, schedule, {}, TODAY) == "2026-10-01"


def add_task(service, due="2026-10-03", action="提交论文"):
    notice_id, _ = service.ingest("lms", "课程作业", f"{action}，{due}截止", "https://course.zju.edu.cn/course/1", external_id="a1")
    service.store.set_analysis(notice_id, summary="完成课程论文", action=action, due_at=due,
                               evidence=due, suggested_date="2026-09-30")
    return service.store.list_tasks()[0]


def test_dedup_revision_and_replanning(tmp_path):
    service = CampusService(tmp_path, {})
    task = add_task(service)
    service.store.plan_task(task["id"], "2026-09-30")
    service.store.complete_task(task["id"])
    same_id, changed = service.ingest("lms", "课程作业", "提交论文，2026-10-03截止",
                                     "https://course.zju.edu.cn/course/1", external_id="a1")
    assert not changed and same_id == task["notice_id"]
    assert len(service.store.revisions(same_id)) == 1
    add_task(service, "2026-10-05")
    current = service.store.list_tasks()[0]
    assert current["id"] == task["id"]
    assert current["planned_date"] is None and current["completed_at"] is None
    assert len(service.store.revisions(same_id)) == 2


def test_several_actions_have_separate_deadlines(tmp_path):
    service = CampusService(tmp_path, {})
    n, _ = service.ingest("manual", "选课", "选课10月3日，退课10月5日")
    analysis = validate_analysis(service.store.get_notice(n), {"summary": "两轮操作", "relevant": True, "tasks": [
        {"action": "选课", "deadline_evidence": "10月3日"},
        {"action": "退课", "deadline_evidence": "10月5日"},
    ]}, today=TODAY)
    service.store.set_analysis(n, **analysis)
    tasks = service.store.list_tasks()
    assert len(tasks) == 2 and tasks[0]["due_at"] != tasks[1]["due_at"]
    service.store.plan_task(tasks[0]["id"], TODAY.isoformat())
    service.store.set_analysis(n, **analysis)
    assert service.store.list_tasks()[0]["planned_date"] == TODAY.isoformat()
    service.store.review_task(tasks[0]["id"], "选课", "2026-10-06")
    assert next(t for t in service.store.list_tasks() if t["id"] == tasks[0]["id"])["planned_date"] is None


def test_bot_duplicates_and_unsupported_forwards(tmp_path):
    service = CampusService(tmp_path, {})
    data = {"conversationType": "1", "senderStaffId": "student", "msgtype": "text", "text": {"content": "请于10月3日提交作业"}}
    assert record_message(service, data, {"student"}).startswith("已记录")
    assert record_message(service, {**data, "msgId": "retry"}, {"student"}).startswith("已记录")
    assert len(service.store.list_notices()) == 1
    record_message(service, {**data, "conversationType": "2"}, set())
    record_message(service, data, {"someone_else"})
    assert len(service.store.list_notices()) == 1
    picture = {"conversationType": "1", "msgtype": "picture", "msgId": "image-1"}
    assert "需补充原文" in record_message(service, picture, set())
    record_message(service, picture, set())
    assert len(service.store.list_notices(review_state="review")) == 1


def test_distinct_bot_links_do_not_collide(tmp_path):
    service = CampusService(tmp_path, {})
    for url in ("https://example.com/a", "https://example.com/b"):
        record_message(service, {"conversationType": "1", "msgtype": "link", "content": {"title": "通知", "url": url}}, set())
    assert len(service.store.list_notices()) == 2


def test_reply_rejects_untrusted_webhook(monkeypatch):
    post = Mock()
    monkeypatch.setattr("daily_automation.dingtalk_listener.requests.post", post)
    assert not _reply({"sessionWebhook": "https://localhost/"}, "已记录")
    post.assert_not_called()


def test_daily_and_due_mail_are_each_sent_once(tmp_path, monkeypatch):
    service = CampusService(tmp_path, {})
    add_task(service)
    sent = []
    monkeypatch.setattr(service, "_send_html", lambda subject, content: sent.append((subject, content)) or True)
    assert service.send_daily_plan(TODAY)
    assert not service.send_daily_plan(TODAY)
    assert service.send_due_reminders(TODAY) == 1
    assert service.send_due_reminders(TODAY) == 0
    assert service.send_due_reminders(date(2026, 10, 2)) == 1
    assert service.send_due_reminders(date(2026, 10, 2)) == 0
    assert len(sent) == 3


def test_failed_mail_can_retry_and_unconfirmed_dates_never_remind(tmp_path, monkeypatch):
    service = CampusService(tmp_path, {})
    task = add_task(service)
    monkeypatch.setattr(service, "_send_html", lambda *_: False)
    assert service.send_due_reminders(TODAY) == 0
    transport = Mock(return_value=True)
    monkeypatch.setattr(service, "_send_html", transport)
    assert service.send_due_reminders(TODAY) == 1
    service.store.review_task(task["id"], task["action"], None)
    assert service.send_due_reminders(date(2026, 10, 2)) == 0
    transport.assert_called_once()


def test_mail_exception_releases_reservation(tmp_path, monkeypatch):
    service = CampusService(tmp_path, {})
    add_task(service)
    monkeypatch.setattr(service, "_send_html", Mock(side_effect=RuntimeError("offline")))
    with pytest.raises(RuntimeError):
        service.send_due_reminders(TODAY)
    monkeypatch.setattr(service, "_send_html", Mock(return_value=True))
    assert service.send_due_reminders(TODAY) == 1


def test_only_confirmed_plan_enters_daily_tasks_and_html_is_escaped(tmp_path):
    service = CampusService(tmp_path, {})
    task = add_task(service, action="提交<script>论文</script>")
    service.manager.save_schedule({"week_schedule": {}})
    service.manager.save_weekly_tasks({"daily_tasks": {}})
    before = service.build_daily_plan(TODAY)
    service.store.plan_task(task["id"], TODAY.isoformat())
    after = service.build_daily_plan(TODAY)
    assert before != after
    assert "提交<script>" not in after and "&lt;script&gt;" in after
    assert (tmp_path / "data/daily_plan_20260930.html").exists()


def test_login_failure_has_error_state_preserving_originals(tmp_path, monkeypatch):
    service = CampusService(tmp_path, {"campus": {"enabled": True}})
    add_task(service)
    monkeypatch.setattr(service_module, "collect_public_zdbk", lambda **_: [])
    class LostLogin:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def collect(self, *args, **kwargs): raise SourceError("登录会话失效")
    monkeypatch.setattr(service_module, "CampusBrowser", LostLogin)
    result = service.sync()
    assert result["warnings"]
    assert all(s["status"] == "error" for s in service.store.source_states() if s["source"] in {"lms", "zdbk_private"})
    assert len(service.store.list_tasks()) == 1


def test_rendered_login_page_and_spa_links():
    assert CampusBrowser._login_required("https://cas.zju.edu.cn/login", "")
    links = CampusBrowser._links("https://course.zju.edu.cn/", '<a href="/#/course/12/assignments">作业</a><a href="https://evil.test/notice">通知</a>', "course.zju.edu.cn")
    assert links == [("https://course.zju.edu.cn/#/course/12/assignments", "作业")]


def test_public_ajax_identity_body_and_pagination():
    session = Mock()
    responses = []
    for i in range(2):
        response = Mock()
        response.json.return_value = {"totalPage": 2, "items": [{"xwbh": f"news{i}", "xwbt": "选课通知", "fbnr": "<p>10月3日前完成选课</p>", "fbsj": "2026-09-30 10:00:00"}]}
        responses.append(response)
    session.post.side_effect = responses
    items = collect_public_zdbk(session)
    assert len(items) == 2 and items[0]["external_id"] == "news0"
    assert items[0]["body"] == "10月3日前完成选课"
    assert session.post.call_args_list[1].kwargs["data"]["queryModel.currentPage"] == 2


def test_public_notice_missing_text_keeps_reviewable_record(tmp_path):
    session = Mock()
    session.post.return_value.json.return_value = {"totalPage": 1, "items": [{"xwbh": "redirect", "xwbt": "外部通知"}]}
    session.get.side_effect = OSError("network unavailable")
    items = collect_public_zdbk(session)
    assert len(items) == 1 and items[0]["needs_review"]
    service = CampusService(tmp_path, {})
    service._save_items(items)
    assert service.store.list_notices()[0]["review_state"] == "review"
    assert not service.store.list_tasks()


def test_timetable_rowspan_and_manual_courses_survive(tmp_path):
    html = '<table><tr><th>节次</th><th>星期一</th><th>星期二</th><th>星期三</th></tr><tr><td>1-2节</td><td rowspan="2">社会学</td><td>管理学</td><td></td></tr><tr><td>3-4节</td><td></td><td>政治学</td></tr></table>'
    timetable = parse_timetable_html(html)
    assert len(timetable["Monday"]) == 1
    assert timetable["Wednesday"][0]["name"] == "政治学"
    service = CampusService(tmp_path, {})
    service.manager.save_schedule({"week_schedule": {"Monday": [{"name": "手动课程"}, {"name": "旧同步课", "source": "zdbk"}]}})
    service._update_timetable(timetable)
    assert [c["name"] for c in service.manager.get_schedule()["week_schedule"]["Monday"]] == ["手动课程", "社会学"]


def test_api_payload_masks_identifiers_and_uses_json_mode(tmp_path, monkeypatch):
    crypto = PasswordCrypto(tmp_path)
    summarizer = DeepSeekSummarizer({"deepseek": {"api_key": crypto.encrypt("test-only-key")}}, tmp_path)
    response = Mock()
    response.json.return_value = {"choices": [{"finish_reason": "stop", "message": {"content": '{"summary":"通知","relevant":true,"tasks":[]}'}}]}
    post = Mock(return_value=response)
    monkeypatch.setattr("daily_automation.notice_processing.requests.post", post)
    summarizer.summarize({"title": "通知", "body": "电话13800138000 https://example.com/?token=private"}, {})
    payload = post.call_args.kwargs["json"]
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["thinking"] == {"type": "disabled"}
    assert "13800138000" not in payload["messages"][1]["content"]
    assert "token=private" not in payload["messages"][1]["content"]
    assert not DeepSeekSummarizer({"deepseek": {"api_key": "plaintext"}}, tmp_path).api_key


def test_summarizer_retries_after_reasoning_truncation(tmp_path, monkeypatch):
    crypto = PasswordCrypto(tmp_path)
    summarizer = DeepSeekSummarizer({"deepseek": {"api_key": crypto.encrypt("test-only-key")}}, tmp_path)
    truncated = Mock()
    truncated.json.return_value = {"choices": [{"finish_reason": "length", "message": {"content": '{"summary":"半'}}]}
    complete = Mock()
    complete.json.return_value = {"choices": [{"finish_reason": "stop", "message": {"content": '{"summary":"通知","relevant":true,"tasks":[]}'}}]}
    post = Mock(side_effect=[truncated, complete])
    monkeypatch.setattr("daily_automation.notice_processing.requests.post", post)
    result = summarizer.summarize({"title": "通知", "body": "正文"}, {})
    assert result["summary"] == "通知"
    assert post.call_count == 2
    assert post.call_args_list[0].kwargs["json"]["max_tokens"] == 2000
    assert post.call_args_list[1].kwargs["json"]["max_tokens"] == 4000


def test_process_pending_continues_after_single_failure(tmp_path, monkeypatch):
    config = {"deepseek": {"api_key": PasswordCrypto(tmp_path).encrypt("test-only-key")}}
    service = CampusService(tmp_path, config)
    service.ingest("manual", "失败通知", "第一条正文")
    service.ingest("manual", "成功通知", "第二条正文")

    def summarize(self, row, profile):
        if "失败" in row["title"]:
            raise ValueError("模型输出未完成")
        return {"summary": "可处理", "relevant": True, "tasks": []}

    monkeypatch.setattr(service_module.DeepSeekSummarizer, "summarize", summarize)
    assert service.process_pending() == 1
    notices = {row["title"]: row for row in service.store.list_notices()}
    assert notices["失败通知"]["review_state"] == "pending"
    assert notices["成功通知"]["review_state"] == "ready"
    state = next(s for s in service.store.source_states() if s["source"] == "deepseek")
    assert state["status"] == "warning"
    assert "1 条摘要失败" in state["detail"]


def test_old_public_notices_are_archived_without_api_call(tmp_path, monkeypatch):
    config = {"deepseek": {"api_key": PasswordCrypto(tmp_path).encrypt("test-only-key")}}
    service = CampusService(tmp_path, config)
    old_id, _ = service.ingest("zdbk_public", "旧通知", "旧正文", published_at="2025-01-01")
    fresh_id, _ = service.ingest("zdbk_public", "新通知", "新正文",
                                 published_at=datetime.now(SHANGHAI).date().isoformat())
    calls = []

    def summarize(self, row, profile):
        calls.append(row["id"])
        return {"summary": "新摘要", "relevant": True, "tasks": []}

    monkeypatch.setattr(service_module.DeepSeekSummarizer, "summarize", summarize)
    assert service.process_pending() == 1
    notices = {row["id"]: row for row in service.store.list_notices()}
    assert notices[old_id]["review_state"] == "ready"
    assert not notices[old_id]["relevance"]
    assert "历史公开通知" in notices[old_id]["summary"]
    assert notices[fresh_id]["review_state"] == "ready"
    assert calls == [fresh_id]


def test_unreadable_link_is_reviewed_not_summarized(tmp_path, monkeypatch):
    config = {"deepseek": {"api_key": PasswordCrypto(tmp_path).encrypt("test-only-key")}}
    service = CampusService(tmp_path, config)
    service.ingest("manual", "", "https://example.com/notice")
    monkeypatch.setattr(service_module, "fetch_notice_link", Mock(side_effect=ValueError("login")))
    summarizer = Mock()
    monkeypatch.setattr(service_module.DeepSeekSummarizer, "summarize", summarizer)
    service.process_pending()
    assert service.store.list_notices()[0]["review_state"] == "review"
    assert not service.store.list_tasks()
    summarizer.assert_not_called()


def test_bot_stale_heartbeat_and_duplicate_process_lock(tmp_path):
    store = NoticeStore(tmp_path)
    store.set_source_state("dingtalk", "ok", "连接正常")
    with store._connect() as db:
        db.execute("UPDATE source_state SET checked_at=?", ((datetime.now(SHANGHAI) - timedelta(minutes=2)).isoformat(),))
    assert store.source_states()[0]["status"] == "warning"
    with runtime_lock(tmp_path / "task.lock"):
        with pytest.raises(RuntimeError):
            with runtime_lock(tmp_path / "task.lock"):
                pytest.fail("duplicate listener acquired lock")
    with runtime_lock(tmp_path / "task.lock"):
        pass


def test_stale_analysis_cannot_overwrite_revised_notice(tmp_path):
    service = CampusService(tmp_path, {})
    task = add_task(service)
    old = service.store.get_notice(task["notice_id"])
    service.ingest("lms", "课程作业", "改为10月5日提交", old["url"], external_id="a1")
    assert not service.store.set_analysis(old["id"], summary="旧摘要", action="提交论文", due_at="2026-10-03", expected_hash=old["content_hash"])
    assert service.store.get_notice(old["id"])["review_state"] == "pending"
    assert not service.store.list_tasks()


def test_same_action_at_two_deadlines_and_personal_priority(tmp_path):
    service = CampusService(tmp_path, {})
    public_id, _ = service.ingest("zdbk_public", "旧公告", "公开事务")
    private_id, _ = service.ingest("lms", "新作业", "选课10月3日和10月5日")
    assert service.store.list_notices(review_state="pending")[0]["id"] == private_id
    service.store.set_analysis(private_id, summary="两轮选课", action="选课", tasks=[
        {"action": "选课", "due_at": "2026-10-03"}, {"action": "选课", "due_at": "2026-10-05"},
        {"action": "选课", "due_at": "2026-10-05"}])
    assert len(service.store.list_tasks()) == 2


def test_stream_connection_is_bounded_and_does_not_log_ticket(monkeypatch):
    client = create_stream_client("test-client", "test-secret")
    response = Mock()
    response.json.return_value = {"endpoint": "wss://wss-open-connection.dingtalk.com/connect", "ticket": "synthetic-ticket"}
    post = Mock(return_value=response)
    monkeypatch.setattr("daily_automation.dingtalk_listener.requests.post", post)
    assert client.open_connection()["ticket"] == "synthetic-ticket"
    assert post.call_args.kwargs["timeout"] == 20
    assert not client.logger.propagate


def test_smtp_uses_local_key_and_records_failure_state(tmp_path, monkeypatch):
    config = {"email": {"enabled": True, "smtp_port": 465, "smtp_server": "mail.example.test",
                        "sender_email": "sender@example.test", "receiver_email": "receiver@example.test",
                        "sender_password": PasswordCrypto(tmp_path).encrypt("test-only-password")}}
    service = CampusService(tmp_path, config)
    server = Mock()
    server.__enter__ = Mock(return_value=server)
    server.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(service_module.smtplib, "SMTP_SSL", Mock(return_value=server))
    assert service._send_html("校内计划", "<p>测试</p>")
    server.login.assert_called_once_with("sender@example.test", "test-only-password")
    assert service.store.source_states()[0]["status"] == "ok"
    server.login.side_effect = OSError("network unavailable")
    assert not service._send_html("校内计划", "<p>测试</p>")
    assert service.store.source_states()[0]["status"] == "error"


def test_link_rejects_private_addresses(monkeypatch):
    from daily_automation.notice_links import _public_url
    monkeypatch.setattr("daily_automation.notice_links.socket.getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(ValueError):
        _public_url("https://example.com/notice")
    with pytest.raises(ValueError):
        _public_url("http://example.com/notice")


def test_semester_week_and_odd_even_courses():
    from daily_automation.course_calendar import parse_course_weeks, course_on_date
    from daily_automation.schedule_manager import get_today_schedule
    assert parse_course_weeks("社会学 1-8周(单)") == [1, 3, 5, 7]
    assert parse_course_weeks("管理学 1-8,10-16周（双）") == [2, 4, 6, 8, 10, 12, 14, 16]
    assert parse_course_weeks("管理学 1-4(周)") == [1, 2, 3, 4]
    assert parse_course_weeks("管理学 1至4周（双）") == [2, 4]
    course = {"name": "社会学", "weeks": [1, 3, 5, 7]}
    schedule = {"semester_start": "2026-09-21", "week_schedule": {"Monday": [course]}}
    assert not course_on_date(course, {}, date(2026, 9, 21))
    assert get_today_schedule(schedule, {}, date(2026, 9, 21))["courses"] == [course]
    assert get_today_schedule(schedule, {}, date(2026, 9, 28))["courses"] == []
    assert get_today_schedule(schedule, {}, date(2026, 10, 5))["courses"] == [course]


def test_api_first_ingests_timetable_and_todos_without_browser(tmp_path, monkeypatch):
    crypto = PasswordCrypto(tmp_path)
    service = CampusService(tmp_path, {"campus": {
        "enabled": True, "username": "student", "password": crypto.encrypt("pw"),
        "remember_password": True, "academic_year": "2026", "term": "秋",
        "semester_start": "2026-09-21",
    }})

    class FakeApi:
        def __init__(self, username, password):
            assert username == "student" and password == "pw"

        def login(self):
            pass

        def login_zdbk(self):
            pass

        def fetch_timetable(self, year, term):
            assert (year, term) == ("2026", "秋")
            return [{"kcmc": "社会学", "xqj": 1, "jc": "1-2节",
                     "zcd": "1-8周", "cdmc": "东1-101", "xm": "张老师"}]

        def login_lms(self):
            pass

        def fetch_todos(self):
            return [{"id": "t1", "course_id": "9", "title": "作业",
                     "course_name": "社会学", "end_time": "2026-10-21T23:59:00+08:00"}]

        def close(self):
            pass

    monkeypatch.setattr(service_module, "CampusCasClient", FakeApi)
    monkeypatch.setattr(service_module, "collect_public_zdbk", lambda **_: [])
    result = service.sync()

    assert result["api"] == {"cas": True, "timetable": True, "todos": True}
    schedule = service.manager.get_schedule()
    assert schedule["week_schedule"]["Monday"][0]["name"] == "社会学"
    assert schedule["timetable_origin"] == "api"
    assert schedule["timetable_term"] == "2026-秋"
    notices = service.store.list_notices()
    assert len(notices) == 1 and notices[0]["source"] == "lms"
    states = {state["source"]: state for state in service.store.source_states()}
    assert states["zdbk_timetable"]["status"] == "ok"
    assert states["lms"]["status"] == "warning"
    assert "未建立专用浏览器" in states["lms"]["detail"]
    assert any("核心数据已通过 API" in warning for warning in result["warnings"])


def test_partial_timetable_keeps_previous_synced_courses(tmp_path):
    service = CampusService(tmp_path, {})
    service.manager.save_schedule({"week_schedule": {
        "Monday": [{"name": f"旧课{i}", "source": "zdbk"} for i in range(3)],
        "Tuesday": [{"name": "手动课", "source": "manual"}],
    }})
    assert service._update_timetable({"Monday": [{"name": "新课", "source": "zdbk"}]}) == 0
    weekly = service.manager.get_schedule()["week_schedule"]
    assert [course["name"] for course in weekly["Monday"]] == ["旧课0", "旧课1", "旧课2"]
    assert weekly["Tuesday"][0]["name"] == "手动课"
    state = next(item for item in service.store.source_states() if item["source"] == "zdbk_timetable")
    assert state["status"] == "warning"
    assert "疑似部分读取" in state["detail"]


def test_browser_fallback_when_api_login_is_rejected(tmp_path, monkeypatch):
    crypto = PasswordCrypto(tmp_path)
    service = CampusService(tmp_path, {"campus": {
        "enabled": True, "username": "student", "password": crypto.encrypt("pw"),
        "remember_password": True,
    }})

    class Rejected:
        def __init__(self, *args, **kwargs):
            pass

        def login(self):
            raise CampusCredentialError("用户名或密码错误")

        def close(self):
            pass

    class Browser:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def collect(self, source, url, extra_urls=None):
            if source == "lms":
                return [], {}
            return [], {"Monday": [{"name": "浏览器课", "source": "zdbk", "weeks": []}]}

    monkeypatch.setattr(service_module, "CampusCasClient", Rejected)
    monkeypatch.setattr(service_module, "CampusBrowser", Browser)
    monkeypatch.setattr(service_module, "collect_public_zdbk", lambda **_: [])
    result = service.sync()

    assert result["api"]["cas"] is False
    assert any("统一身份认证失败" in warning for warning in result["warnings"])
    assert service.manager.get_schedule()["week_schedule"]["Monday"][0]["name"] == "浏览器课"
    states = {state["source"]: state for state in service.store.source_states()}
    assert states["zdbk_timetable"]["status"] == "ok"
    assert states["lms"]["status"] == "ok"
    assert states["zdbk_private"]["status"] == "ok"
