@echo off
chcp 936 >nul
title Morning Automation - All Tasks

echo =========================================
echo    Morning Automation System
echo    [Master + Friend Combined]
echo =========================================
echo.
echo Start Time: %date% %time%
echo.

:: Get directories
set MASTER_DIR=%~dp0
set FRIEND_DIR=C:\Users\lenovo\AppData\Roaming\CherryStudio\Data\Agents\a6xup6rt2\friend_automation\

:: Create log
echo %date% %time% - Morning automation started >> "%MASTER_DIR%logs\morning_master.log"

echo [TASK 1/3] Academic Briefing (Master)
echo ----------------------------------------
cd /d "%MASTER_DIR%"
python "daily_assistant.py" >> "%MASTER_DIR%logs\morning_master.log" 2>&1
echo [OK] Task 1 completed
echo.

echo [TASK 2/3] Course Schedule (Master)
echo ----------------------------------------
cd /d "%MASTER_DIR%"
python "schedule_manager.py" >> "%MASTER_DIR%logs\morning_master.log" 2>&1
echo [OK] Task 2 completed
echo.

echo [TASK 3/3] Academic Briefing (Friend)
echo ----------------------------------------
cd /d "%FRIEND_DIR%"
python "friend_crawler.py" >> "%FRIEND_DIR%logs\friend_crawler.log" 2>&1
echo [OK] Task 3 completed
echo.

echo =========================================
echo    All Tasks Completed
echo    End Time: %date% %time%
echo =========================================
echo.
echo System will sleep in 2 minutes...
echo (Press any key to cancel)
timeout /t 120 /nobreak >nul

if %errorlevel% == 0 (
    echo.
    echo [INFO] Putting computer to sleep...
    rundll32.exe powrprof.dll,SetSuspendState 0,1,0
) else (
    echo.
    echo [INFO] Auto-sleep cancelled
)
