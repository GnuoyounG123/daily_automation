"""Local, deduplicated inbox for campus notices and their derived tasks."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


def _now() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class NoticeStore:
    def __init__(self, runtime_dir: Path):
        runtime_dir.mkdir(parents=True, exist_ok=True)
        self.path = runtime_dir / "campus_notices.sqlite3"
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS notices (
                    id INTEGER PRIMARY KEY,
                    source TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    url TEXT NOT NULL DEFAULT '',
                    published_at TEXT,
                    content_hash TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    action TEXT NOT NULL DEFAULT '',
                    deadline_evidence TEXT NOT NULL DEFAULT '',
                    due_at TEXT,
                    review_state TEXT NOT NULL DEFAULT 'pending',
                    relevance INTEGER NOT NULL DEFAULT 1,
                    estimated_minutes INTEGER NOT NULL DEFAULT 60,
                    suggested_date TEXT,
                    planned_date TEXT,
                    completed_at TEXT,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    UNIQUE(source, external_id)
                );
                CREATE TABLE IF NOT EXISTS notice_revisions (
                    id INTEGER PRIMARY KEY,
                    notice_id INTEGER NOT NULL REFERENCES notices(id),
                    content_hash TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    url TEXT NOT NULL,
                    captured_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS source_state (
                    source TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    checked_at TEXT NOT NULL,
                    item_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS mail_ledger (
                    mail_key TEXT PRIMARY KEY,
                    sent_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_notices_due ON notices(due_at);
                CREATE TABLE IF NOT EXISTS action_items (
                    id INTEGER PRIMARY KEY,
                    notice_id INTEGER NOT NULL REFERENCES notices(id),
                    action_key TEXT NOT NULL,
                    action TEXT NOT NULL,
                    deadline_evidence TEXT NOT NULL DEFAULT '',
                    due_at TEXT,
                    review_state TEXT NOT NULL DEFAULT 'review',
                    estimated_minutes INTEGER NOT NULL DEFAULT 60,
                    suggested_date TEXT,
                    planned_date TEXT,
                    completed_at TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(notice_id, action_key)
                );
                """
            )

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=15000")
        db.execute("PRAGMA journal_mode=WAL")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def upsert_notice(self, *, source: str, external_id: str, title: str,
                      body: str, url: str = "", published_at: str | None = None) -> tuple[int, bool]:
        title, body = title.strip()[:500], body.strip()[:20000]
        if not source or not external_id or not (title or body):
            raise ValueError("Notice requires source, identity, and content")
        digest = _hash(json.dumps([title, body, url], ensure_ascii=False))
        now = _now()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT id, content_hash FROM notices WHERE source=? AND external_id=?",
                (source, external_id),
            ).fetchone()
            if row and row["content_hash"] == digest:
                db.execute("UPDATE notices SET last_seen=? WHERE id=?", (now, row["id"]))
                return row["id"], False
            if row:
                db.execute("UPDATE action_items SET active=0 WHERE notice_id=?", (row["id"],))
                db.execute(
                    """UPDATE notices SET title=?, body=?, url=?, published_at=?, content_hash=?,
                       summary='', action='', deadline_evidence='', due_at=NULL,
                       review_state='pending', suggested_date=NULL, planned_date=NULL,
                       completed_at=NULL, last_seen=? WHERE id=?""",
                    (title, body, url, published_at, digest, now, row["id"]),
                )
                notice_id = row["id"]
            else:
                cursor = db.execute(
                    """INSERT INTO notices
                       (source, external_id, title, body, url, published_at, content_hash, first_seen, last_seen)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (source, external_id, title, body, url, published_at, digest, now, now),
                )
                notice_id = cursor.lastrowid
            db.execute(
                """INSERT INTO notice_revisions
                   (notice_id, content_hash, title, body, url, captured_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (notice_id, digest, title, body, url, now),
            )
            return notice_id, True

    def set_analysis(self, notice_id: int, *, summary: str, action: str,
                     evidence: str = "", due_at: str | None = None,
                     review_state: str = "ready", relevance: bool = True,
                     estimated_minutes: int = 60, suggested_date: str | None = None,
                     tasks: list[dict] | None = None, expected_hash: str | None = None) -> bool:
        if review_state not in {"ready", "pending", "review"}:
            raise ValueError("Invalid review state")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT content_hash FROM notices WHERE id=?", (notice_id,)).fetchone()
            if current is None or (expected_hash is not None and current["content_hash"] != expected_hash):
                return False
            db.execute(
                """UPDATE notices SET summary=?, action=?, deadline_evidence=?, due_at=?,
                   review_state=?, relevance=?, estimated_minutes=?, suggested_date=? WHERE id=?""",
                (summary[:1000], action[:500], evidence[:300], due_at, review_state,
                 int(relevance), max(15, min(int(estimated_minutes), 2400)), suggested_date, notice_id),
            )
            db.execute("UPDATE action_items SET active=0 WHERE notice_id=?", (notice_id,))
            if tasks is None:
                tasks = [{"action": action, "evidence": evidence, "due_at": due_at,
                          "review_state": review_state, "estimated_minutes": estimated_minutes,
                          "suggested_date": suggested_date}] if action else []
            labels_seen, duplicates = {}, set()
            for task in tasks:
                label = task["action"].strip()[:500]
                if not label:
                    continue
                normalized = " ".join(label.split())
                signature = (normalized, task.get("due_at"))
                if signature in duplicates:
                    continue
                duplicates.add(signature)
                occurrence = labels_seen.get(normalized, 0)
                labels_seen[normalized] = occurrence + 1
                key = _hash(normalized if not occurrence else f"{normalized}\n{occurrence}")
                db.execute(
                    """INSERT INTO action_items
                       (notice_id, action_key, action, deadline_evidence, due_at, review_state,
                        estimated_minutes, suggested_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(notice_id, action_key) DO UPDATE SET
                       action=excluded.action, deadline_evidence=excluded.deadline_evidence,
                       planned_date=CASE WHEN action_items.due_at IS excluded.due_at
                                         THEN action_items.planned_date ELSE NULL END,
                       completed_at=CASE WHEN action_items.due_at IS excluded.due_at
                                         THEN action_items.completed_at ELSE NULL END,
                       due_at=excluded.due_at, review_state=excluded.review_state,
                       estimated_minutes=excluded.estimated_minutes,
                       suggested_date=excluded.suggested_date, active=1""",
                    (notice_id, key, label, task.get("evidence", ""), task.get("due_at"),
                     task.get("review_state", "review"), task.get("estimated_minutes", 60),
                     task.get("suggested_date")),
                )
            return True

    def list_tasks(self, limit: int = 500) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                """SELECT a.*, n.source, n.title, n.summary, n.url, n.first_seen, n.relevance
                   FROM action_items a JOIN notices n ON n.id=a.notice_id
                   WHERE a.active=1 ORDER BY COALESCE(a.due_at, '9999'), a.id LIMIT ?""", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def plan_task(self, task_id: int, day: str | None):
        if day:
            datetime.strptime(day, "%Y-%m-%d")
        with self._connect() as db:
            db.execute("UPDATE action_items SET planned_date=? WHERE id=? AND active=1", (day, task_id))

    def complete_task(self, task_id: int, completed: bool = True):
        with self._connect() as db:
            db.execute("UPDATE action_items SET completed_at=? WHERE id=?", (_now() if completed else None, task_id))

    def review_task(self, task_id: int, action: str, due_at: str | None):
        if not action.strip():
            raise ValueError("事项不能为空")
        if due_at:
            datetime.fromisoformat(due_at)
        with self._connect() as db:
            db.execute(
                """UPDATE action_items SET action=?,
                   planned_date=CASE WHEN due_at IS ? THEN planned_date ELSE NULL END,
                   completed_at=CASE WHEN due_at IS ? THEN completed_at ELSE NULL END,
                   due_at=?, review_state='ready',
                   deadline_evidence='用户人工确认', suggested_date=NULL WHERE id=?""",
                (action.strip()[:500], due_at, due_at, due_at, task_id),
            )

    def set_relevance(self, notice_id: int, relevant: bool):
        with self._connect() as db:
            db.execute("UPDATE notices SET relevance=? WHERE id=?", (int(relevant), notice_id))

    def get_notice(self, notice_id: int) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM notices WHERE id=?", (notice_id,)).fetchone()
            return dict(row) if row else None

    def list_notices(self, limit: int = 200, review_state: str | None = None) -> list[dict]:
        with self._connect() as db:
            if review_state:
                rows = db.execute(
                    """SELECT * FROM notices WHERE review_state=?
                       ORDER BY CASE source WHEN 'lms' THEN 0 WHEN 'zdbk_private' THEN 1
                       WHEN 'dingtalk' THEN 2 WHEN 'manual' THEN 2 ELSE 3 END, first_seen, id LIMIT ?""",
                    (review_state, limit),
                ).fetchall()
            else:
                rows = db.execute("SELECT * FROM notices ORDER BY last_seen DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]

    def revisions(self, notice_id: int) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM notice_revisions WHERE notice_id=? ORDER BY id DESC", (notice_id,)
            ).fetchall()
            return [dict(row) for row in rows]

    def plan(self, notice_id: int, date: str | None):
        if date:
            datetime.strptime(date, "%Y-%m-%d")
        with self._connect() as db:
            db.execute("UPDATE notices SET planned_date=? WHERE id=?", (date, notice_id))

    def complete(self, notice_id: int, completed: bool = True):
        with self._connect() as db:
            db.execute(
                "UPDATE notices SET completed_at=? WHERE id=?",
                (_now() if completed else None, notice_id),
            )

    def set_source_state(self, source: str, status: str, detail: str, item_count: int = 0):
        with self._connect() as db:
            db.execute(
                """INSERT INTO source_state(source, status, detail, checked_at, item_count)
                   VALUES (?, ?, ?, ?, ?) ON CONFLICT(source) DO UPDATE SET
                   status=excluded.status, detail=excluded.detail,
                   checked_at=excluded.checked_at, item_count=excluded.item_count""",
                (source, status, detail[:500], _now(), item_count),
            )

    def source_states(self) -> list[dict]:
        with self._connect() as db:
            states = [dict(row) for row in db.execute("SELECT * FROM source_state ORDER BY source")]
        for state in states:
            if state["source"] == "dingtalk" and datetime.now(ZoneInfo("Asia/Shanghai")) - datetime.fromisoformat(state["checked_at"]) > timedelta(seconds=90):
                state.update(status="warning", detail="监听心跳已过期；未收到确认回复的消息请补录")
        return states

    def reserve_mail(self, key: str) -> bool:
        with self._connect() as db:
            try:
                db.execute("INSERT INTO mail_ledger(mail_key, sent_at) VALUES (?, ?)", (key, _now()))
                return True
            except sqlite3.IntegrityError:
                return False

    def release_mail(self, key: str):
        with self._connect() as db:
            db.execute("DELETE FROM mail_ledger WHERE mail_key=?", (key,))
