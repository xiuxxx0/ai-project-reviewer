"""项目扫描：目录遍历、gitignore 风格过滤、文件分类与目录树渲染。"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import LimitsConfig
from .errors import ScanError

DEFAULT_IGNORES = [
    ".git/", ".svn/", ".hg/", "node_modules/", "__pycache__/", "*.pyc", "*.pyo",
    ".venv/", "venv/", "dist/", "build/", "out/", ".idea/", ".vscode/",
    ".DS_Store", "Thumbs.db", ".next/", ".nuxt/", ".cache/", "coverage/",
    ".pytest_cache/", ".mypy_cache/", ".ruff_cache/", "*.egg-info/", ".tox/",
    "target/", ".apr/", "*.min.js", "*.min.css",
]


@dataclass
class FileInfo:
    rel: str
    abs: str
    size: int
    ext: str
    is_text: bool = True
    lines: int = 0
    too_big: bool = False


@dataclass
class ScanResult:
    root: Path
    files: list[FileInfo] = field(default_factory=list)
    excluded_count: int = 0
    truncated: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def total_size(self) -> int:
        return sum(f.size for f in self.files)

    def rel_set(self) -> set[str]:
        return {f.rel for f in self.files}


class IgnoreMatcher:
    """极简 .gitignore 语义：顺序匹配、感叹号取反、斜杠结尾匹配目录及其内容。"""

    def __init__(self, patterns: list[str]):
        self.rules: list[tuple[re.Pattern, bool]] = []
        for raw in patterns:
            p = raw.strip()
            if not p or p.startswith("#"):
                continue
            negate = p.startswith("!")
            if negate:
                p = p[1:]
            regex = self._to_regex(p)
            if regex:
                self.rules.append((re.compile(regex), negate))

    @staticmethod
    def _to_regex(pattern: str) -> str | None:
        p = pattern.rstrip("/")
        if not p:
            return None
        anchored = p.startswith("/") or "/" in p
        p = p.lstrip("/")
        out: list[str] = []
        i = 0
        while i < len(p):
            c = p[i]
            if c == "*":
                if p.startswith("**/", i):
                    out.append(r"(?:.*/)?")
                    i += 3
                elif p.startswith("**", i):
                    out.append(r".*")
                    i += 2
                else:
                    out.append(r"[^/]*")
                    i += 1
            elif c == "?":
                out.append(r"[^/]")
                i += 1
            elif c in ".^$+{}()[]|\\":
                out.append("\\" + c)
                i += 1
            else:
                out.append(c)
                i += 1
        body = "".join(out)
        if anchored:
            return r"^" + body + r"(?:/.*)?$"
        return r"(?:^|.*/)" + body + r"(?:/.*)?$"

    def is_ignored(self, rel: str) -> bool:
        ignored = False
        for regex, negate in self.rules:
            if regex.search(rel):
                ignored = not negate
        return ignored


def load_gitignore(root: Path) -> list[str]:
    """读取根目录 .gitignore（仅单层，MVP 够用）。"""
    path = root / ".gitignore"
    try:
        return [ln.rstrip() for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()]
    except OSError:
        return []


def _read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def scan_project(root: Path, limits: LimitsConfig) -> ScanResult:
    root = root.resolve()
    if not root.is_dir():
        raise ScanError(f"路径不是目录: {root}")
    matcher = IgnoreMatcher(DEFAULT_IGNORES + limits.extra_ignores + load_gitignore(root))
    result = ScanResult(root=root)
    total_bytes = 0
    max_bytes = limits.max_total_kb * 1024
    budget_exceeded = False

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""
        else:
            rel_dir = rel_dir.replace(os.sep, "/")
        kept_dirs = []
        for name in dirnames:
            rel = f"{rel_dir}/{name}" if rel_dir else name
            if matcher.is_ignored(rel):
                result.excluded_count += 1
            else:
                kept_dirs.append(name)
        dirnames[:] = kept_dirs
        for name in sorted(filenames):
            rel = f"{rel_dir}/{name}" if rel_dir else name
            if matcher.is_ignored(rel):
                result.excluded_count += 1
                continue
            if len(result.files) >= limits.max_files:
                result.truncated = True
                result.notes.append(f"文件数超过上限 {limits.max_files}，已截断")
                return result
            abs_path = Path(dirpath) / name
            try:
                size = abs_path.stat().st_size
            except OSError:
                continue
            info = FileInfo(rel=rel, abs=str(abs_path), size=size, ext=abs_path.suffix.lower())
            if budget_exceeded:
                pass  # 只统计元信息，不再读内容
            elif size > limits.max_file_kb * 1024:
                info.too_big = True
                info.is_text = True
            else:
                data = _read_bytes(abs_path)
                if data is None:
                    continue
                info.is_text = b"\x00" not in data
                if info.is_text:
                    info.lines = data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
                total_bytes += size
                if total_bytes > max_bytes:
                    budget_exceeded = True
                    result.notes.append(f"累计读取体积超过上限 {limits.max_total_kb}KB，后续文件仅统计元信息")
            result.files.append(info)
    return result


def render_tree(scan: ScanResult, limit: int = 400) -> str:
    """渲染目录树（目录在前、按名称排序）。"""
    root: dict = {}
    for f in scan.files:
        node = root
        parts = f.rel.split("/")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node.setdefault(parts[-1], None)
    lines: list[str] = []
    budget = {"n": 0}

    def walk(node: dict, prefix: str, name: str):
        lines.append(prefix + name)
        budget["n"] += 1
        if not isinstance(node, dict):
            return
        entries = sorted(node.keys(), key=lambda k: (0 if isinstance(node[k], dict) else 1, k.lower()))
        for i, child in enumerate(entries):
            if budget["n"] >= limit:
                lines.append(prefix + "…（更多条目已省略）")
                return
            last = i == len(entries) - 1
            walk(node[child], prefix + ("    " if last else "│   "),
                 child + ("/" if isinstance(node[child], dict) else ""))

    walk(root, "", scan.root.name + "/")
    return "\n".join(lines)


def scan_summary_text(scan: ScanResult, top_n: int = 10) -> str:
    from collections import Counter
    exts = Counter(f.ext or "(无扩展名)" for f in scan.files)
    lines = [
        f"根目录: {scan.root}",
        f"文件数: {len(scan.files)}（已排除 {scan.excluded_count} 项）",
        f"总大小: {human_size(scan.total_size)}",
        "扩展名统计: " + ", ".join(f"{e}×{c}" for e, c in exts.most_common(top_n)),
    ]
    if scan.truncated:
        lines.append("⚠ 文件数超过上限，结果已截断")
    lines.extend(scan.notes)
    return "\n".join(lines)


def human_size(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f}{unit}" if unit == "B" else f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}TB"
