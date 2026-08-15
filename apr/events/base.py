"""统一 Agent Event 系统：规范事件模型与 Adapter 抽象。

把不同 Agent 的日志统一转换为 AgentEvent：
- timestamp: 时间戳（ISO 字符串，可为空）
- source:    来源标识（dsh / generic / ...）
- actor:     行为主体（user / assistant / tool / system / unknown）
- event_type: 事件类型（message / edit / write / tool_call / tool_result / record ...）
- file:      涉及文件（归一化相对路径，可为空）
- content:   文本内容（消息正文 / 工具摘要 / 记录原文，长度受限）

Adapter.parse 返回事件列表：一行日志可以产出多个事件（例如
assistant/message 中同时包含多个 tool-call 与文本）。
本模块独立于 evidence 层：不修改、不复用 evidence/agent_logs.py。
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

MAX_CONTENT = 2000


@dataclass
class AgentEvent:
    timestamp: str | None = None
    source: str = ""
    actor: str = "unknown"
    event_type: str = "record"
    file: str | None = None
    content: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "source": self.source,
            "actor": self.actor,
            "event_type": self.event_type,
            "file": self.file,
            "content": self.content,
        }


class Adapter(ABC):
    """日志适配器：把一行 JSON 原始对象转换为事件列表（无匹配返回空列表）。"""

    name: str = "base"

    @abstractmethod
    def parse(self, raw: dict, source: str) -> list[AgentEvent]: ...

    def parse_line(self, line: str, source: str) -> list[AgentEvent]:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return []
        if not isinstance(obj, dict):
            return []
        events = self.parse(obj, source)
        for event in events:
            if event.source == "":
                event.source = source
        return events


def parse_events(lines: Iterable[str], adapter: Adapter, source: str) -> list[AgentEvent]:
    """逐行解析 JSONL 文本，返回所有成功转换的事件。"""
    events: list[AgentEvent] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        events.extend(adapter.parse_line(line, source))
    return events


def _clip(text: str, limit: int = MAX_CONTENT) -> str:
    text = str(text)
    return text if len(text) <= limit else text[:limit] + "…"
