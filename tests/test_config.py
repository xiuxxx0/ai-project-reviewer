import os
import unittest

from apr.config import Config, LLMConfig, apply_env, load_config
from tests import fixture_dir


class ConfigTest(unittest.TestCase):
    def test_defaults(self):
        cfg = Config()
        self.assertEqual(cfg.llm.provider, "deepseek")
        self.assertEqual(cfg.llm.model, "deepseek-chat")
        self.assertEqual(cfg.output.language, "zh")
        self.assertEqual(cfg.output.file, "README复盘.md")

    def test_provider_switch_defaults(self):
        cfg = LLMConfig.from_mapping({"provider": "ollama"})
        self.assertEqual(cfg.base_url, "http://localhost:11434")

    def test_load_project_yaml(self):
        root = fixture_dir("config")
        (root / "apr.yaml").write_text(
            "llm:\n  provider: openai\n  model: gpt-4o-mini\n"
            "output:\n  language: en\n", encoding="utf-8")
        cfg = load_config(root)
        self.assertEqual(cfg.llm.provider, "openai")
        self.assertEqual(cfg.llm.model, "gpt-4o-mini")
        self.assertEqual(cfg.output.language, "en")

    def test_env_override(self):
        old = os.environ.get("APR_PROVIDER")
        os.environ["APR_PROVIDER"] = "mock"
        try:
            cfg = apply_env(Config())
            self.assertEqual(cfg.llm.provider, "mock")
        finally:
            if old is None:
                os.environ.pop("APR_PROVIDER", None)
            else:
                os.environ["APR_PROVIDER"] = old

    def test_yaml_parser_lists_and_comments(self):
        from apr._yaml import parse_simple_yaml
        data = parse_simple_yaml(
            "known_skills:\n  - Python  # 注释\n  - Git\n"
            "quiz:\n  enabled: true\n  question_count: 4\n")
        self.assertEqual(data["known_skills"], ["Python", "Git"])
        self.assertIs(data["quiz"]["enabled"], True)
        self.assertEqual(data["quiz"]["question_count"], 4)

    def test_yaml_parser_nested_sections(self):
        from apr._yaml import parse_simple_yaml
        data = parse_simple_yaml(
            "llm:\n  provider: deepseek\n  model: deepseek-chat\n"
            "output:\n  language: zh\n")
        self.assertEqual(data["llm"]["provider"], "deepseek")
        self.assertEqual(data["output"]["language"], "zh")
