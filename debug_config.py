#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import json
import tempfile
import shutil
from pathlib import Path

# 重定向输出
output_file = r"C:\Users\lenovo\AppData\Local\Temp\debug_config_output.txt"
sys.stdout = open(output_file, 'w', encoding='utf-8')
sys.stderr = sys.stdout

sys.path.insert(0, str(Path(__file__).parent))
from config_manager import ConfigManager

# 创建临时目录
test_dir = Path(tempfile.mkdtemp(prefix="debug_test_"))
print(f"测试目录: {test_dir}")

# 创建ConfigManager实例
manager = ConfigManager(test_dir)

# 重置为默认配置
manager.reset_to_default()
print("\n=== 重置后配置 ===")
config = manager.get_config()
print(f"新闻源数量: {len(config.get('news_sources', []))}")
print(f"提醒数量: {len(config.get('reminders', []))}")

# 尝试添加新闻源
print("\n=== 添加新闻源 ===")
result = manager.add_news_source(
    name="测试新闻源",
    url="https://example.com/rss",
    source_type="rss",
    enabled=True
)
print(f"添加新闻源结果: {result}")

sources = manager.get_news_sources()
print(f"新闻源总数: {len(sources)}")
for s in sources:
    print(f"  - {s['name']}")

# 尝试添加提醒
print("\n=== 添加提醒 ===")
result1 = manager.add_reminder("09:00", "早晨学习", "开始一天的学习")
print(f"添加提醒1结果: {result1}")

result2 = manager.add_reminder("22:00", "晚间复盘", "总结一天收获")
print(f"添加提醒2结果: {result2}")

reminders = manager.get_reminders()
print(f"提醒总数: {len(reminders)}")
for r in reminders:
    print(f"  - {r['title']} ({r['time']})")

# 清理
shutil.rmtree(test_dir, ignore_errors=True)
print(f"\n清理测试目录: {test_dir}")
print(f"\n输出文件: {output_file}")
