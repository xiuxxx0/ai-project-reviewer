import unittest

from apr.evidence.base import EvidenceItem, EvidenceSource
from apr.evidence.fusion import fuse


class FusionTest(unittest.TestCase):
    def test_weighted_fusion(self):
        items = [
            EvidenceItem(EvidenceSource.MARKER, "a.py", "AI 标记", ai_score=0.9, confidence=0.9),
            EvidenceItem(EvidenceSource.GIT, "a.py", "2/3 AI 提交", ai_score=0.66, confidence=0.5),
            EvidenceItem(EvidenceSource.AGENT_LOG, "b.py", "Claude 编辑", ai_score=0.85, confidence=0.8),
        ]
        report = fuse(items, {"a.py", "b.py"}, [])
        self.assertIn("a.py", report.per_file)
        self.assertGreaterEqual(report.per_file["a.py"].score, 0.7)
        self.assertEqual(report.per_file["b.py"].classification, "AI 主导")

    def test_drop_unknown_files(self):
        report = fuse(
            [EvidenceItem(EvidenceSource.MARKER, "ghost.py", "x", ai_score=0.9, confidence=0.9)],
            {"a.py"}, [])
        self.assertEqual(report.per_file, {})
        self.assertTrue(any("丢弃" in n for n in report.notes))

    def test_mention_only_is_assisted(self):
        report = fuse(
            [EvidenceItem(EvidenceSource.AGENT_LOG, "c.py", "提及", ai_score=0.4, confidence=0.45)],
            {"c.py"}, [])
        self.assertEqual(report.per_file["c.py"].classification, "AI 辅助")
