import unittest

from apr._yaml import dump_simple_yaml, parse_simple_yaml
from apr.configure import PRESETS, update_config_file
from tests import fixture_dir


class ConfigureTest(unittest.TestCase):
    def test_dump_round_trip(self):
        data = {
            "llm": {"provider": "deepseek", "model": "deepseek-v4-pro",
                    "base_url": "https://api.deepseek.com", "api_key_env": "DEEPSEEK_API_KEY",
                    "temperature": 0.3, "max_tokens": 4096},
            "limits": {"max_files": 300, "extra_ignores": ["docs/", "*.log"]},
            "quiz": {"enabled": True, "question_count": 4},
        }
        parsed = parse_simple_yaml(dump_simple_yaml(data))
        self.assertEqual(parsed, data)

    def test_update_preserves_other_sections(self):
        root = fixture_dir("config")
        cfg_path = root / "apr.yaml"
        cfg_path.write_text(
            "llm:\n  provider: mock\n  model: mock\n"
            "quiz:\n  enabled: false\n"
            "limits:\n  max_files: 100\n", encoding="utf-8")
        new_llm = update_config_file(cfg_path, dict(PRESETS["deepseek-flash"]))
        self.assertEqual(new_llm["provider"], "deepseek")
        self.assertEqual(new_llm["model"], "deepseek-v4-flash")
        self.assertEqual(new_llm["base_url"], "https://api.deepseek.com")
        data = parse_simple_yaml(cfg_path.read_text(encoding="utf-8"))
        self.assertIs(data["quiz"]["enabled"], False)
        self.assertEqual(data["limits"]["max_files"], 100)

    def test_presets_have_valid_provider(self):
        from apr.config import PROVIDER_DEFAULTS
        for preset in PRESETS.values():
            self.assertIn(preset["provider"], PROVIDER_DEFAULTS)
