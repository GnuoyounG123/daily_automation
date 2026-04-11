#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Automation 发布包打包脚本
将客户安装必要文件打包到 release/ 目录
"""

import os
import sys
import shutil
import json
from pathlib import Path

def create_release_package():
    """创建发布包"""
    # 基础路径
    base_dir = Path(__file__).parent
    release_dir = base_dir / "release"
    dist_dir = base_dir / "dist"

    print("📦 开始打包 Daily Automation 发布包")
    print(f"源目录: {base_dir}")
    print(f"发布目录: {release_dir}")
    print()

    # 清理旧目录
    if release_dir.exists():
        print("🧹 清理旧发布目录...")
        shutil.rmtree(release_dir)

    # 创建目录结构
    print("📁 创建目录结构...")
    release_dir.mkdir()
    (release_dir / "data").mkdir()
    (release_dir / "logs").mkdir()

    # 复制必要文件
    print("📋 复制文件...")

    # 1. 主程序
    exe_source = dist_dir / "DailyAutomation.exe"
    if not exe_source.exists():
        print(f"❌ 错误: 找不到主程序 {exe_source}")
        return False
    shutil.copy2(exe_source, release_dir / "DailyAutomation.exe")
    print(f"  ✓ 复制主程序: DailyAutomation.exe")

    # 2. 配置文件
    config_files = [
        "config.json",
        "schedule.json",
        "weekly_tasks.json"
    ]

    for config_file in config_files:
        source = base_dir / config_file
        if source.exists():
            shutil.copy2(source, release_dir / config_file)
            print(f"  ✓ 复制配置文件: {config_file}")
        else:
            print(f"  ⚠️  配置文件不存在: {config_file}")

    # 3. 创建桌面快捷方式脚本
    create_shortcut_script(release_dir)

    # 4. 创建安装说明
    create_readme(release_dir)

    # 5. 创建一键安装批处理
    create_installer_bat(release_dir)

    # 统计文件大小
    total_size = 0
    for file_path in release_dir.rglob("*"):
        if file_path.is_file():
            total_size += file_path.stat().st_size

    print()
    print("✅ 打包完成!")
    print(f"📁 发布目录: {release_dir}")
    print(f"📊 总大小: {total_size / 1024 / 1024:.2f} MB")
    print()
    print("包含文件:")
    for item in release_dir.iterdir():
        if item.is_file():
            size = item.stat().st_size
            print(f"  {item.name} ({size / 1024:.1f} KB)")
        else:
            print(f"  {item.name}/ (目录)")

    return True

def create_shortcut_script(release_dir):
    """创建桌面快捷方式脚本"""
    # PowerShell 脚本
    ps_script = """# Daily Automation 桌面快捷方式创建脚本
# 用法: 右键以管理员身份运行此脚本

param(
    [switch]$Create = $true
)

$ErrorActionPreference = "Stop"

function Create-DesktopShortcut {
    $exePath = Join-Path $PSScriptRoot "DailyAutomation.exe"
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktopPath "每日学术助手.lnk"

    if (Test-Path $shortcutPath) {
        Write-Host "📌 桌面快捷方式已存在，跳过创建" -ForegroundColor Yellow
        return
    }

    # 创建快捷方式
    $WScriptShell = New-Object -ComObject WScript.Shell
    $shortcut = $WScriptShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $exePath
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.Description = "每日学术自动化助手 - 自动获取最新研究动态"
    $shortcut.IconLocation = $exePath  # 使用exe自身图标
    $shortcut.Save()

    Write-Host "✅ 桌面快捷方式创建成功: $shortcutPath" -ForegroundColor Green
}

function Remove-DesktopShortcut {
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktopPath "每日学术助手.lnk"

    if (Test-Path $shortcutPath) {
        Remove-Item $shortcutPath -Force
        Write-Host "🗑️  已删除桌面快捷方式" -ForegroundColor Green
    } else {
        Write-Host "📌 未找到桌面快捷方式" -ForegroundColor Yellow
    }
}

# 主逻辑
Write-Host "📚 Daily Automation 快捷方式管理" -ForegroundColor Cyan
Write-Host "========================================"

if ($Create) {
    Write-Host "正在创建桌面快捷方式..." -ForegroundColor Yellow
    Create-DesktopShortcut
} else {
    Write-Host "正在删除桌面快捷方式..." -ForegroundColor Yellow
    Remove-DesktopShortcut
}

Write-Host ""
Write-Host "💡 提示:" -ForegroundColor Cyan
Write-Host "1. 如需手动创建快捷方式，右键 DailyAutomation.exe → 发送到 → 桌面快捷方式"
Write-Host "2. 如需卸载，可再次运行此脚本并添加 -Create:$false 参数"
Write-Host ""
Pause
"""

    ps_path = release_dir / "create_desktop_shortcut.ps1"
    with open(ps_path, "w", encoding="utf-8") as f:
        f.write(ps_script)

    # 批处理文件（兼容性更好）
    bat_script = """@echo off
chcp 65001 >nul
title Daily Automation 桌面快捷方式创建工具

echo.
echo  ╔════════════════════════════════════════════════════════════════╗
echo  ║        Daily Automation 快捷方式管理                           ║
echo  ╠════════════════════════════════════════════════════════════════╣
echo  ║  1. 创建桌面快捷方式 (推荐)                                    ║
echo  ║  2. 删除桌面快捷方式                                           ║
echo  ║  3. 退出                                                       ║
echo  ╚════════════════════════════════════════════════════════════════╝
echo.

set /p choice="请选择 [1-3]: "

if "%choice%"=="1" goto create_shortcut
if "%choice%"=="2" goto remove_shortcut
if "%choice%"=="3" goto end

echo 无效选择
pause
exit /b 1

:create_shortcut
echo.
echo  正在创建桌面快捷方式...
echo.

REM 检查快捷方式是否已存在
set "desktop=%USERPROFILE%\Desktop"
set "shortcut=%desktop%\每日学术助手.lnk"

if exist "%shortcut%" (
    echo  📌 桌面快捷方式已存在，跳过创建
    pause
    exit /b 0
)

REM 使用 PowerShell 创建快捷方式（最可靠的方法）
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%shortcut%'); $Shortcut.TargetPath = '%~dp0DailyAutomation.exe'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.Description = '每日学术自动化助手'; $Shortcut.Save()"

if exist "%shortcut%" (
    echo  ✅ 桌面快捷方式创建成功！
    echo  📍 位置: %shortcut%
) else (
    echo  ❌ 创建失败，请尝试手动创建：
    echo      1. 右键 DailyAutomation.exe
    echo      2. 选择"发送到"
    echo      3. 选择"桌面快捷方式"
)

goto end

:remove_shortcut
echo.
echo  正在删除桌面快捷方式...
echo.

set "desktop=%USERPROFILE%\Desktop"
set "shortcut=%desktop%\每日学术助手.lnk"

if exist "%shortcut%" (
    del "%shortcut%"
    echo  ✅ 桌面快捷方式已删除
) else (
    echo  📌 未找到桌面快捷方式
)

goto end

:end
echo.
echo  操作完成，按任意键退出...
pause >nul
"""

    bat_path = release_dir / "添加快捷方式.bat"
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_script)

    print("  ✓ 创建快捷方式管理脚本")

def create_readme(release_dir):
    """创建安装说明文档"""
    readme_content = """# 📚 每日学术自动化系统 - 安装使用指南

## 🚀 快速安装

### 方法一：一键安装（推荐）
1. **解压**本文件夹到任意位置（如：`C:\DailyAutomation\`）
2. 运行 `添加快捷方式.bat`
3. 选择 **1. 创建桌面快捷方式**
4. 完成后，双击桌面上的 **每日学术助手** 图标启动程序

### 方法二：手动安装
1. 将 `DailyAutomation.exe` 复制到您喜欢的位置
2. 右键 `DailyAutomation.exe` → **发送到** → **桌面快捷方式**
3. 重命名为 **每日学术助手**（可选）

## 🎮 首次使用

### 1. 安全提示
首次运行时，Windows Defender可能会显示安全警告：
- 点击 **更多信息**
- 点击 **仍要运行**
- （可选）勾选 **始终信任此发布者**

### 2. 初始配置
程序启动后，请按以下步骤配置：

| 配置项 | 操作 | 说明 |
|--------|------|------|
| 📧 邮箱设置 | 更新授权码 | 必须使用QQ邮箱授权码（不是密码） |
| 🔍 关键词 | 添加研究领域 | 如：人工智能、公共治理、大数据 |
| ⏰ 提醒时间 | 保持默认或调整 | 早报09:00，晚间复盘22:00 |

### 3. 测试运行
点击 **立即运行一次** 按钮，测试：
- ✅ 学术信息爬取
- ✅ 邮件发送功能
- ✅ 报告生成

## ⚙️ 配置文件说明

| 文件 | 用途 | 是否必须 |
|------|------|----------|
| `config.json` | 主配置文件 | ✅ 是 |
| `schedule.json` | 日程安排 | ✅ 是 |
| `weekly_tasks.json` | 周任务模板 | ⚠️ 可选 |

## 📧 邮箱配置（重要！）

### 获取QQ邮箱授权码
1. 登录QQ邮箱网页版
2. 点击 **设置** → **账户**
3. 找到 **POP3/IMAP/SMTP服务**
4. 开启 **SMTP服务**
5. 获取 **16位授权码**（记下来）

### 在程序中配置
1. 打开程序 → 配置中心 → 邮件设置
2. 填写以下信息：
   - SMTP服务器：`smtp.qq.com`
   - 端口：`587`
   - 发件邮箱：您的QQ邮箱
   - 授权码：刚获取的16位码
   - 收件邮箱：接收简报的邮箱

## ⏰ 定时任务设置

### 自动设置
1. 在程序界面点击 **配置定时任务**
2. 点击 **一键设置**
3. 系统会自动创建3个Windows计划任务：
   - 09:00 学术早报
   - 14:00 工作提醒
   - 22:00 晚间复盘

### 手动验证
1. 按 `Win + R`，输入 `taskschd.msc`
2. 查看是否存在 `DailyAutomation_` 开头的任务

## 🔧 故障排除

### 问题1：无法启动
**症状**：程序闪退或无响应
**解决**：
1. 安装 [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
2. 右键exe → 属性 → 兼容性 → 以管理员身份运行

### 问题2：爬取失败
**症状**：返回空结果或错误
**解决**：
1. 检查网络连接
2. 查看 `logs/` 目录下的错误日志
3. 尝试使用VPN访问国际学术网站

### 问题3：邮件发送失败
**症状**：提示SMTP错误
**解决**：
1. 确认授权码正确（不是QQ密码）
2. 检查邮箱SMTP服务已开启
3. 尝试其他邮箱（163、Gmail等）

## 📊 输出文件位置

| 文件类型 | 位置 | 说明 |
|----------|------|------|
| 学术简报 | `data/academic_briefing_YYYYMMDD.md` | 每日生成的报告 |
| 运行日志 | `logs/YYYYMMDD.log` | 程序运行记录 |
| 配置文件 | 程序所在目录 | 可手动编辑修改 |

## 📞 技术支持

- **邮箱**：yg1114702713@qq.com
- **响应时间**：24小时内
- **支持内容**：安装问题、配置指导、故障排查

## ⚠️ 重要提醒

1. **授权码安全**：配置文件中的授权码为测试用，请务必更换
2. **数据备份**：定期备份 `data/` 目录的重要报告
3. **系统要求**：Windows 10/11，需要网络连接
4. **隐私声明**：所有数据仅存储本地，不上传云端

---

**祝您使用愉快！科研之路，我们相伴前行。** 🎓

> 版本：V1.0 | 更新日期：2026-04-10
"""

    readme_path = release_dir / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print("  ✓ 创建安装说明文档")

def create_installer_bat(release_dir):
    """创建一键安装批处理文件"""
    installer_content = """@echo off
chcp 65001 >nul
title Daily Automation 一键安装程序

echo.
echo  ╔════════════════════════════════════════════════════════════════╗
echo  ║        Daily Automation 一键安装程序                           ║
echo  ╠════════════════════════════════════════════════════════════════╣
echo  ║  功能：                                                        ║
echo  ║  1. 复制程序到指定目录                                         ║
echo  ║  2. 创建桌面快捷方式                                           ║
echo  ║  3. 配置基础设置                                               ║
echo  ╚════════════════════════════════════════════════════════════════╝
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  需要管理员权限运行此安装程序
    echo 请右键此文件 → 以管理员身份运行
    pause
    exit /b 1
)

:: 选择安装目录
set default_dir=C:\DailyAutomation
echo  默认安装目录: %default_dir%
set /p install_dir="请输入安装目录 (直接回车使用默认): "

if "%install_dir%"=="" set install_dir=%default_dir%

echo.
echo  📍 安装目录: %install_dir%
echo.

:: 确认安装
set /p confirm="是否继续安装? (Y/N): "
if /i "%confirm%" neq "Y" (
    echo 安装取消
    pause
    exit /b 0
)

:: 创建安装目录
echo.
echo  📁 创建目录...
if not exist "%install_dir%" mkdir "%install_dir%"
if not exist "%install_dir%\data" mkdir "%install_dir%\data"
if not exist "%install_dir%\logs" mkdir "%install_dir%\logs"

:: 复制文件
echo  📋 复制文件...
copy "%~dp0DailyAutomation.exe" "%install_dir%\" >nul
copy "%~dp0config.json" "%install_dir%\" >nul 2>&1
copy "%~dp0schedule.json" "%install_dir%\" >nul 2>&1
copy "%~dp0weekly_tasks.json" "%install_dir%\" >nul 2>&1

:: 创建桌面快捷方式
echo  🔗 创建桌面快捷方式...
set "desktop=%USERPROFILE%\Desktop"
set "shortcut=%desktop%\每日学术助手.lnk"

if exist "%shortcut%" (
    echo  📌 桌面快捷方式已存在
) else (
    powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%shortcut%'); $Shortcut.TargetPath = '%install_dir%\DailyAutomation.exe'; $Shortcut.WorkingDirectory = '%install_dir%'; $Shortcut.Description = '每日学术自动化助手'; $Shortcut.Save()"

    if exist "%shortcut%" (
        echo  ✅ 桌面快捷方式创建成功
    ) else (
        echo  ⚠️  快捷方式创建失败，请手动创建
    )
)

:: 设置文件权限（可选）
echo  🔐 设置文件权限...
icacls "%install_dir%" /grant Users:(OI)(CI)F /T >nul 2>&1

:: 完成
echo.
echo  ╔════════════════════════════════════════════════════════════════╗
echo  ║                         安装完成！                             ║
echo  ╠════════════════════════════════════════════════════════════════╣
echo  ║  程序位置: %install_dir%                                       ║
echo  ║  桌面快捷方式: 每日学术助手.lnk                                ║
echo  ║                                                               ║
echo  ║  💡 下一步操作:                                               ║
echo  ║  1. 双击桌面快捷方式启动程序                                   ║
echo  ║  2. 配置邮箱授权码（必须）                                     ║
echo  ║  3. 测试运行一次                                              ║
echo  ╚════════════════════════════════════════════════════════════════╝
echo.

echo  按任意键退出...
pause >nul
"""

    installer_path = release_dir / "一键安装.bat"
    with open(installer_path, "w", encoding="utf-8") as f:
        f.write(installer_content)

    print("  ✓ 创建一键安装程序")

if __name__ == "__main__":
    try:
        success = create_release_package()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 打包过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)