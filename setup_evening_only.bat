@echo off
chcp 936 >nul
title Setup Evening Review Task

:: Get script directory
set SCRIPT_DIR=%~dp0
set ACADEMIC_BATCH=%SCRIPT_DIR%run_daily.bat

echo =========================================
echo    Evening Review Setup
echo =========================================
echo.
echo This task runs at 22:00 (10:00 PM)
echo NO wake timer - assumes computer is on
echo.

:: Delete old evening task if exist
schtasks /query /tn "DailyAutomation_Evening" >nul 2>&1
if %errorlevel% == 0 (
    echo [INFO] Removing old evening task...
    schtasks /delete /tn "DailyAutomation_Evening" /f >nul 2>&1
    echo [OK] Removed old task
)

echo.
echo [INFO] Creating evening task...
echo.

:: Create evening task at 22:00 - NO wake timer needed
schtasks /create /tn "DailyAutomation_Evening" /tr "\"%ACADEMIC_BATCH%\" remind" /sc daily /st 22:00 /ru "%USERNAME%" /f

if %errorlevel% == 0 (
    echo [OK] Evening task created successfully
    echo.
    echo Task Details:
    echo   Name: DailyAutomation_Evening
    echo   Time: 22:00 daily
    echo   Type: Evening review reminder
    echo   Wake: NOT enabled (runs only if PC is on)
) else (
    echo [ERROR] Failed to create task
)

echo.
echo =========================================
echo    Setup Complete
echo =========================================
echo.
pause
