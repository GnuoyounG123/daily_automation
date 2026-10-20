"""Campus inbox orchestration, planning output, and deduplicated email reminders."""

from __future__ import annotations

import hashlib
import html
import re
import smtplib
from datetime import date, datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests

from .campus_sources import CampusBrowser, collect_public_zdbk, LMS_URL, ZDBK_URL, ZDBK_PUBLIC_URL
from .campus_cas import (
    CampusCasClient,
    CampusCaptchaError,
    CampusCredentialError,
    CampusError,
    CampusRateLimitError,
    CampusSessionError,
    parse_lms_todos,
    parse_timetable_items,
    resolve_term,
)
from .notice_links import fetch_notice_link
from .config_manager import ConfigManager
from .notice_processing import DeepSeekSummarizer, validate_analysis
from .notice_store import NoticeStore
from .password_crypto import PasswordCrypto


SHANGHAI = ZoneInfo("Asia/Shanghai")
URL_RE = re.compile(r"https?://[^\s<>]+")


def campus_defaults() -> dict:
    return {
        "enabled": False,
        "lms_url": LMS_URL,
        "zdbk_url": ZDBK_URL,
        "public_url": ZDBK_PUBLIC_URL,
        "username": "",
        "password": "",
        "remember_password": False,
        "academic_year": "",
        "term": "",
        "grade": "",
        "college": "",
        "major": "",
        "timetable_url": "",
        "lms_extra_urls": [],
        "semester_start": "",
    }


def _safe_link(url: str) -> str:
    parsed = urlparse(url or "")
    return url if parsed.scheme in {"http", "https"} else ""


class CampusService:
    def __init__(self, runtime_dir: Path, config: dict | None = None):
        self.runtime_dir = Path(runtime_dir)
        self.manager = ConfigManager(self.runtime_dir)
        self.config = config if config is not None else self.manager.get_config()
        self.settings = {**campus_defaults(), **self.config.get("campus", {})}
        self.store = NoticeStore(self.runtime_dir)

    def ingest(self, source: str, title: str, body: str, url: str = "",
               external_id: str | None = None, published_at: str | None = None) -> tuple[int, bool]:
        if source not in {"dingtalk", "manual", "lms", "zdbk_public", "zdbk_private"}:
            raise ValueError("Unknown notice source")
        body = body.strip()
        if not body and not url:
            raise ValueError("通知内容不能为空")
        title = title.strip() or body[:80] or "未命名通知"
        if not external_id:
            # Forwarding the same message twice must not produce two tasks.
            external_id = hashlib.sha256((title + "\n" + body + "\n" + url).encode("utf-8")).hexdigest()
        if not url:
            match = URL_RE.search(body)
            url = match.group(0).rstrip(".,;，。；)") if match else ""
        return self.store.upsert_notice(source=source, external_id=external_id,
                                        title=title, body=body, url=_safe_link(url),
                                        published_at=published_at)

    def _save_items(self, items: list[dict]) -> int:
        changed = 0
        for item in items:
            fields = dict(item)
            needs_review = fields.pop("needs_review", False)
            notice_id, is_changed = self.store.upsert_notice(**fields)
            if is_changed and needs_review:
                self.store.set_analysis(notice_id, summary="原文未取到，请打开通知核对", action="", review_state="review")
            changed += int(is_changed)
        return changed

    def _credentials(self) -> tuple[str, str]:
        """Return remembered credentials, refusing non-Fernet password storage."""
        username = str(self.settings.get("username") or "").strip()
        stored = str(self.settings.get("password") or "")
        if not username or not self.settings.get("remember_password") or not stored:
            return username, ""
        if not stored.startswith("fernet:"):
            return username, ""
        key_file = self.runtime_dir / ".secret_key"
        try:
            if not key_file.exists() or len(key_file.read_bytes().strip()) != 44:
                return username, ""
        except OSError:
            return username, ""
        password = PasswordCrypto(self.runtime_dir).decrypt(stored)
        if not password or password.startswith(("fernet:", "enc:")):
            return username, ""
        return username, password

    @staticmethod
    def _error_text(exc: Exception) -> str:
        text = re.sub(r"\s+", " ", str(exc)).strip()[:200]
        if isinstance(exc, CampusError):
            return text
        return f"{type(exc).__name__}：{text}"[:220]

    @staticmethod
    def _api_status(exc: Exception) -> str:
        if isinstance(exc, CampusCredentialError):
            return "error"
        if isinstance(exc, (CampusCaptchaError, CampusRateLimitError, CampusSessionError)):
            return "warning"
        return "error"

    def _browser_profile_ready(self) -> bool:
        profile = self.runtime_dir / "campus_browser_profile"
        try:
            return profile.is_dir() and any(profile.iterdir())
        except OSError:
            return False

    def _sync_api(self, warnings: list[str]) -> dict:
        """Read timetable and todos through CAS APIs when remembered credentials exist."""
        result = {"cas": False, "timetable": False, "todos": False, "changed": 0}
        username, password = self._credentials()
        if not username or not password:
            if username and self.settings.get("remember_password"):
                warnings.append("统一身份认证密码未保存或无法解密；本次跳过接口登录，请重新保存密码")
            return result
        try:
            year, term = resolve_term(self.settings)
        except CampusError as exc:
            detail = f"接口课表配置无效：{exc}"
            self.store.set_source_state("zdbk_timetable", "error", detail)
            warnings.append(detail)
            return result
        client = CampusCasClient(username, password)
        try:
            try:
                client.login()
            except Exception as exc:
                detail = f"统一身份认证失败：{self._error_text(exc)}"
                state = self._api_status(exc)
                for source in ("lms", "zdbk_private", "zdbk_timetable"):
                    self.store.set_source_state(source, state, detail)
                warnings.append(detail)
                return result
            result["cas"] = True
            try:
                client.login_zdbk()
                rows = client.fetch_timetable(year, term)
                timetable = parse_timetable_items(rows)
                count = self._update_timetable(timetable, origin="api", year=year, term=term)
                result["timetable"] = count > 0
            except Exception as exc:
                detail = f"教务接口失败：{self._error_text(exc)}"
                self.store.set_source_state("zdbk_timetable", self._api_status(exc), detail)
                warnings.append(detail)
            try:
                client.login_lms()
                notices = parse_lms_todos(client.fetch_todos())
                result["todos"] = True
                result["changed"] += self._save_items(notices)
                self.store.set_source_state("lms", "ok", f"API 待办已读取（{len(notices)} 条）", len(notices))
            except Exception as exc:
                detail = f"学在浙大接口失败：{self._error_text(exc)}"
                self.store.set_source_state("lms", self._api_status(exc), detail)
                warnings.append(detail)
            return result
        finally:
            client.close()

    def _update_timetable(self, timetable: dict[str, list[dict]], origin: str = "browser",
                          year: str = "", term: str = "") -> int:
        count = sum(len(courses) for courses in timetable.values())
        schedule = self.manager.get_schedule()
        weekly = schedule.setdefault("week_schedule", {})
        previous = sum(1 for day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
                       for course in weekly.get(day, []) if course.get("source") == "zdbk")
        if not count:
            detail = "没有识别到课表，已保留原课表" if previous else "没有识别到课表，请检查教务页面"
            self.store.set_source_state("zdbk_timetable", "warning", detail, 0)
            return 0
        previous_term = str(schedule.get("timetable_term") or "")
        new_term = f"{year}-{term}" if year and term else ""
        term_changed = bool(new_term and previous_term and new_term != previous_term)
        if previous and count * 2 < previous and not term_changed:
            # A partial page render must not erase a good semester timetable.
            self.store.set_source_state(
                "zdbk_timetable", "warning",
                f"本次仅识别到 {count} 门（上次 {previous} 门），疑似部分读取；已保留原课表，请核对", count)
            return 0
        if self.settings.get("semester_start"):
            try:
                schedule["semester_start"] = date.fromisoformat(self.settings["semester_start"]).isoformat()
            except (TypeError, ValueError):
                pass
        for day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"):
            manual = [course for course in weekly.get(day, []) if course.get("source") != "zdbk"]
            weekly[day] = manual + timetable.get(day, [])
        schedule["timetable_origin"] = origin
        if year and term:
            schedule["timetable_term"] = f"{year}-{term}"
        if not self.manager.save_schedule(schedule):
            raise RuntimeError("课表保存失败，请检查本地目录权限")
        constrained = any(course.get("weeks") for courses in timetable.values() for course in courses)
        label = "API 课表" if origin == "api" else "课表"
        if constrained and not schedule.get("semester_start"):
            self.store.set_source_state("zdbk_timetable", "warning",
                                        f"{label}已读取；请填写本学期第一周周一日期，以确定单双周课程", count)
        else:
            self.store.set_source_state("zdbk_timetable", "ok", f"{label}已同步", count)
        return count

    def sync(self) -> dict:
        if not self.settings["enabled"]:
            return {"enabled": False, "changed": 0, "warnings": ["校内监测尚未启用"]}
        changed = 0
        warnings = []
        api = self._sync_api(warnings)
        changed += api.get("changed", 0)
        try:
            try:
                items = collect_public_zdbk(list_url=self.settings["public_url"])
            except Exception:
                with CampusBrowser(self.runtime_dir, headless=True) as browser:
                    items, _ = browser.collect("zdbk_public", self.settings["public_url"])
            changed += self._save_items(items)
            self.store.set_source_state("zdbk_public", "ok", "最近公开通知已检查（最多200条）", len(items))
        except Exception as exc:
            detail = str(exc)[:250]
            self.store.set_source_state("zdbk_public", "error", detail)
            warnings.append(f"公开通知：{detail}")

        core_api = api.get("timetable") and api.get("todos")
        extra_pages = bool(self.settings.get("lms_extra_urls") or self.settings.get("timetable_url"))
        if core_api and not self._browser_profile_ready() and not extra_pages:
            # API already covers timetable and todos; do not start Chrome just
            # to fail at a login page the user never set up.
            self.store.set_source_state(
                "lms", "warning", "API 待办已读取；未建立专用浏览器，课程公告和作业页面未检查")
            self.store.set_source_state(
                "zdbk_private", "warning", "API 课表已读取；未建立专用浏览器，个人通知页面未检查")
            warnings.append("核心数据已通过 API 读取；未建立专用浏览器，页面通知未检查")
        else:
            try:
                with CampusBrowser(self.runtime_dir, headless=True) as browser:
                    for source, url in (("lms", self.settings["lms_url"]),
                                        ("zdbk_private", self.settings["zdbk_url"])):
                        covered = api.get("todos") if source == "lms" else api.get("timetable")
                        try:
                            extras = ([self.settings["timetable_url"]] if self.settings.get("timetable_url") else []) if source == "zdbk_private" else self.settings.get("lms_extra_urls", [])
                            items, timetable = browser.collect(source, url, extra_urls=extras)
                            changed += self._save_items(items)
                            if source == "zdbk_private" and not covered:
                                self.store.set_source_state(source, "ok", "已登录并完成页面检查", len(items))
                                self._update_timetable(timetable)
                            else:
                                detail = "已登录并完成页面检查"
                                if covered:
                                    detail += "；核心数据以 API 为准"
                                self.store.set_source_state(source, "ok", detail, len(items))
                        except Exception as exc:
                            detail = str(exc)[:250]
                            state = "warning" if covered else "error"
                            suffix = "（API 数据已读取，页面检查未完成）" if covered else ""
                            self.store.set_source_state(source, state, detail + suffix)
                            if source == "zdbk_private" and not api.get("timetable"):
                                self.store.set_source_state("zdbk_timetable", "error", detail)
                            warnings.append(f"{source}：{detail}")
            except Exception as exc:
                detail = str(exc)[:250]
                for source, covered in (("lms", api.get("todos")), ("zdbk_private", api.get("timetable"))):
                    self.store.set_source_state(source, "warning" if covered else "error",
                                                f"浏览器检查未完成：{detail}")
                if not api.get("timetable"):
                    self.store.set_source_state("zdbk_timetable", "error", detail)
                warnings.append(f"校内登录页面：{detail}")
        processed = self.process_pending()
        for state in self.store.source_states():
            if state["source"] == "deepseek" and state["status"] != "ok":
                warnings.append(state["detail"])
        return {"enabled": True, "changed": changed, "processed": processed,
                "api": {"cas": api.get("cas", False), "timetable": api.get("timetable", False),
                        "todos": api.get("todos", False)},
                "warnings": warnings}

    def process_pending(self, limit: int = 30) -> int:
        today = datetime.now(SHANGHAI).date()
        pending, archived = [], []
        for row in self.store.list_notices(limit=500, review_state="pending"):
            if row["source"] == "zdbk_public":
                try:
                    published = date.fromisoformat(str(row.get("published_at") or "")[:10])
                except ValueError:
                    published = None
                if published and (today - published).days > 180:
                    archived.append(row)
                    continue
            pending.append(row)
        for row in archived:
            # Old public notices are kept for reference but cannot affect current planning.
            self.store.set_analysis(row["id"], summary="历史公开通知（超过 180 天），未自动分析",
                                    action="", review_state="ready", relevance=False,
                                    tasks=[], expected_hash=row["content_hash"])
        pending = pending[:limit]
        if not pending:
            if archived:
                self.store.set_source_state("deepseek", "ok",
                                            f"归档 {len(archived)} 条历史公开通知", 0)
            return 0
        summarizer = DeepSeekSummarizer(self.config, self.runtime_dir)
        if not summarizer.api_key:
            self.store.set_source_state("deepseek", "warning", "未配置 DeepSeek API Key；新通知待摘要")
            return 0
        profile = {key: self.settings.get(key, "") for key in ("grade", "college", "major")}
        processed = 0
        failed_labels = []
        fatal = ""
        for row in pending:
            try:
                if row["source"] in {"manual", "dingtalk"} and row["url"]:
                    remainder = URL_RE.sub("", row["body"]).strip()
                    if len(remainder) < 80:
                        try:
                            linked_title, linked_body = fetch_notice_link(row["url"])
                            row["title"] = linked_title or row["title"]
                            row["body"] = row["body"] + "\n链接原文：\n" + linked_body
                            self.store.upsert_notice(source=row["source"], external_id=row["external_id"],
                                                     title=row["title"], body=row["body"], url=row["url"],
                                                     published_at=row["published_at"])
                            row = self.store.get_notice(row["id"])
                        except Exception:
                            self.store.set_analysis(row["id"], summary="链接原文未取到，请补充原文", action="",
                                                    review_state="review")
                            continue
                result = summarizer.summarize(row, profile)
                analysis = validate_analysis(row, result, self.manager.get_schedule(),
                                             self.manager.get_weekly_tasks())
                saved = self.store.set_analysis(row["id"], **analysis, expected_hash=row["content_hash"])
                processed += int(saved)
            except requests.RequestException as exc:
                fatal = f"通知 #{row['id']} 请求失败：{type(exc).__name__}"
                break
            except Exception as exc:
                # Keep the item pending for retry; one bad notice must not block the batch.
                detail = str(exc).strip().replace("\n", " ")[:120]
                failed_labels.append(f"#{row['id']} {row['source']} {type(exc).__name__}：{detail}")
                continue
        if fatal:
            self.store.set_source_state("deepseek", "error", f"摘要失败：{fatal}")
        elif failed_labels:
            self.store.set_source_state(
                "deepseek", "warning",
                f"{len(failed_labels)} 条摘要失败，已保留待重试；最近：{failed_labels[-1]}")
        elif processed:
            detail = f"摘要已处理 {processed} 条"
            if archived:
                detail += f"；归档 {len(archived)} 条历史公开通知"
            self.store.set_source_state("deepseek", "ok", detail, processed)
        return processed

    def digest_html(self, today: date | None = None) -> str:
        today = today or datetime.now(SHANGHAI).date()
        rows = self.store.list_notices(limit=300)
        active = [row for row in self.store.list_tasks() if row["relevance"] and not row["completed_at"]]
        due = [row for row in active if row["due_at"] and row["review_state"] == "ready"]
        upcoming = [row for row in due if 0 <= (date.fromisoformat(row["due_at"][:10]) - today).days <= 7]
        overdue = [row for row in due if date.fromisoformat(row["due_at"][:10]) < today]
        planned = [row for row in active if row["planned_date"] == today.isoformat()]
        review = [row for row in rows if row["relevance"] and row["review_state"] in {"review", "pending"}]
        review += [row for row in active if row["review_state"] == "review"]
        new = [row for row in rows if row["relevance"] and row["first_seen"][:10] == today.isoformat()]
        parts = ["<section class='campus-notices'><h2>校内事项与待办</h2>"]
        for title, group in (("今天安排", planned), ("七日内截止", upcoming),
                             ("逾期待处理", overdue), ("今天发现", new), ("待核对", review)):
            parts.append(f"<h3>{title}</h3><ul>")
            if not group:
                parts.append("<li>无</li>")
            for row in group[:15]:
                label = row.get("action") or row["summary"] or row["title"]
                due_text = f" · 截止 {html.escape(row['due_at'][:16])}" if row["due_at"] else ""
                start = f" · 建议开始 {html.escape(row['suggested_date'])}" if row["suggested_date"] else ""
                href = _safe_link(row["url"])
                link = f' <a href="{html.escape(href, quote=True)}">原通知</a>' if href else ""
                parts.append(f"<li>{html.escape(label)}{due_text}{start}{link}</li>")
            parts.append("</ul>")
        failed = [state for state in self.store.source_states() if state["status"] != "ok"]
        if failed:
            parts.append("<h3>需要检查的来源</h3><ul>")
            for state in failed:
                parts.append(f"<li>{html.escape(state['source'])}：{html.escape(state['detail'])}</li>")
            parts.append("</ul>")
        parts.append("</section>")
        return "\n".join(parts)

    def _send_html(self, subject: str, content: str) -> bool:
        email = self.config.get("email", {})
        if not email.get("enabled"):
            self.store.set_source_state("campus_email", "warning", "邮件尚未启用；每日计划已保存在本地")
            return False
        password = email.get("sender_password", "")
        password = PasswordCrypto(self.runtime_dir).decrypt(password)
        if password.startswith(("fernet:", "enc:")):
            self.store.set_source_state("campus_email", "error", "邮件授权码无法解密，请重新保存邮箱配置")
            return False
        if not all([email.get("sender_email"), password, email.get("receiver_email")]):
            self.store.set_source_state("campus_email", "warning", "邮箱配置不完整，提醒未发送")
            return False
        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = email["sender_email"]
        msg["To"] = email["receiver_email"]
        msg.attach(MIMEText(content, "html", "utf-8"))
        try:
            port = int(email.get("smtp_port", 587))
            if port == 465:
                server = smtplib.SMTP_SSL(email.get("smtp_server", "smtp.qq.com"), port, timeout=25)
            else:
                server = smtplib.SMTP(email.get("smtp_server", "smtp.qq.com"), port, timeout=25)
                server.starttls()
            with server:
                server.login(email["sender_email"], password)
                server.sendmail(email["sender_email"], email["receiver_email"], msg.as_string())
            self.store.set_source_state("campus_email", "ok", "最近一封校内计划或提醒邮件已发送")
            return True
        except (OSError, ValueError, smtplib.SMTPException):
            self.store.set_source_state("campus_email", "error", "邮件发送失败，请检查邮箱配置或网络；下次运行会重试")
            return False

    def build_daily_plan(self, today: date | None = None) -> str:
        from .schedule_manager import generate_daily_plan
        today = today or datetime.now(SHANGHAI).date()
        schedule = self.manager.get_schedule()
        weekly = self.manager.get_weekly_tasks()
        daily_tasks = {day: list(tasks) for day, tasks in weekly.get("daily_tasks", {}).items()}
        weekday = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[today.weekday()]
        for task in self.store.list_tasks():
            if task["planned_date"] == today.isoformat() and task["relevance"] and not task["completed_at"]:
                daily_tasks.setdefault(weekday, []).append({
                    "content": task["action"], "note": f"截止：{task['due_at'] or '待确认'}"})
        content, _ = generate_daily_plan(schedule, daily_tasks, campus_html=self.digest_html(today), today=today)
        output_dir = self.runtime_dir / "data"
        output_dir.mkdir(exist_ok=True)
        (output_dir / f"daily_plan_{today:%Y%m%d}.html").write_text(content, encoding="utf-8")
        return content

    def send_daily_plan(self, today: date | None = None) -> bool:
        today = today or datetime.now(SHANGHAI).date()
        content = self.build_daily_plan(today)
        key = f"campus-daily:{today.isoformat()}"
        if not self.store.reserve_mail(key):
            return False
        try:
            sent = self._send_html(f"[今日计划] {today.isoformat()} 校内事项与日程", content)
        except Exception:
            self.store.release_mail(key)
            raise
        if not sent:
            self.store.release_mail(key)
        return sent

    def send_due_reminders(self, today: date | None = None) -> int:
        today = today or datetime.now(SHANGHAI).date()
        count = 0
        for row in self.store.list_tasks():
            if not row["relevance"] or not row["due_at"] or row["completed_at"] or row["review_state"] != "ready":
                continue
            days = (date.fromisoformat(row["due_at"][:10]) - today).days
            if days not in {3, 1}:
                continue
            key = f"campus-due:{row['id']}:{row['due_at']}:{days}"
            if not self.store.reserve_mail(key):
                continue
            url = _safe_link(row["url"])
            link = f'<p><a href="{html.escape(url, quote=True)}">查看原通知</a></p>' if url else ""
            content = (f"<h2>{html.escape(row['action'])}</h2>"
                       f"<p>距离截止还有 {days} 天；截止：{html.escape(row['due_at'])}</p>"
                       f"<p>{html.escape(row['summary'])}</p>{link}")
            try:
                sent = self._send_html(f"[临期提醒] {row['action'][:40]} · {days}天", content)
            except Exception:
                self.store.release_mail(key)
                raise
            if sent:
                count += 1
            else:
                self.store.release_mail(key)
        return count

    def run_daily(self) -> dict:
        from .runtime_lock import runtime_lock
        with runtime_lock(self.runtime_dir / "locks" / "campus_daily.lock"):
            result = self.sync()
            if not result["enabled"]:
                return result
            result["daily_email_sent"] = self.send_daily_plan()
            result["deadline_emails_sent"] = self.send_due_reminders()
            for state in self.store.source_states():
                if state["source"] == "campus_email" and state["status"] != "ok":
                    result["warnings"].append(state["detail"])
            return result
