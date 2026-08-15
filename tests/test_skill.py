import json
import unittest
from pathlib import Path

from apr.assessment.quiz import Question, QuizResult
from apr.assessment.skill import (LEVELS, SkillAssessment, SkillAssessmentEntry,
                                  assess_skills)
from apr.evidence.base import EvidenceReport, FileVerdict
from apr.profile import Profile, SkillClaim, TargetSkill
from apr.scanner import FileInfo, ScanResult


def _file(rel: str, ext: str) -> FileInfo:
    return FileInfo(rel=rel, abs="C:/fake/" + rel, size=10, ext=ext)


def _scan(rels: list[tuple[str, str]]) -> ScanResult:
    return ScanResult(root=Path("C:/fake"), files=[_file(rel, ext) for rel, ext in rels])


def _quiz(topics_scores: list[tuple[str, int]]) -> QuizResult:
    questions = [
        Question(id="q%d" % i, question="题%d" % i, options=["a", "b", "c", "d"],
                 answer_index=0, explanation="", topic=topic)
        for i, (topic, _) in enumerate(topics_scores)
    ]
    grades = [{"id": "q%d" % i, "score": score, "comment": ""}
              for i, (_, score) in enumerate(topics_scores)]
    return QuizResult(questions=questions, grades=grades,
                      overall=round(sum(s for _, s in topics_scores) / len(topics_scores)))


def _evidence(verdicts: dict[str, tuple[float, float]]) -> EvidenceReport:
    per_file = {rel: FileVerdict(file=rel, score=score, confidence=conf, items=[])
                for rel, (score, conf) in verdicts.items()}
    return EvidenceReport(items=[], per_file=per_file)


PY_FILES = [("a.py", ".py")] * 42


class SkillTest(unittest.TestCase):
    def test_example_shape(self):
        """与设计示例对齐：claimed intermediate + quiz 75 → final intermediate。"""
        profile = Profile(known_skills=["Python: intermediate"])
        scan = _scan(PY_FILES)
        quiz = _quiz([("Python", 75)])
        evidence = _evidence({"a.py": (0.1, 0.8)})
        result = assess_skills(profile, scan, quiz, evidence)
        self.assertIn("Python", result.entries)
        entry = result.entries["Python"]
        d = result.to_dict()["Python"]
        self.assertEqual(set(d.keys()), {"claimed_level", "evidence", "quiz_score",
                                         "final_level", "confidence"})
        self.assertEqual(entry.claimed_level, "intermediate")
        self.assertEqual(entry.quiz_score, 75)
        self.assertEqual(entry.final_level, "intermediate")
        self.assertTrue(any("42 个文件" in ev for ev in entry.evidence))
        self.assertTrue(any("Quiz" in ev for ev in entry.evidence))
        self.assertTrue(any("AI 贡献证据" in ev for ev in entry.evidence))

    def test_quiz_upgrade_and_downgrade(self):
        profile = Profile(known_skills=["Python: beginner"])
        scan = _scan(PY_FILES)
        up = assess_skills(profile, scan, _quiz([("Python", 95)]), None)
        self.assertEqual(up.entries["Python"].final_level, "intermediate")
        down = assess_skills(profile, scan, _quiz([("Python", 30)]), None)
        self.assertEqual(down.entries["Python"].final_level, "beginner")

    def test_ai_downgrade_and_confidence(self):
        profile = Profile(known_skills=["Python: intermediate"])
        scan = _scan(PY_FILES)
        no_ai = assess_skills(profile, scan, None, None)
        heavy_ai = assess_skills(profile, scan, None, _evidence({"a.py": (0.9, 0.8)}))
        self.assertEqual(no_ai.entries["Python"].final_level, "intermediate")
        self.assertEqual(heavy_ai.entries["Python"].final_level, "beginner")
        self.assertLess(heavy_ai.entries["Python"].confidence,
                        no_ai.entries["Python"].confidence)
        self.assertTrue(any("AI 占主导" in ev for ev in heavy_ai.entries["Python"].evidence))

    def test_chinese_alias_and_fullwidth_colon(self):
        profile = Profile(known_skills=["Python：高级"])
        scan = _scan(PY_FILES)
        result = assess_skills(profile, scan, None, None)
        self.assertEqual(result.entries["Python"].claimed_level, "advanced")

    def test_auto_discovery_without_profile(self):
        scan = _scan([("m.go", ".go")] * 12)
        result = assess_skills(None, scan, None, None)
        self.assertIn("Go", result.entries)
        self.assertIsNone(result.entries["Go"].claimed_level)
        self.assertEqual(result.entries["Go"].final_level, "intermediate")

    def test_skill_only_in_profile(self):
        profile = Profile(known_skills=["Kubernetes"])
        scan = _scan(PY_FILES)
        result = assess_skills(profile, scan, None, None)
        entry = result.entries["Kubernetes"]
        self.assertEqual(entry.final_level, "beginner")
        self.assertTrue(any("未实际使用" in n for n in result.notes))

    def test_empty_inputs(self):
        result = assess_skills()
        self.assertEqual(result.entries, {})
        self.assertEqual(result.to_dict(), {})

    def test_json_serializable(self):
        profile = Profile(known_skills=["Python: intermediate"])
        result = assess_skills(profile, _scan(PY_FILES), _quiz([("Python", 75)]), None)
        data = json.loads(json.dumps(result.to_dict(), ensure_ascii=False))
        self.assertEqual(data["Python"]["final_level"], "intermediate")

    def test_confidence_bounds(self):
        profile = Profile(known_skills=["Python: expert", "Rust"])
        scan = _scan(PY_FILES + [("x.rs", ".rs")])
        result = assess_skills(profile, scan, None, _evidence({"a.py": (0.95, 0.9)}))
        for entry in result.entries.values():
            self.assertGreaterEqual(entry.confidence, 0.15)
            self.assertLessEqual(entry.confidence, 0.95)

    def test_weakest(self):
        profile = Profile(known_skills=["Python: expert", "Rust: beginner"])
        scan = _scan(PY_FILES)
        result = assess_skills(profile, scan, None, None)
        weak = [e.skill for e in result.weakest()]
        self.assertIn("Rust", weak)
        self.assertNotIn("Python", weak)

    def test_new_profile_format_claims(self):
        profile = Profile(
            mastered=[SkillClaim("Python", "basic", ["函数", "文件"])],
            learning=[SkillClaim("Java", "beginner", ["面向对象"])],
            targets=[TargetSkill("Redis", "high")])
        result = assess_skills(profile, _scan(PY_FILES), None, None)
        python = result.entries["Python"]
        self.assertEqual(python.claimed_level, "beginner")  # basic → beginner
        self.assertTrue(any("关注主题" in ev for ev in python.evidence))
        java = result.entries["Java"]
        self.assertTrue(any("正在学习" in ev for ev in java.evidence))
        redis = result.entries["Redis"]
        self.assertTrue(any("优先级 high" in ev for ev in redis.evidence))
        self.assertIsNone(redis.claimed_level)

    def test_noise_skills_filtered(self):
        scan = _scan([("a.py", ".py"), ("b.toml", ".toml"), ("c.yaml", ".yaml"),
                      ("note.txt", ".txt"), ("tpl.example", ".example")])
        result = assess_skills(None, scan, None, None)
        skills = set(result.entries.keys())
        self.assertIn("Python", skills)
        self.assertNotIn("TOML", skills)
        self.assertNotIn("YAML", skills)
        self.assertNotIn("Text", skills)
        self.assertNotIn("example", skills)

    def test_levels_order(self):
        self.assertEqual(LEVELS, ["beginner", "intermediate", "advanced", "expert"])
        self.assertEqual(SkillAssessmentEntry("x", None, [], None, "beginner", 0.5).to_dict()["final_level"], "beginner")
