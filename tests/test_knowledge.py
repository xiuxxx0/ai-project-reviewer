import json
import unittest
from pathlib import Path

from apr.assessment.skill import SkillAssessment, SkillAssessmentEntry
from apr.config import LimitsConfig
from apr.digest import ProjectDigest, TechStack
from apr.knowledge import (KnowledgeGraph, KnowledgeNode, KnowledgeRelation,
                           build_knowledge_graph, mastery_percent)
from apr.profile import Profile, SkillClaim
from apr.scanner import ScanResult, scan_project
from tests import fixture_dir


def _java_project(root: Path, extra_file: str | None = None):
    (root / "UserService.java").write_text(
        "import org.springframework.stereotype.Service;\n"
        "@Service\npublic class UserService {\n"
        "    private final RedisTemplate<String, String> redisTemplate;\n"
        "    public UserService(RedisTemplate<String, String> t) { this.redisTemplate = t; }\n}\n",
        encoding="utf-8")
    if extra_file:
        (root / extra_file).write_text(
            "public class CacheHelper { private final RedisTemplate rt; }\n", encoding="utf-8")


def _scan(root: Path):
    return scan_project(root, LimitsConfig())


def _digest(root: Path, scan):
    return ProjectDigest(root=root, scan=scan,
                         stack=TechStack(languages={"Java": 2}, platforms=[], dependencies={}),
                         key_files=[], tree_text="")


def _assessment(level="beginner", confidence=1.0):
    return SkillAssessment(entries={
        "Redis": SkillAssessmentEntry(skill="Redis", claimed_level="beginner",
                                      evidence=["档案自评"], quiz_score=None,
                                      final_level=level, confidence=confidence),
    })


class KnowledgeTest(unittest.TestCase):
    def test_java_redis_example(self):
        root = fixture_dir("knowledge")
        _java_project(root)
        scan = _scan(root)
        graph = build_knowledge_graph(profile=None, scan=scan,
                                      digest=_digest(root, scan),
                                      skill_assessment=_assessment())
        # 技术节点
        self.assertIn("tech:Redis", graph.nodes)
        self.assertIn("tech:Spring", graph.nodes)   # @Service 命中
        # 文件节点 + uses 关系
        self.assertIn("file:UserService.java", graph.nodes)
        uses = [r for r in graph.relations
                if r.source == "file:UserService.java" and r.target == "tech:Redis"]
        self.assertEqual(len(uses), 1)
        self.assertIn("RedisTemplate", uses[0].detail)
        # 知识点节点 + covers 关系
        for topic in ("缓存", "Key 设计", "过期策略"):
            self.assertIn("topic:" + topic, graph.nodes)
        covers = [r for r in graph.relations
                  if r.source == "tech:Redis" and r.kind == "covers"]
        self.assertEqual(len(covers), 4)
        # 技能节点：掌握程度 40%
        skill = graph.nodes["skill:Redis"]
        self.assertEqual(skill.properties["mastery_percent"], 40)
        self.assertEqual(skill.properties["level"], "beginner")
        assessed = [r for r in graph.relations
                    if r.source == "tech:Redis" and r.target == "skill:Redis"
                    and r.kind == "assessed"]
        self.assertEqual(len(assessed), 1)
        self.assertIn("40%", assessed[0].detail)

    def test_mastery_uses_confidence(self):
        entry = SkillAssessmentEntry(skill="Redis", claimed_level=None, evidence=[],
                                     quiz_score=None, final_level="beginner",
                                     confidence=0.5)
        self.assertEqual(mastery_percent(entry), 20)   # 40 × 0.5
        entry.final_level = "advanced"
        self.assertEqual(mastery_percent(entry), 40)   # 80 × 0.5

    def test_dedupe_tech_nodes(self):
        root = fixture_dir("knowledge")
        _java_project(root, extra_file="CacheHelper.java")
        scan = _scan(root)
        graph = build_knowledge_graph(scan=scan, digest=_digest(root, scan))
        self.assertEqual(len([n for n in graph.nodes.values() if n.kind == "tech"
                              and n.name == "Redis"]), 1)
        uses = [r for r in graph.relations if r.target == "tech:Redis" and r.kind == "uses"]
        self.assertEqual(len(uses), 2)

    def test_profile_topics_and_claims(self):
        root = fixture_dir("knowledge")
        _java_project(root)
        scan = _scan(root)
        profile = Profile(learning=[SkillClaim("Redis", "beginner", ["缓存"])])
        graph = build_knowledge_graph(profile=profile, scan=scan,
                                      digest=_digest(root, scan), skill_assessment=_assessment())
        self.assertIn("topic:缓存", graph.nodes)
        self.assertTrue(graph.nodes["topic:缓存"].properties.get("from_profile"))
        claims = [r for r in graph.relations if r.kind == "user-claims"]
        self.assertEqual(len(claims), 1)

    def test_save_json_round_trip(self):
        root = fixture_dir("knowledge")
        _java_project(root)
        scan = _scan(root)
        graph = build_knowledge_graph(scan=scan, digest=_digest(root, scan),
                                      skill_assessment=_assessment())
        out = graph.save(root / "knowledge_graph.json")
        self.assertTrue(out.is_file())
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 1)
        self.assertEqual(len(data["nodes"]), len(graph.nodes))
        self.assertEqual(len(data["relations"]), len(graph.relations))
        ids = {n["id"] for n in data["nodes"]}
        self.assertIn("tech:Redis", ids)
        self.assertIn("skill:Redis", ids)

    def test_empty_inputs(self):
        graph = build_knowledge_graph()
        self.assertEqual(graph.nodes, {})
        self.assertEqual(graph.relations, [])
        self.assertEqual(graph.to_dict()["stats"]["total_nodes"], 0)

    def test_export_html(self):
        root = fixture_dir("knowledge")
        _java_project(root)
        scan = _scan(root)
        graph = build_knowledge_graph(scan=scan, digest=_digest(root, scan),
                                      skill_assessment=_assessment())
        out = graph.export_html(root / "knowledge_graph.html")
        self.assertTrue(out.is_file())
        content = out.read_text(encoding="utf-8")
        self.assertIn("<svg", content)
        self.assertIn("tech:Redis", content)
        self.assertIn("DATA.project", content)

    def test_counts(self):
        g = KnowledgeGraph()
        g.add_node(KnowledgeNode(id="t:1", kind="tech", name="X"))
        g.add_node(KnowledgeNode(id="s:1", kind="skill", name="X"))
        g.add_relation(KnowledgeRelation(source="t:1", target="s:1", kind="assessed"))
        c = g.counts()
        self.assertEqual(c["total_nodes"], 2)
        self.assertEqual(c["tech"], 1)
        self.assertEqual(c["skill"], 1)
        self.assertEqual(c["total_relations"], 1)
