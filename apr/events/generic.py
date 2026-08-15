"""通用 JSONL 适配器（兜底方案）。

兼容任意 JSONL 记录：
- OpenAI 风格 {"role": ..., "content": ...} → message
- 带 type/timestamp/text/file_path 的记录 → 对应字段映射
- 其他 dict → record（content 为紧凑 JSON 摘要）

无法解析的行返回 None（跳过）。
"""
from __future__ import annotations

import json

from .base import Adapter, AgentEvent, _clip

_ACTORS = {"user", "assistant", "system", "tool"}


class GenericAdapter(Adapter):
    name = "generic"

    def parse(self, raw: dict, source: str) -> AgentEvent | None:
        timestamp = raw.get("timestamp") or raw.get("time") or raw.get("date") or None
        file_path = raw.get("file_path") or raw.get("path") or raw.get("file") or raw.get("target")

        # OpenAI 风格消息
        role = raw.get("role")
        content = raw.get("content")
        if isinstance(role, str) and content is not None:
            actor = role if role in _ACTORS else "unknown"
            return AgentEvent(
                timestamp=str(timestamp) if timestamp else None,
                source=source, actor=actor, event_type="message",
                file=str(file_path).replace("\\", "/") if file_path else None,
                content=_clip(content))

        # 结构化记录：type + text/message/content
        rtype = raw.get("type") or raw.get("event_type") or raw.get("event")
        text = raw.get("text") or raw.get("message") or raw.get("content")
        if isinstance(text, dict):
            text = json.dumps(text, ensure_ascii=False)
        if text is not None or file_path is not None:
            actor = str(rtype) if rtype in _ACTORS else "unknown"
            return AgentEvent(
                timestamp=str(timestamp) if timestamp else None,
                source=source, actor=actor,
                event_type=str(rtype or "record"),
                file=str(file_path).replace("\\", "/") if file_path else None,
                content=_clip(text if text is not None else ""))

        # 兜底：任何 dict 都转成 record
        return AgentEvent(
            timestamp=str(timestamp) if timestamp else None,
            source=source, actor="unknown", event_type="record",
            file=None, content=_clip(json.dumps(raw, ensure_ascii=False, default=str)))
