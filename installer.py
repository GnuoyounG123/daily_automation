import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from daily_automation.installer import *  # noqa: F401,F403
from daily_automation.installer import InstallerApp  # noqa: E402


if __name__ == "__main__":
    app = InstallerApp()
    app.run()
