import json
import unittest

from apr.assessment.blindspot import BlindSpot, BlindSpotReport
from apr.assessment.skill import SkillAssessment, SkillAssessmentEntry
from apr.coach.planner import LearningPlan, PriorityItem
from apr.config import Config
from apr.digest import ProjectDigest, TechStack
from apr.knowledge import build_knowledge_graph
from apr.knowledge.learning_canvas import learning_tech_status
from apr.profile import Profile, SkillClaim
from apr.scanner import scan_project
from tests import fixture_dir


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


def _assessment():
    return SkillAssessment(entries={
        "Redis": SkillAssessmentEntry(skill="Redis", claimed_level="beginner",
                                      evidence=[], quiz_score=40,
                                      final_level="beginner", confidence=0.6),
        "Java": SkillAssessmentEntry(skill="Java", claimed_level="advanced",
                                     evidence=[], quiz_score=None,
                                     final_level="advanced", confidence=0.8),
    })


def _blind_spots():
    return BlindSpotReport(items=[
        BlindSpot(skill="Redis", risk_level="高风险盲区", score=90,
                  evidence=[], suggestions=[]),
    ])


def _plan():
    return LearningPlan(priority=[
        PriorityItem(skill="Redis", level="high",
                     reason=["项目使用Redis"], action=["学习 缓存 基础", "实现 Demo"]),
        PriorityItem(skill="MySQL", level="medium",
                     reason=[""], action=["学习 表设计 基础"]),
    ])


class LearningCanvasTest(unittest.TestCase):
    def test_structure_and_headers(self):
        root, scan, digest = _project()
        profile = Profile(learning=[SkillClaim("Redis", "beginner")])
        graph = build_knowledge_graph(profile=profile, scan=scan, digest=digest,
                                      skill_assessment=_assessment())
        out = graph.export_learning_canvas(root / "knowledge_learning.canvas",
                                          assessment=_assessment(),
                                          blind_spots=_blind_spots(), plan=_plan())
        self.assertTrue(out.is_file())
        data = json.loads(out.read_text(encoding="utf-8"))
        texts = [n["text"] for n in data["nodes"]]
        self.assertTrue(any("学习技能树" in t for t in texts))
        for header in ("我做了什么", "涉及技术", "我学到了什么", "下一步学习"):
            self.assertTrue(any(t == header for t in texts))

    def test_no_file_nodes_no_internal_relations(self):
        root, scan, digest = _project()
        profile = Profile(learning=[SkillClaim("Redis", "beginner")])
        graph = build_knowledge_graph(profile=profile, scan=scan, digest=digest,
                                      skill_assessment=_assessment())
        out = graph.export_learning_canvas(root / "knowledge_learning.canvas",
                                          assessment=_assessment(),
                                          blind_spots=_blind_spots(), plan=_plan())
        data = json.loads(out.read_text(encoding="utf-8"))
        ids = [n["id"] for n in data["nodes"]]
        self.assertFalse(any(i.startswith("file:") for i in ids))
        for e in data["edges"]:
            self.assertNotIn("written-in", e.get("label", ""))

    def test_status_colors(self):
        root, scan, digest = _project()
        profile = Profile(learning=[SkillClaim("Redis", "beginner")])
        graph = build_knowledge_graph(profile=profile, scan=scan, digest=digest,
                                      skill_assessment=_assessment())
        out = graph.export_learning_canvas(root / "knowledge_learning.canvas",
                                          assessment=_assessment(),
                                          blind_spots=_blind_spots(), plan=_plan())
        data = json.loads(out.read_text(encoding="utf-8"))
        # Redis：高风险盲区 → 待学习（红 1）
        redis = [n for n in data["nodes"] if "Redis" in n["text"]][0]
        self.assertEqual(redis["color"], "1")
        self.assertIn("待学习", redis["text"])

    def test_limits(self):
        root, scan, digest = _project()
        profile = Profile(learning=[SkillClaim("Redis", "beginner")])
        graph = build_knowledge_graph(profile=profile, scan=scan, digest=digest,
                                      skill_assessment=_assessment())
        plan = LearningPlan(priority=[
            PriorityItem(skill="S%d" % i, level="medium", reason=[], action=["a"])
            for i in range(15)])
        out = graph.export_learning_canvas(root / "knowledge_learning.canvas",
                                          assessment=_assessment(),
                                          blind_spots=_blind_spots(), plan=plan)
        data = json.loads(out.read_text(encoding="utf-8"))
        techs = [n for n in data["nodes"] if n["x"] == 680 and n["id"].startswith("t")]
        tasks = [n for n in data["nodes"] if n["x"] == 1420 and n["id"].startswith("x")]
        topics = [n for n in data["nodes"] if n["x"] == 1040 and n["id"].startswith("k")]
        self.assertLessEqual(len(techs), 10)
        self.assertLessEqual(len(tasks), 10)
        self.assertLessEqual(len(topics), 20)

    def test_status_helper(self):
        root, scan, digest = _project()
        graph = build_knowledge_graph(scan=scan, digest=digest,
                                      skill_assessment=_assessment())
        st = learning_tech_status(graph, "Java", _assessment(), _blind_spots())
        self.assertEqual(st, "已掌握")
        st = learning_tech_status(graph, "Redis", _assessment(), _blind_spots())
        self.assertEqual(st, "待学习")

    def test_cli_graph_exports_learning_canvas(self):
        from apr.cli import main
        root, scan, digest = _project()
        rc = main(["graph", str(root)])
        self.assertEqual(rc, 0)
        self.assertTrue((root / "knowledge_learning.canvas").is_file())
        self.assertTrue((root / "knowledge_graph.canvas").is_file())  # 原 Canvas 仍在
