import unittest

from apr.assessment.quiz import generate_questions, grade_answers
from apr.llm.base import MockProvider


class QuizTest(unittest.TestCase):
    def test_generate_and_grade_with_mock(self):
        p = MockProvider()
        qs, essay = generate_questions(p, "# 项目画像\n- 项目名：demo", 2)
        self.assertEqual(len(qs), 2)
        self.assertEqual(len(qs[0].options), 4)
        graded = grade_answers(p, qs, [q.options[q.answer_index] for q in qs], essay, "我的回答")
        self.assertEqual(graded["overall"], 70)
        self.assertIn("Mock 示例主题", graded["weakest_topics"])
