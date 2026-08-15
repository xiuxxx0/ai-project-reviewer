"""面向学习者的个人成长报告（learning_report.md）。

与 README复盘.md（技术复盘，面向开发者/面试）互补，本报告回答：
1. 我完成了什么项目
2. 这个项目让我学到了什么（已掌握/正在提升/未掌握）
3. AI 协作情况（AI 帮了什么 / 我的参与）
4. 我的学习盲区（证据引擎计算，非 AI 猜测）
5. 下一步学习路线（短期 1 周 / 中期 1 个月，目标/任务/验证）

全部由已有数据结构确定性渲染：SkillAssessment / BlindSpotReport /
LearningPlan / KnowledgeGraph / EvidenceReport。不调用 LLM、零新依赖。
"""
from __future__ import annotations

from .analyzer import ReviewResult
from .assessment.blindspot import detect_blind_spots
from .assessment.skill import assess_skills
from .coach.planner import build_learning_plan
from .knowledge.knowledge import build_knowledge_graph


def render_learning_report(result: ReviewResult) -> str:
    """渲染 learning_report.md（面向学习者）。复用已有计算，不改动任何模块。"""
    profile = result.profile
    scan = result.scan
    digest = result.digest
    quiz = result.quiz
    evidence = result.evidence

    assessment = assess_skills(profile=profile, scan=scan, quiz=quiz, evidence=evidence)
    blind_spots = detect_blind_spots(profile=profile, scan=scan, digest=digest,
                                      quiz=quiz, evidence=evidence)
    graph = build_knowledge_graph(profile=profile, scan=scan, digest=digest,
                                  evidence=evidence, skill_assessment=assessment)
    plan = build_learning_plan(profile=profile, scan=scan, digest=digest, quiz=quiz,
                               evidence=evidence, assessment=assessment,
                               blind_spots=blind_spots, graph=graph)

    parts = [
        "# 项目学习报告",
        _section1(result, digest, assessment),
        _section2(assessment, blind_spots),
        _section3(evidence, quiz),
        _section4(blind_spots),
        _section5(plan),
    ]
    return "\n\n".join(p.strip() for p in parts).rstrip() + "\n"


def _section1(result: ReviewResult, digest, assessment) -> str:
    """我完成了什么项目：简单语言介绍项目价值。"""
    name = result.project.name
    files = len(result.scan.files)
    skip = {"other", "example", "markdown", "json", "toml", "yaml", "text", "ini", "cfg", "文档"}
    lang_names = [k for k in digest.stack.languages.keys() if str(k).lower() not in skip]
    langs = "、".join(lang_names[:6]) or "多种语言"
    plat_names = [p for p in digest.stack.platforms if p not in ("文档",)]
    platforms = "、".join(plat_names) or "通用编程技术"
    top_skills = [e.skill for e in assessment.sorted_entries()[:4]]
    skills_line = "、".join(top_skills) if top_skills else "编程基础"
    lines = [
        "## 1. 我完成了什么项目", "",
        "**" + name + "** 是一个使用 " + langs + " 编写的项目（共 " + str(files) + " 个文件），"
        "主要涉及 " + platforms + "。", "",
        "通过这个项目，你实际接触了：", "",
        "- " + skills_line, ""
    ]
    if files >= 10:
        lines.append("- 完整的项目结构（扫描、模块划分、配置管理）")
    else:
        lines.append("- 一个可运行的小项目")
    lines.append("")
    return "\n".join(lines)


def _classify(assessment, blind_spots):
    """技能三分类：已掌握 / 正在提升 / 未掌握（确定性规则）。"""
    blind_risk = {}
    for b in blind_spots.items:
        blind_risk[b.skill] = b.risk_level
    mastered, improving, missing = [], [], []
    for entry in assessment.sorted_entries():
        if not entry.project_evidence and entry.skill not in blind_risk:
            continue  # 项目未使用且非盲区：与本项目无关
        level = entry.final_level
        risk = blind_risk.get(entry.skill)
        if level in ("advanced", "expert"):
            mastered.append(entry.skill)
        elif level == "intermediate":
            improving.append(entry.skill)
        else:  # beginner
            if risk in ("高风险盲区", "中风险盲区"):
                missing.append(entry.skill)
            elif entry.quiz_score is not None and entry.quiz_score >= 60:
                improving.append(entry.skill)
            else:
                missing.append(entry.skill)
    return mastered, improving, missing


def _section2(assessment, blind_spots) -> str:
    """这个项目让我学到了什么。"""
    mastered, improving, missing = _classify(assessment, blind_spots)
    lines = ["## 2. 这个项目让我学到了什么", ""]
    lines.append("已掌握：")
    for s in mastered:
        lines.append("✓ " + s)
    if not mastered:
        lines.append("（暂未识别到已掌握的新技能，多跑几次复盘会逐步确认）")
    lines.append("")
    lines.append("正在提升：")
    for s in improving:
        lines.append("△ " + s)
    if not improving:
        lines.append("（暂无）")
    lines.append("")
    lines.append("未掌握：")
    for s in missing:
        lines.append("○ " + s)
    if not missing:
        lines.append("（暂无）")
    return "\n".join(lines)


def _section3(evidence, quiz) -> str:
    """AI 协作情况：AI 帮了什么 / 我的参与（全部来自证据数据）。"""
    ai_dom = ai_help = 0
    doc_ai = 0
    tool_calls = 0
    mentions = 0
    for verdict in evidence.per_file.values():
        if verdict.classification == "AI 主导":
            ai_dom += 1
        elif verdict.classification == "AI 辅助":
            ai_help += 1
        if verdict.file.lower().endswith((".md", ".rst")) and verdict.score and verdict.score >= 0.4:
            doc_ai += 1
    for item in evidence.items:
        if "工具调用" in item.detail:
            tool_calls += 1
        elif "提及" in item.detail:
            mentions += 1
    human = sum(1 for v in evidence.per_file.values()
                if v.classification == "疑似人工")
    ai_lines = []
    if ai_dom + ai_help > 0:
        ai_lines.append("- 代码生成（" + str(ai_dom) + " 个文件 AI 主导、" + str(ai_help) + " 个 AI 辅助）")
    if mentions > 0:
        ai_lines.append("- 思路讨论（对话记录 " + str(mentions) + " 条）")
    if tool_calls > 0:
        ai_lines.append("- Debug 与修改（Agent 工具调用 " + str(tool_calls) + " 次）")
    if doc_ai > 0:
        ai_lines.append("- 文档生成（" + str(doc_ai) + " 个文档由 AI 协助）")
    me_lines = []
    if human > 0:
        me_lines.append("- 修改（" + str(human) + " 个文件判定为人工编写）")
    if quiz is not None and quiz.questions:
        me_lines.append("- 理解（完成 " + str(len(quiz.questions)) + " 题实践验证，得分 " + str(quiz.overall) + "）")
    for note in evidence.participation:
        me_lines.append("- " + note)
    lines = ["## 3. AI 协作情况", "", "AI 帮助了什么："]
    lines.extend(ai_lines or ["- （未检测到 AI 协作证据）"])
    lines += ["", "我的参与："]
    lines.extend(me_lines or ["- （证据不足，尚未识别）"])
    return "\n".join(lines)


def _blind_reason(skill: str, evidence_line: str) -> str:
    """盲区证据行 → 口语化「为什么」（保持证据事实，只做措辞映射）。"""
    if "项目核心依赖" in evidence_line or "项目使用" in evidence_line:
        return "项目使用" + skill
    if evidence_line.startswith("Quiz"):
        score = evidence_line.split("分")[0].replace("Quiz", "").strip()
        return "Quiz 得分偏低（" + score + " 分）"
    if "profile 未掌握" in evidence_line:
        return "用户没有相关经验"
    if "主要由 AI 生成" in evidence_line:
        return "相关代码主要由 AI 生成"
    if "profile 标注正在学习" in evidence_line:
        return "刚开始学习，经验不足"
    if "学习目标" in evidence_line:
        return evidence_line
    return evidence_line.split("（")[0]


def _section4(blind_spots) -> str:
    """我的学习盲区：基于 profile/SkillAssessment/Quiz/KnowledgeGraph 计算。"""
    lines = ["## 4. 我的学习盲区", "",
             "> 基于技能档案、技能评估、Quiz 与知识图谱证据计算，非 AI 猜测。", ""]
    picked = [b for b in blind_spots.sorted_items()
              if b.risk_level in ("高风险盲区", "中风险盲区")][:6]
    if not picked:
        lines.append("暂无高/中风险盲区。继续保持！")
        return "\n".join(lines)
    for item in picked:
        lines.append("### " + item.skill)
        lines.append("")
        lines.append("为什么：")
        for ev in item.evidence:
            lines.append("- " + _blind_reason(item.skill, ev))
        lines.append("")
    return "\n".join(lines)


def _verify_line(item) -> str:
    """验证方式：确定性生成。"""
    parts = []
    joined = "；".join(item.reason)
    if "Quiz" in joined:
        parts.append("apr quiz 得分 ≥ 60")
    if "AI生成" in joined:
        parts.append("独立重写 AI 生成代码并通过自测")
    if not parts:
        parts.append("完成实践任务并理解核心概念")
    return " + ".join(parts)


def _section5(plan) -> str:
    """下一步学习路线：短期 1 周 / 中期 1 个月。"""
    lines = ["## 5. 下一步学习路线", ""]
    if not plan.priority:
        lines.append("暂无足够数据生成学习路线。")
        return "\n".join(lines)
    short = [p for p in plan.priority if p.level == "high"][:2]
    mid = [p for p in plan.priority if p not in short][:3]
    lines.append("### 短期（1 周）")
    lines.append("")
    for item in (short or plan.priority[:2]):
        lines.append("- **" + item.skill + "**")
        lines.append("  - 学习目标：" + (item.action[0] if item.action else "学习 " + item.skill + " 基础"))
        lines.append("  - 实践任务：" + (item.action[1] if len(item.action) > 1 else "完成一个练习 Demo"))
        lines.append("  - 验证方式：" + _verify_line(item))
    lines.append("")
    lines.append("### 中期（1 个月）")
    lines.append("")
    if mid:
        for item in mid:
            lines.append("- **" + item.skill + "**")
            lines.append("  - 学习目标：" + (item.action[0] if item.action else "学习 " + item.skill + " 基础"))
            lines.append("  - 实践任务：" + (item.action[1] if len(item.action) > 1 else "完成一个练习 Demo"))
            lines.append("  - 验证方式：" + _verify_line(item))
    else:
        lines.append("（短期任务完成后，下一轮复盘会给出中期任务）")
    if plan.next_projects:
        lines += ["", "**实践项目**："]
        for p in plan.next_projects:
            lines.append("- " + p)
    return "\n".join(lines)
