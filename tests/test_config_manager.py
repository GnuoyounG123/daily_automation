import unittest
import json
import tempfile
from pathlib import Path
from config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cm = ConfigManager(Path(self.tmpdir))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_get_config_empty(self):
        config = self.cm.get_config()
        self.assertIsInstance(config, dict)

    def test_save_and_load_config(self):
        test_config = {"news_sources": [], "keywords": ["ai"]}
        self.cm.save_config(test_config)
        loaded = self.cm.get_config()
        self.assertEqual(loaded["keywords"], ["ai"])

    def test_add_news_source(self):
        result = self.cm.add_news_source("Test", "http://test.com", "rss")
        self.assertTrue(result)
        sources = self.cm.get_news_sources()
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["name"], "Test")

    def test_add_duplicate_source(self):
        self.cm.add_news_source("Test", "http://test.com", "rss")
        result = self.cm.add_news_source("Test", "http://test.com", "rss")
        self.assertFalse(result)

    def test_delete_news_source(self):
        self.cm.add_news_source("Test", "http://test.com", "rss")
        result = self.cm.delete_news_source(0)
        self.assertTrue(result)
        self.assertEqual(len(self.cm.get_news_sources()), 0)

    def test_get_email_config_default(self):
        email = self.cm.get_email_config()
        self.assertIn("smtp_server", email)
        self.assertIn("sender_password", email)

    def test_update_email_config(self):
        new_email = {"enabled": True, "smtp_server": "smtp.test.com"}
        self.cm.update_email_config(new_email)
        email = self.cm.get_email_config()
        self.assertEqual(email["smtp_server"], "smtp.test.com")

    def test_get_keywords_default(self):
        kw = self.cm.get_keywords()
        self.assertIn("keywords", kw)
        self.assertIn("keywords_cn", kw)

    def test_update_keywords(self):
        self.cm.update_keywords(["ai", "ml"], ["人工智能"])
        kw = self.cm.get_keywords()
        self.assertEqual(kw["keywords"], ["ai", "ml"])

    def test_add_reminder(self):
        self.cm.add_reminder("09:00", "Test", "Desc")
        reminders = self.cm.get_reminders()
        self.assertEqual(len(reminders), 1)

    def test_delete_reminder(self):
        self.cm.add_reminder("09:00", "Test", "Desc")
        self.cm.delete_reminder(0)
        self.assertEqual(len(self.cm.get_reminders()), 0)

    def test_reset_to_default(self):
        config = self.cm.reset_to_default()
        self.assertIn("news_sources", config)
        self.assertIn("email", config)
        self.assertFalse(config["email"]["enabled"])

    def test_api_keys(self):
        keys = self.cm.get_api_keys()
        self.assertIn("semantic_scholar", keys)

    def test_missing_api_keys(self):
        missing = self.cm.check_missing_api_keys()
        core_missing = [m for m in missing if m["key_name"] == "core"]
        self.assertTrue(len(core_missing) > 0)
        self.assertTrue(core_missing[0]["required"])


if __name__ == "__main__":
    unittest.main()
