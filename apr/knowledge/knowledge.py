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
        """导出 Obsidian Canvas（.canvas）：严格四列分层布局。

        列：文件(0) → 技术(400) → 知识点(800) → 技能(1200)；
        统一节点尺寸、固定垂直间距、按关联关系排序（barycenter）最小化连线交叉；
        只保留有真实关联的节点，边不显示重复 label。
        """
        # 1) 从数据模型收集真实关系（数据模型不变）
        uses = []          # file -> tech
        covers = []        # tech -> topic
        assessed = []      # tech -> skill
        for rel in self.relations:
            src, dst = self.nodes.get(rel.source), self.nodes.get(rel.target)
            if src is None or dst is None:
                continue
            if rel.kind == "uses" and src.kind == "file" and dst.kind == "tech":
                uses.append((rel.source, rel.target))
            elif rel.kind == "covers" and src.kind == "tech" and dst.kind == "topic":
                covers.append((rel.source, rel.target))
            elif rel.kind == "assessed" and src.kind == "tech" and dst.kind == "skill":
                assessed.append((rel.source, rel.target))
        uses = sorted(set(uses))
        covers = sorted(set(covers))
        assessed = sorted(set(assessed))

        # 2) 数量限制与过滤（无关联节点一律不显示）
        file_count = {}
        for f, _ in uses:
            file_count[f] = file_count.get(f, 0) + 1
        files = sorted(file_count, key=lambda f: (-file_count[f], f))[:MAX_FILES]
        file_set = set(files)

        tech_count = {}
        for f, t in uses:
            if f in file_set:
                tech_count[t] = tech_count.get(t, 0) + 1
        techs = sorted(tech_count, key=lambda t: (-tech_count[t], t))[:MAX_TECHS]
        tech_set = set(techs)

        kept_topics: list[tuple[str, str]] = []
        seen_topics: set[str] = set()
        per_tech: dict[str, int] = {}
        for tech, topic in covers:  # 按模型顺序：默认知识点在前、档案主题在后
            if tech not in tech_set or topic in seen_topics:
                continue
            if per_tech.get(tech, 0) >= MAX_TOPICS_PER_TECH:
                continue
            seen_topics.add(topic)
            per_tech[tech] = per_tech.get(tech, 0) + 1
            kept_topics.append((tech, topic))
        topic_set = {t for _, t in kept_topics}
        tech_topics: dict[str, list[str]] = {}
        for tech, topic in kept_topics:
            tech_topics.setdefault(tech, []).append(topic)

        # 技能：只保留与展示技术有 assessed 关系、且经知识点承接的
        tech_skills: dict[str, list[str]] = {}
        for tech, skill in assessed:
            if tech in tech_set:
                tech_skills.setdefault(tech, []).append(skill)
        assesses: list[tuple[str, str]] = []
        for tech, skill_list in tech_skills.items():
            for topic in tech_topics.get(tech, []):
                for skill in sorted(set(skill_list)):
                    assesses.append((topic, skill))
        assesses = sorted(set(assesses))
        skill_set = {s for _, s in assesses}
        skills = sorted(skill_set)

        # 排序只使用已过滤的相邻列关系（超限节点不得回流）
        uses_limited = [(f, t) for f, t in uses if f in file_set and t in tech_set]

        # 3) 排序：多种初始顺序 + barycenter，取连线交叉最少的一种
        best = None
        for variant in range(3):
            order = _order_canvas_layers(files, techs, kept_topics, skills,
                                         uses_limited, assesses, variant)
            crossings = _canvas_crossings(order, uses_limited, kept_topics, assesses)
            if best is None or crossings < best[0]:
                best = (crossings, order)
        crossings, (files_o, techs_o, topics_o, skills_o) = best

        # 4) 布局：固定 X、自动 Y（统一尺寸 + 固定间距，天然无重叠）
        id_map: dict[str, str] = {}
        canvas_nodes = []

        canvas_nodes.append({"id": "title", "type": "text",
                             "text": "**RepoCourse · 项目知识图谱**\n" + (self.project or ""),
                             "x": 0, "y": 0, "width": CANVAS_WIDTH, "height": 50,
                             "color": "5"})
        id_map["title"] = "title"
        headers = [("hdr-file", "代码", 0), ("hdr-tech", "技术", COL_X["tech"]),
                   ("hdr-topic", "知识", COL_X["topic"]), ("hdr-skill", "我的技能", COL_X["skill"])]
        for nid, text, x in headers:
            canvas_nodes.append({"id": nid, "type": "text", "text": text,
                                 "x": x, "y": HEADER_Y, "width": NODE_W, "height": HEADER_H,
                                 "color": "2"})
            id_map[nid] = nid

        kind_color = {"file": "5", "tech": "4", "topic": "3", "skill": "6"}

        def place(col_ids: list[str], kind: str):
            x = COL_X[kind]
            for i, nid in enumerate(col_ids):
                node = self.nodes[nid]
                text = _canvas_text(node)
                canvas_nodes.append({
                    "id": nid, "type": "text", "text": text,
                    "x": x, "y": START_Y + i * (NODE_H + Y_GAP),
                    "width": NODE_W, "height": NODE_H,
                    "color": kind_color[kind],
                })
                id_map[nid] = nid

        for col, kind in ((files_o, "file"), (techs_o, "tech"),
                          (topics_o, "topic"), (skills_o, "skill")):
            place(col, kind)

        # 5) 边：只保留相邻列真实关系，不显示 label
        canvas_edges = []
        edge_i = 1
        for src, dst in (uses_limited + kept_topics + assesses):
            if src not in id_map or dst not in id_map:
                continue
            canvas_edges.append({
                "id": "e" + str(edge_i), "fromNode": src, "toNode": dst,
                "fromSide": "right", "toSide": "left", "color": "2",
            })
            edge_i += 1

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"nodes": canvas_nodes, "edges": canvas_edges},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def export_learning_canvas(self, path: Path, assessment=None, blind_spots=None,
                               plan=None) -> Path:
        """学习模式 Canvas（knowledge_learning.canvas）：游戏技能树风格。

        中心项目 → 我做了什么 → 涉及技术（≤10）→ 我学到了什么（≤20）→ 下一步学习（≤10）。
        不显示代码文件与 AST 细节；技术按 已掌握/学习中/待学习 着色。
        独立于 knowledge_graph.canvas（原开发者视图不变）。
        """
        from .learning_canvas import (LEARNING_COL_X, LEARNING_MAX_TASKS,
                                      LEARNING_MAX_TECHS, LEARNING_MAX_TOPICS,
                                      LEARNING_TOPICS_PER_TECH,
                                      LEARNING_STATUS_COLOR, TASK_LEVEL_COLOR,
                                      learning_tech_status)
        canvas_nodes: list[dict] = []
        canvas_edges: list[dict] = []

        def add(nid, text, x, y, w, h, color):
            canvas_nodes.append({"id": nid, "type": "text", "text": text,
                                 "x": x, "y": y, "width": w, "height": h,
                                 "color": color})

        def edge(eid, src, dst):
            canvas_edges.append({"id": eid, "fromNode": src, "toNode": dst,
                                  "fromSide": "right", "toSide": "left",
                                  "color": "2"})

        project = self.project or "项目"
        add("title", "**" + project + " · 学习技能树**", 0, 0, 320, 60, "6")
        add("legend", "图例：绿色=已掌握 黄色=学习中 红色=待学习", 0, 80, 320, 40, "2")
        add("hub", "**" + project + "**", 0, 220, 320, 80, "6")
        headers = [("hdr-do", "我做了什么", LEARNING_COL_X["do"]),
                   ("hdr-tech", "涉及技术", LEARNING_COL_X["tech"]),
                   ("hdr-topic", "我学到了什么", LEARNING_COL_X["topic"]),
                   ("hdr-task", "下一步学习", LEARNING_COL_X["task"])]
        for nid, text, x in headers:
            add(nid, text, x, 80, 260, 40, "2")

        # 第一层：我做了什么（概览卡片，无代码文件）
        ai_files = sum(1 for n in self.nodes.values() if n.kind == "file"
                       and (n.properties.get("ai_contribution") or 0) >= 0.3)
        human_files = sum(1 for n in self.nodes.values() if n.kind == "file"
                           and (n.properties.get("ai_contribution") or 0) < 0.3)
        usage: dict[str, int] = {}
        for rel in self.relations:
            if rel.kind == "uses":
                usage[rel.target] = usage.get(rel.target, 0) + 1
        tech_candidates = [n for n in self.nodes.values() if n.kind == "tech"
                           and usage.get(n.id, 0) > 0]
        tech_candidates.sort(key=lambda n: (-usage.get(n.id, 0), n.name))
        techs = tech_candidates[:LEARNING_MAX_TECHS]
        if not techs:
            techs = sorted([n for n in self.nodes.values() if n.kind == "tech"],
                            key=lambda n: n.name)[:LEARNING_MAX_TECHS]

        do_cards = [
            "独立编写 " + str(human_files) + " 个文件",
            "与 AI 协作完成 " + str(ai_files) + " 个文件",
            "梳理了 " + str(len(techs)) + " 项技术",
        ]
        for i, text in enumerate(do_cards):
            add("c" + str(i + 1), text, LEARNING_COL_X["do"], 140 + i * 180, 260, 80, "5")
            edge("e-do" + str(i + 1), "hub", "c" + str(i + 1))

        # 第二层：涉及技术（状态着色）
        status: dict[str, str] = {}
        for i, node in enumerate(techs):
            st = learning_tech_status(self, node.name, assessment, blind_spots)
            status[node.name] = st
            add("t" + str(i + 1), "**" + node.name + "**\n" + st,
                LEARNING_COL_X["tech"], 140 + i * 180, 260, 80,
                LEARNING_STATUS_COLOR[st])
            edge("e-t" + str(i + 1), "hub", "t" + str(i + 1))

        # 第三层：我学到了什么（知识点，每技术 ≤4，共 ≤20）
        topic_items = []
        seen_topics = set()
        for tech in techs:
            cnt = 0
            for rel in self.relations:
                if rel.source != tech.id or rel.kind != "covers":
                    continue
                tnode = self.nodes.get(rel.target)
                if tnode is None or tnode.id in seen_topics:
                    continue
                seen_topics.add(tnode.id)
                topic_items.append((tech.name, tnode.name, status[tech.name]))
                cnt += 1
                if cnt >= LEARNING_TOPICS_PER_TECH:
                    break
            if len(topic_items) >= LEARNING_MAX_TOPICS:
                break
        for i, (tech_name, topic_name, st) in enumerate(topic_items):
            add("k" + str(i + 1), topic_name, LEARNING_COL_X["topic"],
                140 + i * 180, 260, 80, LEARNING_STATUS_COLOR[st])
            tech_idx = next((j + 1 for j, t in enumerate(techs) if t.name == tech_name), None)
            if tech_idx:
                edge("e-k" + str(i + 1), "t" + str(tech_idx), "k" + str(i + 1))

        # 第四层：下一步学习（任务 ≤10）
        tasks = []
        if plan is not None:
            for item in plan.priority[:LEARNING_MAX_TASKS]:
                action = item.action[0] if item.action else ("学习 " + item.skill)
                tasks.append((item.skill, action, item.level))
        for i, (skill, action, level) in enumerate(tasks):
            add("x" + str(i + 1), "**" + skill + "**\n" + action,
                LEARNING_COL_X["task"], 140 + i * 180, 260, 80,
                TASK_LEVEL_COLOR.get(level, "3"))
            tech_idx = next((j + 1 for j, t in enumerate(techs)
                             if t.name.lower() == skill.lower()), None)
            if tech_idx:
                edge("e-x" + str(i + 1), "t" + str(tech_idx), "x" + str(i + 1))
            else:
                edge("e-x" + str(i + 1), "hub", "x" + str(i + 1))

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

    # 2) 文件节点 + uses / written-in 关系（挂 AI 贡献证据）
    for tech, entries in sorted(usage.items()):
        tech_id = "tech:" + tech
        for entry in entries:
            file_id = "file:" + entry["file"]
            props: dict = {}
            if evidence is not None:
                verdict = evidence.per_file.get(entry["file"])
                if verdict and verdict.score is not None and verdict.confidence >= 0.3:
                    props["ai_contribution"] = round(verdict.score, 2)
                    props["ai_classification"] = verdict.classification
            graph.add_node(KnowledgeNode(id=file_id, kind="file",
                                         name=entry["file"], properties=props))
            graph.add_relation(KnowledgeRelation(
                source=file_id, target=tech_id, kind="uses",
                detail="检测到 " + "、".join(entry["hits"]), confidence=0.9))
            ext = Path(entry["file"]).suffix.lower()
            lang = EXT_LANGUAGE.get(ext, "").split("/")[0]
            if lang and lang in language_counts:
                graph.add_relation(KnowledgeRelation(
                    source=file_id, target="tech:" + lang, kind="written-in",
                    detail="语言归属"))
    # 技术节点聚合：平均 AI 贡献度
    for tech, entries in usage.items():
        scores = []
        if evidence is not None:
            for entry in entries:
                verdict = evidence.per_file.get(entry["file"])
                if verdict and verdict.score is not None and verdict.confidence >= 0.3:
                    scores.append(verdict.score)
        if scores:
            graph.nodes["tech:" + tech].properties["avg_ai_contribution"] = (
                round(sum(scores) / len(scores), 2))

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


# Canvas 布局常量（严格四列分层）
COL_X = {"file": 0, "tech": 400, "topic": 800, "skill": 1200}
NODE_W, NODE_H = 260, 80
Y_GAP = 100                    # 同列节点垂直间距（>=100px）
START_Y = 140                  # 数据节点起始 Y（标题 0，列头 70）
HEADER_Y, HEADER_H = 70, 40
CANVAS_WIDTH = 1460
MAX_FILES = 10                 # 核心文件上限
MAX_TECHS = 15                 # 技术/框架上限
MAX_TOPICS_PER_TECH = 5        # 每个技术核心知识点上限


def _canvas_text(node) -> str:
    if node.kind == "file" and node.properties.get("ai_contribution") is not None:
        pct = round(node.properties["ai_contribution"] * 100)
        return node.name + "\nAI 贡献 " + str(pct) + "%"
    if node.kind == "tech" and node.properties.get("avg_ai_contribution") is not None:
        pct = round(node.properties["avg_ai_contribution"] * 100)
        text = "**" + node.name + "**\n平均 AI 贡献 " + str(pct) + "%"
        if node.properties.get("file_count"):
            text += " · 文件数 " + str(node.properties["file_count"])
        return text
    if node.kind == "skill":
        mastery = node.properties.get("mastery_percent")
        suffix = (str(mastery) + "%") if mastery is not None else "未评估"
        return "**" + node.name + "**\n掌握程度 " + suffix
    if node.kind == "tech":
        text = "**" + node.name + "**"
        if node.properties.get("file_count"):
            text += "\n文件数 " + str(node.properties["file_count"])
        return text
    return node.name


def _barycenter(source_order: list[str], edges: list[tuple[str, str]]) -> list[str]:
    """按已定序的源层平均位置给目标层排序（barycenter 启发式，减少交叉）。"""
    pos = {s: i for i, s in enumerate(source_order)}
    sums: dict[str, float] = {}
    cnt: dict[str, int] = {}
    for a, b in edges:
        if a in pos:
            sums[b] = sums.get(b, 0.0) + pos[a]
            cnt[b] = cnt.get(b, 0) + 1
    return sorted((b for b in sums), key=lambda b: (sums[b] / cnt[b], b))


def _order_canvas_layers(files, techs, kept_topics, skills, uses, assesses, variant):
    """多种初始顺序 + 两轮 barycenter，返回四层节点顺序。"""
    if variant == 0:
        files0 = sorted(files)
    elif variant == 1:
        cnt = {}
        for f, _ in uses:
            cnt[f] = cnt.get(f, 0) + 1
        files0 = sorted(files, key=lambda f: (-cnt.get(f, 0), f))
    else:
        files0 = sorted(files, key=lambda f: sorted(t for a, t in uses if a == f))

    techs_o = _barycenter(files0, uses)
    topics_o = _barycenter(techs_o, kept_topics)
    skills_o = _barycenter(topics_o, assesses)
    files_o = _barycenter(techs_o, [(t, f) for f, t in uses])
    techs_o = _barycenter(files_o, uses)
    return files_o, techs_o, topics_o, skills_o


def _canvas_crossings(order, uses, kept_topics, assesses) -> int:
    """统计相邻列之间的连线交叉总数。"""
    files_o, techs_o, topics_o, skills_o = order

    def pair_crossings(edges, left, right):
        lpos = {n: i for i, n in enumerate(left)}
        rpos = {n: i for i, n in enumerate(right)}
        pairs = sorted((lpos[a], rpos[b]) for a, b in edges if a in lpos and b in rpos)
        total = 0
        for i in range(len(pairs)):
            for j in range(i + 1, len(pairs)):
                if (pairs[i][0] - pairs[j][0]) * (pairs[i][1] - pairs[j][1]) < 0:
                    total += 1
        return total

    return (pair_crossings(uses, files_o, techs_o)
            + pair_crossings(kept_topics, techs_o, topics_o)
            + pair_crossings(assesses, topics_o, skills_o))


def _mm_safe(label: str) -> str:
    """Mermaid mindmap 节点标签清洗：去掉会引起语法错误的字符。"""
    for ch in ("(", ")", "[", "]", "{", "}", "\"", "#", "<", ">", chr(96)):
        label = label.replace(ch, " ")
    return " ".join(label.split()) or "未命名"


# 零依赖可视化模板：Obsidian 关系图谱风格
# 白底 + 圆点节点 + 淡紫直线 + 力导向模拟 + 拖拽/缩放/悬停与点击高亮（无 CDN、无第三方库）
_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RepoCourse · 知识关系图谱</title>
<style>
html, body { margin:0; height:100%; overflow:hidden; background:#ffffff;
  font-family:"Segoe UI","Microsoft YaHei",sans-serif; }
#svg { width:100vw; height:100vh; display:block; cursor:grab; }
#svg.dragging { cursor:grabbing; }
.edge { stroke:#c7a5e6; stroke-width:1.4; pointer-events:none; }
.edge.hubedge { stroke:#d8c4ee; stroke-width:1.2; }
.node-label { fill:#111; font-size:11px; user-select:none; pointer-events:none; }
.dim { opacity:.16; }
#legend { position:fixed; left:16px; bottom:14px; font-size:12px; color:#555;
  background:rgba(255,255,255,.94); border:1px solid #eee; border-radius:10px; padding:10px 14px; }
#legend span { margin-right:12px; }
#legend i { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:4px; }
#stats { position:fixed; right:16px; top:14px; font-size:12px; color:#777;
  background:rgba(255,255,255,.94); border:1px solid #eee; border-radius:10px; padding:8px 12px; }
#btn { position:fixed; right:16px; bottom:14px; font-size:12px; color:#555; background:#fff;
  border:1px solid #ddd; border-radius:8px; padding:6px 12px; cursor:pointer; }
#btn:hover { background:#f5f0ff; }
</style>
</head>
<body>
<svg id="svg"></svg>
<div id="legend">
<span><i style="background:#8a2be2"></i>项目</span>
<span><i style="background:#7c3aed"></i>我的技能</span>
<span><i style="background:#4b5563"></i>技术</span>
<span><i style="background:#9ca3af"></i>文件</span>
<span><i style="background:#d1d5db"></i>知识点</span>
</div>
<div id="stats"></div>
<div id="btn">重新布局</div>
<script>
var DATA = __DATA__;
var W = window.innerWidth, H = window.innerHeight;
var svg = document.getElementById('svg');
var NS = 'http://www.w3.org/2000/svg';
var viewport = document.createElementNS(NS, 'g');
svg.appendChild(viewport);

// ---- 数据：hub（项目） + 数据节点；hub 到文件的派生连线（不改数据模型）----
var SIZE = { hub:20, file:7, tech:10, topic:6, skill:12 };
var COLOR = { hub:'#8a2be2', file:'#9ca3af', tech:'#4b5563', topic:'#d1d5db', skill:'#7c3aed' };
var byId = {}, nodes = [], fileIds = [];
DATA.nodes.forEach(function (n) { byId[n.id] = n; });
DATA.nodes.forEach(function (n) {
  if (n.kind === 'file') fileIds.push(n.id);
  if (n.kind === 'file' || n.kind === 'tech' || n.kind === 'topic' || n.kind === 'skill') {
    nodes.push({ id:n.id, kind:n.kind, name:n.name, props:n.properties || {} });
  }
});
var hubId = 'hub';
nodes.push({ id:hubId, kind:'hub', name: DATA.project || '项目', props:{} });
byId[hubId] = { id:hubId, name:nodes[nodes.length-1].name };
var edges = [];
DATA.relations.forEach(function (r) {
  if (byId[r.source] && byId[r.target]) edges.push({ s:r.source, t:r.target, hub:false });
});
fileIds.forEach(function (f) { edges.push({ s:hubId, t:f, hub:true }); });

// ---- 力导向模拟 ----
var sim = {};
nodes.forEach(function (n) {
  var ang = Math.random() * Math.PI * 2, rr = 60 + Math.random() * 150;
  sim[n.id] = { x:W/2 + rr * Math.cos(ang), y:H/2 + rr * Math.sin(ang), vx:0, vy:0, fx:null, fy:null };
});
function step() {
  var ids = Object.keys(sim), i, j, a, b, dx, dy, d, f;
  for (i = 0; i < ids.length; i++) {
    for (j = i + 1; j < ids.length; j++) {
      a = sim[ids[i]]; b = sim[ids[j]];
      dx = a.x - b.x; dy = a.y - b.y;
      d = Math.sqrt(dx * dx + dy * dy) || 1;
      f = Math.min(900, 26000 / (d * d));
      a.vx += dx / d * f; a.vy += dy / d * f;
      b.vx -= dx / d * f; b.vy -= dy / d * f;
    }
  }
  edges.forEach(function (e) {
    a = sim[e.s]; b = sim[e.t];
    if (!a || !b) return;
    dx = b.x - a.x; dy = b.y - a.y;
    d = Math.sqrt(dx * dx + dy * dy) || 1;
    f = (d - 95) * 0.03;
    a.vx += dx / d * f; a.vy += dy / d * f;
    b.vx -= dx / d * f; b.vy -= dy / d * f;
  });
  ids.forEach(function (k) {
    var p = sim[k];
    if (p.fx !== null) { p.x = p.fx; p.y = p.fy; p.vx = 0; p.vy = 0; return; }
    p.vx += (W / 2 - p.x) * 0.0012;
    p.vy += (H / 2 - p.y) * 0.0012;
    p.vx *= 0.86; p.vy *= 0.86;
    p.x += p.vx; p.y += p.vy;
  });
}

// ---- 渲染 ----
var edgeEls = [], nodeEls = {};
function build() {
  viewport.innerHTML = '';
  edgeEls = [];
  edges.forEach(function (e) {
    var line = document.createElementNS(NS, 'line');
    line.setAttribute('class', e.hub ? 'edge hubedge' : 'edge');
    line.dataset.s = e.s; line.dataset.t = e.t;
    viewport.appendChild(line);
    edgeEls.push(line);
  });
  nodes.forEach(function (n) {
    var g = document.createElementNS(NS, 'g');
    g.dataset.id = n.id;
    var c = document.createElementNS(NS, 'circle');
    c.setAttribute('r', SIZE[n.kind]);
    c.setAttribute('fill', COLOR[n.kind]);
    if (n.kind === 'hub') { c.setAttribute('stroke', '#6d1fb8'); c.setAttribute('stroke-width', 3); }
    c.style.cursor = 'pointer';
    g.appendChild(c);
    var label = n.name;
    if (n.kind === 'skill' && n.props.mastery_percent !== null
        && n.props.mastery_percent !== undefined) {
      label = label + ' ' + n.props.mastery_percent + '%';
    }
    if (n.kind === 'file' && n.props.ai_contribution !== null
        && n.props.ai_contribution !== undefined) {
      label = label + ' [AI ' + Math.round(n.props.ai_contribution * 100) + '%]';
    }
    var t = document.createElementNS(NS, 'text');
    t.setAttribute('class', 'node-label');
    t.setAttribute('text-anchor', 'middle');
    t.setAttribute('dy', SIZE[n.kind] + 13);
    t.textContent = label;
    g.appendChild(t);
    viewport.appendChild(g);
    nodeEls[n.id] = g;
    bindNode(n, g, c);
  });
}

// ---- 交互：拖拽节点 / 平移画布 / 缩放 / 悬停与点击高亮 ----
var tx = 0, ty = 0, scale = 1;
function applyView() {
  viewport.setAttribute('transform', 'translate(' + tx + ',' + ty + ') scale(' + scale + ')');
}
svg.addEventListener('wheel', function (ev) {
  ev.preventDefault();
  scale = Math.min(3, Math.max(0.25, scale * (ev.deltaY < 0 ? 1.1 : 0.9)));
  applyView();
}, { passive:false });

var panning = false, px = 0, py = 0;
svg.addEventListener('pointerdown', function (ev) {
  if (ev.target === svg) { panning = true; px = ev.clientX - tx; py = ev.clientY - ty; svg.classList.add('dragging'); }
});
window.addEventListener('pointermove', function (ev) {
  if (panning) { tx = ev.clientX - px; ty = ev.clientY - py; applyView(); }
});
window.addEventListener('pointerup', function () { panning = false; svg.classList.remove('dragging'); });

var draggingId = null, focusId = null;
var neighborsOf = {};
edges.forEach(function (e) {
  (neighborsOf[e.s] = neighborsOf[e.s] || []).push(e.t);
  (neighborsOf[e.t] = neighborsOf[e.t] || []).push(e.s);
});
function highlight(id) {
  var keep = null;
  if (id) {
    keep = {}; keep[id] = true;
    (neighborsOf[id] || []).forEach(function (k) { keep[k] = true; });
  }
  Object.keys(nodeEls).forEach(function (k) {
    if (!keep || keep[k]) nodeEls[k].classList.remove('dim'); else nodeEls[k].classList.add('dim');
  });
  edgeEls.forEach(function (el) {
    if (!keep || (keep[el.dataset.s] && keep[el.dataset.t])) el.classList.remove('dim');
    else el.classList.add('dim');
  });
}
function bindNode(n, g, c) {
  c.addEventListener('pointerdown', function (ev) {
    ev.stopPropagation();
    draggingId = n.id;
  });
  window.addEventListener('pointermove', function (ev) {
    if (draggingId !== n.id) return;
    sim[n.id].fx = (ev.clientX - tx) / scale;
    sim[n.id].fy = (ev.clientY - ty) / scale;
  });
  window.addEventListener('pointerup', function () {
    if (draggingId === n.id) draggingId = null;
  });
  g.addEventListener('mouseenter', function () { if (!focusId) highlight(n.id); });
  g.addEventListener('mouseleave', function () { if (!focusId) highlight(null); });
  g.addEventListener('click', function (ev) {
    ev.stopPropagation();
    focusId = (focusId === n.id) ? null : n.id;
    highlight(focusId);
  });
}

document.getElementById('btn').addEventListener('click', function () {
  Object.keys(sim).forEach(function (k) {
    var ang = Math.random() * Math.PI * 2, rr = 60 + Math.random() * 150;
    sim[k].x = W/2 + rr * Math.cos(ang);
    sim[k].y = H/2 + rr * Math.sin(ang);
    sim[k].vx = 0; sim[k].vy = 0; sim[k].fx = null; sim[k].fy = null;
  });
});
document.getElementById('stats').textContent = '节点 ' + nodes.length
  + ' / 关系 ' + edges.length + ' ｜ ' + (DATA.project || '');

function frame() {
  step();
  nodes.forEach(function (n) {
    var g = nodeEls[n.id];
    if (!g) return;
    g.setAttribute('transform', 'translate(' + sim[n.id].x + ',' + sim[n.id].y + ')');
  });
  edgeEls.forEach(function (el) {
    var a = sim[el.dataset.s], b = sim[el.dataset.t];
    if (!a || !b) return;
    el.setAttribute('x1', a.x); el.setAttribute('y1', a.y);
    el.setAttribute('x2', b.x); el.setAttribute('y2', b.y);
  });
  requestAnimationFrame(frame);
}
build();
frame();
</script>
</body>
</html>
"""
