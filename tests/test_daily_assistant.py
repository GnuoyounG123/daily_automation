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


if __name__ == "__main__":
    unittest.main()
