"""Official-API access to ZJU services through the unified CAS login.

Credentials are accepted in memory only. This module never writes the password,
the SSO cookie, service cookies, or service tickets to disk or to a log. The
optional "remember password" storage lives in the configuration layer and uses
the existing local Fernet key.

Only documented/observed ZJU endpoints are used. If CAS asks for a CAPTCHA or
the service rate-limits us, the caller should fall back to the interactive
browser session instead of trying to bypass it.
"""

from __future__ import annotations

import hashlib
import html
import re
from datetime import date, datetime
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from .course_calendar import parse_course_weeks


CAS_LOGIN = "https://zjuam.zju.edu.cn/cas/login"
CAS_PUBKEY = "https://zjuam.zju.edu.cn/cas/v2/getPubKey"
ZDBK_ENTRY = (
    "https://zjuam.zju.edu.cn/cas/login?service="
    "https%3A%2F%2Fzdbk.zju.edu.cn%2Fjwglxt%2Fxtgl%2Flogin_ssologin.html"
)
ZDBK_TIMETABLE = "https://zdbk.zju.edu.cn/jwglxt/kbcx/xskbcx_cxXsKb.html"
LMS_ENTRY = "https://courses.zju.edu.cn/user/index"
LMS_TODOS = "https://courses.zju.edu.cn/api/todos?no-intercept=true"
LMS_HOME = "https://courses.zju.edu.cn/"

TERM_TO_XQM = {"秋": "1|秋", "冬": "1|冬", "春": "2|春", "夏": "2|夏"}
TERM_ORDER = ("秋", "冬", "春", "夏")
WEEKDAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
WEEKDAY_TEXT = {
    "星期一": 1, "星期二": 2, "星期三": 3, "星期四": 4,
    "星期五": 5, "星期六": 6, "星期日": 7,
    "周一": 1, "周二": 2, "周三": 3, "周四": 4,
    "周五": 5, "周六": 6, "周日": 7,
}
ALLOWED_HOSTS = {
    "zjuam.zju.edu.cn", "identity.zju.edu.cn",
    "zdbk.zju.edu.cn", "courses.zju.edu.cn", "course.zju.edu.cn",
}
LMS_HOSTS = {"courses.zju.edu.cn", "course.zju.edu.cn"}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


class CampusError(RuntimeError):
    """Base class for API failures safe to show to the user."""


class CampusCredentialError(CampusError):
    """Username/password/account rejected by CAS."""


class CampusCaptchaError(CampusError):
    """CAS or a service requires a CAPTCHA; the browser fallback is required."""


class CampusRateLimitError(CampusError):
    """The service asked us to slow down (HTTP 921 or 429)."""


class CampusSessionError(CampusError):
    """A service session is missing or was rejected."""


class CampusProtocolError(CampusError):
    """An endpoint changed shape or returned an unexpected page."""


def _compact(text: str, limit: int = 240) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()[:limit]


def _safe_message(text: str, username: str = "", password: str = "") -> str:
    message = str(text or "")
    for secret in (password, username):
        if secret:
            message = message.replace(secret, "<已隐藏>")
    return _compact(message)


def _clean_text(value: object, limit: int = 500) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _first_text(*values: object, limit: int = 500) -> str:
    for value in values:
        text = _clean_text(value, limit)
        if text:
            return text
    return ""


def _cookie_value(session: requests.Session, name: str, host: str) -> str:
    """Read a cookie only when its domain applies to ``host``.

    Cookie names such as ``JSESSIONID`` and ``session`` are reused by several
    ZJU hosts, so a name-only lookup could send one service's cookie to another.
    """
    value = ""
    for cookie in session.cookies:
        domain = (cookie.domain or "").lstrip(".").lower()
        if cookie.name != name or not cookie.value or not domain:
            continue
        if host == domain or host.endswith("." + domain):
            value = cookie.value
    return value


def _has_cookie(session: requests.Session, name: str, host: str) -> bool:
    return bool(_cookie_value(session, name, host))


def _meta_refresh_target(html: str, base: str) -> str | None:
    # Keycloak/CAS can end a redirect chain with HTTP 200 + meta refresh.
    for tag in re.findall(r"<meta\b[^>]*>", html or "", re.I):
        if "refresh" not in tag.lower():
            continue
        content = re.search(r"content\s*=\s*(['\"])(.*?)\1", tag, re.I)
        if not content:
            continue
        target = re.search(r"url\s*=\s*['\"]?([^'\";]+)", content.group(2), re.I)
        if target:
            return urljoin(base, target.group(1).strip())
    return None


def _auto_submit_form(html: str, base: str) -> tuple[str, str, dict[str, str]] | None:
    """Return a same-host Keycloak auto-submit form, if one is present.

    A page that contains a password field is a real login form, not an SSO
    hand-off; we must not post a password to it.
    """
    soup = BeautifulSoup(html or "", "lxml")
    for form in soup.find_all("form"):
        action = urljoin(base, str(form.get("action") or base))
        if not _is_allowed_https(action):
            continue
        if form.find("input", {"type": "password"}):
            continue
        data = {}
        for field in form.find_all("input"):
            name = str(field.get("name") or "").strip()
            if name and str(field.get("type") or "").lower() not in {"submit", "button", "checkbox"}:
                data[name] = str(field.get("value") or "")
        if data:
            return action, str(form.get("method") or "get").lower(), data
    return None


def _execution_from(html: str) -> str:
    for tag in re.findall(r"<input\b[^>]*>", html or "", re.I):
        if re.search(r"name\s*=\s*['\"]execution['\"]", tag, re.I):
            value = re.search(r"value\s*=\s*(['\"])(.*?)\1", tag, re.I)
            if value and value.group(2):
                return value.group(2)
    raise CampusProtocolError("统一身份认证登录页缺少 execution，页面可能已改版")


def _is_allowed_https(url: str) -> bool:
    parsed = urlparse(url or "")
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS


def encrypt_cas_password(password: str, modulus_hex: str, exponent_hex: str) -> str:
    """ZJU CAS uses raw RSA (no PKCS#1 padding), matching Celechron."""
    if not re.fullmatch(r"[0-9a-fA-F]+", modulus_hex or "") or not re.fullmatch(r"[0-9a-fA-F]+", exponent_hex or ""):
        raise CampusProtocolError("统一身份认证公钥格式异常")
    modulus = int(modulus_hex, 16)
    exponent = int(exponent_hex, 16)
    plain = int.from_bytes(password.encode("utf-8"), "big")
    if plain >= modulus:
        raise CampusCredentialError("密码长度超出 CAS 公钥模数范围")
    return format(pow(plain, exponent, modulus), "x").zfill(len(modulus_hex))


def parse_timetable_items(items: list[dict]) -> dict[str, list[dict]]:
    """Map ZDBK ``kbList`` rows to the schedule schema used by the app.

    Current ZDBK responses carry course name/teacher/location in the HTML
    ``kcb`` block and start/duration in ``djj``/``skcd``; older responses use
    flat ``kcmc``/``cdmc``/``xm`` fields. Both shapes are accepted.
    """
    result: dict[str, list[dict]] = {day: [] for day in WEEKDAY_NAMES}
    if not isinstance(items, list):
        raise CampusProtocolError("教务课表接口结构异常，缺少课程列表")
    seen = set()
    for row in items:
        if not isinstance(row, dict):
            continue
        if str(row.get("sfyjskc") or "").strip() == "1":
            continue
        kcb_name, kcb_teacher, kcb_location = _parse_kcb_block(row.get("kcb"))
        name = _first_text(row.get("kcmc"), row.get("kcbm"), kcb_name, limit=160)
        day_raw = row.get("xqj") if row.get("xqj") not in (None, "") else row.get("xqjmc")
        day = _weekday(day_raw)
        if not name or not day:
            continue
        time_text = _first_text(row.get("jc"), row.get("jcs"), row.get("jcor"), limit=60)
        if not time_text:
            start = _positive_int(row.get("djj"))
            duration = _positive_int(row.get("skcd"))
            if start:
                time_text = f"{start}-{start + duration - 1}节" if duration > 1 else f"{start}节"
        location = _first_text(row.get("cdmc"), row.get("jxdd"), kcb_location, limit=120)
        teacher = _first_text(row.get("xm"), row.get("jsxm"), kcb_teacher, limit=80)
        weeks_text = _first_text(row.get("zcd"), row.get("zcmc"), limit=120)
        weeks = parse_course_weeks(weeks_text)
        weeks_note = "" if weeks else _weeks_note(row.get("xxq"), row.get("dsz"))
        course = {
            "name": name,
            "time": time_text,
            "location": location,
            "teacher": teacher,
            "source": "zdbk",
            "weeks": weeks,
        }
        if weeks_note:
            course["weeks_note"] = weeks_note
        signature = (day, name, time_text, location, teacher, tuple(weeks), weeks_note)
        if signature in seen:
            continue
        seen.add(signature)
        result[day].append(course)
    if items and not seen:
        keys = sorted({str(key) for row in items if isinstance(row, dict) for key in row})[:12]
        detail = f"（返回字段：{', '.join(keys)}）" if keys else ""
        raise CampusProtocolError(
            "教务课表接口返回了课程，但无法识别课程名或星期，页面结构可能已改版" + detail)
    return result


def _parse_kcb_block(value: object) -> tuple[str, str, str]:
    """Extract course, teacher and location from ZDBK's HTML ``kcb`` block."""
    raw = html.unescape(str(value or ""))
    if not raw:
        return "", "", ""
    match = re.search(
        r"(.*?)<br\s*/?>(.*?)<br\s*/?>(.*?)<br\s*/?>(.*?)(?:zwf|$)",
        raw, re.I | re.S,
    )
    if match:
        parts = [re.sub(r"<[^>]+>", "", part).strip() for part in match.groups()]
    else:
        text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
        text = re.sub(r"<[^>]+>", "", text)
        parts = [_clean_text(line, 160) for line in text.splitlines() if line.strip()]
    if not parts:
        return "", "", ""
    name = _clean_text(parts[0], 160)
    if len(parts) >= 4:
        teacher, location = parts[2], parts[3]
    elif len(parts) == 3:
        teacher, location = parts[1], parts[2]
    elif len(parts) == 2:
        teacher, location = parts[1], ""
    else:
        teacher, location = "", ""
    location = re.sub(r"\s*zwf\s*$", "", location, flags=re.I)
    return name, _clean_text(teacher, 80), _clean_text(location, 120)


def _positive_int(value: object) -> int:
    match = re.search(r"\d+", str(value or ""))
    if not match:
        return 0
    number = int(match.group())
    return number if number > 0 else 0


def _weeks_note(term: object, parity: object) -> str:
    term_text = _clean_text(term, 20)
    parity_text = {"1": "单周", "0": "双周"}.get(_clean_text(parity, 4), "")
    return " ".join(part for part in (term_text, parity_text) if part)


def _weekday(value: object) -> str:
    if isinstance(value, int):
        return WEEKDAY_NAMES[value - 1] if 1 <= value <= 7 else ""
    text = _clean_text(value, 40)
    if text in WEEKDAY_TEXT:
        return WEEKDAY_NAMES[WEEKDAY_TEXT[text] - 1]
    if text.isdigit() and 1 <= int(text) <= 7:
        return WEEKDAY_NAMES[int(text) - 1]
    return ""


def _display_time(value: object) -> str:
    text = _clean_text(value, 80)
    if not text:
        return ""
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if moment.tzinfo is not None:
            moment = moment.astimezone(ZoneInfo("Asia/Shanghai"))
        return moment.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return text


def parse_lms_todos(payload: object) -> list[dict]:
    """Turn Learning at ZJU todos into reviewable notice records."""
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("todo_list", payload.get("todos"))
    else:
        rows = None
    if not isinstance(rows, list):
        raise CampusProtocolError("学在浙大待办接口结构异常，缺少 todo_list")
    notices = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        todo_id = _clean_text(row.get("id") or row.get("todo_id") or row.get("task_id") or "", 120)
        title = _clean_text(row.get("title") or row.get("name") or "", 200)
        course_raw = row.get("course_name") or row.get("course") or ""
        if isinstance(course_raw, dict):
            course_raw = course_raw.get("name") or course_raw.get("course_name") or ""
        course = _clean_text(course_raw, 120)
        course_id = _clean_text(row.get("course_id") or "", 40)
        end_time = _display_time(row.get("end_time") or row.get("deadline") or row.get("due_at") or "")
        if not title and not course:
            continue
        label = " · ".join(part for part in (course, title) if part) or "学在浙大待办"
        body_lines = [f"学在浙大待办：{title or label}"]
        if course:
            body_lines.append(f"课程：{course}")
        if end_time:
            body_lines.append(f"截止时间：{end_time}")
        else:
            body_lines.append("截止时间：接口未提供，请打开原页面核对")
        digest = todo_id or hashlib.sha256(
            (label + "\n" + end_time).encode("utf-8")).hexdigest()
        external_id = f"lms-todo:{course_id}:{digest}" if course_id else f"lms-todo:{digest}"
        if external_id in seen:
            continue
        seen.add(external_id)
        url = f"https://courses.zju.edu.cn/course/{course_id}/" if course_id.isdigit() else LMS_HOME
        notices.append({
            "source": "lms",
            "external_id": external_id,
            "title": label[:500],
            "body": "\n".join(body_lines),
            "url": url,
            "published_at": None,
        })
    if rows and not notices:
        raise CampusProtocolError("学在浙大待办接口返回了条目，但缺少标题和课程信息，页面结构可能已改版")
    return notices


def default_academic_year(today: date | None = None) -> str:
    today = today or date.today()
    return str(today.year if today.month >= 8 else today.year - 1)


def default_term(today: date | None = None) -> str:
    today = today or date.today()
    month = today.month
    if month in {8, 9, 10}:
        return "秋"
    if month in {11, 12, 1}:
        return "冬"
    if month in {2, 3, 4}:
        return "春"
    return "夏"


def resolve_term(settings: dict, today: date | None = None) -> tuple[str, str]:
    """Validate configured term fields or derive them from today's date."""
    year = str(settings.get("academic_year") or "").strip()
    term = str(settings.get("term") or "").strip()
    if year and not re.fullmatch(r"20\d{2}", year):
        raise CampusProtocolError("学年应填写四位起始年份，例如 2025")
    if term and term not in TERM_TO_XQM:
        raise CampusProtocolError("学期应为 秋、冬、春、夏 之一")
    return year or default_academic_year(today), term or default_term(today)


class CampusCasClient:
    """One in-memory CAS session with independent ZDBK and LMS service sessions."""

    def __init__(self, username: str, password: str, timeout: tuple[int, int] = (10, 25),
                 session: requests.Session | None = None):
        self.username = str(username or "").strip()
        self._password = str(password or "")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9"})
        self._cas_ready = False
        self._zdbk_ready = False
        self._lms_ready = False

    def close(self) -> None:
        self._password = ""
        try:
            self.session.close()
        except Exception:
            pass

    def login(self) -> None:
        if not self.username or not self._password:
            raise CampusCredentialError("未提供学号或密码")
        page = self.session.get(ZDBK_ENTRY, timeout=self.timeout)
        self._raise_http(page, "统一身份认证登录页")
        if _is_allowed_https(page.url) and page.url != CAS_LOGIN and _has_cookie(
                self.session, "iPlanetDirectoryPro", "zjuam.zju.edu.cn") and "execution" not in page.text:
            # An already-authenticated session can skip the form.
            self._cas_ready = True
            return
        execution = _execution_from(page.text)
        pubkey_response = self.session.get(CAS_PUBKEY, timeout=self.timeout)
        self._raise_http(pubkey_response, "统一身份认证公钥")
        try:
            pubkey = pubkey_response.json()
            modulus = str(pubkey.get("modulus") or "")
            exponent = str(pubkey.get("exponent") or "")
        except (ValueError, AttributeError) as exc:
            raise CampusProtocolError("统一身份认证公钥接口未返回 JSON") from exc
        encrypted = encrypt_cas_password(self._password, modulus, exponent)
        response = self.session.post(
            CAS_LOGIN,
            data={
                "username": self.username,
                "password": encrypted,
                "authcode": "",
                "execution": execution,
                "_eventId": "submit",
            },
            timeout=self.timeout,
            allow_redirects=False,
        )
        body = response.text or ""
        if "用户名或密码错误" in body or "用户名或者密码有误" in body or "密码错误" in body:
            raise CampusCredentialError("统一身份认证返回：用户名或密码错误")
        if "账号被锁定" in body or "账号已锁定" in body:
            raise CampusCredentialError("统一身份认证返回：账号被锁定，请稍后再试")
        if not _has_cookie(self.session, "iPlanetDirectoryPro", "zjuam.zju.edu.cn"):
            if "验证码" in body or "captcha" in body.lower():
                raise CampusCaptchaError("统一身份认证要求验证码；请使用浏览器登录向导")
            self._raise_http(response, "统一身份认证登录")
            raise CampusCredentialError("未取得统一身份认证会话，请核对账号状态或页面改版")
        self._raise_http(response, "统一身份认证登录")
        self._cas_ready = True

    def login_zdbk(self) -> None:
        if not self._cas_ready:
            raise CampusSessionError("统一身份认证会话尚未建立")
        response = self.session.get(ZDBK_ENTRY, timeout=self.timeout, allow_redirects=False)
        location = response.headers.get("Location", "")
        if response.status_code not in {301, 302, 303, 307, 308} or not location:
            self._raise_http(response, "教务登录")
            raise CampusProtocolError("教务登录未获得 CAS service ticket，SSO 可能已失效")
        target = urljoin(ZDBK_ENTRY, location)
        if target.startswith("http://zdbk.zju.edu.cn"):
            target = "https://" + target[7:]
        if not _is_allowed_https(target) or urlparse(target).hostname != "zdbk.zju.edu.cn":
            raise CampusProtocolError("教务登录跳转到了非预期站点")
        response = self.session.get(target, timeout=self.timeout)
        self._raise_http(response, "教务登录")
        if "zjuam.zju.edu.cn/cas/login" in response.url:
            raise CampusSessionError("教务登录被退回统一身份认证，SSO 可能已失效")
        if not _cookie_value(self.session, "JSESSIONID", "zdbk.zju.edu.cn"):
            raise CampusSessionError("教务登录未取得 JSESSIONID")
        if not _cookie_value(self.session, "route", "zdbk.zju.edu.cn"):
            raise CampusSessionError("教务登录未取得 route")
        self._zdbk_ready = True

    def login_lms(self) -> None:
        if not self._cas_ready:
            raise CampusSessionError("统一身份认证会话尚未建立")
        url = LMS_ENTRY
        for _ in range(15):
            response = self.session.get(url, timeout=self.timeout, allow_redirects=False)
            host = (urlparse(url).hostname or "").lower()
            if response.is_redirect:
                location = response.headers.get("Location", "")
                if not location:
                    raise CampusProtocolError("学在浙大登录跳转缺少 Location")
                url = self._redirect_target(url, location)
                continue
            if not 200 <= response.status_code < 300:
                self._raise_http(response, "学在浙大登录")
                raise CampusProtocolError(f"学在浙大登录失败：HTTP {response.status_code}")
            if host in LMS_HOSTS and _cookie_value(self.session, "session", "courses.zju.edu.cn"):
                self._lms_ready = True
                return
            target = _meta_refresh_target(response.text, url)
            if target:
                url = self._redirect_target(url, target)
                continue
            form = _auto_submit_form(response.text, url)
            if form:
                action, method, data = form
                url = self._redirect_target(url, action)
                if method == "post":
                    response = self.session.post(url, data=data, timeout=self.timeout, allow_redirects=False)
                else:
                    response = self.session.get(url, params=data, timeout=self.timeout, allow_redirects=False)
                location = response.headers.get("Location", "")
                if response.is_redirect and location:
                    url = self._redirect_target(url, location)
                continue
            if host in {"zjuam.zju.edu.cn", "identity.zju.edu.cn"}:
                raise CampusSessionError("学在浙大登录被退回认证页，SSO 可能已失效")
            raise CampusSessionError("学在浙大登录已结束，但未取得 session")
        raise CampusProtocolError("学在浙大登录跳转次数过多")

    def fetch_timetable(self, year: str, term: str) -> list[dict]:
        if not self._zdbk_ready:
            raise CampusSessionError("教务会话尚未建立")
        xqm = TERM_TO_XQM.get(term)
        if not xqm or not re.fullmatch(r"20\d{2}", str(year or "")):
            raise CampusProtocolError("学年或学期参数无效")
        response = self.session.post(
            ZDBK_TIMETABLE,
            data={"xnm": str(year), "xqm": xqm, "captcha_value": ""},
            timeout=self.timeout,
        )
        body = response.text or ""
        if "captcha_error" in body:
            raise CampusCaptchaError("教务课表接口要求验证码；请使用浏览器登录向导")
        self._raise_http(response, "教务课表")
        if "text/html" in (response.headers.get("content-type") or "").lower() or body.lstrip().startswith("<"):
            raise CampusSessionError("教务课表接口返回网页，登录态可能未建立")
        try:
            payload = response.json()
        except ValueError as exc:
            raise CampusProtocolError("教务课表接口未返回 JSON，登录态可能未建立") from exc
        if not isinstance(payload, dict):
            raise CampusProtocolError("教务课表接口结构异常")
        if payload.get("captcha_error") or "captcha_error" in str(payload):
            raise CampusCaptchaError("教务课表接口要求验证码；请使用浏览器登录向导")
        rows = payload.get("kbList")
        if not isinstance(rows, list):
            raise CampusProtocolError("教务课表接口结构异常，缺少 kbList")
        return rows

    def fetch_todos(self) -> list[dict]:
        if not self._lms_ready:
            raise CampusSessionError("学在浙大会话尚未建立")
        response = self.session.get(LMS_TODOS, timeout=self.timeout)
        self._raise_http(response, "学在浙大待办")
        body = response.text or ""
        if "text/html" in (response.headers.get("content-type") or "").lower() or body.lstrip().startswith("<"):
            raise CampusSessionError("学在浙大待办接口返回网页，登录态可能未建立")
        try:
            payload = response.json()
        except ValueError as exc:
            raise CampusProtocolError("学在浙大待办接口未返回 JSON") from exc
        if isinstance(payload, dict):
            rows = payload.get("todo_list", payload.get("todos", []))
        else:
            rows = payload
        if not isinstance(rows, list):
            raise CampusProtocolError("学在浙大待办列表结构异常")
        return rows

    def _redirect_target(self, base: str, location: str) -> str:
        target = urljoin(base, location)
        if target.startswith("http://"):
            parsed = urlparse(target)
            if parsed.hostname in ALLOWED_HOSTS:
                target = "https://" + target[7:]
        if not _is_allowed_https(target):
            raise CampusProtocolError("登录跳转到了非校内域名，已停止")
        return target

    @staticmethod
    def _raise_http(response: requests.Response, label: str) -> None:
        status = response.status_code
        if status in {921, 429}:
            raise CampusRateLimitError(f"{label}请求过于频繁（HTTP {status}），请稍后再试")
        if status >= 400:
            raise CampusProtocolError(f"{label}失败：HTTP {status}")


def probe_account(username: str, password: str, year: str, term: str,
                  timeout: tuple[int, int] = (10, 25)) -> dict:
    """Live read-only account check for the UI/CLI; never persists anything."""
    result = {
        "ok": False,
        "cas": "unknown",
        "zdbk": "unknown",
        "lms": "unknown",
        "zdbk_courses": 0,
        "lms_todos": 0,
        "messages": [],
    }
    client = CampusCasClient(username, password, timeout=timeout)
    try:
        try:
            client.login()
            result["cas"] = "ok"
        except Exception as exc:
            result["cas"] = "error"
            result["messages"].append(f"统一身份认证：{_safe_message(str(exc), username, password) or type(exc).__name__}")
            return result
        try:
            client.login_zdbk()
            rows = client.fetch_timetable(year, term)
            timetable = parse_timetable_items(rows)
            result["zdbk"] = "ok"
            result["zdbk_courses"] = sum(len(courses) for courses in timetable.values())
        except Exception as exc:
            result["zdbk"] = "error"
            result["messages"].append(f"教务：{_safe_message(str(exc), username, password) or type(exc).__name__}")
        try:
            client.login_lms()
            todos = client.fetch_todos()
            result["lms"] = "ok"
            result["lms_todos"] = len(parse_lms_todos(todos))
        except Exception as exc:
            result["lms"] = "error"
            result["messages"].append(f"学在浙大：{_safe_message(str(exc), username, password) or type(exc).__name__}")
        result["ok"] = result["zdbk"] == "ok" and result["lms"] == "ok"
        return result
    finally:
        client.close()
