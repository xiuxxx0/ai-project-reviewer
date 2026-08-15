"""复盘流程编排：扫描 → 证据 → 画像 → 档案 → 问答 → 8 大板块。"""
from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .assessment.quiz import run_quiz
from .cache import SectionCache
from .config import Config
from .digest import ProjectDigest, build_digest
from .errors import LLMError
from .evidence.agent_logs import collect_agent_evidence
from .evidence.base import EvidenceReport
from .evidence.fusion import fuse
from .evidence.git import collect_git_evidence
from .evidence.markers import scan_markers
from .llm.factory import create_provider
from .profile import Profile, load_profile
from .prompts.sections import SECTION_TITLES, build_section_messages
from .scanner import ScanResult, human_size, scan_project


@dataclass
class ReviewResult:
    project: Path
    config: Config
    scan: ScanResult
    digest: ProjectDigest
    evidence: EvidenceReport
    profile: Profile | None
    quiz: object | None
    sections: list[tuple[str, str]]
    git_head: str | None
    started_at: str
    notes: list[str] = field(default_factory=list)


class Progress:
    def __init__(self, verbose: bool = False, quiet: bool = False):
        self.verbose = verbose
        self.quiet = quiet

    def _print(self, text: str):
        if not self.quiet:
            print(text)

    def step(self, msg: str):
        self._print(f"\n▸ {msg}")

    def info(self, msg: str):
        if self.verbose and not self.quiet:
            self._print(f"   · {msg}")

    def warn(self, msg: str):
        if not self.quiet:
            self._print(f"   ⚠ {msg}")

    def ok(self, msg: str):
        if not self.quiet:
            self._print(f"   ✔ {msg}")

    def section(self, index: int, total: int, name: str):
        if not self.quiet:
            self._print(f"\n   [{index}/{total}] 生成「{name}」…")


def _hash_of(messages: list) -> str:
    h = hashlib.sha256()
    for m in messages:
        h.update(m.role.encode("utf-8"))
        h.update(m.content.encode("utf-8"))
    return h.hexdigest()[:16]


def _call_with_retry(llm, messages: list, config: Config, progress: Progress,
                     title: str, retries: int = 2) -> str:
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return llm.complete(messages, temperature=config.llm.temperature,
                                max_tokens=config.llm.max_tokens)
        except LLMError as e:
            last_err = e
            progress.warn(f"调用失败（第 {attempt} 次）：{e}")
            if attempt < retries:
                progress.info("重试中…")
    return (f"## {title}\n\n"
            f"> ⚠ 本节因 LLM 调用失败而未生成：{last_err}\n\n"
            f"请检查 API Key / 网络 / 模型配置后重试。")


def run_review(project: Path, config: Config, progress: Progress,
               skip_quiz: bool = False, force_quiz: bool = False,
               use_cache: bool = True) -> ReviewResult:
    project = project.resolve()
    notes: list[str] = []

    progress.step(f"扫描项目：{project}")
    scan = scan_project(project, config.limits)
    progress.info(f"共 {len(scan.files)} 个文件（排除 {scan.excluded_count} 项），"
                  f"总大小 {human_size(scan.total_size)}")

    progress.step("采集 AI 生成证据（Git / Agent 日志 / 代码标记）")
    items = []
    ev_notes: list[str] = []
    participation: list[str] = []
    if config.evidence.markers:
        m = scan_markers(scan)
        items.extend(m)
        progress.info(f"代码标记：{len(m)} 条")
    git_head = None
    if config.evidence.git:
        g_items, g_notes, git_head = collect_git_evidence(project)
        items.extend(g_items)
        ev_notes.extend(g_notes)
        progress.info(f"Git 证据：{len(g_items)} 条")
    if config.evidence.agent_logs:
        a_items, participation, a_notes = collect_agent_evidence(project, scan, config.evidence)
        items.extend(a_items)
        ev_notes.extend(a_notes)
        progress.info(f"Agent 日志证据：{len(a_items)} 条")
    evidence = fuse(items, scan.rel_set(), ev_notes, participation)
    for note in ev_notes:
        progress.info(note)

    progress.step("生成项目画像（技术栈 / 目录树 / 关键文件）")
    digest = build_digest(project, scan, config.limits)
    if digest.stack.platforms:
        progress.info("检测到平台/框架：" + "、".join(digest.stack.platforms))

    progress.step("加载个人技能档案")
    profile = load_profile(project / config.profile)
    if profile is None or profile.is_empty:
        progress.warn(f"未找到有效的技能档案 {config.profile}（可用 apr init 生成）")
    else:
        progress.info(f"档案：{profile.name or '（匿名）'}，已掌握 {len(profile.known_skills)} 项技能")

    quiz = None
    llm = None
    quiz_enabled = config.quiz.enabled and not skip_quiz
    interactive = force_quiz or sys.stdin.isatty()
    if quiz_enabled:
        if not interactive:
            progress.warn("未检测到交互终端，跳过实践验证问答（--force-quiz 可强制）")
        else:
            progress.step("实践验证：交互问答")
            llm = llm or create_provider(config.llm)
            try:
                quiz = run_quiz(llm, digest.render(include_excerpts=False),
                                config.quiz.question_count)
            except LLMError as e:
                progress.warn(f"问答环节失败：{e}")
                notes.append(f"实践验证失败：{e}")

    progress.step("生成 8 大板块")
    llm = llm or create_provider(config.llm)
    cache = SectionCache(enabled=use_cache)
    digest_full = digest.render(include_excerpts=True)
    digest_short = digest.render(include_excerpts=False)
    evidence_text = evidence.summary_text()
    profile_text = profile.render_text() if (profile and not profile.is_empty) else "（未提供技能档案）"
    quiz_text = quiz.render_text() if quiz else "（本次未进行实践验证）"

    sections: list[tuple[str, str]] = []
    for idx, title in enumerate(SECTION_TITLES, 1):
        progress.section(idx, len(SECTION_TITLES), title)
        if title in ("我的学习盲区", "AI 协作分析"):
            # 盲区与 AI 协作分析由证据引擎计算（report 层渲染），不调用 LLM 猜测
            sections.append((title, ""))
            continue
        messages = build_section_messages(idx, digest_full, digest_short,
                                          evidence_text, profile_text, quiz_text,
                                          config.output.language)
        key = cache.key(str(project), git_head or "nogit", str(config.cache_dict()),
                        f"section-{idx}", _hash_of(messages))
        cached = cache.get(key)
        if cached:
            progress.info("命中缓存")
            sections.append((title, cached))
            continue
        md = _call_with_retry(llm, messages, config, progress, title)
        sections.append((title, md))
        cache.put(key, md)

    return ReviewResult(project=project, config=config, scan=scan, digest=digest,
                        evidence=evidence, profile=profile, quiz=quiz, sections=sections,
                        git_head=git_head, started_at=datetime.now().isoformat(timespec="seconds"),
                        notes=notes)
