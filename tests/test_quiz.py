import unittest

from apr.assessment.quiz import generate_questions, grade_answers
from apr.llm.base import MockProvider


class QuizTest(unittest.TestCase):
    def test_generate_retries_on_bad_json(self):
        from unittest import mock
        from apr.errors import LLMError
        p = MockProvider()
        calls = {"n": 0}

        def fake_complete_json(messages, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise LLMError("无法从模型输出中解析 JSON")
            return {"questions": [{
                "id": "q1", "question": "题", "options": ["A", "B", "C", "D"],
                "answer_index": 0, "explanation": "解析", "topic": "主题"}],
                "essay": "简答"}

        with mock.patch.object(p, "complete_json", side_effect=fake_complete_json):
            qs, essay = generate_questions(p, "# 项目画像", 1)
        self.assertEqual(len(qs), 1)
        self.assertEqual(calls["n"], 2)   # 第一次失败 → 纠错重试成功

    def test_generate_and_grade_with_mock(self):
        p = MockProvider()
        qs, essay = generate_questions(p, "# 项目画像\n- 项目名：demo", 2)
        self.assertEqual(len(qs), 2)
        self.assertEqual(len(qs[0].options), 4)
        graded = grade_answers(p, qs, [q.options[q.answer_index] for q in qs], essay, "我的回答")
        self.assertEqual(graded["overall"], 70)
        self.assertIn("Mock 示例主题", graded["weakest_topics"])
