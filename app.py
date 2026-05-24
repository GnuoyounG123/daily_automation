#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility entry for the Streamlit web UI."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from daily_automation.web_app import main  # noqa: E402


if __name__ == "__main__":
    main()
