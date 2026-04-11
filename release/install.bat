@echo off
chcp 65001 >nul
title Daily Automation 安装工具

set "APP_DIR=%~dp0"
set "APP_EXE=%APP_DIR%DailyAutomation.exe"

:menu
echo.
echo  ╔════════════════════════════════════════════════════════════════╗
echo  ║          Daily Automation 安装工具                           ║
echo  ╠════════════════════════════════════════════════════════════════╣
echo  ║  1. 安装应用（创建桌面快捷方式）                           ║
echo  ║  2. 设置定时任务（每天自动运行）                           ║
echo  ║  3. 运行应用                                               ║
echo  ║  4. 退出                                                   ║
echo  ╚════════════════════════════════════════════════════════════════╝
echo.

set /p choice="请选择 [1-4]: "

if "%choice%"=="1" goto install
if "%choice%"=="2" goto schedule
if "%choice%"=="3" goto run
if "%choice%"=="4" goto end
echo 无效选择
pause
goto menu

:install
echo.
echo  ══════════════════════════════════════════════════════════════════
echo  [安装应用] 创建桌面快捷方式

echo 正在创建桌面快捷方式...

:: 获取桌面路径
for /f "tokens=2*" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" /v Desktop') do set "DESKTOP=%%b"

:: 创建快捷方式
set "SHORTCUT=%DESKTOP%\Daily Automation.lnk"
set "ICON=%APP_EXE%,0"

:: 使用PowerShell创建快捷方式
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%APP_EXE%'; $s.WorkingDirectory = '%APP_DIR%'; $s.IconLocation = '%ICON%'; $s.Save()"

if exist "%SHORTCUT%" (
    echo [成功] 桌面快捷方式已创建
) else (
    echo [错误] 快捷方式创建失败
)

echo.
goto menu

:schedule
echo.
echo  ══════════════════════════════════════════════════════════════════
echo  [设置定时任务] 每天自动运行

echo 正在设置定时任务...

:: 运行任务计划程序设置脚本
if exist "%APP_DIR%setup_task_scheduler.bat" (
    call "%APP_DIR%setup_task_scheduler.bat"
) else (
    echo [错误] setup_task_scheduler.bat 未找到
)

echo.
goto menu

:run
echo.
echo  ══════════════════════════════════════════════════════════════════
echo  [运行应用]

echo 正在启动 Daily Automation...
start "" "%APP_EXE%"

goto menu

:end
echo 退出安装工具...
pause
