"""DSH（DeepSeek Harness）JSONL 会话日志适配器。

宽松匹配 DSH 会话结构：
- 顶层 type: user / assistant / system / tool
- 顶层 timestamp（或 time / date）
- message.role / message.content（字符串或块列表）
  - 文本块：{"type": "text", "text": "..."}
  - 工具块：{"type": "tool_use", "name": "Edit", "input": {...}}
- 工具 input 中的 file_path / path / target 归一化为相对路径（优先相对 cwd）
"""
from __future__ import annotations

import json
from pathlib import PurePosixPath

from .base import Adapter, AgentEvent, _clip

_EDIT_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}


class DSHAdapter(Adapter):
    name = "dsh"

    def parse(self, raw: dict, source: str) -> AgentEvent | None:
        message = raw.get("message")
        role = ""
        content_blocks: list = []
        if isinstance(message, dict):
            role = str(message.get("role") or "")
            content = message.get("content")
            if isinstance(content, list):
                content_blocks = content
            elif isinstance(content, str):
                content_blocks = [{"type": "text", "text": content}]

        actor = str(raw.get("type") or role or "unknown")
        timestamp = raw.get("timestamp") or raw.get("time") or raw.get("date") or None
        cwd = str(raw.get("cwd") or "")

        # 工具调用：优先识别（Edit/Write → edit/write；其余 → tool_call）
        for block in content_blocks:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = str(block.get("name") or "tool")
            inp = block.get("input") if isinstance(block.get("input"), dict) else {}
            file_path = self._file(inp, cwd)
            event_type = ("edit" if name in {"Edit", "MultiEdit"} else
                          "write" if name in {"Write", "NotebookEdit"} else "tool_call")
            summary = _clip(json.dumps({k: v for k, v in inp.items()
                                        if k != "old_string" and k != "new_string"},
                                       ensure_ascii=False, default=str), 500)
            return AgentEvent(
                timestamp=str(timestamp) if timestamp else None,
                source=source, actor="assistant", event_type=event_type,
                file=file_path, content=name + " " + summary)

        # 普通消息：文本块拼接
        texts = []
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(str(block.get("text") or ""))
            elif isinstance(block, str):
                texts.append(block)
        text = _clip("\n".join(t for t in texts if t))
        if text:
            return AgentEvent(
                timestamp=str(timestamp) if timestamp else None,
                source=source,
                actor=actor if actor in {"user", "assistant", "system", "tool"} else "unknown",
                event_type="message", file=None, content=text)

        # 顶层直接带内容/文件兜底
        fallback = raw.get("text") or raw.get("content") or raw.get("payload")
        if fallback is not None:
            return AgentEvent(
                timestamp=str(timestamp) if timestamp else None,
                source=source, actor=actor if actor in {"user", "assistant", "system", "tool"} else "unknown",
                event_type=str(raw.get("event_type") or raw.get("event") or "record"),
                file=self._file(raw, cwd), content=_clip(fallback))
        return None

    @staticmethod
    def _file(entry: dict, cwd: str) -> str | None:
        fp = entry.get("file_path") or entry.get("path") or entry.get("target")
        if not fp:
            return None
        fp_n = str(fp).replace("\\", "/")
        if cwd:
            cwd_n = cwd.replace("\\", "/").rstrip("/")
            # 兼容盘符：C:/proj/x 与 /proj/x 统一比较
            drive_fp = fp_n.split(":", 1)[1] if ":" in fp_n.split("/", 1)[0] else fp_n
            drive_cwd = cwd_n.split(":", 1)[1] if ":" in cwd_n.split("/", 1)[0] else cwd_n
            if drive_cwd and drive_fp.startswith(drive_cwd + "/"):
                fp_n = drive_fp[len(drive_cwd) + 1:]
        return PurePosixPath(fp_n).as_posix().lstrip("/") or None
