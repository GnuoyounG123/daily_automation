"""Semester week constraints shared by daily plans and workload suggestions."""

import re
from datetime import date


def parse_course_weeks(text: str) -> list[int]:
    match = re.search(r"([\d\s,，、\-－~～至到]+)\s*[（(]?\s*周[）)]?\s*(?:[（(]?\s*([单双]))?", text)
    if not match:
        return []
    weeks = set()
    for part in re.split(r"[,，、]", match[1]):
        span = re.fullmatch(r"\s*(\d{1,2})(?:\s*[-－~～至到]\s*(\d{1,2}))?\s*", part)
        if span:
            start, end = int(span[1]), int(span[2] or span[1])
            if 1 <= start <= end <= 30:
                weeks.update(range(start, end + 1))
    if match[2]:
        parity = 1 if match[2] == "单" else 0
        weeks = {week for week in weeks if week % 2 == parity}
    return sorted(weeks)


def course_on_date(course: dict, schedule: dict, today: date) -> bool:
    weeks = course.get("weeks", [])
    if not weeks:
        return True
    try:
        start = date.fromisoformat(schedule.get("semester_start", ""))
    except (ValueError, TypeError):
        # Week-specific courses need an anchor before entering a dated daily plan.
        return False
    week = (today - start).days // 7 + 1
    return week in weeks
