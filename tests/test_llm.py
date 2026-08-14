import unittest

from apr.errors import LLMError
from apr.llm.base import ChatMessage, MockProvider, extract_json


class LLMTest(unittest.TestCase):
    def test_extract_fenced(self):
        self.assertEqual(extract_json('\u0060\u0060\u0060json\n{"a": 1}\n\u0060\u0060\u0060'), {"a": 1})

    def test_extract_embedded(self):
        self.assertEqual(extract_json('前言 {"b": [1,2]} 后记'), {"b": [1, 2]})

    def test_extract_fail(self):
        with self.assertRaises(LLMError):
            extract_json("没有 JSON")

    def test_mock_sections(self):
        p = MockProvider()
        out = p.complete([ChatMessage("system", "[TASK: section-3]"), ChatMessage("user", "x")])
        self.assertIn("## 项目结构", out)

    def test_mock_quiz_json(self):
        p = MockProvider()
        data = p.complete_json([ChatMessage("system", "[TASK: quiz-generate]"),
                                ChatMessage("user", "x")])
        self.assertEqual(len(data["questions"]), 2)
