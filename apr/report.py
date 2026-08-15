"""报告渲染：8 大板块 + 技能评估 + 附录。"""
from __future__ import annotations

from . import __version__
from .analyzer import ReviewResult
from .assessment.blindspot import detect_blind_spots
from .assessment.skill import LEVEL_LABELS, SkillAssessment, assess_skills


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
    meta.append(f"{n + 2}. [附录 A：AI 生成证据明细](#附录-aai-生成证据明细)")
    if result.quiz:
        meta.append(f"{n + 3}. [附录 B：实践验证记录](#附录-b实践验证记录)")
    # 学习盲区：由证据引擎计算，替换 LLM 生成的占位内容
    blind_spots = detect_blind_spots(profile=result.profile, scan=result.scan,
                                     digest=result.digest, quiz=result.quiz,
                                     evidence=result.evidence)
    blind_md = blind_spots.render_markdown()
    body = ["", "---", ""]
    for title, md in result.sections:
        body.append(blind_md if title == "我的学习盲区" else md)
        body += ["", "---", ""]
    skill_assessment = assess_skills(result.profile, result.scan, result.quiz, result.evidence)
    body.append(_render_skill_section(skill_assessment))
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
