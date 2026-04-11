#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置保存测试 - 增删改查配置项
测试ConfigManager的所有CRUD操作
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config_manager import ConfigManager


class ConfigSaveTest:
    """配置保存测试类"""

    def __init__(self):
        self.test_dir = None
        self.manager = None
        self.original_config = None

    def setup(self):
        """测试前准备"""
        print("="*60)
        print("配置保存测试")
        print("="*60)

        # 创建临时目录
        self.test_dir = Path(tempfile.mkdtemp(prefix="daily_automation_test_"))
        print(f"测试目录: {self.test_dir}")

        # 创建ConfigManager实例
        self.manager = ConfigManager(self.test_dir)

        # 保存原始配置（如果有）
        original_dir = Path(__file__).parent
        original_config_file = original_dir / "config.json"
        if original_config_file.exists():
            with open(original_config_file, 'r', encoding='utf-8') as f:
                self.original_config = json.load(f)

        # 重置为默认配置
        self.manager.reset_to_default()
        print("[OK] 测试环境准备完成")

    def teardown(self):
        """测试后清理"""
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
            print(f"[OK] 清理测试目录: {self.test_dir}")

    def run_all_tests(self):
        """运行所有测试"""
        tests = [
            self.test_news_source_crud,
            self.test_keywords_crud,
            self.test_reminders_crud,
            self.test_email_config_crud,
            self.test_schedule_crud,
            self.test_import_export,
        ]

        passed = 0
        failed = 0

        for test in tests:
            try:
                test()
                passed += 1
            except Exception as e:
                failed += 1
                print(f"[FAIL] {test.__name__} 失败: {e}")
                import traceback
                traceback.print_exc()

        print("\n" + "="*60)
        print(f"测试结果: 通过 {passed}/{len(tests)}，失败 {failed}")
        print("="*60)

        return failed == 0

    def test_news_source_crud(self):
        """测试新闻源CRUD"""
        print("\n[测试] 新闻源CRUD操作")

        # 先清空现有新闻源（重置后创建空配置）
        config = self.manager.get_config()
        config['news_sources'] = []
        self.manager.save_config(config)

        # 1. 添加新闻源
        result = self.manager.add_news_source(
            name="测试新闻源",
            url="https://example.com/rss",
            source_type="rss",
            enabled=True
        )
        assert result == True, "添加新闻源失败"

        sources = self.manager.get_news_sources()
        assert len(sources) == 1, f"期望1个新闻源，实际有{len(sources)}个"
        assert sources[0]['name'] == "测试新闻源"
        assert sources[0]['url'] == "https://example.com/rss"
        print("  [OK] 添加新闻源")

        # 2. 更新新闻源
        result = self.manager.update_news_source(
            index=0,
            name="更新后的新闻源",
            enabled=False
        )
        assert result == True, "更新新闻源失败"

        sources = self.manager.get_news_sources()
        assert sources[0]['name'] == "更新后的新闻源"
        assert sources[0]['enabled'] == False
        print("  [OK] 更新新闻源")

        # 3. 删除新闻源
        result = self.manager.delete_news_source(0)
        assert result == True, "删除新闻源失败"
        sources = self.manager.get_news_sources()
        assert len(sources) == 0, f"期望0个新闻源，实际有{len(sources)}个"
        print("  [OK] 删除新闻源")

        print("[PASS] 新闻源CRUD测试通过")

    def test_keywords_crud(self):
        """测试关键词CRUD"""
        print("\n[测试] 关键词CRUD操作")

        # 设置测试关键词
        en_keywords = ["artificial intelligence", "machine learning"]
        cn_keywords = ["人工智能", "机器学习"]

        self.manager.update_keywords(en_keywords, cn_keywords)

        # 验证
        keywords = self.manager.get_keywords()
        assert keywords['keywords'] == en_keywords
        assert keywords['keywords_cn'] == cn_keywords
        print("  [OK] 更新关键词")

        # 验证配置文件
        config = self.manager.get_config()
        assert 'keywords' in config
        assert 'keywords_cn' in config
        print("  [OK] 关键词已保存到配置文件")

        print("[PASS] 关键词CRUD测试通过")

    def test_reminders_crud(self):
        """测试提醒CRUD"""
        print("\n[测试] 提醒CRUD操作")

        # 先清空现有提醒（重置后创建空配置）
        config = self.manager.get_config()
        config['reminders'] = []
        self.manager.save_config(config)

        # 1. 添加提醒
        result1 = self.manager.add_reminder("09:00", "早晨学习", "开始一天的学习")
        assert result1 == True, "添加提醒1失败"
        result2 = self.manager.add_reminder("22:00", "晚间复盘", "总结一天收获")
        assert result2 == True, "添加提醒2失败"

        reminders = self.manager.get_reminders()
        assert len(reminders) == 2, f"期望2个提醒，实际有{len(reminders)}个"
        assert reminders[0]['title'] == "早晨学习"
        print("  [OK] 添加提醒")

        # 2. 更新提醒
        result = self.manager.update_reminder(
            index=0,
            time="10:00",
            description="调整后的学习时间"
        )
        assert result == True, "更新提醒失败"

        reminders = self.manager.get_reminders()
        assert reminders[0]['time'] == "10:00"
        assert reminders[0]['description'] == "调整后的学习时间"
        print("  [OK] 更新提醒")

        # 3. 删除提醒
        result = self.manager.delete_reminder(0)
        assert result == True, "删除提醒失败"
        reminders = self.manager.get_reminders()
        assert len(reminders) == 1, f"期望1个提醒，实际有{len(reminders)}个"
        print("  [OK] 删除提醒")

        print("[PASS] 提醒CRUD测试通过")

    def test_email_config_crud(self):
        """测试邮箱配置CRUD"""
        print("\n[测试] 邮箱配置CRUD操作")

        test_config = {
            'enabled': True,
            'smtp_server': 'smtp.test.com',
            'smtp_port': 587,
            'sender_email': 'test@example.com',
            'sender_password': 'test123',
            'receiver_email': 'receiver@example.com',
            'subject_prefix': '[测试]'
        }

        self.manager.update_email_config(test_config)

        # 验证
        email_config = self.manager.get_email_config()
        for key, value in test_config.items():
            assert email_config.get(key) == value, f"字段 {key} 不匹配"

        print("  [OK] 邮箱配置保存")

        # 验证配置文件
        config = self.manager.get_config()
        assert 'email' in config
        assert config['email']['enabled'] == True
        print("  [OK] 邮箱配置已保存到配置文件")

        print("[PASS] 邮箱配置CRUD测试通过")

    def test_schedule_crud(self):
        """测试课程表CRUD"""
        print("\n[测试] 课程表CRUD操作")

        # 1. 添加课程
        self.manager.add_course(
            day="Monday",
            name="测试课程",
            time="10:00-12:00",
            location="测试教室",
            teacher="测试老师",
            note="测试备注"
        )

        schedule = self.manager.get_week_schedule()
        monday_courses = schedule.get("Monday", [])
        assert len(monday_courses) == 1
        assert monday_courses[0]['name'] == "测试课程"
        print("  [OK] 添加课程")

        # 2. 删除课程
        self.manager.delete_course("Monday", 0)
        schedule = self.manager.get_week_schedule()
        monday_courses = schedule.get("Monday", [])
        assert len(monday_courses) == 0
        print("  [OK] 删除课程")

        print("[PASS] 课程表CRUD测试通过")

    def test_import_export(self):
        """测试导入导出"""
        print("\n[测试] 配置导入导出操作")

        # 1. 先清空现有配置，然后设置测试数据
        config = self.manager.get_config()
        config['news_sources'] = []
        config['reminders'] = []
        self.manager.save_config(config)

        self.manager.add_news_source("测试源", "https://test.com", "rss", True)
        self.manager.update_keywords(["test"], ["测试"])
        self.manager.add_reminder("12:00", "测试提醒", "测试描述")

        # 2. 导出配置
        export_data = self.manager.export_all_config()
        assert 'config' in export_data
        assert 'schedule' in export_data
        assert 'weekly_tasks' in export_data
        print("  [OK] 导出配置")

        # 验证导出的数据
        exported_sources = export_data['config'].get('news_sources', [])
        assert len(exported_sources) == 1, f"导出时期望1个新闻源，实际有{len(exported_sources)}个"

        # 3. 创建新的管理器并导入
        new_test_dir = Path(tempfile.mkdtemp(prefix="daily_automation_test2_"))
        new_manager = ConfigManager(new_test_dir)
        new_manager.import_all_config(export_data)

        # 验证导入的数据
        new_sources = new_manager.get_news_sources()
        assert len(new_sources) == 1, f"导入后期望1个新闻源，实际有{len(new_sources)}个"
        assert new_sources[0]['name'] == "测试源"

        new_keywords = new_manager.get_keywords()
        assert new_keywords['keywords'] == ["test"]

        print("  [OK] 导入配置")

        # 清理
        shutil.rmtree(new_test_dir, ignore_errors=True)

        print("[PASS] 配置导入导出测试通过")


def main():
    """主测试函数"""
    tester = ConfigSaveTest()

    try:
        tester.setup()
        success = tester.run_all_tests()
        tester.teardown()

        if success:
            print("\n[SUCCESS] 所有配置保存测试通过！")
            return 0
        else:
            print("\n[FAIL] 部分配置保存测试失败")
            return 1
    except Exception as e:
        print(f"\n[ERROR] 测试过程出现异常: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())