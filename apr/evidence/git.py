"""Git 提交历史证据。

判定思路：提交作者/邮箱或 Co-authored-by 信息匹配 AI 特征 → 该提交视为 AI 参与；
按文件聚合：AI 参与提交占比 + AI 新增代码行占比 → 文件级 AI 贡献度。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .base import EvidenceItem, EvidenceSource

AI_AUTHOR_RE = re.compile(
    r"(?i)(claude|anthropic|copilot|cursor|chatgpt|openai|gpt-4|gpt|gemini|bard|codex|aider|"
    r"devin|deepseek|codeium|windsurf|amazon\s*q|q\s*developer|replit|bolt\.new|lovable|"
    r"v0\b|cognition|codium|tabnine|sourcegraph|continue)")
CO_AUTHOR_RE = re.compile(r"Co-authored-by:\s*([^<]*?)\s*<([^>]+)>")


def _run(root: Path, args: list[str], timeout: int = 120):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def collect_git_evidence(root: Path, max_commits: int = 500):
    """返回 (证据列表, 备注列表, HEAD 提交哈希或 None)。"""
    notes: list[str] = []
    try:
        inside = _run(root, ["rev-parse", "--is-inside-work-tree"])
    except FileNotFoundError:
        return [], ["未找到 git 命令，跳过 Git 证据"], None
    except subprocess.TimeoutExpired:
        return [], ["git 命令超时，跳过 Git 证据"], None
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return [], ["目录不是 Git 仓库，跳过 Git 证据"], None

    head = None
    try:
        head = _run(root, ["rev-parse", "HEAD"]).stdout.strip() or None
        meta_out = _run(root, ["log", "-n", str(max_commits),
                               "--pretty=format:%x1e%H%x1f%an%x1f%ae%x1f%aI%x1f%s"]).stdout
        body_out = _run(root, ["log", "-n", str(max_commits),
                               "--pretty=format:%x1e%H%x1f%B"]).stdout
        name_out = _run(root, ["log", "-n", str(max_commits),
                               "--pretty=format:%x1e%H", "--name-only"]).stdout
        num_out = _run(root, ["log", "-n", str(max_commits),
                              "--pretty=format:%x1e%H", "--numstat"]).stdout
    except subprocess.TimeoutExpired:
        return [], ["git log 超时，跳过 Git 证据"], head

    commits: dict[str, dict] = {}
    order: list[str] = []

    def _blocks(text: str):
        for block in text.split("\x1e"):
            if block.strip():
                yield block

    for block in _blocks(meta_out):
        fields = block.split("\x1f")
        h = fields[0].strip()
        if not h or len(fields) < 5:
            continue
        commits[h] = {
            "author": fields[1].strip(), "email": fields[2].strip(),
            "date": fields[3].strip()[:10], "subject": fields[4].strip(),
            "co_authors": [], "files": [], "numstat": {},
        }
        order.append(h)

    for block in _blocks(body_out):
        fields = block.split("\x1f", 1)
        h = fields[0].strip()
        if h in commits:
            body = fields[1] if len(fields) > 1 else ""
            commits[h]["co_authors"] = [(m.group(1).strip(), m.group(2).strip())
                                        for m in CO_AUTHOR_RE.finditer(body)]

    for block in _blocks(name_out):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if lines and lines[0] in commits:
            commits[lines[0]]["files"] = lines[1:]

    for block in _blocks(num_out):
        lines = block.splitlines()
        if not lines or lines[0].strip() not in commits:
            continue
        h = lines[0].strip()
        for ln in lines[1:]:
            parts = ln.split("\t")
            if len(parts) == 3 and parts[0] != "-":
                try:
                    commits[h]["numstat"][parts[2]] = int(parts[0])
                except ValueError:
                    pass

    def is_ai(c: dict) -> bool:
        hay = f'{c["author"]} {c["email"]}'
        if AI_AUTHOR_RE.search(hay):
            return True
        return any(AI_AUTHOR_RE.search(n) or AI_AUTHOR_RE.search(e) for n, e in c["co_authors"])

    per_file: dict[str, dict] = {}
    for h in reversed(order):
        c = commits[h]
        ai = is_ai(c)
        for f in c["files"]:
            entry = per_file.setdefault(f, {"touches": 0, "ai": 0, "added": 0,
                                            "ai_added": 0, "first_ai": None, "last": None})
            entry["touches"] += 1
            if ai:
                entry["ai"] += 1
            if entry["first_ai"] is None:
                entry["first_ai"] = ai
            if entry["last"] is None:
                entry["last"] = c["date"]
            added = c["numstat"].get(f, 0)
            entry["added"] += added
            if ai:
                entry["ai_added"] += added

    items: list[EvidenceItem] = []
    ai_commits = sum(1 for c in commits.values() if is_ai(c))
    for f, e in per_file.items():
        if e["ai"] == 0 and e["touches"] < 2:
            continue
        ratio = e["ai"] / e["touches"]
        line_ratio = e["ai_added"] / e["added"] if e["added"] else 0.0
        score = 0.6 * ratio + 0.4 * line_ratio
        if e["first_ai"]:
            score = min(1.0, score + 0.15)
        if e["ai"] == 0:
            score = 0.0
        conf = min(0.7, 0.25 + 0.1 * e["touches"])
        detail = (f"{e['ai']}/{e['touches']} 次提交疑似 AI 参与，"
                  f"AI 相关新增行占比 {line_ratio:.0%}，首次提交{'由 AI 参与' if e['first_ai'] else '非 AI'}")
        items.append(EvidenceItem(source=EvidenceSource.GIT, file=f, detail=detail,
                                  when=e["last"], ai_score=score, confidence=conf))

    if commits:
        human_share = 1 - ai_commits / len(commits)
        notes.append(f"Git 证据：分析最近 {len(commits)} 次提交，其中 {ai_commits} 次疑似 AI 参与"
                     f"（作者/Co-author），人工提交占比约 {human_share:.0%}")
    return items, notes, head
