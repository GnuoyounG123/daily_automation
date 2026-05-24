# Repository architecture

Daily Automation is organized around a local browser web UI, an optional
desktop app, and reusable automation modules. Keep source files, runtime state,
build output, and release artifacts separate so future changes can be reviewed
cleanly.

## Runtime entry points

| Area | File | Responsibility |
| --- | --- | --- |
| Web UI | `app.py` -> `src/daily_automation/web_app.py` | Primary local Streamlit interface, briefing-first home, task progress, and configuration |
| Launcher | `launcher.py` -> `src/daily_automation/launcher.py` | Starts the local web server or runs backend tasks from a menu/script |
| Desktop GUI | `gui_app.py` -> `src/daily_automation/gui_app.py` | Optional Tkinter/PyInstaller desktop application |
| CLI | `daily_assistant.py` -> `src/daily_automation/daily_assistant.py` | Crawl, process, report, email, and reminder workflows |
| Installer | `installer.py` -> `src/daily_automation/installer.py` | Windows installation and scheduled task setup |

## Core modules

| Module | File | Responsibility |
| --- | --- | --- |
| Paths | `src/daily_automation/app_paths.py` | Development and PyInstaller path resolution |
| Config | `src/daily_automation/config_manager.py` | JSON config CRUD and defaults |
| Secrets | `src/daily_automation/password_crypto.py` | Local Fernet password encryption |
| Fetching | `src/daily_automation/web_fetcher.py` | Multi-backend HTTP and JS-rendered fetching |
| Parsing | `src/daily_automation/html_parser.py` | HTML, RSS, and fallback parsing strategies |
| Academic APIs | `src/daily_automation/api_sources.py` | Semantic Scholar, DBLP, OpenAlex, CrossRef, and related APIs |
| Schedule | `src/daily_automation/schedule_manager.py` | Course/task schedule loading and email plan output |

## Repository zones

| Zone | Purpose | Git policy |
| --- | --- | --- |
| Root Python modules | Thin compatibility wrappers for old commands/imports | Track |
| `app.py` | Thin compatibility wrapper for Streamlit `streamlit run app.py` | Track |
| `src/daily_automation/` | Application source package | Track |
| `tests/` | Unit tests only | Track |
| `docs/` | Architecture and maintenance notes | Track |
| `runtime_local/` | Local config, secrets, generated reports, and logs | Ignore |
| `packaging/` | PyInstaller specs and build helpers | Track |
| `scripts/windows/` | Windows run and scheduled-task scripts | Track |
| `archive/legacy_scripts/` | Historical one-off repair scripts | Track or delete after review |
| `artifacts/` | PyInstaller output and release packages | Ignore |
| `release/` | Legacy residue only; remove after locked files are closed | Ignore |
| `Setup_ForGemini/` | Local export/package scratch area | Ignore |

## Import compatibility

The application now uses a standard `src/` package layout. Root files such as
`gui_app.py`, `daily_assistant.py`, and `config_manager.py` are compatibility
wrappers so existing commands and tests continue to work while new code can use
`daily_automation.*` imports.
