@echo off
chcp 936 >nul
title Daily Automation

:: Change to project root
set PROJECT_DIR=%~dp0..\..
cd /d "%PROJECT_DIR%"

:: Set Python command
set PYTHON_CMD=python

:: Check Python
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.x
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo =========================================
echo    Daily Automation Assistant
echo =========================================
echo.
echo Python Version:
%PYTHON_CMD% --version
echo.

:: Run main program
if "%1"=="" (
    echo [INFO] Running full mode...
    %PYTHON_CMD% daily_assistant.py all
) else (
    echo [INFO] Running mode: %1
    %PYTHON_CMD% daily_assistant.py %1
)

echo.
echo =========================================
echo    Done
echo =========================================
pause
