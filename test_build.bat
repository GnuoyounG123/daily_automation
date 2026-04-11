@echo off
chcp 65001 >nul
title Daily Automation 打包测试

echo.
echo  ══════════════════════════════════════════════════════════════════
echo  [桌面版打包测试] 生成独立exe文件
echo  ══════════════════════════════════════════════════════════════════
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    exit /b 1
)

:: 安装PyInstaller
echo [1/4] 安装打包工具...
pip install pyinstaller -q
if errorlevel 1 (
    echo [错误] PyInstaller安装失败
    exit /b 1
)

:: 清理旧文件
echo [2/4] 清理旧构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "release" rmdir /s /q "release"

:: 打包
echo [3/4] 正在打包（可能需要1-2分钟）...
python -m PyInstaller build_exe.spec --clean --noconfirm
if errorlevel 1 (
    echo [错误] 打包失败
    exit /b 1
)

:: 检查结果
if not exist "dist\DailyAutomation.exe" (
    echo [错误] 未生成exe文件
    exit /b 1
)

:: 创建发布目录
echo [4/4] 创建发布包...
if not exist "release" mkdir release
copy "dist\DailyAutomation.exe" "release\" >nul

:: 复制必要文件
if not exist "release\data" mkdir release\data
if not exist "release\logs" mkdir release\logs
copy "daily_assistant.py" "release\" >nul 2>&1
copy "config_manager.py" "release\" >nul 2>&1
copy "config.json" "release\" >nul 2>&1
copy "schedule.json" "release\" >nul 2>&1
copy "weekly_tasks.json" "release\" >nul 2>&1

:: 计算文件大小
for %%A in (release\DailyAutomation.exe) do set size=%%~zA
set /a sizeMB=%size%/1048576

echo.
echo  ══════════════════════════════════════════════════════════════════
echo  打包成功！
echo  文件位置: release\DailyAutomation.exe
echo  文件大小: %sizeMB% MB
echo  ══════════════════════════════════════════════════════════════════
echo.

:: 创建使用说明
echo # Daily Automation 使用说明 > release\README.md
echo. >> release\README.md
echo ## 快速开始 >> release\README.md
echo. >> release\README.md
echo 1. 双击 `DailyAutomation.exe` 启动配置界面 >> release\README.md
echo 2. 在界面中配置新闻源、关键词、提醒等 >> release\README.md
echo 3. 点击"立即运行一次"执行爬取任务 >> release\README.md
echo. >> release\README.md
echo ## 系统要求 >> release\README.md
echo Windows 10/11，无需安装Python >> release\README.md
echo. >> release\README.md
echo ## 定时任务 >> release\README.md
echo 使用Windows任务计划程序设置定时运行 >> release\README.md

echo  发布目录: release\
echo  测试完成，请检查exe文件是否正常运行