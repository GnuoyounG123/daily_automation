import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from daily_automation.password_crypto import *  # noqa: F401,F403
