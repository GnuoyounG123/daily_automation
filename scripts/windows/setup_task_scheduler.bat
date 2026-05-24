@echo off
chcp 936 >nul
title Setup Scheduled Tasks

:: Get script directory
set SCRIPT_DIR=%~dp0
set BATCH_PATH=%SCRIPT_DIR%run_daily.bat

echo =========================================
echo    Setup Daily Automation Tasks
echo =========================================
echo.
echo Script Path: %BATCH_PATH%
echo.

:: Delete old tasks if exist
schtasks /query /tn "DailyAutomation_Morning" >nul 2>&1
if %errorlevel% == 0 (
    echo [INFO] Removing existing morning task...
    schtasks /delete /tn "DailyAutomation_Morning" /f >nul 2>&1
)

schtasks /query /tn "DailyAutomation_Evening" >nul 2>&1
if %errorlevel% == 0 (
    echo [INFO] Removing existing evening task...
    schtasks /delete /tn "DailyAutomation_Evening" /f >nul 2>&1
)

echo.
echo [INFO] Creating scheduled tasks...
echo.

:: Create morning task (9:00 AM)
schtasks /create /tn "DailyAutomation_Morning" /tr "\"%BATCH_PATH%\"" /sc daily /st 09:00 /ru "%USERNAME%" /f

if %errorlevel% == 0 (
    echo [OK] Morning task created (9:00 AM)
) else (
    echo [ERROR] Failed to create morning task
)

:: Create evening task (10:00 PM)
schtasks /create /tn "DailyAutomation_Evening" /tr "\"%BATCH_PATH%\"" /sc daily /st 22:00 /ru "%USERNAME%" /f

if %errorlevel% == 0 (
    echo [OK] Evening task created (10:00 PM)
) else (
    echo [ERROR] Failed to create evening task
)

echo.
echo =========================================
echo    Setup Complete!
echo =========================================
echo.
echo Tasks Created:
echo   - Morning Report: 9:00 AM daily
echo   - Evening Review: 10:00 PM daily
echo.
echo To view tasks: taskschd.msc
echo To delete: schtasks /delete /tn "TaskName" /f
echo.
pause
