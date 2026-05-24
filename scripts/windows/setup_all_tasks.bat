@echo off
chcp 936 >nul
title Setup All Scheduled Tasks

:: Get script directory
set SCRIPT_DIR=%~dp0
set ACADEMIC_BATCH=%SCRIPT_DIR%run_daily.bat
set SCHEDULE_BATCH=%SCRIPT_DIR%run_schedule.bat

echo =========================================
echo    Setup All Daily Automation Tasks
echo =========================================
echo.

:: Delete old tasks if exist
echo [INFO] Cleaning up old tasks...
schtasks /query /tn "DailyAutomation_Morning" >nul 2>&1
if %errorlevel% == 0 (
    schtasks /delete /tn "DailyAutomation_Morning" /f >nul 2>&1
    echo [OK] Removed old morning task
)

schtasks /query /tn "DailyAutomation_Evening" >nul 2>&1
if %errorlevel% == 0 (
    schtasks /delete /tn "DailyAutomation_Evening" /f >nul 2>&1
    echo [OK] Removed old evening task
)

schtasks /query /tn "DailySchedule" >nul 2>&1
if %errorlevel% == 0 (
    schtasks /delete /tn "DailySchedule" /f >nul 2>&1
    echo [OK] Removed old schedule task
)

echo.
echo [INFO] Creating new tasks...
echo.

:: Task 1: Academic Briefing at 9:00 AM
echo [1/3] Creating Academic Briefing task (9:00 AM)...
schtasks /create /tn "DailyAutomation_Morning" /tr "\"%ACADEMIC_BATCH%\"" /sc daily /st 09:00 /ru "%USERNAME%" /f
if %errorlevel% == 0 (
    echo [OK] Academic Briefing created
) else (
    echo [ERROR] Failed to create Academic Briefing
)

:: Task 2: Course Schedule at 9:05 AM
echo [2/3] Creating Course Schedule task (9:05 AM)...
schtasks /create /tn "DailySchedule" /tr "\"%SCHEDULE_BATCH%\"" /sc daily /st 09:05 /ru "%USERNAME%" /f
if %errorlevel% == 0 (
    echo [OK] Course Schedule created
) else (
    echo [ERROR] Failed to create Course Schedule
)

:: Task 3: Evening Review at 10:00 PM
echo [3/3] Creating Evening Review task (10:00 PM)...
schtasks /create /tn "DailyAutomation_Evening" /tr "\"%ACADEMIC_BATCH%\" remind" /sc daily /st 22:00 /ru "%USERNAME%" /f
if %errorlevel% == 0 (
    echo [OK] Evening Review created
) else (
    echo [ERROR] Failed to create Evening Review
)

echo.
echo =========================================
echo    All Tasks Created Successfully!
echo =========================================
echo.
echo Daily Schedule:
echo   09:00 - Academic Briefing
echo   09:05 - Course Schedule
echo   22:00 - Evening Review
echo.
echo To view all tasks: taskschd.msc
echo To delete a task: schtasks /delete /tn "TaskName" /f
echo.
pause
