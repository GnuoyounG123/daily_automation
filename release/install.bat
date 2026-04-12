@echo off
chcp 936 >nul
title Daily Automation Setup

set "APP_DIR=%~dp0"
set "APP_EXE=%APP_DIR%DailyAutomation.exe"

:menu
echo.
echo  ======================================================
echo          Daily Automation Setup Tool
echo  ======================================================
echo    1. Install (Create Desktop Shortcut)
echo    2. Setup Scheduled Tasks
echo    3. Run Application
echo    4. Exit
echo  ======================================================
echo.

set /p choice="Select [1-4]: "

if "%choice%"=="1" goto install
if "%choice%"=="2" goto schedule
if "%choice%"=="3" goto run
if "%choice%"=="4" goto end
echo Invalid selection
pause
goto menu

:install
echo.
echo  ------------------------------------------------------
echo  [Install] Creating desktop shortcut...

for /f "tokens=2*" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" /v Desktop') do set "DESKTOP=%%b"

set "SHORTCUT=%DESKTOP%\Daily Automation.lnk"
set "ICON=%APP_EXE%,0"

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%APP_EXE%'; $s.WorkingDirectory = '%APP_DIR%'; $s.IconLocation = '%ICON%'; $s.Save()"

if exist "%SHORTCUT%" (
    echo [OK] Desktop shortcut created
) else (
    echo [ERROR] Shortcut creation failed
)

echo.
goto menu

:schedule
echo.
echo  ------------------------------------------------------
echo  [Scheduled Tasks] Setting up daily auto-run...

if exist "%APP_DIR%setup_task_scheduler.bat" (
    call "%APP_DIR%setup_task_scheduler.bat"
) else (
    echo [ERROR] setup_task_scheduler.bat not found
)

echo.
goto menu

:run
echo.
echo  ------------------------------------------------------
echo  [Run] Starting Daily Automation...
start "" "%APP_EXE%"
goto menu

:end
echo Exiting...
pause
