import unittest
from pathlib import Path

from apr.analyzer import ReviewResult
from apr.assessment.quiz import Question, QuizResult
from apr.config import Config
from apr.digest import ProjectDigest, TechStack
from apr.evidence.base import EvidenceReport
from apr.profile import Profile
from apr.report import render_report
from apr.scanner import FileInfo, ScanResult

SECTION_TITLES = ("项目介绍", "技术栈", "项目结构", "核心代码分析", "AI 生成部分",
                  "我的学习盲区", "面试问题", "下一步练习")


def _make_result(profile=None, quiz=None, evidence=None, files=None):
    scan = ScanResult(root=Path("C:/fake/proj"), files=files or [])
    digest = ProjectDigest(root=Path("C:/fake/proj"), scan=scan,
                           stack=TechStack(languages={"Python": 10}, platforms=[],
                                           dependencies={}),
                           key_files=[], tree_text="proj/")
    sections = [(t, "## " + t + "\n\n（测试内容）") for t in SECTION_TITLES]
    return ReviewResult(project=Path("C:/fake/proj"), config=Config(), scan=scan,
                        digest=digest, evidence=evidence or EvidenceReport(),
                        profile=profile, quiz=quiz, sections=sections,
                        git_head=None, started_at="2026-01-01T00:00:00", notes=[])


def _quiz(score: int) -> QuizResult:
    return QuizResult(
        questions=[Question(id="q1", question="题", options=["a", "b", "c", "d"],
                            answer_index=0, explanation="", topic="Python")],
        grades=[{"id": "q1", "score": score, "comment": ""}],
        overall=score)


class ReportSkillSectionTest(unittest.TestCase):
    def test_skill_section_present_with_fields(self):
        profile = Profile(known_skills=["Python: intermediate"])
        files = [FileInfo(rel="a.py", abs="C:/fake/a.py", size=10, ext=".py")]
        result = _make_result(profile=profile, quiz=_quiz(75), files=files)
        text = render_report(result)
        self.assertIn("## 我的技能评估", text)
        self.assertIn("### Python", text)
        self.assertIn("**自评**：intermediate", text)
        self.assertIn("**项目证据**：", text)
        self.assertIn("使用 Python 编写 1 个文件", text)
        self.assertIn("**Quiz 表现**：75/100", text)
        self.assertIn("**最终等级**：", text)
        self.assertIn("掌握（intermediate）", text)
        self.assertIn("**可信度**：", text)

    def test_quiz_80_upgrades_level(self):
        profile = Profile(known_skills=["Python: intermediate"])
        files = [FileInfo(rel="a.py", abs="C:/fake/a.py", size=10, ext=".py")]
        result = _make_result(profile=profile, quiz=_quiz(80), files=files)
        text = render_report(result)
        self.assertIn("熟练（advanced）", text)

    def test_original_structure_kept(self):
        result = _make_result()
        text = render_report(result)
        for title in SECTION_TITLES:
            self.assertIn("## " + title, text)
        self.assertIn("## 附录 A：AI 生成证据明细", text)
        self.assertLess(text.find("## 我的技能评估"), text.find("## 附录 A"))
        self.assertIn("9. [我的技能评估](#我的技能评估)", text)
        self.assertIn("10. [附录 A：AI 生成证据明细]", text)
        self.assertIn("1. [项目介绍](#项目介绍)", text)
        self.assertIn("8. [下一步练习](#下一步练习)", text)

    def test_empty_inputs_no_break(self):
        result = _make_result()
        text = render_report(result)
        self.assertIn("暂无足够数据生成技能评估", text)
        self.assertIn("## 项目介绍", text)

    def test_quiz_not_done_shows_unverified(self):
        profile = Profile(known_skills=["Python: intermediate"])
        result = _make_result(profile=profile, quiz=None)
        text = render_report(result)
        self.assertIn("**Quiz 表现**：未验证", text)
        self.assertIn("**自评**：intermediate", text)

    def test_confidence_percent_format(self):
        profile = Profile(known_skills=["Python: intermediate"])
        files = [FileInfo(rel="a.py", abs="C:/fake/a.py", size=10, ext=".py")]
        result = _make_result(profile=profile, quiz=_quiz(75), files=files)
        text = render_report(result)
        import re
        self.assertIsNotNone(re.search(r"\*\*可信度\*\*：\d+%", text))
