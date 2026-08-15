"""学习盲区引擎：由证据计算，而非 AI 猜测。

五路信号（全部来自真实数据）：
1. 项目需要该技能（Knowledge Graph uses 关系 / 语言文件统计）
2. 用户 profile 等级（mastered / learning / target / 未声明）
3. Quiz 评分（按技能聚合）
4. AI 生成比例（该技能文件在证据层的平均 AI 贡献度）
5. Knowledge Graph 关联（项目核心依赖 = 多文件使用）

输出 BlindSpotReport：逐技能「等级 / 证据 / 建议」，确定性可复现、可测试。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..digest import EXT_LANGUAGE, ProjectDigest
from ..evidence.base import EvidenceReport
from ..knowledge.knowledge import TECH_TOPICS, build_knowledge_graph
from ..profile import Profile
from ..scanner import ScanResult
from .quiz import QuizResult
from .skill import assess_skills


def _core(name: str) -> str:
    return str(name).split("/")[0]


@dataclass
class BlindSpot:
    skill: str
    risk_level: str                 # 高风险盲区 / 中风险盲区 / 低风险盲区
    score: int
    evidence: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class BlindSpotReport:
    items: list[BlindSpot] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def sorted_items(self) -> list[BlindSpot]:
        return sorted(self.items, key=lambda b: (-b.score, b.skill))

    def high_risk(self) -> list[BlindSpot]:
        return [b for b in self.items if b.risk_level == "高风险盲区"]

    def render_markdown(self) -> str:
        lines = [
            "## 我的学习盲区",
            "",
            "> 由证据引擎计算：项目需求 × 技能档案 × Quiz × AI 贡献 × 知识图谱关联，非 AI 猜测。",
            "",
        ]
        if not self.items:
            lines += ["暂无足够证据判断学习盲区。建议：", "",
                      "- 填写 profile.yaml 技能档案", "- 运行 apr quiz 完成实践验证", ""]
            return "\n".join(lines)
        for item in self.sorted_items():
            lines += [
                f"### {item.skill}",
                "",
                f"- **等级**：{item.risk_level}",
                "- **证据**：",
            ]
            for ev in item.evidence:
                lines.append(f"    - {ev}")
            lines.append("- **建议**：")
            for sug in item.suggestions:
                lines.append(f"    - {sug}")
            lines.append("")
        if self.notes:
            lines.append("")
            lines.extend(f"- {n}" for n in self.notes)
            lines.append("")
        return "\n".join(lines)

    def render_text(self) -> str:
        lines = ["## 学习盲区（证据计算）"]
        for item in self.sorted_items():
            lines.append(f"- {item.skill}：{item.risk_level}（{item.score} 分）")
        return "\n".join(lines)


def _profile_status(profile: Profile | None, skill: str):
    """返回 (状态, 附加信息)。状态：unclaimed / learning / mastered / target。"""
    if profile is None:
        return "unclaimed", None
    core = _core(skill).lower()

    def match(name: str) -> bool:
        return str(name).strip().lower() == core

    for claim in profile.learning:
        if match(claim.name):
            return "learning", None
    for claim in profile.mastered:
        if match(claim.name):
            return "mastered", claim.level
    for target in profile.targets:
        if match(target.name):
            return "target", target.priority
    for raw in profile.known_skills:
        name = str(raw).split(":")[0].strip()
        if match(name):
            level = str(raw).split(":", 1)[1].strip() if ":" in str(raw) else None
            return "mastered", level or None
    return "unclaimed", None


def _project_usage(skill: str, scan: ScanResult | None, graph) -> tuple[int, list[str]]:
    """返回 (文件数, 文件列表)：语言文件 + Knowledge Graph uses 关系文件。"""
    files: list[str] = []
    if scan is not None:
        core = _core(skill)
        for f in scan.files:
            if _core(EXT_LANGUAGE.get(f.ext, "")) == core:
                files.append(f.rel)
    if graph is not None:
        tech_id = "tech:" + skill
        for rel in graph.relations:
            if rel.target == tech_id and rel.kind == "uses" and rel.source not in files:
                files.append(rel.source.replace("file:", ""))
    return len(files), files


def _ai_ratio(files: list[str], evidence: EvidenceReport | None):
    """该技能文件的平均 AI 贡献度。返回 (比例或 None, 参与判定文件数)。"""
    if evidence is None:
        return None, 0
    scores = []
    for rel in files:
        verdict = evidence.per_file.get(rel)
        if verdict and verdict.score is not None and verdict.confidence >= 0.3:
            scores.append(verdict.score)
    if not scores:
        return None, 0
    return sum(scores) / len(scores), len(scores)


def _quiz_score(skill: str, quiz: QuizResult | None) -> int | None:
    """按 question.topic 匹配技能，聚合平均得分。"""
    if quiz is None:
        return None
    core = _core(skill).lower()
    scores = []
    for q, g in zip(quiz.questions, quiz.grades):
        topic = (q.topic or "").strip().lower()
        if core and (core in topic or topic.split("/")[0] == core):
            try:
                scores.append(int(g.get("score", 0)))
            except (TypeError, ValueError):
                continue
    if not scores:
        return None
    return round(sum(scores) / len(scores))


def detect_blind_spots(profile: Profile | None = None,
                       scan: ScanResult | None = None,
                       digest: ProjectDigest | None = None,
                       quiz: QuizResult | None = None,
                       evidence: EvidenceReport | None = None,
                       graph=None,
                       min_score: int = 35) -> BlindSpotReport:
    """五路信号计算学习盲区。graph 不传时内部构建（复用现有 Knowledge Graph）。

    候选技能 = Skill Assessment 条目 ∪ 知识图谱中「有 uses 关系」的技术节点
    （签名检测出的 Redis/Spring 等技术也参与判定）。
    """
    assessment = assess_skills(profile=profile, scan=scan, quiz=quiz, evidence=evidence)
    if graph is None:
        graph = build_knowledge_graph(profile=profile, scan=scan, digest=digest,
                                      evidence=evidence, skill_assessment=assessment)
    report = BlindSpotReport()
    low_risk_skills: list[str] = []

    candidates: dict[str, object | None] = {e.skill: e for e in assessment.entries.values()}
    for node in graph.nodes.values():
        if node.kind != "tech":
            continue
        has_use = any(r.target == node.id and r.kind == "uses" for r in graph.relations)
        if has_use:
            candidates.setdefault(node.name, None)

    for skill in sorted(candidates):
        entry = candidates.get(skill)
        file_count, files = _project_usage(skill, scan, graph)
        if file_count == 0:
            # 项目不需要该技能 → 不是本项目盲区
            report.notes.append(f"{skill}：档案声明但项目未使用，不计入盲区")
            continue

        status, extra = _profile_status(profile, skill)
        ai_ratio, ai_n = _ai_ratio(files, evidence)

        score = 0
        evidence_lines: list[str] = []
        suggestions: list[str] = []

        # 1) 项目需要该技能
        if file_count >= 2:
            score += 30
            evidence_lines.append(f"项目核心依赖 {skill}（{file_count} 个文件使用）")
        else:
            score += 15
            evidence_lines.append(f"项目使用 {skill}（1 个文件）")

        # 2) 用户 profile 等级
        if status == "unclaimed":
            score += 35
            evidence_lines.append(f"用户 profile 未掌握 {skill}")
            suggestions.append(f"系统学习 {skill} 基础")
        elif status == "learning":
            score += 25
            evidence_lines.append("profile 标注正在学习")
            suggestions.append(f"按学习计划推进 {skill}")
        elif status == "target":
            score += 20
            evidence_lines.append(f"学习目标（优先级 {extra or '未标注'}）")
            suggestions.append(f"按学习目标推进 {skill}")
        else:  # mastered
            level = extra or "未标注"
            evidence_lines.append(f"profile 自评 {level}")
            if level in ("beginner", "basic", "入门"):
                score += 10
                suggestions.append(f"通过实战项目巩固 {skill}")
            elif level in ("advanced", "expert", "高级", "专家", "精通"):
                score -= 10
            # intermediate：不加减

        # 3) Quiz 评分
        quiz_score = entry.quiz_score if entry is not None else _quiz_score(skill, quiz)
        if quiz_score is None:
            score += 5
            evidence_lines.append("暂无 Quiz 验证")
            suggestions.append(f"用 apr quiz 验证 {skill}")
        elif quiz_score < 60:
            score += 25
            evidence_lines.append(f"Quiz {quiz_score} 分")
            suggestions.append(f"完成 {skill} 专项练习，目标 60 分以上")
        elif quiz_score < 80:
            score += 10
            evidence_lines.append(f"Quiz {quiz_score} 分")
        else:
            evidence_lines.append(f"Quiz {quiz_score} 分")

        # 4) AI 生成比例
        if ai_ratio is not None and ai_n > 0:
            pct = ai_ratio
            if pct > 0.6:
                score += 25
                evidence_lines.append(f"相关代码主要由 AI 生成（AI 贡献 {pct:.0%}）")
                suggestions.append(f"独立重写 {skill} 相关的 AI 生成代码")
            elif pct >= 0.3:
                score += 10
                evidence_lines.append(f"部分代码由 AI 生成（AI 贡献 {pct:.0%}）")
            else:
                evidence_lines.append(f"代码以人工编写为主（AI 贡献 {pct:.0%}）")

        # 5) Knowledge Graph 关联（知识点 → 学习建议）
        topics = TECH_TOPICS.get(skill, [])
        if topics:
            suggestions.append(f"学习 {topics[0]} 基础")
            if len(topics) > 1:
                suggestions.append(f"掌握 {topics[1]}")

        risk = "高风险盲区" if score >= 70 else ("中风险盲区" if score >= 45 else "低风险盲区")
        if score >= min_score:
            report.items.append(BlindSpot(
                skill=skill, risk_level=risk, score=score,
                evidence=evidence_lines, suggestions=suggestions[:4]))
        else:
            low_risk_skills.append(skill)

    low_risk = [s for s in low_risk_skills if s not in {b.skill for b in report.items}]
    # 项目使用但风险低：已掌握良好，未列为盲区
    if low_risk:
        report.notes.append("项目使用但风险低、未列为盲区：" + "、".join(sorted(low_risk)[:10]))
    return report
