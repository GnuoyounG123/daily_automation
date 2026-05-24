import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from daily_automation.schedule_manager import *  # noqa: F401,F403
from daily_automation.schedule_manager import main  # noqa: E402


if __name__ == "__main__":
    main()
