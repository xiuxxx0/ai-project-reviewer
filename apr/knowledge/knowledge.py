"""Knowledge Graph 基础版（JSON + dataclass，无外部数据库）。

图层关系：
  文件(file) --uses--> 技术(tech) --covers--> 知识点(topic)
  技术(tech) --assessed--> 用户技能(skill，含掌握程度百分比)

输出：knowledge_graph.json（节点 + 关系标准图结构）。
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..assessment.skill import SkillAssessment
from ..digest import EXT_LANGUAGE, ProjectDigest
from ..profile import Profile
from ..scanner import ScanResult

# 等级 → 掌握程度基线百分比（beginner=40%，与设计示例一致）
LEVEL_PERCENT = {"beginner": 40, "intermediate": 60, "advanced": 80, "expert": 95}

# 文件名标记：技术 → 匹配的文件名
NAME_MARKERS = {
    "Docker": ["dockerfile", "docker-compose.yml", "docker-compose.yaml"],
    "Maven": ["pom.xml"],
    "Gradle": ["build.gradle", "build.gradle.kts"],
}

# 代码内容签名：技术 → 特征标识符（Java 生态为主，可扩展）
CONTENT_SIGNATURES = {
    "Redis": ["RedisTemplate", "StringRedisTemplate", "Redisson", "redisTemplate",
              "@Cacheable", "@CacheEvict", "RedisConnectionFactory", "jedis",
              "lettuce", "import redis"],
    "MySQL": ["JdbcTemplate", "DataSource", "jdbc:mysql", "MyBatis", "@Mapper",
              "@Table(", "EntityManager", "@Entity", "mysql-connector", "pymysql",
              "sqlalchemy", "@Query("],
    "Spring": ["@RestController", "@Controller", "@Service", "@Autowired", "@Component",
               "ApplicationContext", "@Transactional", "SpringApplication",
               "@Bean", "@Configuration"],
    "Spring Boot": ["@SpringBootApplication", "spring-boot-starter", "SpringBootApplication"],
    "MyBatis": ["SqlSessionFactory", "mybatis", "@Mapper", "Mapper.xml"],
    "MongoDB": ["MongoTemplate", "mongodb", "pymongo", "MongoRepository", "mongoengine"],
    "Kafka": ["KafkaTemplate", "@KafkaListener", "KafkaProducer", "kafka-python"],
    "Elasticsearch": ["ElasticsearchRestTemplate", "RestHighLevelClient", "elasticsearch"],
    "JWT": ["Jwt", "jwt", "JsonWebToken", "JJWT", "@PreAuthorize", "jose"],
    "REST API": ["@GetMapping", "@PostMapping", "@PutMapping", "@DeleteMapping",
                 "@RequestMapping", "RestController", "fastapi", "FastAPI"],
    "Vue": ["createApp", "<script setup>", "ref(", "reactive(", "useRouter", "defineComponent"],
    "React": ["useState", "useEffect", "ReactDOM", "createRoot", "jsx"],
    "Django": ["django", "settings.py", "urlpatterns", "ModelAdmin"],
    "FastAPI": ["FastAPI(", "fastapi", "APIRouter", "Depends("],
}

# 技术 → 默认核心知识点（用于生成 topic 节点）
TECH_TOPICS = {
    "Redis": ["缓存", "Key 设计", "过期策略", "缓存穿透/击穿/雪崩"],
    "MySQL": ["表设计", "索引", "SQL 优化", "事务"],
    "Spring": ["IoC/DI", "AOP", "Bean 生命周期", "事务管理"],
    "Spring Boot": ["自动配置", "起步依赖", "配置管理", "Actuator"],
    "MyBatis": ["SQL 映射", "动态 SQL", "一级/二级缓存"],
    "MongoDB": ["文档模型", "聚合查询", "索引"],
    "Kafka": ["生产者/消费者", "分区与偏移", "消息可靠性"],
    "Elasticsearch": ["倒排索引", "DSL 查询", "分词"],
    "JWT": ["令牌结构", "签名验证", "刷新机制"],
    "REST API": ["资源设计", "HTTP 语义", "状态码", "分页"],
    "Vue": ["响应式", "组件", "路由", "状态管理"],
    "React": ["组件", "Hooks", "虚拟 DOM", "状态管理"],
    "Docker": ["镜像", "容器", "Dockerfile", "网络与卷"],
    "Django": ["MTV 架构", "ORM", "中间件", "Admin"],
    "FastAPI": ["路由", "依赖注入", "Pydantic", "异步"],
}


@dataclass
class KnowledgeNode:
    id: str
    kind: str                    # file | tech | topic | skill
    name: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "name": self.name,
                "properties": self.properties}


@dataclass
class KnowledgeRelation:
    source: str
    target: str
    kind: str                    # uses | covers | assessed | user-claims | written-in
    detail: str = ""
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {"source": self.source, "target": self.target, "kind": self.kind,
                "detail": self.detail, "confidence": self.confidence}


@dataclass
class KnowledgeGraph:
    nodes: dict[str, KnowledgeNode] = field(default_factory=dict)
    relations: list[KnowledgeRelation] = field(default_factory=list)
    project: str = ""
    generated_at: str = ""

    def add_node(self, node: KnowledgeNode) -> KnowledgeNode:
        existing = self.nodes.get(node.id)
        if existing is None:
            self.nodes[node.id] = node
            return node
        existing.properties.update(node.properties)
        return existing

    def add_relation(self, relation: KnowledgeRelation) -> None:
        key = (relation.source, relation.target, relation.kind)
        if not any((r.source, r.target, r.kind) == key for r in self.relations):
            self.relations.append(relation)

    def counts(self) -> dict:
        c = Counter(n.kind for n in self.nodes.values())
        return {"total_nodes": len(self.nodes), "total_relations": len(self.relations),
                "file": c["file"], "tech": c["tech"], "topic": c["topic"],
                "skill": c["skill"]}

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "project": self.project,
            "generated_at": self.generated_at,
            "stats": self.counts(),
            "nodes": [n.to_dict() for n in sorted(self.nodes.values(), key=lambda n: n.id)],
            "relations": [r.to_dict() for r in self.relations],
        }

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
                        encoding="utf-8")
        return path

    def export_html(self, path: Path) -> Path:
        """导出零依赖的交互式可视化 HTML（内嵌数据 + 原生 JS 力导向布局）。"""
        data = json.dumps(self.to_dict(), ensure_ascii=False).replace("</", "<\\/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_HTML_TEMPLATE.replace("__DATA__", data), encoding="utf-8")
        return path

    def export_obsidian_canvas(self, path: Path) -> Path:
        """导出 Obsidian Canvas（.canvas）：分层排布的可视化画布，直接拖入 Vault 使用。"""
        layer_x = {"file": 0, "tech": 460, "topic": 920, "skill": 1380}
        layer_color = {"file": "5", "tech": "4", "topic": "3", "skill": "6"}
        canvas_nodes = []
        id_map: dict[str, str] = {}
        for i, node in enumerate(sorted(self.nodes.values(), key=lambda n: n.id)):
            id_map[node.id] = "n" + str(i + 1)
        y_cursor = {k: 40 for k in layer_x}
        for node in sorted(self.nodes.values(), key=lambda n: (n.kind, n.id)):
            if node.kind == "skill":
                mastery = node.properties.get("mastery_percent")
                text = "**" + node.name + "**\n掌握程度 " + (str(mastery) + "%" if mastery is not None else "未评估")
            elif node.kind == "tech":
                text = "**" + node.name + "**"
                if node.properties.get("file_count"):
                    text += "\n文件数 " + str(node.properties["file_count"])
            else:
                text = node.name
            lines = text.count("\n") + 1
            height = 20 * lines + 26
            x = layer_x.get(node.kind, 0)
            y = y_cursor.get(node.kind, 40)
            y_cursor[node.kind] = y + height + 24
            canvas_nodes.append({
                "id": id_map[node.id], "type": "text", "text": text,
                "x": x, "y": y, "width": 280, "height": height,
                "color": layer_color.get(node.kind, "1"),
            })
        canvas_edges = []
        for i, rel in enumerate(self.relations):
            if rel.source not in id_map or rel.target not in id_map:
                continue
            canvas_edges.append({
                "id": "e" + str(i + 1),
                "fromNode": id_map[rel.source], "toNode": id_map[rel.target],
                "fromSide": "right", "toSide": "left",
                "label": rel.kind,
                "color": "2",
            })
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"nodes": canvas_nodes, "edges": canvas_edges},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def export_obsidian_mindmap(self, path: Path) -> Path:
        """导出 Mermaid mindmap 的 Markdown（.md）：Obsidian 原生渲染为思维导图。"""
        lines = ["mindmap", "  root((" + _mm_safe(self.project or "项目") + "))"]
        tech_nodes = sorted([n for n in self.nodes.values() if n.kind == "tech"],
                            key=lambda n: n.name)
        for tech in tech_nodes:
            lines.append("    " + _mm_safe(tech.name))
            file_ids = sorted({r.source for r in self.relations
                               if r.target == tech.id and r.kind == "uses"})
            for fid in file_ids:
                node = self.nodes.get(fid)
                lines.append("      " + _mm_safe(node.name if node else fid))
            topic_ids = sorted({r.target for r in self.relations
                                if r.source == tech.id and r.kind == "covers"})
            for tid in topic_ids:
                node = self.nodes.get(tid)
                lines.append("      " + _mm_safe(node.name if node else tid))
            skill_ids = sorted({r.target for r in self.relations
                                    if r.source == tech.id
                                    and r.target.startswith("skill:")})
            for sid in skill_ids:
                node = self.nodes.get(sid)
                if node is None:
                    continue
                mastery = node.properties.get("mastery_percent")
                label = node.name + (" 掌握" + str(mastery) + "%" if mastery is not None else "")
                lines.append("      " + _mm_safe(label))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def render_text(self) -> str:
        c = self.counts()
        lines = [
            "知识图谱概览：",
            f"- 节点 {c['total_nodes']}：文件 {c['file']} / 技术 {c['tech']} / "
            f"知识点 {c['topic']} / 技能 {c['skill']}",
            f"- 关系 {c['total_relations']}",
            "",
            "技能掌握：",
        ]
        for node in self.nodes.values():
            if node.kind == "skill":
                m = node.properties.get("mastery_percent")
                lines.append(f"- {node.name}：掌握程度 {m}%"
                             + (f"（判定 {node.properties.get('level')}）"
                                if node.properties.get("level") else ""))
        return "\n".join(lines)


def mastery_percent(entry) -> int | None:
    """SkillAssessment 条目 → 掌握程度百分比（等级基线 × 置信度）。"""
    base = LEVEL_PERCENT.get(entry.final_level)
    if base is None:
        return None
    return int(round(base * entry.confidence))


def _detect_tech_usage(scan: ScanResult | None) -> dict:
    """返回 {技术: [{"file": rel, "hits": [命中特征]}]}。"""
    usage: dict = {}
    if scan is None:
        return usage
    for f in scan.files:
        if not f.is_text or f.too_big:
            continue
        base = Path(f.rel).name.lower()
        for tech, names in NAME_MARKERS.items():
            if base in names:
                usage.setdefault(tech, []).append({"file": f.rel, "hits": [base]})
        try:
            text = Path(f.abs).read_text(encoding="utf-8", errors="replace")[:200000]
        except OSError:
            continue
        for tech, patterns in CONTENT_SIGNATURES.items():
            hits = [p for p in patterns if p in text]
            if hits:
                usage.setdefault(tech, []).append({"file": f.rel, "hits": hits[:5]})
    return usage


def build_knowledge_graph(profile: Profile | None = None,
                          scan: ScanResult | None = None,
                          digest: ProjectDigest | None = None,
                          evidence=None,
                          skill_assessment: SkillAssessment | None = None) -> KnowledgeGraph:
    """把 项目代码 → 技术栈 → 知识点 → 用户技能 组织成关联图。

    evidence 参数保留给后续扩展（如把 AI 贡献证据作为节点属性）。
    """
    graph = KnowledgeGraph(
        project=scan.root.name if scan else "",
        generated_at=datetime.now().isoformat(timespec="seconds"))

    usage = _detect_tech_usage(scan)
    language_counts: dict = {}
    if digest is not None:
        language_counts = {k.split("/")[0]: v for k, v in digest.stack.languages.items()}

    # 1) 技术节点：代码签名命中的技术 + 语言统计
    for tech in sorted(set(usage) | set(language_counts)):
        props: dict = {}
        if tech in language_counts:
            props["file_count"] = language_counts[tech]
        graph.add_node(KnowledgeNode(id="tech:" + tech, kind="tech", name=tech,
                                     properties=props))

    # 2) 文件节点 + uses / written-in 关系
    for tech, entries in sorted(usage.items()):
        tech_id = "tech:" + tech
        for entry in entries:
            file_id = "file:" + entry["file"]
            graph.add_node(KnowledgeNode(id=file_id, kind="file", name=entry["file"]))
            graph.add_relation(KnowledgeRelation(
                source=file_id, target=tech_id, kind="uses",
                detail="检测到 " + "、".join(entry["hits"]), confidence=0.9))
            ext = Path(entry["file"]).suffix.lower()
            lang = EXT_LANGUAGE.get(ext, "").split("/")[0]
            if lang and lang in language_counts:
                graph.add_relation(KnowledgeRelation(
                    source=file_id, target="tech:" + lang, kind="written-in",
                    detail="语言归属"))

    # 3) 知识点节点：默认映射 + 档案主题
    for tech in sorted(usage):
        tech_id = "tech:" + tech
        for topic in TECH_TOPICS.get(tech, []):
            topic_id = "topic:" + topic
            graph.add_node(KnowledgeNode(id=topic_id, kind="topic", name=topic))
            graph.add_relation(KnowledgeRelation(
                source=tech_id, target=topic_id, kind="covers",
                detail=f"{tech} 核心知识点"))
    if profile is not None:
        for claim in profile.all_claims():
            tech_id = "tech:" + claim.name
            if tech_id not in graph.nodes:
                graph.add_node(KnowledgeNode(
                    id=tech_id, kind="tech", name=claim.name,
                    properties={"from_profile": True}))
            skill_id = "skill:" + claim.name
            graph.add_node(KnowledgeNode(
                id=skill_id, kind="skill", name=claim.name,
                properties={"claimed_level": claim.level}))
            graph.add_relation(KnowledgeRelation(
                source=tech_id, target=skill_id, kind="user-claims",
                detail=f"档案自评 {claim.level or '未标注'}"))
            for topic in claim.topics:
                topic_id = "topic:" + topic
                graph.add_node(KnowledgeNode(
                    id=topic_id, kind="topic", name=topic,
                    properties={"from_profile": True}))
                graph.add_relation(KnowledgeRelation(
                    source=tech_id, target=topic_id, kind="covers",
                    detail="来自技能档案主题"))

    # 4) 技能节点：Skill Assessment 结果（含掌握程度）
    if skill_assessment is not None:
        for entry in skill_assessment.entries.values():
            skill_id = "skill:" + entry.skill
            mastery = mastery_percent(entry)
            graph.add_node(KnowledgeNode(
                id=skill_id, kind="skill", name=entry.skill,
                properties={
                    "level": entry.final_level,
                    "confidence": entry.confidence,
                    "claimed_level": entry.claimed_level,
                    "mastery_percent": mastery,
                }))
            tech_id = "tech:" + entry.skill
            if tech_id in graph.nodes and mastery is not None:
                graph.add_relation(KnowledgeRelation(
                    source=tech_id, target=skill_id, kind="assessed",
                    detail=f"掌握程度 {mastery}%（判定 {entry.final_level}，"
                           f"置信度 {entry.confidence:.0%}）",
                    confidence=entry.confidence))
    return graph


def _mm_safe(label: str) -> str:
    """Mermaid mindmap 节点标签清洗：去掉会引起语法错误的字符。"""
    for ch in ("(", ")", "[", "]", "{", "}", "\"", "#", "<", ">", chr(96)):
        label = label.replace(ch, " ")
    return " ".join(label.split()) or "未命名"


# 零依赖可视化模板：内嵌数据 + 原生 JS 力导向布局（无 CDN、无第三方库）
_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Knowledge Graph</title>
<style>
body { background:#0f1420; color:#e6e9f0; font-family:"Segoe UI","Microsoft YaHei",sans-serif; margin:0; }
header { padding:14px 20px; background:#1a2130; border-bottom:1px solid #2a3448; }
h1 { font-size:18px; margin:0 0 6px 0; }
.legend span { margin-right:16px; font-size:12px; }
.legend i { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:4px; }
svg { display:block; margin:0 auto; }
.edge { stroke:#3a465e; stroke-opacity:.55; stroke-width:1; }
.node { cursor:pointer; }
.node circle { stroke:#0f1420; stroke-width:1.5; }
#tip { position:fixed; background:#1a2130; border:1px solid #2a3448; border-radius:8px;
       padding:10px 12px; font-size:12px; line-height:1.7; max-width:360px; display:none; z-index:9; }
#tip b { color:#7ab3ff; }
.hint { color:#8b93a7; font-size:12px; margin-top:4px; }
</style>
</head>
<body>
<header>
<h1>Knowledge Graph — <span id="stats"></span></h1>
<div class="legend">
<span><i style="background:#60a5fa"></i>文件</span>
<span><i style="background:#34d399"></i>技术</span>
<span><i style="background:#fbbf24"></i>知识点</span>
<span><i style="background:#a78bfa"></i>技能（掌握程度 %）</span>
</div>
<div class="hint">拖动节点调整布局 ｜ 点击节点查看属性与关联 ｜ 数据来自 knowledge_graph.json</div>
</header>
<svg id="svg" width="1280" height="780"></svg>
<div id="tip"></div>
<script>
var DATA = __DATA__;
var COLORS = { file:'#60a5fa', tech:'#34d399', topic:'#fbbf24', skill:'#a78bfa' };
var W = 1280, H = 780;
var nodes = DATA.nodes, edges = DATA.relations;
var pos = {}, idMap = {};
nodes.forEach(function (n, i) {
  idMap[n.id] = n;
  var ang = (i / Math.max(1, nodes.length)) * Math.PI * 2;
  var r = Math.min(W, H) / 2.7;
  pos[n.id] = { x: W/2 + r * Math.cos(ang), y: H/2 + r * Math.sin(ang) };
});
var disp = {};
for (var iter = 0; iter < 500; iter++) {
  var ids = Object.keys(pos);
  ids.forEach(function (k) { disp[k] = { x:0, y:0 }; });
  for (var i = 0; i < ids.length; i++) {
    for (var j = i + 1; j < ids.length; j++) {
      var a = pos[ids[i]], b = pos[ids[j]];
      var dx = a.x - b.x, dy = a.y - b.y;
      var d2 = dx * dx + dy * dy || 1;
      var f = 9000 / d2, d = Math.sqrt(d2);
      disp[ids[i]].x += dx / d * f; disp[ids[i]].y += dy / d * f;
      disp[ids[j]].x -= dx / d * f; disp[ids[j]].y -= dy / d * f;
    }
  }
  edges.forEach(function (e) {
    if (!pos[e.source] || !pos[e.target]) return;
    var dx = pos[e.target].x - pos[e.source].x, dy = pos[e.target].y - pos[e.source].y;
    var d = Math.sqrt(dx * dx + dy * dy) || 1, f = d * 0.0025;
    disp[e.source].x += dx / d * f; disp[e.source].y += dy / d * f;
    disp[e.target].x -= dx / d * f; disp[e.target].y -= dy / d * f;
  });
  ids.forEach(function (k) {
    pos[k].x = Math.max(60, Math.min(W - 60, pos[k].x + disp[k].x * 0.05));
    pos[k].y = Math.max(60, Math.min(H - 60, pos[k].y + disp[k].y * 0.05));
  });
}
var svg = document.getElementById('svg');
svg.innerHTML = '';
edges.forEach(function (e) {
  if (!pos[e.source] || !pos[e.target]) return;
  var line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
  line.setAttribute('x1', pos[e.source].x); line.setAttribute('y1', pos[e.source].y);
  line.setAttribute('x2', pos[e.target].x); line.setAttribute('y2', pos[e.target].y);
  line.setAttribute('class', 'edge');
  svg.appendChild(line);
});
nodes.forEach(function (n) {
  var g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  g.setAttribute('transform', 'translate(' + pos[n.id].x + ',' + pos[n.id].y + ')');
  var c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  c.setAttribute('r', n.kind === 'tech' ? 10 : (n.kind === 'skill' ? 12 : 6));
  c.setAttribute('fill', COLORS[n.kind] || '#888');
  c.setAttribute('class', 'node');
  g.appendChild(c);
  var t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  var label = n.name;
  if (label.length > 16) label = label.slice(0, 15) + '…';
  if (n.kind === 'skill' && n.properties && n.properties.mastery_percent !== null
      && n.properties.mastery_percent !== undefined) {
    label = label + ' ' + n.properties.mastery_percent + '%';
  }
  t.setAttribute('y', n.kind === 'skill' ? 26 : 16);
  t.setAttribute('text-anchor', 'middle');
  t.setAttribute('font-size', n.kind === 'tech' ? '11' : '9');
  t.setAttribute('fill', '#cdd5e4');
  t.textContent = label;
  g.appendChild(t);
  g.addEventListener('click', function (ev) {
    var tip = document.getElementById('tip');
    var html = '<b>' + n.name + '</b>（' + n.kind + '）';
    var props = n.properties || {};
    Object.keys(props).forEach(function (k) {
      html += '<br>' + k + ': ' + props[k];
    });
    var rels = edges.filter(function (r) { return r.source === n.id || r.target === n.id; });
    if (rels.length) {
      html += '<br><br>关联（' + rels.length + '）：';
      rels.slice(0, 8).forEach(function (r) {
        var other = r.source === n.id ? r.target : r.source;
        var otherNode = idMap[other];
        html += '<br>· ' + (otherNode ? otherNode.name : other) + '（' + r.kind + '）';
      });
    }
    tip.innerHTML = html;
    tip.style.display = 'block';
    tip.style.left = (ev.clientX + 14) + 'px';
    tip.style.top = (ev.clientY + 14) + 'px';
  });
  svg.appendChild(g);
});
document.getElementById('stats').textContent = '节点 ' + nodes.length + ' / 关系 '
  + edges.length + '（' + DATA.project + '，' + DATA.generated_at + '）';
</script>
</body>
</html>
"""
