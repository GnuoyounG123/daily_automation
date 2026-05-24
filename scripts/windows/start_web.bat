@echo off
chcp 65001 >nul
title Daily Automation Web UI

set PROJECT_DIR=%~dp0..\..
cd /d "%PROJECT_DIR%"

echo =========================================
echo    Daily Automation - Web UI
echo =========================================
echo.
echo Starting local web server at http://localhost:8501
echo Keep this window open while using the app.
echo.

python launcher.py web

echo.
echo Web server stopped.
pause
