"""Compatibility entry point for the campus monitor CLI."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from daily_automation.campus_cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
