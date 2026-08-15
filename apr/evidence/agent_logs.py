"""Agent 对话/行为记录：统一事件模型与多适配器解析。

统一事件模型 AgentEvent：agent 来源、行为类型（user/assistant/edit/write/tool/mention）、
涉及文件、时间。适配器：
- 手动文本导入：<项目>/.apr/logs 下的 txt/md/log/json/jsonl（通用兜底）
- Claude Code：~/.claude/projects/**/*.jsonl（工具调用轨迹）
- DSH / Cursor：可选配置目录，按通用 JSON/JSONL 解析
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from ..scanner import ScanResult
from .base import EvidenceItem, EvidenceSource

STRONG_PATH_KEYS = {"file", "file_path", "filepath", "path", "target", "filename",
                    "rel_path", "relative_path", "fileName", "filePath"}
_Q = chr(34) + chr(39) + chr(96)  # " ' 反引号


@dataclass
class AgentEvent:
    agent: str
    kind: str            # user | assistant | edit | write | tool | mention
    file: str | None = None
    when: str | None = None
    detail: str = ""


def _norm_rel(path: str) -> str:
    p = path.replace("\\", "/").strip().strip(_Q)
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def _match_any(value: str, rel_set: set[str]) -> str | None:
    n = _norm_rel(value)
    if n in rel_set:
        return n
    base = Path(n).name
    hits = [r for r in rel_set if Path(r).name == base]
    if len(hits) == 1:
        return hits[0]
    return None


def _tokenize(line: str) -> list[str]:
    return [t for t in re.split(r"[\s\"';:()<>\[\]{}=|]+", line)
            if t and ("/" in t or "." in t)]


def _events_from_json_obj(obj, rel_set: set[str], agent: str, when=None) -> list[AgentEvent]:
    events: list[AgentEvent] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in STRONG_PATH_KEYS and isinstance(value, str):
                rel = _match_any(value, rel_set)
                if rel:
                    kind = "edit" if str(key).lower() in ("file_path", "filepath", "target") else "mention"
                    events.append(AgentEvent(
                        agent=agent, kind=kind, file=rel,
                        when=str(obj.get("timestamp") or obj.get("time") or when or ""),
                        detail=f"JSON 字段 {key} 指向 {rel}"))
            events.extend(_events_from_json_obj(value, rel_set, agent, when))
    elif isinstance(obj, list):
        for item in obj:
            events.extend(_events_from_json_obj(item, rel_set, agent, when))
    return events


def _events_from_text_or_json(text: str, rel_set: set[str], agent: str) -> list[AgentEvent]:
    events: list[AgentEvent] = []
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            return _events_from_json_obj(json.loads(stripped), rel_set, agent, None)
        except json.JSONDecodeError:
            pass
    for line in stripped.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("{") and s.endswith("}"):
            try:
                events.extend(_events_from_json_obj(json.loads(s), rel_set, agent, None))
                continue
            except json.JSONDecodeError:
                pass
        for token in _tokenize(s):
            rel = _norm_rel(token)
            if rel in rel_set:
                events.append(AgentEvent(agent=agent, kind="mention", file=rel,
                                         detail=f"对话文本提及 {rel}"))
                break
    return events


def collect_manual(root: Path, scan: ScanResult, manual_dir: str):
    """解析项目内手动导入的对话记录（.apr/logs 下的 txt/md/log/json/jsonl）。"""
    events: list[AgentEvent] = []
    notes: list[str] = []
    base = root / manual_dir
    if not base.is_dir():
        return events, notes
    rel_set = scan.rel_set()
    files = [p for p in base.rglob("*") if p.is_file()]
    if not files:
        return events, notes
    for path in files:
        try:
            size = path.stat().st_size
            if size > 20 * 1024 * 1024:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        events.extend(_events_from_text_or_json(text, rel_set, f"manual:{path.name}"))
    seen = set()
    deduped = []
    for ev in events:
        key = (ev.file, ev.kind, ev.agent)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ev)
    notes.append(f"手动日志：解析 {len(files)} 个文件，得到 {len(deduped)} 条文件提及事件（{manual_dir}）")
    return deduped[:300], notes


def collect_claude(root: Path, scan: ScanResult, claude_dir: str):
    events: list[AgentEvent] = []
    notes: list[str] = []
    base = Path(claude_dir).expanduser()
    if not base.is_dir():
        return events, notes
    rel_set = scan.rel_set()
    jsonl_files = sorted([p for p in base.rglob("*.jsonl") if p.is_file()],
                         key=lambda p: p.stat().st_mtime, reverse=True)[:30]
    user_msgs = assistant_msgs = edits = 0
    for path in jsonl_files:
        try:
            size = path.stat().st_size
            if size > 50 * 1024 * 1024:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            cwd = obj.get("cwd") or ""
            ts = obj.get("timestamp") or ""
            mtype = obj.get("type")
            if mtype == "user":
                user_msgs += 1
                continue
            if mtype != "assistant":
                continue
            assistant_msgs += 1
            message = obj.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = block.get("name") or ""
                inp = block.get("input") if isinstance(block.get("input"), dict) else {}
                fp = inp.get("file_path") or inp.get("path") or ""
                if not fp:
                    continue
                rel = _match_claude_path(fp, cwd, rel_set)
                if not rel:
                    continue
                edits += 1
                kind = "edit" if name in ("Edit", "MultiEdit") else (
                    "write" if name in ("Write", "NotebookEdit") else "tool")
                events.append(AgentEvent(agent="claude-code", kind=kind, file=rel, when=str(ts),
                                         detail=f"Claude Code 工具调用 {name} 修改 {rel}"))
    if jsonl_files:
        notes.append(f"Claude Code 日志：解析 {len(jsonl_files)} 个会话文件，识别 {edits} 次文件编辑事件"
                     f"（用户消息 {user_msgs} / 助手消息 {assistant_msgs}）")
    return events, notes


def _match_claude_path(fp: str, cwd: str, rel_set: set[str]) -> str | None:
    direct = _match_any(fp, rel_set)
    if direct:
        return direct
    p = Path(fp)
    if p.is_absolute() and cwd:
        try:
            rel = Path(fp).relative_to(cwd).as_posix()
        except ValueError:
            rel = ""
        if rel in rel_set:
            return rel
    return None


def collect_generic(root: Path, scan: ScanResult, base: Path, agent: str):
    events: list[AgentEvent] = []
    notes: list[str] = []
    if not base.is_dir():
        return events, notes
    rel_set = scan.rel_set()
    candidates = [p for p in list(base.rglob("*.jsonl")) + list(base.rglob("*.json")) if p.is_file()]
    candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[:50]
    for path in candidates:
        try:
            size = path.stat().st_size
            if size > 50 * 1024 * 1024:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            s = line.strip()
            if not s or not s.startswith("{"):
                continue
            try:
                events.extend(_events_from_json_obj(json.loads(s), rel_set, agent, None))
            except json.JSONDecodeError:
                continue
    if candidates:
        notes.append(f"{agent} 日志：解析 {len(candidates)} 个文件，得到 {len(events)} 条提及/编辑事件")
    return events[:300], notes


def collect_dsh_events(root: Path, scan: ScanResult, dsh_dir: str):
    """用统一事件系统（apr.events）解析 DSH JSONL，桥接为证据项。

    事件 → 证据映射：edit/write → AI 编辑证据；tool_call → 工具调用；
    tool_result/record → 弱提及。仅保留能匹配到项目文件的证据。
    """
    from ..events import load_events
    items: list[EvidenceItem] = []
    notes: list[str] = []
    base = Path(dsh_dir).expanduser()
    if not base.is_dir():
        return items, notes
    rel_set = scan.rel_set()
    files = sorted([p for p in base.rglob("*.jsonl") if p.is_file()],
                   key=lambda p: p.stat().st_mtime, reverse=True)[:50]
    score_map = {"edit": (0.85, 0.8), "write": (0.8, 0.8), "tool_call": (0.6, 0.5),
                 "tool_result": (0.3, 0.4), "record": (0.4, 0.45)}
    seen: set = set()
    total = 0
    for path in files:
        try:
            events = load_events(path, source="dsh")
        except OSError:
            continue
        for ev in events:
            if not ev.file:
                continue
            rel = _match_any(ev.file, rel_set)
            if not rel or (rel, ev.event_type) in seen:
                continue
            seen.add((rel, ev.event_type))
            total += 1
            score, conf = score_map.get(ev.event_type, (0.4, 0.45))
            when = str(ev.timestamp)[:10] if ev.timestamp else None
            items.append(EvidenceItem(
                source=EvidenceSource.AGENT_LOG, file=rel,
                detail=f"dsh: {ev.event_type} {rel}（{ev.actor}）",
                when=when, ai_score=score, confidence=conf))
    if files:
        notes.append(f"DSH 日志（统一事件系统）：解析 {len(files)} 个文件，桥接 {total} 条证据")
    return items, notes


def collect_agent_evidence(root: Path, scan: ScanResult, config):
    """聚合所有 Agent 日志源。返回 (证据列表, 参与度描述, 备注列表)。"""
    events: list[AgentEvent] = []
    notes: list[str] = []
    participation: list[str] = []
    if config.manual_logs_dir:
        evs, nts = collect_manual(root, scan, config.manual_logs_dir)
        events.extend(evs)
        notes.extend(nts)
    if config.claude_projects_dir:
        evs, nts = collect_claude(root, scan, config.claude_projects_dir)
        events.extend(evs)
        notes.extend(nts)
    if config.dsh_logs_dir:
        evs, nts = collect_dsh_events(root, scan, config.dsh_logs_dir)
        events.extend(evs)
        notes.extend(nts)
    if config.cursor_logs_dir:
        evs, nts = collect_generic(root, scan, Path(config.cursor_logs_dir).expanduser(), "cursor")
        events.extend(evs)
        notes.extend(nts)
    items = events_to_items(events)
    users = sum(1 for e in events if e.kind == "user")
    assistants = sum(1 for e in events if e.kind == "assistant")
    if users or assistants:
        participation.append(f"Agent 会话参与度：用户消息 {users} / 助手消息 {assistants}"
                             f"（比值约 {users / max(1, assistants):.1f}:1）")
    return items, participation, notes


def events_to_items(events: list[AgentEvent]) -> list[EvidenceItem]:
    score_map = {"edit": (0.85, 0.8), "write": (0.8, 0.8), "tool": (0.6, 0.5),
                 "mention": (0.4, 0.45)}
    seen: set = set()
    items: list[EvidenceItem] = []
    for ev in events:
        if not ev.file:
            continue
        key = (ev.file, ev.kind, ev.agent)
        if key in seen:
            continue
        seen.add(key)
        score, conf = score_map.get(ev.kind, (0.4, 0.4))
        items.append(EvidenceItem(source=EvidenceSource.AGENT_LOG, file=ev.file,
                                  detail=f"{ev.agent}: {ev.detail}", when=ev.when,
                                  ai_score=score, confidence=conf))
    return items
