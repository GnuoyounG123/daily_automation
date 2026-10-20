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


class TestWeatherAPI(unittest.TestCase):
    def test_clothing_advice_uses_temperature_ranges(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from daily_assistant import WeatherAPI

        self.assertEqual(WeatherAPI._get_clothing_advice("5"), "天气较凉，建议穿厚外套")
        self.assertEqual(WeatherAPI._get_clothing_advice("15"), "天气温和，适合正常穿着")
        self.assertEqual(WeatherAPI._get_clothing_advice("23"), "天气暖和，适合轻便穿着")
        self.assertEqual(WeatherAPI._get_clothing_advice("31"), "天气炎热，注意防晒补水")

    def test_parse_weather_data_for_23_degrees_is_not_cold(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from daily_assistant import WeatherAPI

        data = {
            "current_condition": [{
                "weatherDesc": [{"value": "Patchy rain nearby"}],
                "temp_C": "23",
                "FeelsLikeC": "25",
                "humidity": "52",
                "windspeedKmph": "11",
                "winddir16Point": "SSE",
                "uvIndex": "2"
            }],
            "weather": [{}, {"weatherDesc": [{"value": "Cloudy"}]}]
        }

        weather = WeatherAPI._parse_weather_data(data)
        self.assertEqual(weather["穿衣建议"], "天气暖和，适合轻便穿着")

    def test_weather_city_is_trimmed_and_url_encoded(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from daily_assistant import WeatherAPI
        from unittest.mock import patch

        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps({
                    "current_condition": [{
                        "weatherDesc": [{"value": "Sunny"}],
                        "temp_C": "23",
                        "FeelsLikeC": "25",
                        "humidity": "50",
                        "windspeedKmph": "5",
                        "winddir16Point": "N",
                        "uvIndex": "3"
                    }],
                    "weather": [{}, {}]
                }).encode("utf-8")

        def fake_urlopen(req, timeout=10):
            captured["url"] = req.full_url
            return FakeResponse()

        with patch("urllib.request.urlopen", fake_urlopen):
            weather = WeatherAPI.get_weather("  Hangzhou  ")

        self.assertIsNotNone(weather)
        self.assertTrue(captured["url"].endswith("/Hangzhou?format=j1"))

    def test_empty_weather_city_defaults_to_beijing(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from daily_assistant import WeatherAPI
        from unittest.mock import patch

        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps({
                    "current_condition": [{"weatherDesc": [{"value": "Sunny"}], "temp_C": "20"}],
                    "weather": [{}, {}]
                }).encode("utf-8")

        def fake_urlopen(req, timeout=10):
            captured["url"] = req.full_url
            return FakeResponse()

        with patch("urllib.request.urlopen", fake_urlopen):
            WeatherAPI.get_weather("   ")

        self.assertTrue(captured["url"].endswith("/Beijing?format=j1"))


class TestApiSourceManager(unittest.TestCase):
    def test_search_single_reports_rate_limit(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from daily_assistant import ApiSourceManager

        class FakeSource:
            name = "Semantic Scholar API"
            last_error = "HTTP 429 限流，请配置 API Key 或稍后重试"

            def search(self, keywords, max_results=10):
                return []

        manager = ApiSourceManager.__new__(ApiSourceManager)
        manager.sources = [FakeSource()]
        manager._log_messages = []
        manager.last_error = ""

        items = manager.search_single("Semantic Scholar API", ["ai"])

        self.assertEqual(items, [])
        self.assertIn("429", manager.last_error)

    def test_semantic_scholar_429_text_body_is_reported(self):
        import sys
        from unittest.mock import patch
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from daily_automation.api_sources import SemanticScholarApi
        from daily_automation.web_fetcher import FetchResult

        class FakeFetcher:
            def fetch(self, *args, **kwargs):
                return FetchResult(
                    url="https://api.semanticscholar.org/graph/v1/paper/search",
                    content="Too Many Requests",
                    status_code=429,
                )

        api = SemanticScholarApi.__new__(SemanticScholarApi)
        api._api_key = ""
        api.last_error = ""
        api._fetcher = FakeFetcher()

        with patch("daily_automation.api_sources.time.sleep", lambda *_: None):
            items = api.search(["ai"], max_results=3)

        self.assertEqual(items, [])
        self.assertIn("429", api.last_error)


if __name__ == "__main__":
    unittest.main()
