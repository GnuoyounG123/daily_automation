#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包exe测试脚本
测试PyInstaller能否成功打包GUI应用
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path


def check_pyinstaller():
    """检查PyInstaller是否安装"""
    print("="*60)
    print("检查PyInstaller安装状态")
    print("="*60)

    try:
        import PyInstaller
        print(f"[OK] PyInstaller已安装，版本: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("[FAIL] PyInstaller未安装")
        print("\n安装命令: pip install pyinstaller")
        return False


def clean_build_dirs():
    """清理构建目录"""
    print("\n" + "="*60)
    print("清理构建目录")
    print("="*60)

    base_dir = Path(__file__).parent
    dirs_to_clean = ['build', 'dist']

    for dir_name in dirs_to_clean:
        dir_path = base_dir / dir_name
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                print(f"[OK] 已清理 {dir_name}/")
            except Exception as e:
                print(f"[WARN] 清理 {dir_name}/ 失败: {e}")
        else:
            print(f"[OK] {dir_name}/ 不存在，无需清理")


def run_pyinstaller():
    """执行PyInstaller打包"""
    print("\n" + "="*60)
    print("执行PyInstaller打包")
    print("="*60)

    base_dir = Path(__file__).parent
    spec_file = base_dir / "build_exe.spec"

    if not spec_file.exists():
        print(f"[FAIL] 规格文件不存在: {spec_file}")
        return False

    print(f"规格文件: {spec_file}")

    # 构建命令
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        str(spec_file),
        '--clean',
        '--noconfirm'
    ]

    print(f"执行命令: {' '.join(cmd)}")
    print("\n打包中，请稍候...")
    print("-"*60)

    try:
        result = subprocess.run(
            cmd,
            cwd=str(base_dir),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=300  # 5分钟超时
        )

        # 输出结果
        if result.stdout:
            print("标准输出:")
            print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)

        if result.stderr:
            print("\n错误输出:")
            print(result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)

        print("-"*60)

        if result.returncode == 0:
            print("[OK] PyInstaller执行成功")
            return True
        else:
            print(f"[FAIL] PyInstaller返回错误码: {result.returncode}")
            return False

    except subprocess.TimeoutExpired:
        print("[FAIL] 打包超时（超过5分钟）")
        return False
    except Exception as e:
        print(f"[FAIL] 执行异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_output():
    """验证输出文件"""
    print("\n" + "="*60)
    print("验证打包输出")
    print("="*60)

    base_dir = Path(__file__).parent
    dist_dir = base_dir / "dist"
    exe_file = dist_dir / "DailyAutomation.exe"

    # 检查dist目录
    if not dist_dir.exists():
        print("[FAIL] dist目录不存在")
        return False
    print(f"[OK] dist目录存在")

    # 检查exe文件
    if not exe_file.exists():
        print(f"[FAIL] EXE文件不存在: {exe_file}")
        # 列出dist目录内容
        print("\ndist目录内容:")
        for item in dist_dir.iterdir():
            print(f"  - {item.name}")
        return False

    # 获取文件大小
    file_size = exe_file.stat().st_size
    file_size_mb = file_size / (1024 * 1024)

    print(f"[OK] EXE文件存在: {exe_file}")
    print(f"[INFO] 文件大小: {file_size_mb:.2f} MB ({file_size:,} bytes)")

    # 检查文件大小是否合理
    if file_size_mb < 5:
        print("[WARN] 文件过小，可能缺少依赖")
    elif file_size_mb > 100:
        print("[WARN] 文件过大，可能包含不必要的依赖")
    else:
        print("[OK] 文件大小在正常范围内")

    return True


def main():
    """主函数"""
    print("\n" + "="*70)
    print(" Daily Automation - 打包exe测试 ")
    print("="*70)

    # 1. 检查PyInstaller
    if not check_pyinstaller():
        print("\n[FAIL] 测试中止：PyInstaller未安装")
        return 1

    # 2. 清理旧构建
    clean_build_dirs()

    # 3. 执行打包
    if not run_pyinstaller():
        print("\n[FAIL] 打包失败")
        return 1

    # 4. 验证输出
    if not verify_output():
        print("\n[FAIL] 输出验证失败")
        return 1

    print("\n" + "="*70)
    print(" [SUCCESS] 打包exe测试全部通过！")
    print("="*70)
    print("\n生成文件:")
    print(f"  - dist/DailyAutomation.exe")
    print("\n使用说明:")
    print("  1. 双击 DailyAutomation.exe 即可运行")
    print("  2. 首次运行会在同目录生成配置文件")
    print("  3. 无需安装Python，可移植到任何Windows电脑")

    return 0


if __name__ == "__main__":
    sys.exit(main())
