import unittest
from pathlib import Path

from apr.analyzer import ReviewResult
from apr.assessment.quiz import Question, QuizResult
from apr.config import Config
from apr.digest import ProjectDigest, TechStack
from apr.evidence.base import EvidenceReport, FileVerdict
from apr.learning_report import render_learning_report
from apr.profile import Profile, SkillClaim
from apr.scanner import scan_project
from tests import fixture_dir


def _quiz(score):
    return QuizResult(
        questions=[Question(id="q1", question="题", options=["a", "b", "c", "d"],
                            answer_index=0, explanation="", topic="Redis")],
        grades=[{"id": "q1", "score": score, "comment": ""}], overall=score)


def _evidence():
    return EvidenceReport(items=[], per_file={
        "Cache0.java": FileVerdict(file="Cache0.java", score=0.82, confidence=0.8, items=[]),
        "Cache1.java": FileVerdict(file="Cache1.java", score=0.05, confidence=0.7, items=[]),
    })


def _project():
    root = fixture_dir("knowledge")
    for i in range(2):
        (root / ("Cache%d.java" % i)).write_text(
            "public class Cache%d { private final RedisTemplate rt; }\n" % i,
            encoding="utf-8")
    scan = scan_project(root, Config().limits)
    digest = ProjectDigest(root=root, scan=scan,
                           stack=TechStack(languages={"Java": 2}, platforms=[],
                                           dependencies={}),
                           key_files=[], tree_text="")
    return root, scan, digest


def _result(root, scan, digest, profile=None, quiz=None, evidence=None):
    sections = [(t, "## " + t + "\n\n（测试内容）") for t in
                ("项目介绍", "技术栈", "项目结构", "核心代码分析", "AI 生成部分",
                 "我的学习盲区", "面试问题", "下一步练习")]
    return ReviewResult(project=root, config=Config(), scan=scan, digest=digest,
                        evidence=evidence or EvidenceReport(), profile=profile,
                        quiz=quiz, sections=sections, git_head=None,
                        started_at="2026-01-01T00:00:00", notes=[])


class LearningReportTest(unittest.TestCase):
    def test_five_sections_structure(self):
        root, scan, digest = _project()
        result = _result(root, scan, digest,
                         profile=Profile(learning=[SkillClaim("Redis", "beginner")]),
                         quiz=_quiz(45), evidence=_evidence())
        text = render_learning_report(result)
        self.assertIn("# 项目学习报告", text)
        self.assertIn("## 1. 我完成了什么项目", text)
        self.assertIn("## 2. 这个项目让我学到了什么", text)
        self.assertIn("## 3. AI 协作情况", text)
        self.assertIn("## 4. 我的学习盲区", text)
        self.assertIn("## 5. 下一步学习路线", text)

    def test_learned_classification_symbols(self):
        root, scan, digest = _project()
        result = _result(root, scan, digest,
                         profile=Profile(learning=[SkillClaim("Redis", "beginner")]),
                         quiz=_quiz(45), evidence=_evidence())
        text = render_learning_report(result)
        self.assertIn("已掌握：", text)
        self.assertIn("正在提升：", text)
        self.assertIn("未掌握：", text)
        self.assertIn("○ ", text)

    def test_blindspot_evidence_based(self):
        root, scan, digest = _project()
        result = _result(root, scan, digest,
                         profile=Profile(learning=[SkillClaim("Redis", "beginner")]),
                         quiz=_quiz(45), evidence=_evidence())
        text = render_learning_report(result)
        self.assertIn("### Redis", text)
        self.assertIn("为什么：", text)
        self.assertIn("项目使用Redis", text)
        self.assertIn("Quiz 得分偏低", text)
        self.assertIn("非 AI 猜测", text)

    def test_ai_collab_section(self):
        root, scan, digest = _project()
        result = _result(root, scan, digest,
                         profile=Profile(learning=[SkillClaim("Redis", "beginner")]),
                         quiz=_quiz(45), evidence=_evidence())
        text = render_learning_report(result)
        self.assertIn("AI 帮助了什么：", text)
        self.assertIn("代码生成", text)
        self.assertIn("我的参与：", text)

    def test_route_short_and_mid(self):
        root, scan, digest = _project()
        result = _result(root, scan, digest,
                         profile=Profile(learning=[SkillClaim("Redis", "beginner")]),
                         quiz=_quiz(45), evidence=_evidence())
        text = render_learning_report(result)
        self.assertIn("### 短期（1 周）", text)
        self.assertIn("### 中期（1 个月）", text)
        self.assertIn("学习目标：", text)
        self.assertIn("实践任务：", text)
        self.assertIn("验证方式：", text)

    def test_empty_inputs_no_crash(self):
        root = Path("C:/fake/empty")
        from apr.scanner import ScanResult
        scan = ScanResult(root=root, files=[])
        digest = ProjectDigest(root=root, scan=scan,
                               stack=TechStack(languages={}, platforms=[],
                                               dependencies={}),
                               key_files=[], tree_text="")
        result = _result(root, scan, digest)
        text = render_learning_report(result)
        self.assertIn("# 项目学习报告", text)
        self.assertIn("## 5. 下一步学习路线", text)

    def test_cli_writes_two_reports(self):
        from apr.cli import main
        root, scan, digest = _project()
        rc = main(["review", str(root), "--provider", "mock", "--skip-quiz"])
        self.assertEqual(rc, 0)
        readme = root / "output" / "README复盘.md"
        learn = root / "output" / "learning_report.md"
        self.assertTrue(readme.is_file())
        self.assertTrue(learn.is_file())
        self.assertIn("## 项目介绍", readme.read_text(encoding="utf-8"))
        self.assertIn("# 项目学习报告", learn.read_text(encoding="utf-8"))
        self.assertIn("## 4. 我的学习盲区", learn.read_text(encoding="utf-8"))
