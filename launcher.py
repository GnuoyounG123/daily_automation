import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from daily_automation.launcher import *  # noqa: F401,F403
from daily_automation.launcher import main  # noqa: E402


if __name__ == "__main__":
    main()
