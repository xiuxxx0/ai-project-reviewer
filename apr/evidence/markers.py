"""代码内 AI 标记扫描。

识别注释中的 AI 生成标记（如 # AI-GENERATED、// written by claude）与人工标记
（# HAND-WRITTEN 等），转换为文件级证据。
"""
from __future__ import annotations

import re
from pathlib import Path

from ..scanner import ScanResult
from .base import EvidenceItem, EvidenceSource

POSITIVE_PAT = re.compile(
    r"(?i)\b(ai[\-\s]?generated|generated\s+by\s+(?:ai|an?\s+ai|claude|copilot|cursor|"
    r"chat\s?gpt|gpt-4|gpt|gemini|bard|codex|deepseek|qwen|codeium)|"
    r"written\s+by\s+(?:claude|copilot|cursor|chat\s?gpt|gpt|gemini|deepseek|codex)|"
    r"@ai\b|ai[\-\s]?written|co[\-\s]?authored\s+by\s+(?:claude|copilot|cursor|gpt))")
NEGATIVE_PAT = re.compile(
    r"(?i)\b(hand[\-\s]?written|written\s+by\s+(?:me|myself|human|author)|"
    r"not\s+(?:written\s+by\s+)?ai|human[\-\s]?written|@human\b|我手写|手动编写|人工编写)")


def scan_markers(scan: ScanResult) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for f in scan.files:
        if not f.is_text or f.too_big or f.size == 0:
            continue
        try:
            text = Path(f.abs).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        pos = len(POSITIVE_PAT.findall(text))
        neg = len(NEGATIVE_PAT.findall(text))
        if pos == 0 and neg == 0:
            continue
        pos_lines = [ln.strip()[:120] for ln in text.splitlines() if POSITIVE_PAT.search(ln)][:2]
        neg_lines = [ln.strip()[:120] for ln in text.splitlines() if NEGATIVE_PAT.search(ln)][:2]
        if pos > 0 and neg == 0:
            score = min(0.95, 0.6 + 0.35 * min(pos / 20, 1.0))
            conf = 0.85
            detail = f"检测到 {pos} 处 AI 生成标记，如：{' | '.join(pos_lines)}"
        elif neg > 0 and pos == 0:
            score, conf = 0.1, 0.8
            detail = f"检测到 {neg} 处人工编写标记，如：{' | '.join(neg_lines)}"
        else:
            score = min(0.9, 0.5 + 0.3 * min(pos / 20, 1.0))
            conf = 0.6
            detail = f"同时存在 AI 标记({pos})与人工标记({neg})"
        items.append(EvidenceItem(source=EvidenceSource.MARKER, file=f.rel,
                                  detail=detail, ai_score=score, confidence=conf))
    return items
