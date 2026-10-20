"""Best-effort campus collectors with explicit authentication and coverage states."""

from __future__ import annotations

import hashlib
import re
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

import requests
from bs4 import BeautifulSoup
from .runtime_lock import runtime_lock
from .notice_links import fetch_notice_link
from .course_calendar import parse_course_weeks


LMS_URL = "https://course.zju.edu.cn/"
LMS_HOSTS = {"course.zju.edu.cn", "courses.zju.edu.cn"}
ZDBK_URL = "https://zdbk.zju.edu.cn/jwglxt/xtgl/login_slogin.html?language=zh_CN"
ZDBK_PUBLIC_URL = "https://zdbk.zju.edu.cn/jwglxt/xtgl/xwck_cxMoreLoginNews.html"
NOTICE_LINK = re.compile(r"作业|通知|公告|待办|homework|assignment|notice|announcement|xwck", re.I)
COURSE_LINK = re.compile(r"/course/|我的课程|课程中心|课表|课程表|kbcx", re.I)
DATE_TEXT = re.compile(r"20\d{2}[-/.年]\s*\d{1,2}[-/.月]\s*\d{1,2}")
WEEKDAYS = {"星期一": "Monday", "星期二": "Tuesday", "星期三": "Wednesday", "星期四": "Thursday",
            "星期五": "Friday", "星期六": "Saturday", "星期日": "Sunday", "周一": "Monday",
            "周二": "Tuesday", "周三": "Wednesday", "周四": "Thursday", "周五": "Friday",
            "周六": "Saturday", "周日": "Sunday"}


class SourceError(RuntimeError):
    pass


def _clean(text: str) -> str:
    return re.sub(r"[ \t\xa0]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()


def _soup(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "lxml")
    for node in soup.select("script, style, nav, footer, header, noscript"):
        node.decompose()
    return soup


def _item_from_html(source: str, url: str, html: str, anchor_title: str = "") -> dict | None:
    soup = _soup(html)
    main = soup.select_one("main, article, .article, .content, #content") or soup.body or soup
    for node in main.select(".view-count, .read-count, [data-view-count]"):
        node.decompose()
    text = _clean(main.get_text("\n", strip=True))[:20000]
    text = re.sub(r"(?:浏览次数|浏览人数|阅读量|点击次数)\s*[:：]?\s*\d+", "", text)
    if len(text) < 35:
        return None
    heading = main.find(["h1", "h2", "h3", "h4"])
    title = _clean(heading.get_text(" ", strip=True)) if heading else anchor_title
    title = title or (_clean(soup.title.get_text(" ", strip=True)) if soup.title else "")
    if not title or not (NOTICE_LINK.search(title) or NOTICE_LINK.search(url) or NOTICE_LINK.search(text[:200])):
        return None
    published = DATE_TEXT.search(text[:800])
    published_at = published.group(0).replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-").replace(".", "-") if published else None
    return {
        "source": source,
        "external_id": parse_qs(urlparse(url).query).get("xwbh", [url])[0] or hashlib.sha256(text.encode()).hexdigest(),
        "title": title[:500],
        "body": text,
        "url": url,
        "published_at": published_at,
    }


def collect_public_zdbk(session: requests.Session | None = None, list_url: str = ZDBK_PUBLIC_URL,
                        max_pages: int = 5) -> list[dict]:
    if urlparse(list_url).hostname != "zdbk.zju.edu.cn" or urlparse(list_url).scheme != "https":
        raise SourceError("公开通知地址不在本科教学管理平台域名中")
    session = session or requests.Session()
    items = []
    endpoint = list_url.split("?", 1)[0] + "?doType=query"
    for page_no in range(1, max_pages + 1):
        response = session.post(endpoint, data={
            "queryModel.showCount": 40, "queryModel.currentPage": page_no,
            "queryModel.sortName": "sfzd desc,fbsj", "queryModel.sortOrder": "desc",
        }, timeout=25)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            raise SourceError("教务公开通知接口结构已变化，需要校准")
        for row in data["items"]:
            identity, title = str(row.get("xwbh") or ""), str(row.get("xwbt") or "")
            if not identity or not title:
                raise SourceError("公开通知缺少编号或标题，需要校准")
            url = "https://zdbk.zju.edu.cn/jwglxt/xtgl/xwck_ckLoginNews.html?" + urlencode({"xwbh": identity})
            soup = _soup(str(row.get("fbnr") or ""))
            body = _clean(soup.get_text("\n", strip=True))
            attachments = [urljoin(url, a["href"]) for a in soup.find_all("a", href=True)
                           if urlparse(urljoin(url, a["href"])).scheme in {"http", "https"}]
            if attachments:
                body += "\n附件或原文链接：\n" + "\n".join(attachments[:20])
            needs_review = False
            if not body:
                # Some grid entries redirect to an external article and omit fbnr.
                try:
                    detail = session.get(url, timeout=20, allow_redirects=False)
                    detail.raise_for_status()
                    if detail.status_code in {301, 302, 303, 307, 308}:
                        _, body = fetch_notice_link(urljoin(url, detail.headers.get("Location", "")))
                    else:
                        parsed = _item_from_html("zdbk_public", url, detail.text, title)
                        if not parsed:
                            raise SourceError("通知详情无可确认的文字正文")
                        body = parsed["body"]
                except Exception:
                    needs_review = True
                    body = "正文未能读取，可能为外部链接、图片或受限页面；请打开原通知补充原文。"
            items.append({"source": "zdbk_public", "external_id": identity,
                          "title": title, "body": body, "url": url,
                          "published_at": row.get("fbsj"), "needs_review": needs_review})
        if not data["items"] or page_no >= int(data.get("totalPage") or 1):
            break
    return items


def parse_timetable_html(html: str) -> dict[str, list[dict]]:
    """Read a rendered weekday table, without replacing the user's manual course data."""
    soup = _soup(html)
    result: dict[str, list[dict]] = {day: [] for day in WEEKDAYS.values()}
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        # Expand row/column spans before assigning courses to weekdays.
        grid, spans = [], {}
        for row_no, row in enumerate(rows):
            expanded, col = {}, 0
            for cell in row.find_all(["th", "td"], recursive=False):
                while (row_no, col) in spans:
                    expanded[col] = spans[(row_no, col)]
                    col += 1
                width, height = int(cell.get("colspan", 1)), int(cell.get("rowspan", 1))
                for dx in range(width):
                    expanded[col + dx] = cell
                    for dy in range(1, height):
                        spans[(row_no + dy, col + dx)] = cell
                col += width
            for (r, c), cell in spans.items():
                if r == row_no:
                    expanded.setdefault(c, cell)
            grid.append(expanded)
        columns, header_index = {}, 0
        for index, cells in enumerate(grid):
            columns = {i: WEEKDAYS[name] for i, cell in cells.items()
                       if (name := _clean(cell.get_text(" ", strip=True))) in WEEKDAYS}
            if len(columns) >= 3:
                header_index = index
                break
        if len(columns) < 3:
            continue
        seen_cells = set()
        for cells in grid[header_index + 1:]:
            for index, weekday in columns.items():
                if index not in cells or (weekday, id(cells[index])) in seen_cells:
                    continue
                raw = _clean(cells[index].get_text(" ", strip=True))
                if not raw or raw in {"无", "--", "-"}:
                    continue
                seen_cells.add((weekday, id(cells[index])))
                time = " ".join(dict.fromkeys(_clean(cells[c].get_text(" ", strip=True))
                                               for c in sorted(cells) if c < min(columns)))
                lessons = cells[index].select(".timetable_con") or [cells[index]]
                for lesson in lessons:
                    text = _clean(lesson.get_text(" ", strip=True))
                    course = {"name": text[:160], "time": time[:60], "location": "", "teacher": "",
                              "source": "zdbk", "weeks": parse_course_weeks(text)}
                    if course not in result[weekday]:
                        result[weekday].append(course)
    return result


class CampusBrowser:
    def __init__(self, runtime_dir: Path, headless: bool = True):
        self.profile_dir = runtime_dir / "campus_browser_profile"
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.driver = None
        self._lock = None
        self._lock_held = False

    def __enter__(self):
        try:
            self._lock = runtime_lock(self.profile_dir.parent / "locks" / "campus_browser.lock")
            self._lock.__enter__()
            self._lock_held = True
            from selenium import webdriver
            options = webdriver.ChromeOptions()
            options.add_argument(f"--user-data-dir={self.profile_dir.resolve()}")
            options.add_argument("--disable-notifications")
            options.add_argument("--window-size=1280,900")
            if self.headless:
                options.add_argument("--headless=new")
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(35)
            return self
        except Exception as exc:
            if self.driver:
                self.driver.quit()
            if self._lock_held:
                self._lock.__exit__(None, None, None)
            raise SourceError(f"无法启动专用 Chrome 浏览器：{type(exc).__name__}") from exc

    def __exit__(self, *_):
        try:
            if self.driver:
                self.driver.quit()
        finally:
            if self._lock_held:
                self._lock.__exit__(None, None, None)
                self._lock_held = False

    def login_interactive(self):
        self.driver.get(LMS_URL)
        lms_tab = self.driver.current_window_handle
        self.driver.execute_script("window.open(arguments[0], '_blank')", ZDBK_URL)
        zdbk_tab = self.driver.window_handles[-1]
        input("请完成两个平台登录；学在浙大登录后还需点击进入平台，教务可打开本学期课表。完成后回到此窗口按 Enter 保存会话...")
        result = {}
        for source, tab, hosts in (("lms", lms_tab, LMS_HOSTS),
                                   ("zdbk_private", zdbk_tab, {"zdbk.zju.edu.cn"})):
            try:
                self.driver.switch_to.window(tab)
                url = self.driver.current_url
                if urlparse(url).hostname in hosts and not self._login_required(url, self.driver.page_source):
                    result[source] = url
                    if source == "zdbk_private":
                        for frame in BeautifulSoup(self.driver.page_source, "lxml").find_all("iframe", src=True):
                            if "kbcx" in frame["src"].lower():
                                result["timetable_url"] = urljoin(url, frame["src"])
                                break
            except Exception:
                continue
        return result

    def _visit(self, url: str) -> tuple[str, str]:
        import time
        self.driver.get(url)
        time.sleep(2)
        return self.driver.current_url, self.driver.page_source

    @staticmethod
    def _login_required(url: str, html: str) -> bool:
        host = urlparse(url).hostname or ""
        if "cas.zju.edu.cn" in host or "login_slogin" in url:
            return True
        soup = BeautifulSoup(html, "lxml")
        password = soup.select_one("input[type=password]")
        text = soup.get_text(" ", strip=True)
        if host in LMS_HOSTS and ("统一身份认证登录" in text or "/login" in urlparse(url).path) and "退出" not in text:
            return True
        return bool(password and ("登录" in text or "身份认证" in text))

    @staticmethod
    def _links(base: str, html: str, site: str) -> list[tuple[str, str]]:
        soup = BeautifulSoup(html, "lxml")
        links = []
        allowed_hosts = LMS_HOSTS if site in LMS_HOSTS else {site}
        for anchor in soup.select("a[href], iframe[src]"):
            url = urljoin(base, anchor.get("href") or anchor.get("src"))
            if urlparse(url).scheme not in {"http", "https"} or urlparse(url).hostname not in allowed_hosts or url == base:
                continue
            if re.search(r"delete|remove|logout|submit|save", url, re.I):
                continue
            label = _clean(anchor.get_text(" ", strip=True))
            if NOTICE_LINK.search(label + " " + url) or COURSE_LINK.search(label + " " + url):
                links.append((url, label))
        return links

    def collect(self, source: str, root_url: str, max_pages: int = 35,
                extra_urls: list[str] | None = None) -> tuple[list[dict], dict[str, list[dict]]]:
        site = urlparse(root_url).hostname
        if site not in LMS_HOSTS | {"zdbk.zju.edu.cn"}:
            raise SourceError("校内页面地址不在允许的域名中")
        queue = deque([(root_url, "", 0)])
        for url in extra_urls or []:
            allowed_hosts = LMS_HOSTS if site in LMS_HOSTS else {site}
            if urlparse(url).scheme != "https" or urlparse(url).hostname not in allowed_hosts:
                raise SourceError("补充页面入口必须是相同校内域名的 HTTPS 地址")
            queue.append((url, "课表" if source == "zdbk_private" else "作业通知", 1))
        visited = set()
        items = {}
        timetable = {day: [] for day in WEEKDAYS.values()}
        authenticated = False
        failures = 0
        while queue and len(visited) < max_pages:
            url, anchor_title, depth = queue.popleft()
            if url in visited:
                continue
            visited.add(url)
            try:
                final_url, html = self._visit(url)
            except Exception:
                failures += 1
                continue
            if self._login_required(final_url, html):
                if not authenticated:
                    raise SourceError("登录会话失效，请运行校内登录向导")
                raise SourceError("部分校内页面要求重新登录，本次检查未完成")
            authenticated = True
            if source == "zdbk_private":
                parsed = parse_timetable_html(html)
                for day, courses in parsed.items():
                    for course in courses:
                        if course not in timetable[day]:
                            timetable[day].append(course)
            if depth and (NOTICE_LINK.search(url) or NOTICE_LINK.search(anchor_title)):
                item = _item_from_html(source, final_url, html, anchor_title)
                if item:
                    items[item["external_id"]] = item
            if depth < 2:
                for link in self._links(final_url, html, site):
                    if link[0] not in visited:
                        queue.append((*link, depth + 1))
        if not authenticated:
            raise SourceError("无法确认校内登录状态")
        if failures or queue:
            raise SourceError("部分课程页面未完成检查，请核对入口或网络状态")
        if not items and not any(timetable.values()):
            raise SourceError("登录成功，但未发现可解析的课程或通知入口；需要校准页面")
        return list(items.values()), timetable
