import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from daily_automation.daily_assistant import *  # noqa: F401,F403,E402
from daily_automation.daily_assistant import main, main_async  # noqa: E402


if __name__ == "__main__":
    import asyncio
    import sys

    if "--async" in sys.argv:
        asyncio.run(main_async())
    else:
        main()
