"""证据模型：多源采集的统一表示。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EvidenceSource(str, Enum):
    GIT = "git"
    AGENT_LOG = "agent-log"
    MARKER = "marker"
    CHANGE = "change-trace"


@dataclass
class EvidenceItem:
    source: EvidenceSource
    file: str | None = None
    detail: str = ""
    when: str | None = None
    ai_score: float | None = None   # 该证据暗示的 AI 参与度（0~1）
    confidence: float = 0.5         # 证据可信度（0~1）

    def short(self) -> str:
        when = f" @{self.when}" if self.when else ""
        return f"[{self.source.value}]{when} {self.detail}"


@dataclass
class FileVerdict:
    file: str
    score: float | None
    confidence: float
    items: list[EvidenceItem] = field(default_factory=list)

    @property
    def classification(self) -> str:
        if self.score is None or self.confidence < 0.3:
            return "证据不足"
        if self.score >= 0.7:
            return "AI 主导"
        if self.score >= 0.4:
            return "AI 辅助"
        return "疑似人工"


@dataclass
class EvidenceReport:
    items: list[EvidenceItem] = field(default_factory=list)
    per_file: dict[str, FileVerdict] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    participation: list[str] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        result = {"AI 主导": 0, "AI 辅助": 0, "疑似人工": 0, "证据不足": 0}
        for v in self.per_file.values():
            result[v.classification] += 1
        return result

    def top_ai(self, n: int = 10) -> list[FileVerdict]:
        scored = [v for v in self.per_file.values() if v.score is not None and v.confidence >= 0.3]
        scored.sort(key=lambda v: (-v.score, v.file))
        return scored[:n]

    def ai_share(self) -> float | None:
        scored = [v.score for v in self.per_file.values() if v.score is not None and v.confidence >= 0.3]
        return (sum(scored) / len(scored)) if scored else None

    def summary_text(self, top_n: int = 25) -> str:
        c = self.counts()
        n_dom = c["AI 主导"]
        n_help = c["AI 辅助"]
        n_human = c["疑似人工"]
        n_unknown = c["证据不足"]
        lines = [
            "## AI 生成证据摘要",
            f"- 证据总数：{len(self.items)} 条（来源：git / agent-log / marker）",
            f"- 文件级判定：AI 主导 {n_dom} / AI 辅助 {n_help} / 疑似人工 {n_human} / 证据不足 {n_unknown}",
        ]
        share = self.ai_share()
        if share is not None:
            lines.append(f"- 有证据文件的平均 AI 贡献度：{share:.0%}")
        for v in self.top_ai(top_n):
            lines.append(f"- {v.file}：AI 贡献度 {v.score:.0%}，置信度 {v.confidence:.0%}，"
                         f"判定「{v.classification}」；证据：" + " | ".join(i.short() for i in v.items[:3]))
        for p in self.participation:
            lines.append(p)
        return "\n".join(lines)

    def summary_markdown(self, top_n: int = 50) -> str:
        c = self.counts()
        lines = [
            "### 判定总览",
            "",
            "| 判定 | 文件数 |",
            "| --- | --- |",
        ]
        for k, v in c.items():
            lines.append(f"| {k} | {v} |")
        share = self.ai_share()
        lines.append("")
        if share is not None:
            lines.append(f"**有证据文件的平均 AI 贡献度**：{share:.0%}")
        else:
            lines.append("**有证据文件的平均 AI 贡献度**：无")
        lines += ["", "### 文件级证据明细", "",
                  "| 文件 | AI 贡献度 | 置信度 | 判定 | 证据摘要 |",
                  "| --- | --- | --- | --- | --- |"]
        for v in self.top_ai(top_n):
            detail = "；".join(i.short() for i in v.items[:3])
            lines.append(f"| {v.file} | {v.score:.0%} | {v.confidence:.0%} | {v.classification} | {detail} |")
        for p in self.participation:
            lines.append("")
            lines.append(f"- {p}")
        return "\n".join(lines)
