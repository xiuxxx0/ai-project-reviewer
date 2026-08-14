import unittest

from apr.config import LimitsConfig
from apr.digest import build_digest
from apr.scanner import scan_project
from tests import fixture_dir


class DigestTest(unittest.TestCase):
    def test_tech_detection(self):
        root = fixture_dir("digest")
        (root / "package.json").write_text(
            '{"dependencies": {"react": "^18.0.0"}, "devDependencies": {"vite": "^5"}}',
            encoding="utf-8")
        (root / "requirements.txt").write_text("flask==2.3.0\nnumpy>=1.24\n", encoding="utf-8")
        (root / "main.py").write_text("print(1)\n", encoding="utf-8")
        scan = scan_project(root, LimitsConfig())
        digest = build_digest(root, scan, LimitsConfig())
        self.assertIn("JavaScript/Node.js", digest.stack.platforms)
        self.assertIn("Python", digest.stack.platforms)
        self.assertIn("react", digest.stack.dependencies.get("package.json", []))
        self.assertIn("flask", digest.stack.dependencies.get("requirements.txt", []))
        self.assertIn("main.py", [f.rel for f in digest.key_files])
        self.assertIn("目录树", digest.render(include_excerpts=False))
