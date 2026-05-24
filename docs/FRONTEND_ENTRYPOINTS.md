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
```

Do not point "启动网页端" scripts at the Tkinter executable. The web UI and
desktop GUI are separate entry points over the same backend and runtime data.
