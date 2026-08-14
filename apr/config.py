"""配置加载与合并。

优先级：内置默认 ← ~/.apr/apr.yaml ← 项目根 apr.yaml ← 环境变量 ← CLI 参数。
YAML 解析使用内置简化解析器（apr._yaml），零第三方依赖。
各配置文件按「节」整体覆盖（不做深合并）。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._yaml import parse_simple_yaml
from .errors import ConfigError

PROVIDER_DEFAULTS = {
    "deepseek": {"base_url": "https://api.deepseek.com", "api_key_env": "DEEPSEEK_API_KEY", "model": "deepseek-chat"},
    "openai": {"base_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY", "model": "gpt-4o-mini"},
    "openai-compatible": {"base_url": "", "api_key_env": "APR_API_KEY", "model": ""},
    "ollama": {"base_url": "http://localhost:11434", "api_key_env": "", "model": "qwen2.5:7b"},
    "mock": {"base_url": "", "api_key_env": "", "model": "mock"},
}


def _get(mapping: Any, key: str, default: Any = None) -> Any:
    return mapping.get(key, default) if isinstance(mapping, dict) else default


@dataclass
class LLMConfig:
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    api_key_env: str = "DEEPSEEK_API_KEY"
    api_key: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096

    @classmethod
    def from_mapping(cls, m: Any) -> "LLMConfig":
        provider = str(_get(m, "provider", "deepseek") or "deepseek").lower()
        defaults = PROVIDER_DEFAULTS.get(provider, {})
        api_key_env = _get(m, "api_key_env") or defaults.get("api_key_env") or "APR_API_KEY"
        api_key = os.environ.get(str(api_key_env), "") or os.environ.get("APR_API_KEY", "")
        return cls(
            provider=provider,
            model=str(_get(m, "model") or defaults.get("model") or ""),
            base_url=str(_get(m, "base_url") or defaults.get("base_url") or ""),
            api_key_env=str(api_key_env),
            api_key=api_key,
            temperature=float(_get(m, "temperature", 0.3)),
            max_tokens=int(_get(m, "max_tokens", 4096)),
        )


@dataclass
class OutputConfig:
    file: str = "README复盘.md"
    language: str = "zh"

    @classmethod
    def from_mapping(cls, m: Any) -> "OutputConfig":
        language = str(_get(m, "language", "zh")).lower()
        if language not in ("zh", "en"):
            raise ConfigError(f"output.language 仅支持 zh|en，收到: {language}")
        return cls(file=str(_get(m, "file", "README复盘.md")), language=language)


@dataclass
class LimitsConfig:
    max_files: int = 300
    max_file_kb: int = 200
    max_total_kb: int = 2000
    max_dir_tree_entries: int = 400
    extra_ignores: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, m: Any) -> "LimitsConfig":
        extra = _get(m, "extra_ignores", [])
        if not isinstance(extra, list):
            raise ConfigError("limits.extra_ignores 必须是列表")
        return cls(
            max_files=int(_get(m, "max_files", 300)),
            max_file_kb=int(_get(m, "max_file_kb", 200)),
            max_total_kb=int(_get(m, "max_total_kb", 2000)),
            max_dir_tree_entries=int(_get(m, "max_dir_tree_entries", 400)),
            extra_ignores=[str(x) for x in extra],
        )


@dataclass
class EvidenceConfig:
    markers: bool = True
    git: bool = True
    agent_logs: bool = True
    manual_logs_dir: str = ".apr/logs"
    claude_projects_dir: str = "~/.claude/projects"
    dsh_logs_dir: str | None = None
    cursor_logs_dir: str | None = None

    @classmethod
    def from_mapping(cls, m: Any) -> "EvidenceConfig":
        def _b(v: Any, d: bool) -> bool:
            return d if v is None else bool(v)

        def _s(v: Any, d: str) -> str:
            return str(v) if v else d

        return cls(
            markers=_b(_get(m, "markers"), True),
            git=_b(_get(m, "git"), True),
            agent_logs=_b(_get(m, "agent_logs"), True),
            manual_logs_dir=_s(_get(m, "manual_logs_dir"), ".apr/logs"),
            claude_projects_dir=_s(_get(m, "claude_projects_dir"), "~/.claude/projects"),
            dsh_logs_dir=_get(m, "dsh_logs_dir") or None,
            cursor_logs_dir=_get(m, "cursor_logs_dir") or None,
        )


@dataclass
class QuizConfig:
    enabled: bool = True
    question_count: int = 4

    @classmethod
    def from_mapping(cls, m: Any) -> "QuizConfig":
        return cls(
            enabled=True if _get(m, "enabled") is None else bool(_get(m, "enabled")),
            question_count=int(_get(m, "question_count", 4)),
        )


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    evidence: EvidenceConfig = field(default_factory=EvidenceConfig)
    quiz: QuizConfig = field(default_factory=QuizConfig)
    profile: str = "profile.yaml"

    def cache_dict(self) -> dict:
        """参与缓存键的核心配置。"""
        return {
            "provider": self.llm.provider,
            "model": self.llm.model,
            "language": self.output.language,
        }


def _load_yaml_file(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ConfigError(f"无法读取配置文件 {path}: {e}") from e
    data = parse_simple_yaml(text)
    if not isinstance(data, dict):
        raise ConfigError(f"配置文件格式错误（应为映射）: {path}")
    return data


def load_config(project_root: Path, config_path: Path | None = None) -> Config:
    merged: dict = {}
    if config_path is not None:
        merged = _load_yaml_file(config_path)
    else:
        merged = _load_yaml_file(Path.home() / ".apr" / "apr.yaml")
        merged.update(_load_yaml_file(project_root / "apr.yaml"))
    cfg = Config(
        llm=LLMConfig.from_mapping(_get(merged, "llm", {})),
        output=OutputConfig.from_mapping(_get(merged, "output", {})),
        limits=LimitsConfig.from_mapping(_get(merged, "limits", {})),
        evidence=EvidenceConfig.from_mapping(_get(merged, "evidence", {})),
        quiz=QuizConfig.from_mapping(_get(merged, "quiz", {})),
        profile=str(_get(merged, "profile", "profile.yaml")),
    )
    return apply_env(cfg)


def apply_env(cfg: Config) -> Config:
    """环境变量覆盖：APR_PROVIDER / APR_MODEL / APR_BASE_URL / APR_API_KEY / APR_API_KEY_ENV。"""
    env = os.environ
    if env.get("APR_PROVIDER"):
        cfg.llm.provider = env["APR_PROVIDER"].lower()
    if env.get("APR_MODEL"):
        cfg.llm.model = env["APR_MODEL"]
    if env.get("APR_BASE_URL"):
        cfg.llm.base_url = env["APR_BASE_URL"]
    if env.get("APR_API_KEY_ENV"):
        cfg.llm.api_key_env = env["APR_API_KEY_ENV"]
    if env.get("APR_API_KEY"):
        cfg.llm.api_key = env["APR_API_KEY"]
    elif cfg.llm.api_key_env and env.get(cfg.llm.api_key_env):
        cfg.llm.api_key = env[cfg.llm.api_key_env]
    return cfg
