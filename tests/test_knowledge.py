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
        self.assertIn("hub", content)               # 中心项目节点
        self.assertIn("重新布局", content)           # 重置按钮
        self.assertIn("#c7a5e6", content)           # Obsidian 风格连线色
        self.assertIn("wheel", content)             # 缩放交互
        self.assertIn("mouseenter", content)        # 悬停高亮

    def test_export_obsidian_canvas(self):
        root = fixture_dir("knowledge")
        _java_project(root)
        scan = _scan(root)
        graph = build_knowledge_graph(scan=scan, digest=_digest(root, scan),
                                      skill_assessment=_assessment())
        out = graph.export_obsidian_canvas(root / "knowledge_graph.canvas")
        self.assertTrue(out.is_file())
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        # 标题与列头
        texts = [n["text"] for n in data["nodes"]]
        self.assertTrue(any("RepoCourse · 项目知识图谱" in t for t in texts))
        for header in ("代码", "技术", "知识", "我的技能"):
            self.assertTrue(any(t == header for t in texts))
        # 统一尺寸（数据节点）
        data_nodes = [n for n in data["nodes"]
                      if n["id"] not in ("title", "hdr-file", "hdr-tech", "hdr-topic", "hdr-skill")]
        for n in data_nodes:
            self.assertEqual(n["width"], 260)
            self.assertEqual(n["height"], 80)
        # 固定 X 四列
        xs = {n["x"] for n in data_nodes}
        self.assertEqual(xs, {0, 400, 800, 1200})
        # 同列无重叠：固定 180 步进（80 高 + 100 间距）
        for x in (0, 400, 800, 1200):
            ys = sorted(n["y"] for n in data_nodes if n["x"] == x)
            for a, b in zip(ys, ys[1:]):
                self.assertGreaterEqual(b - a, 180)
        # 边不显示 label
        self.assertFalse(any("label" in e for e in data["edges"]))
        # 无孤立节点（除标题/列头）
        referenced = set()
        for e in data["edges"]:
            referenced.add(e["fromNode"])
            referenced.add(e["toNode"])
        for n in data_nodes:
            self.assertIn(n["id"], referenced)
        # 无重复节点 id
        ids = [n["id"] for n in data["nodes"]]
        self.assertEqual(len(ids), len(set(ids)))
        # 技术节点保留，技能节点含掌握程度
        self.assertGreaterEqual(len([n for n in data_nodes if n["color"] == "4"]), 1)
        skills = [n for n in data_nodes if "掌握程度" in n["text"]]
        self.assertGreaterEqual(len(skills), 1)

    def test_canvas_limits(self):
        root = fixture_dir("knowledge")
        for i in range(12):
            (root / ("f%02d.py" % i)).write_text(
                "from x import RedisTemplate\n", encoding="utf-8")
        scan = _scan(root)
        profile = Profile(learning=[SkillClaim(
            "Redis", "beginner", ["t1", "t2", "t3", "t4", "t5", "t6"])])
        graph = build_knowledge_graph(profile=profile, scan=scan,
                                      digest=_digest(root, scan),
                                      skill_assessment=_assessment())
        out = graph.export_obsidian_canvas(root / "knowledge_graph.canvas")
        data = json.loads(out.read_text(encoding="utf-8"))
        data_nodes = [n for n in data["nodes"]
                      if n["id"] not in ("title", "hdr-file", "hdr-tech", "hdr-topic", "hdr-skill")]
        self.assertLessEqual(len([n for n in data_nodes if n["x"] == 0]), 10)      # 文件 ≤10
        self.assertLessEqual(len([n for n in data_nodes if n["x"] == 400]), 15)    # 技术 ≤15
        self.assertLessEqual(len([n for n in data_nodes if n["x"] == 800]), 5)     # 每技术知识点 ≤5

    def test_canvas_barycenter_no_crossings(self):
        from apr.knowledge.knowledge import _canvas_crossings
        root = fixture_dir("knowledge")
        (root / "A.java").write_text("@Service\npublic class A {}\n", encoding="utf-8")   # → Spring
        (root / "B.py").write_text("from x import RedisTemplate\n", encoding="utf-8")      # → Redis
        scan = _scan(root)
        graph = build_knowledge_graph(scan=scan, digest=_digest(root, scan),
                                      skill_assessment=_assessment())
        out = graph.export_obsidian_canvas(root / "knowledge_graph.canvas")
        data = json.loads(out.read_text(encoding="utf-8"))
        data_nodes = [n for n in data["nodes"]
                      if n["id"] not in ("title", "hdr-file", "hdr-tech", "hdr-topic", "hdr-skill")]
        col = {0: [], 400: [], 800: [], 1200: []}
        for n in sorted(data_nodes, key=lambda n: n["y"]):
            col[n["x"]].append(n["id"])
        uses = [(e["fromNode"], e["toNode"]) for e in data["edges"]
                if e["fromNode"] in col[0] and e["toNode"] in col[400]]
        covers = [(e["fromNode"], e["toNode"]) for e in data["edges"]
                  if e["fromNode"] in col[400] and e["toNode"] in col[800]]
        assesses = [(e["fromNode"], e["toNode"]) for e in data["edges"]
                    if e["fromNode"] in col[800] and e["toNode"] in col[1200]]
        crossings = _canvas_crossings((col[0], col[400], col[800], col[1200]),
                                      uses, covers, assesses)
        self.assertEqual(crossings, 0)

    def test_export_obsidian_mindmap(self):
        root = fixture_dir("knowledge")
        _java_project(root)
        scan = _scan(root)
        graph = build_knowledge_graph(scan=scan, digest=_digest(root, scan),
                                      skill_assessment=_assessment())
        out = graph.export_obsidian_mindmap(root / "knowledge_graph-mindmap.md")
        self.assertTrue(out.is_file())
        content = out.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("mindmap"))
        self.assertIn("Redis", content)
        self.assertIn("缓存", content)
        self.assertIn("掌握40%", content)
        self.assertIn("UserService.java", content)

    def test_ai_contribution_in_graph(self):
        from apr.evidence.base import EvidenceReport, FileVerdict
        root = fixture_dir("knowledge")
        _java_project(root)
        scan = _scan(root)
        evidence = EvidenceReport(items=[], per_file={
            "UserService.java": FileVerdict(file="UserService.java", score=0.82,
                                            confidence=0.8, items=[])})
        graph = build_knowledge_graph(scan=scan, digest=_digest(root, scan),
                                      evidence=evidence, skill_assessment=_assessment())
        file_node = graph.nodes["file:UserService.java"]
        self.assertEqual(file_node.properties["ai_contribution"], 0.82)
        self.assertEqual(file_node.properties["ai_classification"], "AI 主导")
        tech_node = graph.nodes["tech:Redis"]
        self.assertEqual(tech_node.properties["avg_ai_contribution"], 0.82)

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
