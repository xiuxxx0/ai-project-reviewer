"""CLI 入口。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .analyzer import Progress, run_review
from .config import PROVIDER_DEFAULTS, Config, load_config
from .digest import build_digest
from .errors import AprError, QuizAborted
from .llm.factory import create_provider
from .report import render_report
from .scanner import scan_project, scan_summary_text
from .templates import APR_YAML_TEMPLATE, PROFILE_YAML_TEMPLATE

BANNER = f"AI Project Reviewer v{__version__} — AI 项目复盘助手"


def _reconfigure_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _add_llm_options(p: argparse.ArgumentParser):
    p.add_argument("--provider", help="覆盖 LLM provider（deepseek/openai/openai-compatible/ollama/mock）")
    p.add_argument("--model", help="覆盖模型名")
    p.add_argument("--base-url", help="覆盖 API base_url")
    p.add_argument("--api-key", help="直接提供 API Key（优先于环境变量）")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apr", description="AI 项目复盘助手：扫描代码项目，生成 README复盘.md")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_review = sub.add_parser("review", help="复盘项目并生成报告")
    p_review.add_argument("project", nargs="?", default=".", help="项目路径（默认当前目录）")
    p_review.add_argument("--config", help="指定 apr.yaml 配置文件路径")
    _add_llm_options(p_review)
    p_review.add_argument("--output", help="输出报告路径（默认写入项目根目录的 README复盘.md）")
    p_review.add_argument("--language", choices=["zh", "en"], help="报告语言")
    p_review.add_argument("--skip-quiz", action="store_true", help="跳过实践验证问答")
    p_review.add_argument("--force-quiz", action="store_true", help="非交互环境下也强制问答")
    p_review.add_argument("--quiz-count", type=int, help="选择题数量")
    p_review.add_argument("--no-cache", action="store_true", help="不使用缓存")
    p_review.add_argument("--dry-run", action="store_true", help="只展示计划，不调用 LLM")
    p_review.add_argument("--verbose", "-v", action="store_true", help="输出详细信息")
    p_review.add_argument("--quiet", "-q", action="store_true", help="只输出最终结果")

    p_scan = sub.add_parser("scan", help="扫描项目并预览技术栈（不调用 LLM）")
    p_scan.add_argument("project", nargs="?", default=".")
    p_scan.add_argument("--config", help="指定 apr.yaml 配置文件路径")
    p_scan.add_argument("--verbose", "-v", action="store_true")

    p_quiz = sub.add_parser("quiz", help="只运行实践验证问答")
    p_quiz.add_argument("project", nargs="?", default=".")
    p_quiz.add_argument("--config", help="指定 apr.yaml 配置文件路径")
    _add_llm_options(p_quiz)
    p_quiz.add_argument("--quiz-count", type=int, help="选择题数量")
    p_quiz.add_argument("--verbose", "-v", action="store_true")

    p_init = sub.add_parser("init", help="在项目根目录生成 apr.yaml 与 profile.yaml 模板")
    p_init.add_argument("project", nargs="?", default=".")
    p_init.add_argument("--force", action="store_true", help="覆盖已存在的文件")
    return parser


def _apply_overrides(cfg: Config, args) -> Config:
    if getattr(args, "provider", None):
        cfg.llm.provider = args.provider.lower()
        d = PROVIDER_DEFAULTS.get(cfg.llm.provider, {})
        cfg.llm.model = args.model or d.get("model") or cfg.llm.model
        cfg.llm.base_url = args.base_url or d.get("base_url") or cfg.llm.base_url
        cfg.llm.api_key_env = d.get("api_key_env") or cfg.llm.api_key_env
    if getattr(args, "model", None):
        cfg.llm.model = args.model
    if getattr(args, "base_url", None):
        cfg.llm.base_url = args.base_url
    if getattr(args, "api_key", None):
        cfg.llm.api_key = args.api_key
    if getattr(args, "language", None):
        cfg.output.language = args.language
    if getattr(args, "quiz_count", None):
        cfg.quiz.question_count = args.quiz_count
    return cfg


def cmd_review(project: Path, cfg: Config, args) -> int:
    print(BANNER)
    print(f"目标项目：{project}")
    print(f"LLM：{cfg.llm.provider}/{cfg.llm.model}")
    if args.dry_run:
        print("--dry-run：仅展示计划，不调用 LLM。")
        return 0
    progress = Progress(verbose=args.verbose, quiet=args.quiet)
    try:
        result = run_review(project, cfg, progress,
                            skip_quiz=args.skip_quiz, force_quiz=args.force_quiz,
                            use_cache=not args.no_cache)
    except QuizAborted:
        print("\n已取消问答。")
        return 130
    out = Path(args.output) if args.output else project / cfg.output.file
    if not out.is_absolute():
        out = project / out
    report = render_report(result)
    try:
        out.write_text(report, encoding="utf-8")
    except OSError as e:
        print(f"✖ 写入报告失败：{e}", file=sys.stderr)
        return 1
    print("")
    print(f"✔ 报告已生成：{out}")
    size_kb = len(report.encode("utf-8")) // 1024
    quiz_note = f" ｜ 实践验证 {result.quiz.overall}/100" if result.quiz else ""
    print(f"  大小 {size_kb} KB ｜ 板块 {len(result.sections)} 个 ｜ 证据 {len(result.evidence.items)} 条{quiz_note}")
    return 0


def cmd_scan(project: Path, cfg: Config, args) -> int:
    scan = scan_project(project, cfg.limits)
    digest = build_digest(project, scan, cfg.limits)
    print(BANNER)
    print(scan_summary_text(scan))
    print("")
    print("目录树：")
    print(digest.tree_text)
    if digest.stack.platforms:
        print("")
        print("平台/框架： " + "、".join(digest.stack.platforms))
    if digest.stack.dependencies:
        print("")
        for m, deps in digest.stack.dependencies.items():
            print(f"{m}: {', '.join(deps[:20])}")
    return 0


def cmd_quiz(project: Path, cfg: Config, args) -> int:
    from .assessment.quiz import run_quiz
    print(BANNER)
    progress = Progress(verbose=args.verbose)
    scan = scan_project(project, cfg.limits)
    digest = build_digest(project, scan, cfg.limits)
    llm = create_provider(cfg.llm)
    result = run_quiz(llm, digest.render(include_excerpts=False), cfg.quiz.question_count)
    print("")
    print(result.render_markdown())
    return 0


def cmd_init(args) -> int:
    project = Path(args.project or ".").resolve()
    project.mkdir(parents=True, exist_ok=True)
    files = [("apr.yaml", APR_YAML_TEMPLATE), ("profile.yaml", PROFILE_YAML_TEMPLATE)]
    for name, content in files:
        target = project / name
        if target.exists() and not args.force:
            print(f"· 跳过已存在的 {name}（--force 可覆盖）")
            continue
        target.write_text(content, encoding="utf-8")
        print(f"✔ 已生成 {target}")
    print("")
    print("下一步：")
    print("  1. 编辑 profile.yaml 填写你的技能档案")
    print("  2. 设置环境变量（如 DEEPSEEK_API_KEY）或修改 apr.yaml")
    print("  3. 运行 apr review . 生成复盘报告")
    return 0


def main(argv=None) -> int:
    _reconfigure_stdout()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            return cmd_init(args)
        project = Path(args.project or ".").resolve()
        if not project.is_dir():
            print(f"✖ 路径不是目录：{project}", file=sys.stderr)
            return 1
        cfg = load_config(project, Path(args.config) if getattr(args, "config", None) else None)
        cfg = _apply_overrides(cfg, args)
        if args.command == "review":
            return cmd_review(project, cfg, args)
        if args.command == "scan":
            return cmd_scan(project, cfg, args)
        if args.command == "quiz":
            return cmd_quiz(project, cfg, args)
    except AprError as e:
        print(f"✖ 错误：{e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已取消。")
        return 130
    return 1
