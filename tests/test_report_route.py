import unittest
from pathlib import Path

from apr.analyzer import ReviewResult
from apr.assessment.quiz import Question, QuizResult
from apr.config import Config
from apr.digest import ProjectDigest, TechStack
from apr.evidence.base import EvidenceReport, FileVerdict
from apr.profile import Profile, SkillClaim
from apr.report import render_report
from apr.scanner import scan_project
from tests import fixture_dir

SECTION_TITLES = ("项目介绍", "技术栈", "项目结构", "核心代码分析", "AI 生成部分",
                  "我的学习盲区", "面试问题", "下一步练习")


def _quiz(score):
    return QuizResult(
        questions=[Question(id="q1", question="题", options=["a", "b", "c", "d"],
                            answer_index=0, explanation="", topic="Redis")],
        grades=[{"id": "q1", "score": score, "comment": ""}], overall=score)


def _evidence():
    return EvidenceReport(items=[], per_file={
        "Cache0.java": FileVerdict(file="Cache0.java", score=0.82, confidence=0.8, items=[])})


def _redis_project():
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
    sections = [(t, "## " + t + "\n\n（测试内容）") for t in SECTION_TITLES]
    return ReviewResult(project=root, config=Config(), scan=scan, digest=digest,
                        evidence=evidence or EvidenceReport(), profile=profile,
                        quiz=quiz, sections=sections, git_head=None,
                        started_at="2026-01-01T00:00:00", notes=[])


class ReportRouteTest(unittest.TestCase):
    def test_route_section_present(self):
        root, scan, digest = _redis_project()
        profile = Profile(learning=[SkillClaim("Redis", "beginner")])
        result = _result(root, scan, digest, profile=profile, quiz=_quiz(45),
                         evidence=_evidence())
        text = render_report(result)
        self.assertIn("## 下一阶段学习路线", text)
        self.assertIn("### Redis", text)
        self.assertIn("**原因**：", text)
        self.assertIn("**学习路线**：", text)
        self.assertIn("1. ", text)
        self.assertIn("**实践项目**：", text)
        # 示例三要素：使用 / Quiz / 用户等级
        self.assertIn("项目使用Redis", text)
        self.assertIn("Quiz评分45", text)
        self.assertIn("用户技能等级", text)
        self.assertIn("Redis 实战练习", text)

    def test_old_report_structure_compatible(self):
        root, scan, digest = _redis_project()
        result = _result(root, scan, digest,
                         profile=Profile(learning=[SkillClaim("Redis", "beginner")]),
                         quiz=_quiz(45), evidence=_evidence())
        text = render_report(result)
        # 8 大板块保持原样
        for title in SECTION_TITLES:
            self.assertIn("## " + title, text)
        # 目录编号：技能评估 9、学习路线 10、附录 A 11
        self.assertIn("9. [我的技能评估](#我的技能评估)", text)
        self.assertIn("10. [下一阶段学习路线](#下一阶段学习路线)", text)
        self.assertIn("11. [附录 A：AI 生成证据明细]", text)
        self.assertIn("12. [附录 B：实践验证记录]", text)
        # 顺序：技能评估 → 学习路线 → 附录
        pos_skill = text.find("## 我的技能评估")
        pos_route = text.find("## 下一阶段学习路线")
        pos_appendix = text.find("## 附录 A")
        self.assertLess(pos_skill, pos_route)
        self.assertLess(pos_route, pos_appendix)
        # 学习盲区（证据引擎章节）仍然存在
        self.assertIn("非 AI 猜测", text)

    def test_route_fallback_empty(self):
        from apr.scanner import ScanResult
        root = Path("C:/fake/empty")
        scan = ScanResult(root=root, files=[])
        digest = ProjectDigest(root=root, scan=scan,
                               stack=TechStack(languages={}, platforms=[], dependencies={}),
                               key_files=[], tree_text="")
        result = _result(root, scan, digest)
        text = render_report(result)
        self.assertIn("## 下一阶段学习路线", text)
        self.assertIn("暂无足够数据生成学习路线", text)
        self.assertIn("## 项目介绍", text)
