"""报告渲染：8 大板块 + 附录。"""
from __future__ import annotations

from . import __version__
from .analyzer import ReviewResult


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
    meta.append(f"{len(result.sections) + 1}. [附录 A：AI 生成证据明细](#附录-aai-生成证据明细)")
    if result.quiz:
        meta.append(f"{len(result.sections) + 2}. [附录 B：实践验证记录](#附录-b实践验证记录)")
    body = ["", "---", ""]
    for title, md in result.sections:
        body.append(md)
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
