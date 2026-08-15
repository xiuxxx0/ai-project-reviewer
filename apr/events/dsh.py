"""DSH（DeepSeek Harness）JSONL 会话日志适配器。

真实 DSH 格式（type 为事件式）：
- {"type":"session", "cwd":"...", "createdAt":<ms>}          → 跳过（仅取 cwd 上下文）
- {"type":"user/message", "time":<ms>, "data":{"content":[块]}}    → message
- {"type":"assistant/message", "data":{"content":[块]}}
    - 文本/推理块 → message
    - {"type":"tool-call","name":"...","arguments":"<JSON 字符串>"} → tool_call/edit/write
- {"type":"tool/result", "data":{"callId","content":[块],"isError"}} → tool_result

同时兼容旧假设格式（type=user/assistant + message.role/content，Claude 风格）。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import PurePosixPath

from .base import Adapter, AgentEvent, _clip

_EDIT_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit", "edit", "write"}


def _ms_to_iso(value) -> str | None:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()
        except (ValueError, OSError, OverflowError):
            return str(value)
    return str(value) if value else None


class DSHAdapter(Adapter):
    name = "dsh"

    def __init__(self):
        self._cwd = ""   # 会话级 cwd（session 行携带，后续事件行复用）

    def parse(self, raw: dict, source: str) -> list[AgentEvent]:
        etype = str(raw.get("type") or "")
        timestamp = _ms_to_iso(raw.get("time") or raw.get("createdAt") or raw.get("timestamp"))
        if etype == "session":
            self._cwd = str(raw.get("cwd") or "")
        cwd = str(raw.get("cwd") or self._cwd)
        data = raw.get("data") if isinstance(raw.get("data"), dict) else {}

        # ---- 真实 DSH 事件式格式 ----
        if etype == "user/message":
            text = _join_text(data.get("content"))
            return [AgentEvent(timestamp=timestamp, source=source, actor="user",
                               event_type="message", file=None, content=_clip(text))] if text else []
        if etype == "assistant/message":
            return self._assistant_blocks(data.get("content"), timestamp, source, cwd)
        if etype == "tool/result":
            text = _join_text(data.get("content"))
            error = bool(data.get("isError"))
            return [AgentEvent(timestamp=timestamp, source=source, actor="tool",
                               event_type="tool_result", file=None,
                               content=_clip(("错误：\n" if error else "") + text))]
        if etype in ("session", "turn/start", "turn/end", "session/title",
                     "session/rename", "mode/set", "turn/complete"):
            return []  # 会话级记录不产出事件

        # ---- 旧假设格式（Claude 风格，宽容兼容）----
        message = raw.get("message")
        if isinstance(message, dict):
            role = str(message.get("role") or "")
            content = message.get("content")
            blocks = content if isinstance(content, list) else (
                [{"type": "text", "text": content}] if isinstance(content, str) else [])
            if any(isinstance(b, dict) and b.get("type") == "tool_use" for b in blocks):
                return self._assistant_blocks(blocks, timestamp, source, cwd,
                                              tool_block_key="tool_use", input_key="input")
            text = _join_text(blocks)
            if text:
                actor = role if role in {"user", "assistant", "system", "tool"} else "unknown"
                return [AgentEvent(timestamp=timestamp, source=source, actor=actor,
                                   event_type="message", file=None, content=_clip(text))]

        # ---- 顶层兜底 ----
        fallback = raw.get("text") or raw.get("content") or raw.get("payload")
        if fallback is not None:
            actor = str(raw.get("type") or "unknown")
            return [AgentEvent(timestamp=timestamp, source=source,
                               actor=actor if actor in {"user", "assistant", "system", "tool"} else "unknown",
                               event_type=str(raw.get("event_type") or raw.get("event") or "record"),
                               file=self._file(raw, cwd), content=_clip(fallback))]
        return []

    @classmethod
    def _assistant_blocks(cls, content, timestamp, source, cwd,
                          tool_block_key="tool-call", input_key="arguments") -> list[AgentEvent]:
        events: list[AgentEvent] = []
        texts: list[str] = []
        for block in content or []:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == tool_block_key:
                name = str(block.get("name") or "tool")
                if input_key == "arguments":
                    args_raw = block.get("arguments") or "{}"
                    if isinstance(args_raw, str):
                        try:
                            args_obj = json.loads(args_raw)
                        except json.JSONDecodeError:
                            args_obj = {"arguments": args_raw}
                    else:
                        args_obj = args_raw if isinstance(args_raw, dict) else {}
                else:
                    args_obj = block.get(input_key) if isinstance(block.get(input_key), dict) else {}
                event_type = ("edit" if name in {"Edit", "MultiEdit", "edit"} else
                              "write" if name in {"Write", "NotebookEdit", "write"} else "tool_call")
                events.append(AgentEvent(
                    timestamp=timestamp, source=source, actor="assistant",
                    event_type=event_type, file=cls._file(args_obj, cwd),
                    content=_clip(name + " " + json.dumps(
                        {k: v for k, v in args_obj.items()
                         if k not in ("old_string", "new_string", "code", "fullSource")},
                        ensure_ascii=False, default=str)[:500])))
            elif btype in ("text", "reasoning"):
                texts.append(str(block.get("text") or ""))
        if texts:
            events.append(AgentEvent(timestamp=timestamp, source=source, actor="assistant",
                                     event_type="message", file=None,
                                     content=_clip("\n".join(t for t in texts if t))))
        return events

    @staticmethod
    def _file(entry: dict, cwd: str) -> str | None:
        fp = entry.get("file_path") or entry.get("path") or entry.get("target")
        if not fp:
            return None
        fp_n = str(fp).replace("\\", "/")
        if cwd:
            cwd_n = cwd.replace("\\", "/").rstrip("/")
            drive_fp = fp_n.split(":", 1)[1] if ":" in fp_n.split("/", 1)[0] else fp_n
            drive_cwd = cwd_n.split(":", 1)[1] if ":" in cwd_n.split("/", 1)[0] else cwd_n
            if drive_cwd and drive_fp.startswith(drive_cwd + "/"):
                fp_n = drive_fp[len(drive_cwd) + 1:]
        return PurePosixPath(fp_n).as_posix().lstrip("/") or None


def _join_text(content) -> str:
    parts = []
    for block in content or []:
        if isinstance(block, dict) and block.get("type") in ("text", "reasoning"):
            parts.append(str(block.get("text") or ""))
        elif isinstance(block, str):
            parts.append(block)
    return "\n".join(p for p in parts if p)
