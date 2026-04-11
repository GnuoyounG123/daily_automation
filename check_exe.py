#!/usr/bin/env python3
from pathlib import Path
import json

base_dir = Path(__file__).parent
dist_dir = base_dir / "dist"
exe_file = dist_dir / "DailyAutomation.exe"
build_dir = base_dir / "build"
spec_file = base_dir / "build_exe.spec"

print("="*60)
print("打包exe测试结果检查")
print("="*60)

# 检查spec文件
print(f"\n[1] 规格文件: {spec_file}")
print(f"    存在: {spec_file.exists()}")

# 检查build目录
print(f"\n[2] 构建目录: {build_dir}")
print(f"    存在: {build_dir.exists()}")
if build_dir.exists():
    items = list(build_dir.iterdir())
    print(f"    子项目数: {len(items)}")

# 检查dist目录
print(f"\n[3] 输出目录: {dist_dir}")
print(f"    存在: {dist_dir.exists()}")
if dist_dir.exists():
    items = list(dist_dir.iterdir())
    print(f"    内容:")
    for item in items:
        if item.is_file():
            size_mb = item.stat().st_size / (1024*1024)
            print(f"      - {item.name} ({size_mb:.2f} MB)")
        else:
            print(f"      - {item.name}/ (目录)")

# 检查exe文件
print(f"\n[4] 可执行文件: {exe_file}")
print(f"    存在: {exe_file.exists()}")
if exe_file.exists():
    size = exe_file.stat().st_size
    size_mb = size / (1024*1024)
    print(f"    大小: {size_mb:.2f} MB ({size:,} bytes)")

    # 评估
    if size_mb < 5:
        status = "过小 - 可能缺少依赖"
    elif size_mb > 200:
        status = "过大 - 可能包含多余依赖"
    else:
        status = "正常范围"
    print(f"    状态: {status}")

print("\n" + "="*60)
print("结论:")
if exe_file.exists() and exe_file.stat().st_size > 1024*1024:
    print("[SUCCESS] 打包exe测试通过！")
    print(f"\n可执行文件位置:")
    print(f"  {exe_file}")
else:
    print("[FAIL] 打包exe测试未通过")
print("="*60)

# 输出JSON结果
result = {
    "spec_exists": spec_file.exists(),
    "dist_exists": dist_dir.exists(),
    "exe_exists": exe_file.exists(),
    "exe_size_mb": round(exe_file.stat().st_size / (1024*1024), 2) if exe_file.exists() else 0
}
print("\nJSON结果:")
print(json.dumps(result, indent=2))
