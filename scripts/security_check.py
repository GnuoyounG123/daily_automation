#!/usr/bin/env python3
"""Fail fast when private runtime files or obvious secrets enter Git."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCKED_PATH_PARTS = {
    "runtime_local",
    "customer_test_copy",
    ".secret_key",
    "config.json",
}
SECRET_PATTERNS = {
    "github_token": re.compile(r"(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,}"),
    "github_pat": re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [ROOT / line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    failures: list[str] = []
    for path in tracked_files():
        relative = path.relative_to(ROOT)
        parts = set(relative.parts)
        if parts & BLOCKED_PATH_PARTS:
            failures.append(f"blocked tracked path: {relative}")
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".exe", ".zip"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                failures.append(f"{name} pattern found in {relative}")

    if failures:
        print("Security check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Security check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
