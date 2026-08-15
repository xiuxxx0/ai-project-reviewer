import unittest
from pathlib import Path

from apr.analyzer import ReviewResult
from apr.assessment.blindspot import BlindSpotReport, detect_blind_spots
from apr.assessment.quiz import Question, QuizResult
from apr.config import Config
from apr.digest import ProjectDigest, TechStack
from apr.evidence.base import EvidenceReport, FileVerdict
from apr.profile import Profile
from apr.report import render_report
from apr.scanner import ScanResult, scan_project
from tests import fixture_dir


def _quiz(topics_scores):
    questions = [Question(id="q%d" % i, question="题", options=["a", "b", "c", "d"],
                          answer_index=0, explanation="", topic=t)
                 for i, (t, _) in enumerate(topics_scores)]
    grades = [{"id": "q%d" % i, "score": s, "comment": ""} for i, (_, s) in enumerate(topics_scores)]
    return QuizResult(questions=questions, grades=grades,
                      overall=round(sum(s for _, s in topics_scores) / len(topics_scores)))


def _evidence(verdicts):
    per_file = {rel: FileVerdict(file=rel, score=s, confidence=c, items=[])
                for rel, (s, c) in verdicts.items()}
    return EvidenceReport(items=[], per_file=per_file)


def _project(extra_py: int = 0):
    root = fixture_dir("knowledge")
    (root / "UserService.java").write_text(
        "@Service\npublic class UserService {\n"
        "  private final RedisTemplate<String,String> t;\n}\n", encoding="utf-8")
    (root / "CacheHelper.java").write_text(
        "public class CacheHelper { private final RedisTemplate rt; }\n", encoding="utf-8")
    for i in range(extra_py):
        (root / ("m%d.py" % i)).write_text("print(1)\n", encoding="utf-8")
    scan = scan_project(root, Config().limits)
    digest = ProjectDigest(root=root, scan=scan,
                           stack=TechStack(languages={"Java": 1}, platforms=[], dependencies={}),
                           key_files=[], tree_text="")
    return root, scan, digest


class BlindSpotTest(unittest.TestCase):
    def test_high_risk_example(self):
        """设计示例：项目核心依赖 Redis + 未掌握 + Quiz 40 + AI 主导 → 高风险盲区。"""
        root, scan, digest = _project()
        profile = Profile(mastered=[])          # 未声明 Redis
        quiz = _quiz([("Redis", 40)])
        evidence = _evidence({"UserService.java": (0.82, 0.8)})
        report = detect_blind_spots(profile=profile, scan=scan, digest=digest,
                                    quiz=quiz, evidence=evidence)
        skills = {b.skill: b for b in report.items}
        self.assertIn("Redis", skills)
        redis = skills["Redis"]
        self.assertEqual(redis.risk_level, "高风险盲区")
        joined = "\n".join(redis.evidence)
        self.assertIn("项目核心依赖 Redis", joined)
        self.assertIn("用户 profile 未掌握 Redis", joined)
        self.assertIn("Quiz 40 分", joined)
        self.assertIn("主要由 AI 生成", joined)
        joined_sug = "\n".join(redis.suggestions)
        self.assertIn("学习 缓存 基础", joined_sug)
        self.assertIn("独立重写", joined_sug)

    def test_mastered_and_good_quiz_not_blind(self):
        root, scan, digest = _project(extra_py=2)
        profile = Profile(mastered=[])
        profile.known_skills = ["Python: intermediate"]
        quiz = _quiz([("Python", 85)])
        evidence = _evidence({"m0.py": (0.1, 0.8)})
        report = detect_blind_spots(profile=profile, scan=scan, digest=digest,
                                    quiz=quiz, evidence=evidence)
        self.assertNotIn("Python", {b.skill for b in report.items})
        self.assertTrue(any("风险低" in n and "Python" in n for n in report.notes))

    def test_learning_status_evidence(self):
        root, scan, digest = _project()
        from apr.profile import SkillClaim
        profile = Profile(learning=[SkillClaim("Redis", "beginner")])
        report = detect_blind_spots(profile=profile, scan=scan, digest=digest)
        redis = {b.skill: b for b in report.items}["Redis"]
        self.assertTrue(any("正在学习" in ev for ev in redis.evidence))
        self.assertEqual(redis.risk_level, "中风险盲区")

    def test_target_priority_evidence(self):
        root, scan, digest = _project()
        from apr.profile import TargetSkill
        profile = Profile(targets=[TargetSkill("Redis", "high")])
        report = detect_blind_spots(profile=profile, scan=scan, digest=digest)
        redis = {b.skill: b for b in report.items}["Redis"]
        self.assertTrue(any("优先级 high" in ev for ev in redis.evidence))

    def test_profile_only_skill_excluded(self):
        root, scan, digest = _project(extra_py=1)
        from apr.profile import SkillClaim
        profile = Profile(mastered=[SkillClaim("Kubernetes", "basic")])
        report = detect_blind_spots(profile=profile, scan=scan, digest=digest)
        self.assertNotIn("Kubernetes", {b.skill for b in report.items})
        self.assertTrue(any("项目未使用" in n for n in report.notes))

    def test_report_integration_replaces_llm_section(self):
        root, scan, digest = _project()
        profile = Profile()
        quiz = _quiz([("Redis", 40)])
        evidence = _evidence({"UserService.java": (0.82, 0.8)})
        sections = [(t, "## " + t + "\n\n（测试内容）") for t in
                    ("项目介绍", "技术栈", "项目结构", "核心代码分析", "AI 生成部分",
                     "我的学习盲区", "面试问题", "下一步练习")]
        result = ReviewResult(project=root, config=Config(), scan=scan, digest=digest,
                              evidence=evidence, profile=profile, quiz=quiz,
                              sections=sections, git_head=None,
                              started_at="2026-01-01T00:00:00", notes=[])
        text = render_report(result)
        self.assertIn("## 我的学习盲区", text)
        self.assertIn("高风险盲区", text)
        self.assertIn("非 AI 猜测", text)
        # LLM 占位内容被替换（盲区节不再出现测试内容）
        blind_start = text.find("## 我的学习盲区")
        blind_end = text.find("---", blind_start)
        self.assertNotIn("（测试内容）", text[blind_start:blind_end])

    def test_empty_inputs(self):
        report = detect_blind_spots()
        self.assertEqual(report.items, [])
        self.assertIn("暂无足够证据", report.render_markdown())
        self.assertIsInstance(report, BlindSpotReport)
