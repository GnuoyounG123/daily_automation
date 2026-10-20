import unittest
import json
import tempfile
from pathlib import Path
from config_manager import ConfigManager, CONFIG_VERSION


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

    def test_weather_city_is_normalized(self):
        self.cm.save_config({"weather_city": "  Hangzhou  "})
        self.assertEqual(self.cm.get_weather_city(), "Hangzhou")

        self.cm.update_weather_city("   ")
        self.assertEqual(self.cm.get_weather_city(), "Beijing")

    def test_ensure_default_config_migrates_legacy_sources(self):
        self.cm.save_config({
            "weather_city": " Hangzhou ",
            "news_sources": [
                {"name": "Semantic Scholar", "url": "https://www.semanticscholar.org/",
                 "type": "web", "enabled": True},
                {"name": "AMiner", "url": "https://www.aminer.cn/",
                 "type": "web", "enabled": True},
            ],
        })

        self.assertFalse(self.cm.ensure_default_config())
        config = self.cm.get_config()

        self.assertEqual(config["weather_city"], "Hangzhou")
        self.assertEqual(config["config_version"], CONFIG_VERSION)
        semantic = config["news_sources"][0]
        self.assertEqual(semantic["type"], "api")
        self.assertEqual(
            semantic["url"], "https://api.semanticscholar.org/graph/v1/paper/search")
        self.assertFalse(config["news_sources"][1]["enabled"])

    def test_source_migration_runs_only_once(self):
        self.cm.save_config({
            "news_sources": [
                {"name": "AMiner", "url": "https://www.aminer.cn/",
                 "type": "web", "enabled": True},
            ],
        })
        self.cm.ensure_default_config()

        config = self.cm.get_config()
        config["news_sources"][0]["enabled"] = True
        self.cm.save_config(config)

        self.assertFalse(self.cm.ensure_default_config())
        self.assertTrue(self.cm.get_config()["news_sources"][0]["enabled"])


if __name__ == "__main__":
    unittest.main()
