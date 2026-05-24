@echo off
chcp 936 >nul
title Setup Morning Task with Wake Timer

set SCRIPT_DIR=%~dp0
set ALL_BATCH=%SCRIPT_DIR%run_all_morning.bat

echo =========================================
echo    Setup Morning Automation
 echo    [Wake Timer Enabled]
echo =========================================
echo.

:: Delete old morning tasks
schtasks /delete /tn "MorningAutomation_All" /f >nul 2>&1
schtasks /delete /tn "DailyAutomation_Morning" /f >nul 2>&1
schtasks /delete /tn "DailySchedule" /f >nul 2>&1
schtasks /delete /tn "FriendCrawler" /f >nul 2>&1
echo [OK] Cleaned up old tasks

echo.
echo [INFO] Creating morning task...
echo.

:: Create task - use highest privileges for wake
schtasks /create /tn "MorningAutomation_All" /tr "\"%ALL_BATCH%\"" /sc daily /st 09:00 /ru SYSTEM /f /rl HIGHEST

if %errorlevel% == 0 (
    echo [OK] Task created successfully!
    echo.
    echo Task Name: MorningAutomation_All
    echo Run Time: 09:00 daily
    echo Script: %ALL_BATCH%
) else (
    echo [ERROR] Failed to create task
    echo Error code: %errorlevel%
)

echo.
echo =========================================
echo    NEXT STEPS (IMPORTANT!)
echo =========================================
echo.
echo 1. Opening Task Scheduler...
echo 2. Find [MorningAutomation_All] in the list
echo 3. Right-click -^> Properties
echo 4. Click [Conditions] tab
echo 5. CHECK: [x] Wake the computer to run this task
echo 6. Click OK
echo.
echo =========================================
pause
start taskschd.msc
