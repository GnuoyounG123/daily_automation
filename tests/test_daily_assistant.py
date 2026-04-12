import unittest
import json
import tempfile
from pathlib import Path


class TestEmailSender(unittest.TestCase):
    def test_enabled_flag_position(self):
        config = {
            "enabled": True,
            "smtp_server": "smtp.qq.com",
            "smtp_port": 587,
            "sender_email": "test@test.com",
            "sender_password": "",
            "receiver_email": "test@test.com"
        }
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from daily_assistant import EmailSender
        sender = EmailSender(config)
        self.assertTrue(sender.enabled)

    def test_disabled_by_default(self):
        config = {
            "smtp_server": "smtp.qq.com",
            "smtp_port": 587,
            "sender_email": "",
            "sender_password": "",
            "receiver_email": ""
        }
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from daily_assistant import EmailSender
        sender = EmailSender(config)
        self.assertFalse(sender.enabled)


class TestTranslator(unittest.TestCase):
    def test_translate_en_to_cn(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from daily_assistant import Translator
        result = Translator.translate_text("artificial intelligence")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)


if __name__ == "__main__":
    unittest.main()
