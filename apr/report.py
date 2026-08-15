"""报告渲染：8 大板块 + 技能评估 + 学习路线 + 附录。"""
from __future__ import annotations

from . import __version__
from .analyzer import ReviewResult
from .assessment.blindspot import detect_blind_spots
from .assessment.collab import build_ai_collab_report
from .assessment.skill import LEVEL_LABELS, SkillAssessment, assess_skills
from .coach.planner import LearningPlan, build_learning_plan


def _render_skill_section(assessment: SkillAssessment) -> str:
    """「我的技能评估」章节：技能名称/自评/项目证据/Quiz表现/最终等级/可信度。"""
    lines = ["## 我的技能评估", ""]
    if not assessment.entries:
        lines += [
            "暂无足够数据生成技能评估。建议：",
            "",
            "- 填写 profile.yaml 技能档案（known_skills）",
            "- 运行 apr quiz 完成实践验证",
            "",
        ]
        return "\n".join(lines)
    for entry in assessment.sorted_entries():
        claimed = entry.claimed_level or "未标注"
        quiz = f"{entry.quiz_score}/100" if entry.quiz_score is not None else "未验证"
        label = LEVEL_LABELS.get(entry.final_level, entry.final_level)
        lines += [
            f"### {entry.skill}",
            "",
            f"- **自评**：{claimed}",
            "- **项目证据**：",
        ]
        for ev in entry.project_evidence or ["（无项目证据）"]:
            lines.append(f"    - {ev}")
        lines += [
            f"- **Quiz 表现**：{quiz}",
            f"- **最终等级**：{label}（{entry.final_level}）",
            f"- **可信度**：{entry.confidence:.0%}",
            "",
        ]
    return "\n".join(lines)


def _render_route_section(plan: LearningPlan, assessment: SkillAssessment) -> str:
    """「下一阶段学习路线」章节：当前不足 → 原因 → 学习任务 → 实践项目。"""
    lines = ["## 下一阶段学习路线", "",
             "> 由 Learning Coach 基于五类数据生成：技能评估 × 知识图谱 × Quiz × 技术栈 × AI 贡献。",
             ""]
    if not plan.priority:
        lines += ["暂无足够数据生成学习路线。建议：", "",
                  "- 填写 profile.yaml 技能档案", "- 运行 apr quiz 完成实践验证", ""]
        return "\n".join(lines)
    for item in plan.priority:
        reasons = list(item.reason)
        entry = assessment.entries.get(item.skill)
        if entry is not None:
            level = entry.claimed_level or entry.final_level
            level_line = "用户技能等级 " + (LEVEL_LABELS.get(level, level) if level else "未评估")
            if level_line not in reasons:
                reasons.append(level_line)
        lines += ["### " + item.skill, "", "**原因**："]
        for r in reasons:
            lines.append("- " + r)
        lines += ["", "**学习路线**："]
        for i, a in enumerate(item.action, 1):
            lines.append(str(i) + ". " + a)
        lines.append("")
    if plan.next_projects:
        lines += ["**实践项目**："]
        for p in plan.next_projects:
            lines.append("- " + p)
        lines.append("")
    return "\n".join(lines)


def render_report(result: ReviewResult) -> str:
    cfg = result.config
    name = result.project.name
    meta = [
        f"# {name} · 项目复盘",
        "",
        f"> 由 **AI Project Reviewer v{__version__}** 自动生成",
        f"> 生成时间：{result.started_at} ｜ 模型：{cfg.llm.provider}/{cfg.llm.model} ｜ 语言：{cfg.output.language}",
        f"> 项目路径：{result.project}",
        "",
        "## 目录",
        "",
    ]
    for i, (title, _) in enumerate(result.sections, 1):
        meta.append(f"{i}. [{title}](#{title})")
    n = len(result.sections)
    meta.append(f"{n + 1}. [我的技能评估](#我的技能评估)")
    meta.append(f"{n + 2}. [下一阶段学习路线](#下一阶段学习路线)")
    meta.append(f"{n + 3}. [附录 A：AI 生成证据明细](#附录-aai-生成证据明细)")
    if result.quiz:
        meta.append(f"{n + 4}. [附录 B：实践验证记录](#附录-b实践验证记录)")
    # 学习盲区与 AI 协作分析：由证据引擎计算，替换 LLM 占位内容
    blind_spots = detect_blind_spots(profile=result.profile, scan=result.scan,
                                     digest=result.digest, quiz=result.quiz,
                                     evidence=result.evidence)
    blind_md = blind_spots.render_markdown()
    collab_md = build_ai_collab_report(result.evidence).render_markdown()
    body = ["", "---", ""]
    for title, md in result.sections:
        if title == "我的学习盲区":
            body.append(blind_md)
        elif title == "AI 协作分析":
            body.append(collab_md)
        else:
            body.append(md)
        body += ["", "---", ""]
    skill_assessment = assess_skills(result.profile, result.scan, result.quiz, result.evidence)
    body.append(_render_skill_section(skill_assessment))
    body += ["", "---", ""]
    learning_plan = build_learning_plan(profile=result.profile, scan=result.scan,
                                        digest=result.digest, quiz=result.quiz,
                                        evidence=result.evidence,
                                        assessment=skill_assessment,
                                        blind_spots=blind_spots)
    body.append(_render_route_section(learning_plan, skill_assessment))
    body += ["", "---", ""]
    appendix = ["## 附录 A：AI 生成证据明细", ""]
    if result.evidence.items:
        appendix.append(result.evidence.summary_markdown())
    else:
        appendix.append("本报告未采集到可用证据。")
    if result.notes:
        appendix += ["", "### 过程备注", ""]
        appendix.extend(f"- {n}" for n in result.notes)
    if result.quiz:
        appendix += ["", "---", "", "## 附录 B：实践验证记录", "", result.quiz.render_markdown()]
    footer = ["", "---", "",
              "*本报告由 AI Project Reviewer 自动生成，仅供学习复盘参考；标注「推测」的内容未经证据证实。*"]
    return "\n".join(meta + body + appendix + footer)
