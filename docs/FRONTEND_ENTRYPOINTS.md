# Frontend entry points

The primary frontend is now the local browser UI:

```powershell
python launcher.py web
```

or:

```powershell
python -m streamlit run app.py
```

Windows helper:

```text
scripts\windows\启动网页端.bat
```

The desktop executable/Tkinter UI is kept as an optional packaged interface:

```powershell
python gui_app.py
```

Backend task commands remain unchanged:

```powershell
python daily_assistant.py all
python daily_assistant.py crawl
python daily_assistant.py remind
python daily_assistant.py test-email
```

Campus commands:

```powershell
python campus_monitor.py doctor
python campus_monitor.py api-check
python campus_monitor.py status
python campus_monitor.py sync
python campus_monitor.py daily
python campus_monitor.py listen
```

`doctor` is a local-only readiness check and does not access the network. The web
UI shows the same checks at the top of the campus tab.

Do not point "启动网页端" scripts at the Tkinter executable. The web UI and
desktop GUI are separate entry points over the same backend and runtime data.

The Streamlit UI persists each manual run under `runtime_local/runs/` so users
can inspect whether a task succeeded, warned, failed, timed out, or never
started.
