"""统一 Agent Event 系统。

用法：
    from apr.events import load_events, ADAPTERS
    events = load_events(Path("sessions.jsonl"), source="dsh")
    events = load_events(Path("chat.jsonl"))          # 默认通用适配器

已支持：dsh（DeepSeek Harness JSONL）、generic（通用 JSONL）。
暂不实现 Cursor 适配器。
"""
from __future__ import annotations

from pathlib import Path

from .base import Adapter, AgentEvent, parse_events
from .dsh import DSHAdapter
from .generic import GenericAdapter

ADAPTERS: dict[str, Adapter] = {
    "dsh": DSHAdapter(),
    "generic": GenericAdapter(),
}


def load_events(path: Path, source: str | None = None) -> list[AgentEvent]:
    """读取 JSONL 文件并转换为统一事件列表。source 缺省时用通用适配器。"""
    adapter = ADAPTERS.get(source or "generic")
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return parse_events(text.splitlines(), adapter, adapter.name)


__all__ = ["Adapter", "AgentEvent", "ADAPTERS", "load_events", "parse_events",
           "DSHAdapter", "GenericAdapter"]
