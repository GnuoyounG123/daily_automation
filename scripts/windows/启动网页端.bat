@echo off
chcp 65001 >nul
title Daily Automation 网页端

set PROJECT_DIR=%~dp0..\..
cd /d "%PROJECT_DIR%"

echo =========================================
echo    Daily Automation - 网页端
echo =========================================
echo.
echo 正在启动本地网页端：http://localhost:8501
echo 使用期间请保持本窗口打开。
echo.

python launcher.py web

echo.
echo 网页端已停止。
pause
