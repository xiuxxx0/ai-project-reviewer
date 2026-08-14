import unittest

from apr.config import LimitsConfig
from apr.evidence.markers import scan_markers
from apr.scanner import scan_project
from tests import fixture_dir


class MarkersTest(unittest.TestCase):
    def test_markers(self):
        root = fixture_dir("markers")
        (root / "ai.py").write_text(
            "# AI-GENERATED: 本文件由 Claude 生成\ndef f():\n    return 1\n",
            encoding="utf-8")
        (root / "human.py").write_text(
            "# HAND-WRITTEN\ndef g():\n    return 2\n", encoding="utf-8")
        (root / "plain.py").write_text("def h():\n    return 3\n", encoding="utf-8")
        scan = scan_project(root, LimitsConfig())
        items = scan_markers(scan)
        by_file = {i.file: i for i in items}
        self.assertIn("ai.py", by_file)
        self.assertGreaterEqual(by_file["ai.py"].ai_score, 0.6)
        self.assertIn("human.py", by_file)
        self.assertLess(by_file["human.py"].ai_score, 0.3)
        self.assertNotIn("plain.py", by_file)
