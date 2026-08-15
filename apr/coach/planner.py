"""Learning Coach：个性化学习计划（行动导向，非简单总结）。

输入五类已有数据，输出 LearningPlan：
1. Skill Assessment 结果（等级/置信度/quiz 分）
2. Knowledge Graph（项目技术使用关系）
3. Quiz 成绩（薄弱技能）
4. 项目技术栈（语言/平台/依赖）
5. AI 贡献分析（哪些代码是 AI 写的）

计划结构（与设计示例一致）：
{
  "priority": [{"skill", "level", "reason", "action"}],
  "next_projects": ["..."]
}

纯确定性规划器（不调用 LLM）；已有模块全部复用、不做修改。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..assessment.blindspot import (BlindSpotReport, _ai_ratio, _profile_status,
                                    _project_usage, detect_blind_spots)
from ..assessment.skill import SkillAssessment, assess_skills
from ..digest import ProjectDigest
from ..evidence.base import EvidenceReport
from ..knowledge.knowledge import TECH_TOPICS, KnowledgeGraph, build_knowledge_graph
from ..profile import Profile
from ..scanner import ScanResult

_RISK_TO_LEVEL = {"高风险盲区": "high", "中风险盲区": "medium", "低风险盲区": "low"}


@dataclass
class PriorityItem:
    skill: str
    level: str                  # high / medium / low
    reason: list[str] = field(default_factory=list)
    action: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"skill": self.skill, "level": self.level,
                "reason": list(self.reason), "action": list(self.action)}


@dataclass
class LearningPlan:
    priority: list[PriorityItem] = field(default_factory=list)
    next_projects: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "priority": [item.to_dict() for item in self.priority],
            "next_projects": list(self.next_projects),
        }

    def render_markdown(self) -> str:
        lines = ["## 学习计划", ""]
        if not self.priority:
            lines.append("暂无足够数据生成学习计划。")
            return "\n".join(lines)
        for item in self.priority:
            lines.append("### " + item.skill + "（" + item.level + "）")
            lines.append("")
            lines.append("**为什么学**：")
            for r in item.reason:
                lines.append("- " + r)
            lines.append("")
            lines.append("**怎么做**：")
            for i, a in enumerate(item.action, 1):
                lines.append(str(i) + ". " + a)
            lines.append("")
        if self.next_projects:
            lines.append("**下一步项目**：")
            for p in self.next_projects:
                lines.append("- " + p)
            lines.append("")
        return "\n".join(lines)

    def render_text(self) -> str:
        out = []
        for i in self.priority:
            out.append("- " + i.skill + "：" + i.level + "（" + "、".join(i.reason) + "）")
        return "\n".join(out)


def _build_reasons(skill, usage, quiz_score, ai_ratio, status, extra):
    reasons = []
    if usage >= 3:
        reasons.append("项目大量使用" + skill)
    elif usage >= 1:
        reasons.append("项目使用" + skill)
    if quiz_score is not None and quiz_score < 80:
        reasons.append("Quiz评分" + str(quiz_score))
    if ai_ratio is not None:
        if ai_ratio > 0.6:
            reasons.append("相关代码主要由AI生成")
        elif ai_ratio >= 0.3:
            reasons.append("部分代码由AI生成")
    if status == "unclaimed":
        reasons.append("技能档案尚未掌握")
    elif status == "learning":
        reasons.append("正在学习中")
    elif status == "target":
        reasons.append("学习目标（优先级" + str(extra or "未标注") + "）")
    return reasons[:4]


def _build_actions(skill, usage, ai_ratio, quiz_score):
    actions = []
    topics = TECH_TOPICS.get(skill, [])
    if topics:
        actions.append("学习" + topics[0] + "基础")
    else:
        actions.append("学习 " + skill + " 基础")
    actions.append("实现 " + skill + " 练习 Demo")
    if quiz_score is not None and quiz_score < 60:
        actions.append("针对 " + skill + " 做专项练习，目标 60 分以上")
    if ai_ratio is not None and ai_ratio > 0.6:
        actions.append("独立重写项目中 " + skill + " 的 AI 生成代码")
    elif usage >= 2:
        actions.append("重构项目中 " + skill + " 相关模块")
    elif usage == 1:
        actions.append("在项目中扩展 " + skill + " 的应用")
    return actions


def _build_next_projects(priority, profile):
    projects = []
    for item in priority:
        if item.level == "high":
            projects.append(item.skill + " 实战练习")
    if profile is not None:
        for target in profile.targets:
            if str(target.priority).lower() == "high":
                projects.append(target.name + " Demo 项目")
        for claim in profile.learning:
            projects.append(claim.name + " 练习项目")
    deduped = []
    for p in projects:
        if p not in deduped:
            deduped.append(p)
    return deduped[:4]


def _quiz_for(skill, assessment):
    entry = assessment.entries.get(skill)
    return entry.quiz_score if entry is not None else None


def build_learning_plan(profile: Profile | None = None,
                        scan: ScanResult | None = None,
                        digest: ProjectDigest | None = None,
                        quiz=None,
                        evidence: EvidenceReport | None = None,
                        assessment: SkillAssessment | None = None,
                        graph: KnowledgeGraph | None = None,
                        blind_spots: BlindSpotReport | None = None) -> LearningPlan:
    """五类输入 → LearningPlan。

    assessment/graph/blind_spots 可预传入（支持 mock 测试与复用计算结果）；
    缺省时内部用已有模块计算，不改动任何已有模块。
    """
    if assessment is None:
        assessment = assess_skills(profile=profile, scan=scan, quiz=quiz, evidence=evidence)
    if graph is None:
        graph = build_knowledge_graph(profile=profile, scan=scan, digest=digest,
                                      evidence=evidence, skill_assessment=assessment)
    if blind_spots is None:
        blind_spots = detect_blind_spots(profile=profile, scan=scan, digest=digest,
                                         quiz=quiz, evidence=evidence, graph=graph)

    plan = LearningPlan()
    for item in blind_spots.sorted_items():
        skill = item.skill
        usage, files = _project_usage(skill, scan, graph)
        ai_ratio, _ = _ai_ratio(files, evidence)
        status, extra = _profile_status(profile, skill)
        quiz_score = _quiz_for(skill, assessment)
        plan.priority.append(PriorityItem(
            skill=skill,
            level=_RISK_TO_LEVEL.get(item.risk_level, "low"),
            reason=_build_reasons(skill, usage, quiz_score, ai_ratio, status, extra),
            action=_build_actions(skill, usage, ai_ratio, quiz_score),
        ))
    plan.next_projects = _build_next_projects(plan.priority, profile)
    plan.notes = list(blind_spots.notes)
    return plan
