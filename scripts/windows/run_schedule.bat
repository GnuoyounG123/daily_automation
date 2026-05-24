@echo off
chcp 936 >nul
title Schedule Manager

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
echo    Schedule & Task Manager
echo =========================================
echo.
echo Python Version:
%PYTHON_CMD% --version
echo.

:: Run schedule manager
echo [INFO] Generating daily plan...
%PYTHON_CMD% schedule_manager.py

echo.
echo =========================================
echo    Done
echo =========================================
pause
