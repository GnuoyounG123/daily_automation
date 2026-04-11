#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件功能测试
测试邮件配置管理和发送功能
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config_manager import ConfigManager
from daily_assistant import EmailSender, log_message


class EmailFunctionTest:
    """邮件功能测试类"""

    def __init__(self):
        self.test_dir = None
        self.manager = None

    def setup(self):
        """测试前准备"""
        print("="*60)
        print("邮件功能测试")
        print("="*60)

        # 创建临时目录
        self.test_dir = Path(tempfile.mkdtemp(prefix="email_test_"))
        print(f"测试目录: {self.test_dir}")

        # 创建ConfigManager实例
        self.manager = ConfigManager(self.test_dir)

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
            self.test_email_config_crud,
            self.test_email_sender_init,
            self.test_email_sender_disabled,
            self.test_email_sender_missing_config,
            self.test_email_markdown_to_html,
            self.test_mock_email_send,
        ]

        passed = 0
        failed = 0

        for test in tests:
            print(f"\n[测试] {test.__name__}")
            try:
                result = test()
                if result:
                    print(f"  [OK] {test.__name__} 通过")
                    passed += 1
                else:
                    print(f"  [FAIL] {test.__name__} 失败")
                    failed += 1
            except Exception as e:
                failed += 1
                print(f"  [ERROR] {test.__name__} 异常: {e}")
                import traceback
                traceback.print_exc()

        print("\n" + "="*60)
        print(f"测试结果: 通过 {passed}/{len(tests)}，失败 {failed}")
        print("="*60)

        return failed == 0

    def test_email_config_crud(self):
        """测试邮箱配置CRUD"""
        print("  测试邮箱配置增删改查...")

        test_config = {
            'enabled': True,
            'smtp_server': 'smtp.test.com',
            'smtp_port': 587,
            'sender_email': 'test@example.com',
            'sender_password': 'test123',
            'receiver_email': 'receiver@example.com',
            'subject_prefix': '[测试]'
        }

        # 1. 更新配置
        result = self.manager.update_email_config(test_config)
        assert result, "更新邮箱配置失败"
        print("  [OK] 更新邮箱配置")

        # 2. 读取配置并验证
        email_config = self.manager.get_email_config()
        assert email_config.get('enabled') == True, "enabled字段不匹配"
        assert email_config.get('smtp_server') == 'smtp.test.com', "smtp_server字段不匹配"
        assert email_config.get('smtp_port') == 587, "smtp_port字段不匹配"
        assert email_config.get('sender_email') == 'test@example.com', "sender_email字段不匹配"
        assert email_config.get('receiver_email') == 'receiver@example.com', "receiver_email字段不匹配"
        assert email_config.get('subject_prefix') == '[测试]', "subject_prefix字段不匹配"
        print("  [OK] 读取邮箱配置验证通过")

        # 3. 验证配置文件持久化
        config_file = self.test_dir / "config.json"
        assert config_file.exists(), "配置文件不存在"
        with open(config_file, 'r', encoding='utf-8') as f:
            saved_config = json.load(f)
        assert 'email' in saved_config, "配置文件中缺少email字段"
        assert saved_config['email']['smtp_server'] == 'smtp.test.com', "持久化数据不匹配"
        print("  [OK] 配置文件持久化验证通过")

        return True

    def test_email_sender_init(self):
        """测试邮件发送器初始化"""
        print("  测试EmailSender初始化...")

        config = {
            'enabled': True,
            'smtp_server': 'smtp.qq.com',
            'smtp_port': 465,
            'sender_email': 'sender@test.com',
            'sender_password': 'password123',
            'receiver_email': 'receiver@test.com',
            'subject_prefix': '[学术简报]'
        }

        sender = EmailSender(config)

        assert sender.enabled == True, "enabled属性不正确"
        assert sender.smtp_server == 'smtp.qq.com', "smtp_server属性不正确"
        assert sender.smtp_port == 465, "smtp_port属性不正确"
        assert sender.sender_email == 'sender@test.com', "sender_email属性不正确"
        assert sender.sender_password == 'password123', "sender_password属性不正确"
        assert sender.receiver_email == 'receiver@test.com', "receiver_email属性不正确"
        assert sender.subject_prefix == '[学术简报]', "subject_prefix属性不正确"

        print("  [OK] EmailSender初始化正确")
        return True

    def test_email_sender_disabled(self):
        """测试邮件发送器禁用状态"""
        print("  测试邮件发送器禁用状态...")

        config = {
            'enabled': False,
            'smtp_server': 'smtp.qq.com',
            'smtp_port': 587,
            'sender_email': 'sender@test.com',
            'sender_password': 'password123',
            'receiver_email': 'receiver@test.com',
        }

        sender = EmailSender(config)

        # 当禁用时，发送应该返回False但不报错
        result = sender.send_report("测试内容")
        assert result == False, "禁用状态下应返回False"

        print("  [OK] 禁用状态处理正确")
        return True

    def test_email_sender_missing_config(self):
        """测试邮件发送器配置不完整"""
        print("  测试邮件发送器配置不完整处理...")

        # 缺少发件人邮箱
        config1 = {
            'enabled': True,
            'sender_email': '',
            'sender_password': 'password123',
        }
        sender1 = EmailSender(config1)
        result1 = sender1.send_report("测试内容")
        assert result1 == False, "缺少发件人时应返回False"
        print("  [OK] 缺少发件人邮箱处理正确")

        # 缺少密码
        config2 = {
            'enabled': True,
            'sender_email': 'sender@test.com',
            'sender_password': '',
        }
        sender2 = EmailSender(config2)
        result2 = sender2.send_report("测试内容")
        assert result2 == False, "缺少密码时应返回False"
        print("  [OK] 缺少密码处理正确")

        return True

    def test_email_markdown_to_html(self):
        """测试Markdown转HTML功能"""
        print("  测试Markdown转HTML...")

        config = {'enabled': False}
        sender = EmailSender(config)

        markdown_content = """# 标题1
## 标题2
### 标题3

**粗体文本**
*斜体文本*

[链接文本](https://example.com)

---

普通段落文本
"""

        html = sender._convert_markdown_to_html(markdown_content)

        # 验证HTML包含预期的标签
        assert '<h1>' in html and '</h1>' in html, "H1标题转换失败"
        assert '<h2>' in html and '</h2>' in html, "H2标题转换失败"
        assert '<h3>' in html and '</h3>' in html, "H3标题转换失败"
        assert '<b>' in html and '</b>' in html, "粗体转换失败"
        assert '<i>' in html and '</i>' in html, "斜体转换失败"
        assert '<a href="https://example.com">链接文本</a>' in html, "链接转换失败"
        assert '<hr>' in html, "分隔线转换失败"
        assert '<br>' in html, "换行转换失败"
        assert '<!DOCTYPE html>' in html, "HTML文档声明缺失"
        assert '<html>' in html, "HTML标签缺失"

        print("  [OK] Markdown转HTML功能正常")
        return True

    def test_mock_email_send(self):
        """测试模拟邮件发送（Mock SMTP）"""
        print("  测试模拟邮件发送...")

        config = {
            'enabled': True,
            'smtp_server': 'smtp.qq.com',
            'smtp_port': 587,
            'sender_email': 'sender@test.com',
            'sender_password': 'password123',
            'receiver_email': 'receiver@test.com',
            'subject_prefix': '[测试]'
        }

        sender = EmailSender(config)

        # Mock SMTP服务器
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server

            # 执行发送
            result = sender.send_report("测试邮件内容")

            # 验证SMTP调用
            mock_smtp.assert_called_once_with('smtp.qq.com', 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with('sender@test.com', 'password123')
            mock_server.sendmail.assert_called_once()
            mock_server.quit.assert_called_once()

            assert result == True, "发送应该返回True"

        print("  [OK] 模拟邮件发送流程正确")

        # 测试SSL端口（465）
        with patch('smtplib.SMTP_SSL') as mock_smtp_ssl:
            mock_server = MagicMock()
            mock_smtp_ssl.return_value = mock_server

            config_ssl = config.copy()
            config_ssl['smtp_port'] = 465
            sender_ssl = EmailSender(config_ssl)

            result = sender_ssl.send_report("测试邮件内容")

            mock_smtp_ssl.assert_called_once_with('smtp.qq.com', 465)
            mock_server.login.assert_called_once()
            mock_server.quit.assert_called_once()

            assert result == True, "SSL发送应该返回True"

        print("  [OK] SSL端口发送流程正确")
        return True


def main():
    """主测试函数"""
    tester = EmailFunctionTest()

    try:
        tester.setup()
        success = tester.run_all_tests()
        tester.teardown()

        if success:
            print("\n[SUCCESS] 邮件功能测试全部通过！")
            print("\n注意：实际邮件发送测试需要真实的SMTP配置")
            print("如需测试真实发送，请在配置界面中设置邮箱信息后使用")
            return 0
        else:
            print("\n[FAIL] 部分邮件功能测试失败")
            return 1
    except Exception as e:
        print(f"\n[ERROR] 测试过程出现异常: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
