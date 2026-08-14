"""项目画像：技术栈检测、语言统计、关键文件选择与上下文渲染。"""
from __future__ import annotations

import fnmatch
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .config import LimitsConfig
from .scanner import FileInfo, ScanResult, human_size, render_tree

try:
    import tomllib  # Python 3.11+
except ImportError:
    tomllib = None

# (glob 或路径前缀, 平台/框架名)
MANIFESTS = [
    ("package.json", "JavaScript/Node.js"), ("package-lock.json", "JavaScript/Node.js"),
    ("pnpm-lock.yaml", "JavaScript/Node.js"), ("yarn.lock", "JavaScript/Node.js"),
    ("requirements.txt", "Python"), ("pyproject.toml", "Python"), ("setup.py", "Python"),
    ("Pipfile", "Python"), ("poetry.lock", "Python"), ("uv.lock", "Python"),
    ("go.mod", "Go"), ("go.sum", "Go"),
    ("Cargo.toml", "Rust"), ("Cargo.lock", "Rust"),
    ("pom.xml", "Java/Maven"), ("build.gradle", "Java/Gradle"), ("build.gradle.kts", "Java/Gradle"),
    ("composer.json", "PHP"), ("Gemfile", "Ruby"), ("mix.exs", "Elixir"),
    ("*.csproj", ".NET"), ("*.sln", ".NET"),
    ("Dockerfile", "Docker"), ("docker-compose.yml", "Docker"), ("docker-compose.yaml", "Docker"),
    (".github/workflows", "CI/GitHub Actions"),
    ("tsconfig.json", "TypeScript"), ("jsconfig.json", "JavaScript"),
    ("tailwind.config.js", "Tailwind CSS"), ("tailwind.config.ts", "Tailwind CSS"),
    ("vite.config.ts", "Vite"), ("vite.config.js", "Vite"),
    ("next.config.js", "Next.js"), ("next.config.mjs", "Next.js"), ("nuxt.config.ts", "Nuxt"),
    ("eslint.config.js", "ESLint"), (".eslintrc.*", "ESLint"), ("prettier.config.*", "Prettier"),
    ("CMakeLists.txt", "C/C++/CMake"), ("Makefile", "Make"),
    ("README.md", "文档"), ("README*", "文档"),
]

EXT_LANGUAGE = {
    ".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript/React", ".jsx": "JavaScript/React",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin", ".swift": "Swift",
    ".c": "C", ".h": "C/C++", ".cpp": "C++", ".hpp": "C++", ".cs": "C#",
    ".rb": "Ruby", ".php": "PHP", ".sh": "Shell", ".ps1": "PowerShell",
    ".md": "Markdown", ".yml": "YAML", ".yaml": "YAML", ".json": "JSON",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".less": "Less",
    ".vue": "Vue", ".svelte": "Svelte", ".sql": "SQL", ".toml": "TOML",
    ".dockerfile": "Docker", ".ini": "INI", ".cfg": "INI", ".txt": "Text",
}

KEY_NAME_SCORES = {
    "readme": 12, "main": 9, "app": 8, "index": 7, "server": 8, "entry": 7,
    "cli": 7, "core": 6, "config": 5, "settings": 5, "routes": 6, "router": 6,
    "models": 6, "schema": 5, "utils": 4,
}
MANIFEST_NAMES = {"package.json", "requirements.txt", "pyproject.toml", "go.mod",
                  "Cargo.toml", "pom.xml", "composer.json", "Gemfile", "Dockerfile",
                  "tsconfig.json", "vite.config.ts", "next.config.js"}


@dataclass
class TechStack:
    languages: dict[str, int] = field(default_factory=dict)          # 语言 → 文件数
    platforms: list[str] = field(default_factory=list)               # 平台/框架
    dependencies: dict[str, list[str]] = field(default_factory=dict)  # 清单 → 依赖


def detect_tech_stack(files: list[FileInfo], root: Path) -> TechStack:
    stack = TechStack()
    rels = {f.rel for f in files}
    counts: Counter = Counter()
    for f in files:
        counts[EXT_LANGUAGE.get(f.ext, f.ext.lstrip(".") or "other")] += 1
    stack.languages = dict(counts.most_common(12))
    for pattern, label in MANIFESTS:
        if "/" in pattern:
            hit = any(r == pattern or r.startswith(pattern + "/") for r in rels)
        else:
            hit = any(fnmatch.fnmatch(Path(r).name, pattern) or fnmatch.fnmatch(r, pattern) for r in rels)
        if hit and label not in stack.platforms:
            stack.platforms.append(label)
    parsers = [
        ("package.json", _parse_package_json), ("requirements.txt", _parse_requirements),
        ("pyproject.toml", _parse_pyproject), ("go.mod", _parse_gomod),
        ("Cargo.toml", _parse_cargo), ("pom.xml", _parse_pom),
        ("composer.json", _parse_composer), ("Gemfile", _parse_gemfile),
    ]
    for name, parser in parsers:
        path = root / name
        if name not in rels or not path.is_file():
            continue
        try:
            deps = parser(path)
        except Exception:
            deps = []
        if deps:
            stack.dependencies[name] = deps[:60]
    return stack


def _parse_package_json(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    deps: dict = {}
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        if isinstance(data.get(section), dict):
            deps.update(data[section])
    return sorted(deps.keys())


def _parse_requirements(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-") or line.startswith("git+"):
            continue
        m = re.match(r"^([A-Za-z0-9_.\-]+)", line)
        if m:
            out.append(m.group(1))
    return sorted(set(out))


def _dep_name(dep: str) -> str:
    m = re.match(r"^([A-Za-z0-9_.\-]+)", dep.strip())
    return m.group(1) if m else dep


def _parse_pyproject(path: Path) -> list[str]:
    if tomllib is not None:
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            data = {}
        deps = list(data.get("project", {}).get("dependencies", []))
        for group in data.get("project", {}).get("optional-dependencies", {}).values():
            if isinstance(group, list):
                deps.extend(group)
        poetry = data.get("tool", {}).get("poetry", {})
        if isinstance(poetry, dict):
            deps.extend(k for k in poetry.get("dependencies", {}) if str(k).lower() != "python")
        return sorted({_dep_name(d) for d in deps if isinstance(d, str)})
    text = path.read_text(encoding="utf-8", errors="replace")
    names = set()
    for section in re.finditer(r"\[project\.(?:optional-)?dependencies\]([^\[]*)", text):
        names.update(re.findall(r'^\s*"([A-Za-z0-9_.\-]+)"\s*=', section.group(1), re.M))
    return sorted(names)


def _parse_gomod(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    names = set(re.findall(r"^\s*require\s+([\w.\-/]+)\s+v[\w.\-+]+", text, re.M))
    names.update(re.findall(r"^\s*([\w.\-/]+)\s+v[\w.\-+]+", text, re.M))
    names.discard("module")
    return sorted(names)


def _parse_cargo(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    names = set()
    in_deps = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            in_deps = s in ("[dependencies]", "[dev-dependencies]", "[build-dependencies]")
            continue
        if in_deps and "=" in line and not s.startswith("#"):
            names.add(s.split("=", 1)[0].strip())
    return sorted(names)


def _parse_pom(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return sorted(set(f"{g}:{a}" for g, a in re.findall(
        r"<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>", text)))


def _parse_composer(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    deps: dict = {}
    for section in ("require", "require-dev"):
        if isinstance(data.get(section), dict):
            deps.update(data[section])
    return sorted(deps.keys())


def _parse_gemfile(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return sorted(set(re.findall(r"""^\s*gem\s+['"]([^'"]+)['"]""", text, re.M)))


def select_key_files(files: list[FileInfo], limit: int = 20) -> list[FileInfo]:
    scored = []
    for f in files:
        if not f.is_text or f.too_big:
            continue
        base = Path(f.rel).name.lower()
        stem = Path(base).stem
        score = KEY_NAME_SCORES.get(stem, 0)
        if base in MANIFEST_NAMES:
            score = max(score, 8)
        score -= f.rel.count("/") * 0.5
        if f.size < 50000:
            score += 1
        if base.endswith((".md", ".toml", ".yaml", ".yml", ".json", ".cfg", ".ini")):
            score += 1.5
        scored.append((score, f))
    scored.sort(key=lambda t: (-t[0], t[1].rel))
    return [f for _, f in scored[:limit]]


@dataclass
class ProjectDigest:
    root: Path
    scan: ScanResult
    stack: TechStack
    key_files: list[FileInfo]
    tree_text: str

    def render(self, include_excerpts: bool = True, max_excerpt_chars: int = 24000) -> str:
        blocks: list[str] = []
        blocks.append(
            f"# 项目画像\n\n- 项目名：{self.root.name}\n- 路径：{self.root}\n"
            f"- 文件数：{len(self.scan.files)}（扫描排除 {self.scan.excluded_count} 项"
            + ("，已截断" if self.scan.truncated else "")
            + f"）\n- 总大小：{human_size(self.scan.total_size)}"
        )
        if self.scan.notes:
            blocks.append("扫描备注：" + "；".join(self.scan.notes))
        blocks.append("## 目录树\n\n    " + self.tree_text.replace("\n", "\n    "))
        blocks.append("## 技术栈检测\n\n- 语言统计：" + "、".join(
            f"{k} {v}" for k, v in self.stack.languages.items()))
        if self.stack.platforms:
            blocks.append("- 平台/框架：" + "、".join(self.stack.platforms))
        for manifest, deps in self.stack.dependencies.items():
            blocks.append(f"- {manifest} 主要依赖：{'、'.join(deps[:40])}")
        blocks.append("## 关键文件\n\n" + "\n".join(
            f"- {f.rel}（{human_size(f.size)}）" for f in self.key_files))
        if include_excerpts:
            blocks.append(self.excerpts(max_excerpt_chars))
        return "\n\n".join(blocks)

    def excerpts(self, max_chars: int = 24000) -> str:
        parts = ["## 关键文件内容摘录"]
        used = 0
        for f in self.key_files:
            try:
                text = Path(f.abs).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            cap = min(4000, max_chars - used)
            if cap <= 500:
                break
            snippet = text[:cap]
            indented = "\n".join("    " + ln for ln in snippet.splitlines())
            parts.append(f"### {f.rel}\n\n{indented}")
            used += cap
        return "\n\n".join(parts)


def build_digest(root: Path, scan: ScanResult, limits: LimitsConfig) -> ProjectDigest:
    stack = detect_tech_stack(scan.files, root)
    key_files = select_key_files(scan.files)
    tree = render_tree(scan, limits.max_dir_tree_entries)
    return ProjectDigest(root=root, scan=scan, stack=stack, key_files=key_files, tree_text=tree)
