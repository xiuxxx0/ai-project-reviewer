import json
import unittest

from apr.assessment.blindspot import BlindSpot, BlindSpotReport
from apr.assessment.quiz import Question, QuizResult
from apr.assessment.skill import SkillAssessment, SkillAssessmentEntry
from apr.coach import LearningPlan, PriorityItem, build_learning_plan
from apr.config import Config
from apr.digest import ProjectDigest, TechStack
from apr.evidence.base import EvidenceReport, FileVerdict
from apr.knowledge import KnowledgeGraph, KnowledgeNode, KnowledgeRelation
from apr.profile import Profile, SkillClaim, TargetSkill
from apr.scanner import scan_project
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


def _project():
    root = fixture_dir("knowledge")
    for i in range(3):
        (root / ("Cache%d.java" % i)).write_text(
            "public class Cache%d { private final RedisTemplate rt; }\n" % i,
            encoding="utf-8")
    scan = scan_project(root, Config().limits)
    digest = ProjectDigest(root=root, scan=scan,
                           stack=TechStack(languages={"Java": 3}, platforms=[], dependencies={}),
                           key_files=[], tree_text="")
    return root, scan, digest


class CoachTest(unittest.TestCase):
    def test_example_shape(self):
        root, scan, digest = _project()
        profile = Profile(learning=[SkillClaim("Redis", "beginner")],
                          targets=[TargetSkill("Spring Security", "high")])
        quiz = _quiz([("Redis", 45)])
        evidence = _evidence({"Cache0.java": (0.82, 0.8)})
        plan = build_learning_plan(profile=profile, scan=scan, digest=digest,
                                   quiz=quiz, evidence=evidence)
        d = plan.to_dict()
        self.assertEqual(set(d.keys()), {"priority", "next_projects"})
        self.assertGreaterEqual(len(d["priority"]), 1)
        redis = [p for p in d["priority"] if p["skill"] == "Redis"][0]
        self.assertEqual(set(redis.keys()), {"skill", "level", "reason", "action"})
        self.assertEqual(redis["level"], "high")
        joined = "\n".join(redis["reason"])
        self.assertIn("项目大量使用Redis", joined)
        self.assertIn("Quiz评分45", joined)
        self.assertIn("相关代码主要由AI生成", joined)
        self.assertIn("正在学习中", joined)
        actions = redis["action"]
        self.assertIn("学习缓存基础", actions)
        self.assertIn("实现 Redis 练习 Demo", actions)
        self.assertIn("独立重写项目中 Redis 的 AI 生成代码", actions)
        self.assertIn("Redis 实战练习", d["next_projects"])
        self.assertIn("Spring Security Demo 项目", d["next_projects"])

    def test_mock_inputs_no_recompute(self):
        """预传 assessment/graph/blind_spots（mock），scan=None 也能出计划。"""
        assessment = SkillAssessment(entries={
            "X": SkillAssessmentEntry(skill="X", claimed_level=None, evidence=[],
                                      quiz_score=40, final_level="beginner",
                                      confidence=0.5)})
        graph = KnowledgeGraph()
        graph.add_node(KnowledgeNode(id="file:a.java", kind="file", name="a.java"))
        graph.add_node(KnowledgeNode(id="tech:X", kind="tech", name="X"))
        graph.add_relation(KnowledgeRelation(source="file:a.java", target="tech:X",
                                             kind="uses", detail=""))
        blind_spots = BlindSpotReport(items=[
            BlindSpot(skill="X", risk_level="高风险盲区", score=100,
                      evidence=["e"], suggestions=["s"])])
        plan = build_learning_plan(assessment=assessment, graph=graph,
                                   blind_spots=blind_spots)
        self.assertEqual(len(plan.priority), 1)
        item = plan.priority[0]
        self.assertEqual(item.skill, "X")
        self.assertEqual(item.level, "high")
        self.assertTrue(any("项目使用X" in r for r in item.reason))
        self.assertTrue(any("技能档案尚未掌握" in r for r in item.reason))

    def test_ordering_by_risk(self):
        assessment = SkillAssessment(entries={
            "A": SkillAssessmentEntry(skill="A", claimed_level=None, evidence=[],
                                      quiz_score=None, final_level="beginner",
                                      confidence=0.5),
            "B": SkillAssessmentEntry(skill="B", claimed_level=None, evidence=[],
                                      quiz_score=None, final_level="beginner",
                                      confidence=0.5)})
        graph = KnowledgeGraph()
        for name in ("A", "B"):
            graph.add_node(KnowledgeNode(id="file:" + name + ".java", kind="file", name=name))
            graph.add_node(KnowledgeNode(id="tech:" + name, kind="tech", name=name))
            graph.add_relation(KnowledgeRelation(source="file:" + name + ".java",
                                                 target="tech:" + name, kind="uses"))
        blind_spots = BlindSpotReport(items=[
            BlindSpot(skill="A", risk_level="中风险盲区", score=50, evidence=[], suggestions=[]),
            BlindSpot(skill="B", risk_level="高风险盲区", score=90, evidence=[], suggestions=[]),
        ])
        plan = build_learning_plan(assessment=assessment, graph=graph,
                                   blind_spots=blind_spots)
        self.assertEqual([p.skill for p in plan.priority], ["B", "A"])

    def test_empty_inputs(self):
        plan = build_learning_plan()
        self.assertEqual(plan.priority, [])
        self.assertEqual(plan.next_projects, [])
        self.assertIn("暂无足够数据", plan.render_markdown())

    def test_json_serializable(self):
        root, scan, digest = _project()
        plan = build_learning_plan(profile=Profile(), scan=scan, digest=digest)
        data = json.loads(json.dumps(plan.to_dict(), ensure_ascii=False))
        self.assertIn("priority", data)
        self.assertIn("next_projects", data)

    def test_dataclasses(self):
        item = PriorityItem(skill="Redis", level="high", reason=["r"], action=["a"])
        self.assertEqual(item.to_dict()["skill"], "Redis")
        plan = LearningPlan(priority=[item], next_projects=["p"])
        self.assertEqual(plan.to_dict()["next_projects"], ["p"])
