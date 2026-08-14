"""多源证据融合：按文件聚合、加权平均 → AI 贡献度与判定。"""
from __future__ import annotations

import math

from .base import EvidenceItem, EvidenceReport, EvidenceSource, FileVerdict

WEIGHTS = {EvidenceSource.MARKER: 1.0, EvidenceSource.AGENT_LOG: 0.9,
           EvidenceSource.GIT: 0.8, EvidenceSource.CHANGE: 0.8}


def fuse(items: list[EvidenceItem], scan_files: set[str], notes: list[str],
         participation: list[str] | None = None) -> EvidenceReport:
    report = EvidenceReport(items=items, notes=notes, participation=participation or [])
    dropped = 0
    grouped: dict[str, list[EvidenceItem]] = {}
    for item in items:
        if item.file is None:
            continue
        f = item.file.replace("\\", "/").strip().lstrip("./")
        if f not in scan_files:
            dropped += 1
            continue
        grouped.setdefault(f, []).append(item)
    if dropped:
        report.notes.append(f"融合时丢弃 {dropped} 条指向已删除/未扫描文件的证据")
    for f, its in grouped.items():
        scored = []
        weight_conf_sum = 0.0
        weight_sum = 0.0
        for i in its:
            if i.ai_score is None:
                continue
            w = WEIGHTS.get(i.source, 0.7)
            scored.append(i)
            weight_conf_sum += w * i.confidence
            weight_sum += w
        if not scored:
            continue
        score = sum(i.ai_score * i.confidence * WEIGHTS.get(i.source, 0.7)
                    for i in scored) / weight_conf_sum
        conf = min(0.95, (sum(i.confidence * WEIGHTS.get(i.source, 0.7) for i in scored) / weight_sum)
                   + 0.05 * math.log2(1 + len(scored)))
        report.per_file[f] = FileVerdict(file=f, score=score, confidence=conf, items=scored)
    return report
