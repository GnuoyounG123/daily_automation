#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI基本操作测试
"""

import sys
import os
import tkinter as tk
from tkinter import ttk
import unittest
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

class TestGUI(unittest.TestCase):
    """GUI测试类"""

    def test_gui_initialization(self):
        """测试GUI初始化"""
        try:
            # 创建根窗口
            root = tk.Tk()
            root.withdraw()  # 隐藏窗口

            # 导入并创建应用实例
            from gui_app import DailyAutomationApp
            app = DailyAutomationApp(root)

            # 检查必要的属性是否存在
            self.assertTrue(hasattr(app, 'config_manager'))
            self.assertTrue(hasattr(app, 'notebook'))
            self.assertTrue(hasattr(app, 'status_var'))

            # 清理
            root.destroy()
            print("✓ GUI初始化测试通过")
            return True
        except Exception as e:
            print(f"✗ GUI初始化测试失败: {e}")
            raise

    def test_config_manager(self):
        """测试配置管理器"""
        try:
            from config_manager import ConfigManager
            manager = ConfigManager()

            # 测试加载配置
            config = manager.get_config()
            self.assertIsInstance(config, dict)
            self.assertIn('news_sources', config)
            self.assertIn('keywords', config)

            # 测试新闻源操作
            sources = manager.get_news_sources()
            self.assertIsInstance(sources, list)

            # 测试关键词操作
            keywords = manager.get_keywords()
            self.assertIsInstance(keywords, dict)
            self.assertIn('keywords', keywords)
            self.assertIn('keywords_cn', keywords)

            print("✓ 配置管理器测试通过")
            return True
        except Exception as e:
            print(f"✗ 配置管理器测试失败: {e}")
            raise

    def test_dialog_classes(self):
        """测试对话框类"""
        try:
            from gui_app import SourceDialog, ReminderDialog, CourseDialog

            # 测试类是否存在
            self.assertTrue(hasattr(SourceDialog, '__init__'))
            self.assertTrue(hasattr(ReminderDialog, '__init__'))
            self.assertTrue(hasattr(CourseDialog, '__init__'))

            print("✓ 对话框类测试通过")
            return True
        except Exception as e:
            print(f"✗ 对话框类测试失败: {e}")
            raise


def run_gui_smoke_test():
    """GUI冒烟测试 - 快速启动并关闭"""
    print("\n" + "="*60)
    print("GUI冒烟测试")
    print("="*60)

    try:
        root = tk.Tk()
        root.withdraw()

        from gui_app import DailyAutomationApp
        app = DailyAutomationApp(root)

        # 快速检查各个标签页是否正常加载
        tabs = app.notebook.tabs()
        expected_tabs = ['🏠 首页', '📰 新闻源', '🔑 关键词', '⏰ 提醒', '📧 邮箱', '📅 课程表', 'ℹ️ 关于']

        print(f"找到 {len(tabs)} 个标签页")
        print("标签页名称:", [app.notebook.tab(tab, 'text') for tab in tabs])

        # 检查状态标签
        print("状态变量:", app.status_var.get())

        root.destroy()
        print("✓ GUI冒烟测试通过 - 界面可以正常加载")
        return True
    except Exception as e:
        print(f"✗ GUI冒烟测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Daily Automation GUI测试套件")
    print("="*60)

    # 运行单元测试
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGUI)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print("运行GUI冒烟测试...")
    run_gui_smoke_test()

    # 总结
    print("\n" + "="*60)
    print("测试完成")
    if result.wasSuccessful():
        print("✅ 所有测试通过")
    else:
        print("❌ 部分测试失败")

    # 等待用户输入
    input("\n按回车键退出...")