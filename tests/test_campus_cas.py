"""CAS/API unit tests use synthetic responses and never contact ZJU services."""

from datetime import date
from types import SimpleNamespace

import pytest

from daily_automation.campus_cas import (
    CAS_LOGIN,
    CAS_PUBKEY,
    LMS_ENTRY,
    LMS_TODOS,
    ZDBK_ENTRY,
    ZDBK_TIMETABLE,
    CampusCaptchaError,
    CampusCasClient,
    CampusCredentialError,
    CampusProtocolError,
    CampusRateLimitError,
    CampusSessionError,
    _auto_submit_form,
    _cookie_value,
    _execution_from,
    _meta_refresh_target,
    encrypt_cas_password,
    parse_lms_todos,
    parse_timetable_items,
    probe_account,
    resolve_term,
)


class FakeResponse:
    def __init__(self, status=200, text="", json_data=None, headers=None, url="", cookies=None):
        self.status_code = status
        self.text = text
        self._json = json_data
        self.headers = headers or {}
        self.url = url
        self.cookies = cookies or []
        self.is_redirect = status in {301, 302, 303, 307, 308} and bool(self.headers.get("Location"))

    def json(self):
        if self._json is None:
            raise ValueError("not json")
        return self._json


def cookie(name, value, domain):
    return SimpleNamespace(name=name, value=value, domain=domain)


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}
        self.cookies = []
        self.calls = []

    def _next(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        for item in response.cookies:
            self.cookies.append(item)
        return response

    def get(self, url, **kwargs):
        return self._next("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self._next("POST", url, **kwargs)

    def close(self):
        pass


def toy_key():
    p, q, e = 1009, 1013, 65537
    n = p * q
    d = pow(e, -1, (p - 1) * (q - 1))
    return n, e, d


def test_raw_rsa_round_trip_and_padding():
    n, e, d = toy_key()
    plain = "ZJ"
    encrypted = encrypt_cas_password(plain, format(n, "x"), format(e, "x"))
    assert len(encrypted) == len(format(n, "x"))
    recovered = pow(int(encrypted, 16), d, n).to_bytes((n.bit_length() + 7) // 8, "big")
    assert recovered.lstrip(b"\x00").decode() == plain
    with pytest.raises(CampusProtocolError):
        encrypt_cas_password(plain, "not-hex", "10001")


def test_execution_meta_refresh_and_cookie_scoping():
    assert _execution_from('<input value="token-1" name="execution">') == "token-1"
    with pytest.raises(CampusProtocolError):
        _execution_from("<html>changed</html>")
    assert _meta_refresh_target(
        '<meta http-equiv="refresh" content="0; URL=\'/cas/login?service=x\'">',
        "https://zjuam.zju.edu.cn/cas/login") == "https://zjuam.zju.edu.cn/cas/login?service=x"
    assert _meta_refresh_target("<html>no refresh</html>", "https://zjuam.zju.edu.cn/") is None

    session = FakeSession([])
    session.cookies = [
        cookie("session", "wrong", "evil.test"),
        cookie("session", "right", "courses.zju.edu.cn"),
        cookie("route", "zdbk-route", "zdbk.zju.edu.cn"),
    ]
    assert _cookie_value(session, "session", "courses.zju.edu.cn") == "right"
    assert _cookie_value(session, "session", "course.zju.edu.cn") == ""
    assert _cookie_value(session, "route", "zdbk.zju.edu.cn") == "zdbk-route"


def test_auto_submit_form_ignores_password_form_and_external_action():
    keycloak = ('<form action="https://identity.zju.edu.cn/auth" method="post">'
                '<input name="code" value="abc"></form>')
    assert _auto_submit_form(keycloak, "https://zjuam.zju.edu.cn/") == (
        "https://identity.zju.edu.cn/auth", "post", {"code": "abc"})
    login_form = ('<form action="https://zjuam.zju.edu.cn/cas/login" method="post">'
                  '<input type="password" name="password"></form>')
    assert _auto_submit_form(login_form, "https://zjuam.zju.edu.cn/") is None
    external = '<form action="https://evil.test/callback"><input name="x" value="1"></form>'
    assert _auto_submit_form(external, "https://zjuam.zju.edu.cn/") is None


def test_timetable_mapping_weeks_location_and_duplicates():
    rows = [
        {"kcmc": "社会学", "xqj": "1", "jc": "1-2节", "zcd": "1-8周(单)",
         "cdmc": "东1-101", "xm": "张老师"},
        {"kcmc": "社会学", "xqj": 1, "jc": "1-2节", "zcd": "1-8周(单)",
         "cdmc": "东1-101", "xm": "张老师"},
        {"kcmc": "管理学", "xqjmc": "星期三", "jcs": "3-4", "zcd": "1-16周",
         "cdmc": "西2-202", "xm": "李老师"},
        {"kcmc": "", "xqj": 2},
        {"kcmc": "无星期", "xqj": 9},
    ]
    timetable = parse_timetable_items(rows)
    assert len(timetable["Monday"]) == 1
    course = timetable["Monday"][0]
    assert course["name"] == "社会学"
    assert course["time"] == "1-2节"
    assert course["location"] == "东1-101"
    assert course["teacher"] == "张老师"
    assert course["source"] == "zdbk"
    assert course["weeks"] == [1, 3, 5, 7]
    assert timetable["Wednesday"][0]["name"] == "管理学"

    assert parse_timetable_items([]) == {day: [] for day in (
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")}
    with pytest.raises(CampusProtocolError):
        parse_timetable_items([{"xqj": 1}])


def test_timetable_accepts_current_kcb_html_shape():
    rows = [
        {"kcb": "高等数学（甲）I<br>01<br>张老师<br>东1A-101zwf",
         "xqj": "2", "djj": "3", "skcd": "2", "xxq": "秋冬"},
        {"kcb": "大学物理<br/>02<br>李老师<br/>西2-202zwf<br>",
         "xqj": 4, "djj": 6, "skcd": 3, "xxq": "秋", "dsz": "1"},
        {"kcb": "线性代数&lt;br&gt;03&lt;br&gt;王老师&lt;br&gt;东2-303zwf",
         "xqj": "5", "djj": "1", "skcd": "1", "xxq": "春"},
        {"kcb": "", "xqj": 5},
    ]
    timetable = parse_timetable_items(rows)
    assert len(timetable["Tuesday"]) == 1
    course = timetable["Tuesday"][0]
    assert course["name"] == "高等数学（甲）I"
    assert course["teacher"] == "张老师"
    assert course["location"] == "东1A-101"
    assert course["time"] == "3-4节"
    assert course["weeks"] == []
    assert course["weeks_note"] == "秋冬"

    physics = timetable["Thursday"][0]
    assert physics["name"] == "大学物理"
    assert physics["location"] == "西2-202"
    assert physics["time"] == "6-8节"
    assert physics["weeks_note"] == "秋 单周"

    linear = timetable["Friday"][0]
    assert linear["name"] == "线性代数"
    assert linear["teacher"] == "王老师"
    assert linear["time"] == "1节"


def test_lms_todos_are_stable_and_carry_deadline_evidence():
    payload = {"todo_list": [
        {"id": "t1", "course_id": "12", "title": "作业一", "course_name": "社会学",
         "end_time": "2026-10-21T23:59:00+08:00"},
        {"id": "t1", "course_id": "12", "title": "作业一", "course_name": "社会学",
         "end_time": "2026-10-21T23:59:00+08:00"},
        {"id": "t2", "course_id": "13", "title": "测验", "course_name": "管理学",
         "end_time": "2026-10-22 08:00:00"},
    ]}
    notices = parse_lms_todos(payload)
    assert len(notices) == 2
    first = notices[0]
    assert first["source"] == "lms"
    assert first["external_id"] == "lms-todo:12:t1"
    assert first["title"] == "社会学 · 作业一"
    assert "截止时间：2026-10-21 23:59" in first["body"]
    assert first["url"] == "https://courses.zju.edu.cn/course/12/"
    assert parse_lms_todos({"todo_list": []}) == []
    with pytest.raises(CampusProtocolError):
        parse_lms_todos({"unexpected": []})
    with pytest.raises(CampusProtocolError):
        parse_lms_todos({"todo_list": [{"id": "bad"}]})


def test_term_resolution_and_defaults():
    assert resolve_term({}, date(2026, 9, 1)) == ("2026", "秋")
    assert resolve_term({}, date(2026, 1, 5)) == ("2025", "冬")
    assert resolve_term({"academic_year": "2025", "term": "春"}, date(2026, 9, 1)) == ("2025", "春")
    with pytest.raises(CampusProtocolError):
        resolve_term({"academic_year": "25", "term": "秋"})
    with pytest.raises(CampusProtocolError):
        resolve_term({"academic_year": "2025", "term": "秋春"})


def test_login_uses_raw_rsa_and_requires_sso_cookie():
    n, e, _ = toy_key()
    session = FakeSession([
        FakeResponse(text='<input name="execution" value="exec-1">', url=CAS_LOGIN),
        FakeResponse(json_data={"modulus": format(n, "x"), "exponent": format(e, "x")}, url=CAS_PUBKEY),
        FakeResponse(status=302, headers={"Location": "https://zjuam.zju.edu.cn/cas/login"},
                     url=CAS_LOGIN, cookies=[cookie("iPlanetDirectoryPro", "sso", "zjuam.zju.edu.cn")]),
    ])
    client = CampusCasClient("2025", "pw", session=session)
    client.login()
    assert client._cas_ready
    posted = session.calls[2][2]["data"]
    assert posted["username"] == "2025"
    assert posted["password"] != "pw"
    assert posted["execution"] == "exec-1"


def test_login_errors_are_classified_without_echoing_password():
    n, e, _ = toy_key()
    for body, expected in (("用户名或密码错误", CampusCredentialError),
                           ("请输入验证码", CampusCaptchaError)):
        session = FakeSession([
            FakeResponse(text='<input name="execution" value="exec-1">', url=CAS_LOGIN),
            FakeResponse(json_data={"modulus": format(n, "x"), "exponent": format(e, "x")}, url=CAS_PUBKEY),
            FakeResponse(text=body, url=CAS_LOGIN),
        ])
        client = CampusCasClient("2025", "pw", session=session)
        with pytest.raises(expected) as error:
            client.login()
        assert "pw" not in str(error.value)
        assert "2025" not in str(error.value)


def test_zdbk_service_session_requires_jsessionid_and_route():
    session = FakeSession([
        FakeResponse(status=302, headers={"Location": "http://zdbk.zju.edu.cn/jwglxt/xtgl/login_ssologin.html?ticket=t"}),
        FakeResponse(text="ok", cookies=[
            cookie("JSESSIONID", "j", "zdbk.zju.edu.cn"),
            cookie("route", "r", "zdbk.zju.edu.cn"),
        ]),
    ])
    client = CampusCasClient("2025", "pw", session=session)
    client._cas_ready = True
    client.login_zdbk()
    assert client._zdbk_ready
    assert session.calls[1][1].startswith("https://zdbk.zju.edu.cn/")


def test_lms_meta_refresh_chain_requires_courses_session_cookie():
    session = FakeSession([
        FakeResponse(text='<meta http-equiv="refresh" content="0;url=https://identity.zju.edu.cn/auth">',
                     url=LMS_ENTRY),
        FakeResponse(status=302, headers={"Location": "https://courses.zju.edu.cn/user/index"}),
        FakeResponse(text="app", cookies=[cookie("session", "s", "courses.zju.edu.cn")],
                     url="https://courses.zju.edu.cn/user/index"),
    ])
    client = CampusCasClient("2025", "pw", session=session)
    client._cas_ready = True
    client.login_lms()
    assert client._lms_ready
    assert len(session.calls) == 3


def test_api_errors_captcha_rate_limit_and_html():
    client = CampusCasClient("2025", "pw", session=FakeSession([
        FakeResponse(status=921),
    ]))
    client._zdbk_ready = True
    with pytest.raises(CampusRateLimitError):
        client.fetch_timetable("2026", "秋")

    client = CampusCasClient("2025", "pw", session=FakeSession([
        FakeResponse(text="captcha_error", headers={"content-type": "application/json"}),
    ]))
    client._zdbk_ready = True
    with pytest.raises(CampusCaptchaError):
        client.fetch_timetable("2026", "秋")

    client = CampusCasClient("2025", "pw", session=FakeSession([
        FakeResponse(text="<html>login</html>", headers={"content-type": "text/html"}),
    ]))
    client._zdbk_ready = True
    with pytest.raises(CampusSessionError):
        client.fetch_timetable("2026", "秋")

    client = CampusCasClient("2025", "pw", session=FakeSession([
        FakeResponse(json_data={"kbList": [{"kcmc": "社会学", "xqj": 1}]}),
    ]))
    client._zdbk_ready = True
    assert client.fetch_timetable("2026", "秋")[0]["kcmc"] == "社会学"
    assert ZDBK_TIMETABLE in client.session.calls[0][1]


def test_lms_todos_http_shape():
    client = CampusCasClient("2025", "pw", session=FakeSession([
        FakeResponse(json_data={"todo_list": [{"id": "1", "title": "作业"}]},
                     headers={"content-type": "application/json"}),
    ]))
    client._lms_ready = True
    assert client.fetch_todos()[0]["title"] == "作业"
    assert LMS_TODOS in str(client.session.calls[0][1])

    client = CampusCasClient("2025", "pw", session=FakeSession([
        FakeResponse(text="<html>", headers={"content-type": "text/html"}),
    ]))
    client._lms_ready = True
    with pytest.raises(CampusSessionError):
        client.fetch_todos()


def test_probe_account_reports_partial_failure_without_secrets(monkeypatch):
    class FakeClient:
        def __init__(self, username, password, timeout=(10, 25)):
            self.username, self.password = username, password

        def login(self):
            pass

        def login_zdbk(self):
            raise CampusSessionError("教务会话失败")

        def login_lms(self):
            pass

        def fetch_todos(self):
            return [{"id": "1", "course_id": "2", "title": "作业", "course_name": "课程"}]

        def close(self):
            pass

    monkeypatch.setattr("daily_automation.campus_cas.CampusCasClient", FakeClient)
    result = probe_account("2025", "very-secret", "2026", "秋")
    assert result["cas"] == "ok"
    assert result["zdbk"] == "error"
    assert result["lms"] == "ok"
    assert result["lms_todos"] == 1
    assert not result["ok"]
    assert "very-secret" not in str(result)
