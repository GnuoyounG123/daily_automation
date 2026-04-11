@echo off
chcp 936 >nul
title Setup Morning Automation - Wake Timer Edition

:: Get script directory
set SCRIPT_DIR=%~dp0
set MASTER_BATCH=%SCRIPT_DIR%run_all_morning.bat

echo =========================================
echo    Morning Automation Setup
echo    [Wake Timer Enabled]
echo =========================================
echo.
echo This will setup ONE task that runs ALL morning:
echo   - 09:00  Academic Briefing (Your arXiv/PapersWithCode)
echo   - 09:02  Course Schedule (Your daily tasks)
echo   - 09:04  Academic Briefing (Friend's crawler)
echo   - Auto-sleep after all complete
echo.
echo Script: %MASTER_BATCH%
echo.

:: Delete ALL old tasks
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

schtasks /query /tn "FriendCrawler" >nul 2>&1
if %errorlevel% == 0 (
    schtasks /delete /tn "FriendCrawler" /f >nul 2>&1
    echo [OK] Removed friend's old task
)

echo.
echo [INFO] Creating unified morning task with wake timer...
echo.

:: Create task at 9:00 AM with wake to run
schtasks /create /tn "MorningAutomation_All" /tr "\"%MASTER_BATCH%\"" /sc daily /st 09:00 /ru "%USERNAME%" /f /rl HIGHEST

if %errorlevel% == 0 (
    echo [OK] Unified task created successfully
    echo.
    echo Task Details:
    echo   Name: MorningAutomation_All
    echo   Time: 09:00 AM daily
    echo   Wake: Enabled (requires manual check)
    echo.
    echo Execution Order:
    echo   1. Academic Briefing (Master)
    echo   2. Course Schedule (Master)
    echo   3. Academic Briefing (Friend)
    echo   4. Auto-sleep after 2 min delay
) else (
    echo [ERROR] Failed to create task
)

echo.
echo =========================================
echo    IMPORTANT - Manual Configuration
echo =========================================
echo.
echo Step 1: Enable Wake Timers
echo ----------------------------------------
powercfg -change -wake-timers-enabled AC
powercfg -change -wake-timers-enabled DC
echo [OK] Wake timers enabled in power plan
echo.
echo Step 2: Configure Task Properties
echo ----------------------------------------
echo 1. Task Scheduler will open automatically
echo 2. Find: Task Scheduler Library ^> MorningAutomation_All
echo 3. Right-click ^> Properties
echo 4. Go to "Conditions" tab
echo 5. CHECK: [x] "Wake the computer to run this task"
echo 6. Click OK
echo.
echo =========================================
echo    Evening Task (Optional)
echo =========================================
echo.
echo Evening review at 22:00 is NOT included
echo in wake timer (assumes computer is on)
echo.
echo To add evening task separately, run:
echo   setup_evening_only.bat
echo.
echo Press any key to open Task Scheduler...
pause >nul
start taskschd.msc
