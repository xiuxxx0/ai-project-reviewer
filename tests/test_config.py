import os
import unittest

from apr.config import Config, LLMConfig, apply_env, load_config
from tests import fixture_dir


class ConfigTest(unittest.TestCase):
    def test_defaults(self):
        cfg = Config()
        self.assertEqual(cfg.llm.provider, "deepseek")
        self.assertEqual(cfg.llm.model, "deepseek-v4-pro")
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
            "llm:\n  provider: deepseek\n  model: deepseek-v4-pro\n"
            "output:\n  language: zh\n")
        self.assertEqual(data["llm"]["provider"], "deepseek")
        self.assertEqual(data["output"]["language"], "zh")

    def test_yaml_parser_list_of_maps(self):
        from apr._yaml import parse_simple_yaml
        data = parse_simple_yaml(
            "skills:\n  mastered:\n    - name: Python\n      level: basic\n"
            "      topics:\n        - 基础语法\n        - 函数\n"
            "  learning:\n    - name: Java\n      level: beginner\n"
            "profile:\n  name: 修\n  goal:\n    - Java后端开发\n")
        m = data["skills"]["mastered"][0]
        self.assertEqual(m["name"], "Python")
        self.assertEqual(m["level"], "basic")
        self.assertEqual(m["topics"], ["基础语法", "函数"])
        self.assertEqual(data["skills"]["learning"][0]["name"], "Java")
        self.assertEqual(data["profile"]["name"], "修")
        self.assertEqual(data["profile"]["goal"], ["Java后端开发"])

    def test_yaml_dump_round_trip_with_map_items(self):
        from apr._yaml import dump_simple_yaml, parse_simple_yaml
        data = {
            "skills": {"mastered": [{"name": "Python", "level": "basic",
                                     "topics": ["函数", "文件"]}]},
            "prefs": {"chinese": True, "count": 3},
        }
        self.assertEqual(parse_simple_yaml(dump_simple_yaml(data)), data)
