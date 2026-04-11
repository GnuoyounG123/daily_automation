@echo off
chcp 65001 >nul
title Daily Automation 打包工具

echo.
echo  ╔════════════════════════════════════════════════════════════════╗
echo  ║          Daily Automation 打包脚本                             ║
echo  ╠════════════════════════════════════════════════════════════════╣
echo  ║  1. 打包桌面版 (推荐) - 双击即用的GUI程序                       ║
echo  ║  2. 打包命令行版 - 仅脚本文件                                   ║
echo  ║  3. 退出                                                       ║
echo  ╚════════════════════════════════════════════════════════════════╝
echo.

set /p choice="请选择 [1-3]: "

if "%choice%"=="1" goto gui_pack
if "%choice%"=="2" goto cli_pack
if "%choice%"=="3" goto end
echo 无效选择
pause
exit /b 1

:gui_pack
echo.
echo  ══════════════════════════════════════════════════════════════════
echo  [桌面版打包] 生成独立exe文件，用户双击即用
echo  ══════════════════════════════════════════════════════════════════
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

:: 安装PyInstaller
echo [1/4] 安装打包工具...
pip install pyinstaller -q

:: 清理旧文件
echo [2/4] 清理旧构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

:: 打包
echo [3/4] 正在打包（可能需要1-2分钟）...
pyinstaller build_exe.spec --clean --noconfirm

:: 检查结果
if not exist "dist\DailyAutomation.exe" (
    echo [错误] 打包失败
    pause
    exit /b 1
)

:: 创建发布目录
echo [4/4] 创建发布包...
if not exist "release" mkdir release
copy "dist\DailyAutomation.exe" "release\" >nul

:: 复制必要文件
if not exist "release\data" mkdir release\data
if not exist "release\logs" mkdir release\logs
echo [文件复制] 正在复制必需文件...

:: 复制文件并显示状态
echo  复制 daily_assistant.py...
copy "daily_assistant.py" "release\"
if errorlevel 1 echo  [错误] daily_assistant.py 复制失败!

echo  复制 config_manager.py...
copy "config_manager.py" "release\"
if errorlevel 1 echo  [错误] config_manager.py 复制失败!

echo  复制配置文件...
copy "config.json" "release\"
if errorlevel 1 echo  [警告] config.json 复制失败
copy "schedule.json" "release\"
if errorlevel 1 echo  [警告] schedule.json 复制失败
copy "weekly_tasks.json" "release\"
if errorlevel 1 echo  [警告] weekly_tasks.json 复制失败

:: 验证必需文件
echo [文件验证] 检查必需文件...
set "missing=0"
if not exist "release\daily_assistant.py" (
    echo  [严重] daily_assistant.py 缺失!
    set "missing=1"
)
if not exist "release\config_manager.py" (
    echo  [严重] config_manager.py 缺失!
    set "missing=1"
)
if not exist "release\config.json" (
    echo  [严重] config.json 缺失!
    set "missing=1"
)

if %missing% equ 1 (
    echo  [错误] 必需文件缺失，打包失败！
    pause
    exit /b 1
) else (
    echo  [完成] 所有必需文件检查通过
)

:: 计算文件大小
for %%A in (release\DailyAutomation.exe) do set size=%%~zA
set /a sizeMB=%size%/1048576

echo.
echo  ══════════════════════════════════════════════════════════════════
echo  打包成功！
echo  文件位置: release\DailyAutomation.exe
echo  文件大小: %sizeMB% MB
echo  ══════════════════════════════════════════════════════════════════

goto create_readme

:cli_pack
echo.
echo  ══════════════════════════════════════════════════════════════════
echo  [命令行版打包] 仅复制脚本文件
echo  ══════════════════════════════════════════════════════════════════
echo.

:: 创建发布目录
echo [1/1] 复制文件...
if not exist "release" mkdir release
if not exist "release\data" mkdir release\data
if not exist "release\logs" mkdir release\logs

copy "gui_app.py" "release\" >nul 2>&1
copy "daily_assistant.py" "release\" >nul 2>&1
copy "config_manager.py" "release\" >nul 2>&1
copy "config.json" "release\" >nul 2>&1
copy "schedule.json" "release\" >nul 2>&1
copy "weekly_tasks.json" "release\" >nul 2>&1

echo 运行方式: python gui_app.py
goto create_readme

:create_readme
:: 创建使用说明
echo # Daily Automation 使用说明 > release\README.md
echo. >> release\README.md
echo ## 快速开始 >> release\README.md
echo. >> release\README.md
if "%choice%"=="1" (
    echo 1. 双击 `DailyAutomation.exe` 启动配置界面 >> release\README.md
    echo 2. 在界面中配置新闻源、关键词、提醒等 >> release\README.md
    echo 3. 点击"立即运行一次"执行爬取任务 >> release\README.md
    echo. >> release\README.md
    echo ## 系统要求 >> release\README.md
    echo Windows 10/11，无需安装Python >> release\README.md
) else (
    echo 1. 安装Python 3.8+ >> release\README.md
    echo 2. 运行: python gui_app.py >> release\README.md
)
echo. >> release\README.md
echo ## 定时任务 >> release\README.md
echo 使用Windows任务计划程序设置定时运行 >> release\README.md

echo.
echo  发布目录: release\
echo  用户可直接复制release文件夹使用
echo.

:end
pause
