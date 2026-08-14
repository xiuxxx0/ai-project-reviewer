import unittest
from pathlib import Path

from apr.config import LimitsConfig
from apr.scanner import IgnoreMatcher, render_tree, scan_project
from tests import fixture_dir


def _setup(root: Path):
    (root / "a.py").write_text("print('hi')\n", encoding="utf-8")
    (root / "b.log").write_text("log\n", encoding="utf-8")
    (root / "vendor" / "x.py").write_text("x\n", encoding="utf-8")
    (root / "node_modules" / "y.js").write_text("y\n", encoding="utf-8")
    (root / ".gitignore").write_text("*.log\nvendor/\n", encoding="utf-8")
    (root / "bin.dat").write_bytes(b"\x00\x01\x02")
    (root / "src" / "main.py").write_text("def main():\n    pass\n", encoding="utf-8")


class ScannerTest(unittest.TestCase):
    def test_scan_excludes(self):
        root = fixture_dir("scanner")
        _setup(root)
        scan = scan_project(root, LimitsConfig())
        rels = {f.rel for f in scan.files}
        self.assertIn("a.py", rels)
        self.assertIn("src/main.py", rels)
        self.assertNotIn("b.log", rels)
        self.assertNotIn("vendor/x.py", rels)
        self.assertNotIn("node_modules/y.js", rels)
        self.assertGreaterEqual(scan.excluded_count, 3)

    def test_text_and_lines(self):
        root = fixture_dir("scanner")
        _setup(root)
        scan = scan_project(root, LimitsConfig())
        by_rel = {f.rel: f for f in scan.files}
        self.assertTrue(by_rel["a.py"].is_text)
        self.assertEqual(by_rel["a.py"].lines, 1)
        self.assertEqual(by_rel["src/main.py"].lines, 2)
        self.assertFalse(by_rel["bin.dat"].is_text)

    def test_matcher_negation(self):
        m = IgnoreMatcher(["*.log", "!keep.log"])
        self.assertTrue(m.is_ignored("a.log"))
        self.assertFalse(m.is_ignored("keep.log"))

    def test_tree(self):
        root = fixture_dir("scanner")
        _setup(root)
        scan = scan_project(root, LimitsConfig())
        tree = render_tree(scan, 100)
        self.assertIn("a.py", tree)
        self.assertIn("src/", tree)
