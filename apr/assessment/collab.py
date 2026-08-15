"""AI 协作分析：分析用户与 AI 如何共同完成项目（非作弊检测）。

基于既有证据系统（EvidenceReport，不做任何修改）确定性计算：
1. AI 参与比例：AI 代码生成 / AI 辅助修改 / 人工设计
2. AI 参与类型：代码生成 / Debug辅助 / 架构讨论 / 文档生成 / 学习解释
3. 用户参与行为：直接接受 / 修改 / 重构 AI 代码 / 自己设计模块
4. 优势与提升建议
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..evidence.base import EvidenceReport


@dataclass
class AIContributionReport:
    ai_generation_pct: int = 0
    ai_assist_pct: int = 0
    human_pct: int = 0
    participation_types: list[str] = field(default_factory=list)
    user_behaviors: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "participation": {
                "ai_generation": self.ai_generation_pct,
                "ai_assist": self.ai_assist_pct,
                "human": self.human_pct,
            },
            "ai_participation_types": list(self.participation_types),
            "user_behaviors": list(self.user_behaviors),
            "strengths": list(self.strengths),
            "suggestions": list(self.suggestions),
        }

    def render_markdown(self) -> str:
        lines = [
            "## AI 协作分析", "",
            "> 本节分析你与 AI 如何共同完成这个项目（基于 Git / Agent 日志 / 代码标记证据，不是作弊检测，而是协作复盘）。", "",
            "本项目 AI 协作情况：", "",
            "**AI 参与比例**：", "",
            "| AI 代码生成 | AI 辅助修改 | 人工设计 |",
            "| --- | --- | --- |",
            f"| {self.ai_generation_pct}% | {self.ai_assist_pct}% | {self.human_pct}% |",
            "",
            "**AI 主要用于**：", "",
        ]
        lines.extend("- ✓ " + t for t in (self.participation_types or ["（证据不足，暂无法判断）"]))
        lines += ["", "**你的参与**：", ""]
        lines.extend("- " + b for b in (self.user_behaviors or ["（证据不足，暂无法判断）"]))
        lines += ["", "**你的优势**：", ""]
        lines.extend("- " + s for s in (self.strengths or ["（待更多证据确认）"]))
        lines += ["", "**提升建议**：", ""]
        lines.extend("- " + s for s in (self.suggestions or ["保持当前协作方式，定期复盘巩固。"]))
        if self.notes:
            lines += ["", "备注："]
            lines.extend("- " + n for n in self.notes)
        return "\n".join(lines)


def build_ai_collab_report(evidence: EvidenceReport) -> AIContributionReport:
    """从证据层计算 AI 协作分析报告。"""
    report = AIContributionReport()

    verdicts = [v for v in evidence.per_file.values()
                if v.score is not None and v.confidence >= 0.3]
    unverified = len(evidence.per_file) - len(verdicts)
    ai_gen = sum(1 for v in verdicts if v.classification == "AI 主导")
    ai_assist = sum(1 for v in verdicts if v.classification == "AI 辅助")
    human = sum(1 for v in verdicts if v.classification == "疑似人工")
    total = len(verdicts)

    if total > 0:
        report.ai_generation_pct = round(ai_gen / total * 100)
        report.ai_assist_pct = round(ai_assist / total * 100)
        report.human_pct = max(0, 100 - report.ai_generation_pct - report.ai_assist_pct)
    if unverified > 0:
        report.notes.append(f"{unverified} 个文件证据不足，未计入比例")

    # ---- 2. AI 参与类型（五类，按证据激活）----
    tool_calls = sum(1 for i in evidence.items if "工具调用" in i.detail)
    mentions = sum(1 for i in evidence.items if "提及" in i.detail)
    doc_ai = sum(1 for v in evidence.per_file.values()
                 if v.file.lower().endswith((".md", ".rst")) and v.score
                 and v.score >= 0.4 and v.confidence >= 0.3)
    if ai_gen + ai_assist > 0:
        report.participation_types.append(f"代码生成（{ai_gen + ai_assist} 个文件由 AI 主导或辅助）")
    if tool_calls > 0:
        report.participation_types.append(f"Debug辅助（Agent 工具调用 {tool_calls} 次）")
    if mentions > 0:
        report.participation_types.append(f"架构讨论（对话记录提及 {mentions} 条）")
    if doc_ai > 0:
        report.participation_types.append(f"文档生成（{doc_ai} 个文档由 AI 协助）")
    for p in evidence.participation:
        m = re.search(r"用户消息 (\d+) / 助手消息 (\d+)", p)
        if m and int(m.group(2)) > int(m.group(1)) * 1.5:
            report.participation_types.append(
                "学习解释（助手解释为主，消息比 " + m.group(2) + ":" + m.group(1) + "）")

    # ---- 3. 用户参与行为（Git 提交 / Agent 日志 / 文件修改记录推断）----
    if ai_gen > 0:
        report.user_behaviors.append(f"直接接受 AI 代码（{ai_gen} 个文件判定 AI 主导）")
    if ai_assist > 0:
        report.user_behaviors.append(f"修改 AI 代码（{ai_assist} 个文件在 AI 基础上人工修改）")
    refactor = 0
    for v in verdicts:
        for i in v.items:
            m = re.search(r"(\d+)/(\d+) 次提交疑似 AI 参与", i.detail)
            if m and int(m.group(1)) > 0 and int(m.group(1)) < int(m.group(2)):
                refactor += 1
                break
    if refactor > 0:
        report.user_behaviors.append(
            f"重构 AI 代码（{refactor} 个文件先后经历 AI 与人工提交）")
    if human > 0:
        report.user_behaviors.append(f"自己设计模块（{human} 个文件判定人工编写）")

    # ---- 4. 优势与建议 ----
    if ai_assist + refactor + human > ai_gen:
        report.strengths.append("能够修改和整合 AI 代码")
    if report.human_pct >= 40:
        report.strengths.append("保持了较高的人工参与比例")
    if ai_gen == 0 and human > 0:
        report.strengths.append("项目主体为独立设计")

    if total > 0 and ai_gen / total >= 0.5:
        report.suggestions.append("尝试减少直接复制 AI 输出，先读懂再整合。")
    if ai_gen > 0:
        report.suggestions.append("对 AI 生成的模块逐个做代码评审。")
    if total > 0 and report.human_pct < 30:
        report.suggestions.append("尝试先自己设计，再让 AI 实现。")
    return report
