@echo off
chcp 65001 >nul
title Daily Automation Packager

set PROJECT_DIR=%~dp0..\..
cd /d "%PROJECT_DIR%"

echo =========================================
echo    Daily Automation Packager
echo =========================================
echo.
echo This builds the optional desktop executable.
echo The primary development UI remains: python launcher.py web
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found.
    pause
    exit /b 1
)

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller is not installed.
    echo Run: python -m pip install pyinstaller
    pause
    exit /b 1
)

python -m PyInstaller packaging\pyinstaller\build_exe.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

if not exist "dist\DailyAutomation.exe" (
    echo [ERROR] dist\DailyAutomation.exe was not created.
    pause
    exit /b 1
)

if not exist "artifacts\manual_exe" mkdir "artifacts\manual_exe"
copy "dist\DailyAutomation.exe" "artifacts\manual_exe\DailyAutomation.exe" >nul

echo.
echo [OK] Build complete:
echo artifacts\manual_exe\DailyAutomation.exe
echo.
pause
