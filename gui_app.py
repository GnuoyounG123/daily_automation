import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from daily_automation.gui_app import *  # noqa: F401,F403,E402
from daily_automation.gui_app import main, run_task_mode  # noqa: E402


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--task":
        run_task_mode()
    else:
        main()
