"""apr config：便捷查看/切换 LLM 配置。

- apr config                   交互式向导（选供应商 → 填模型 → 写入配置）
- apr config show              显示当前生效配置与来源
- apr config set --preset ...  按预设/参数修改并持久化
  默认写入全局 ~/.apr/apr.yaml；加 --local 只写当前项目的 apr.yaml。
"""
from __future__ import annotations

import sys
from pathlib import Path

from ._yaml import dump_simple_yaml, parse_simple_yaml
from .config import PROVIDER_DEFAULTS, Config, load_config

PRESETS = {
    "deepseek-pro": {"provider": "deepseek", "model": "deepseek-v4-pro"},
    "deepseek-flash": {"provider": "deepseek", "model": "deepseek-v4-flash"},
    "openai-mini": {"provider": "openai", "model": "gpt-4o-mini"},
    "ollama-qwen": {"provider": "ollama", "model": "qwen2.5:7b"},
}

PROVIDER_CHOICES = ["deepseek", "openai", "openai-compatible", "ollama", "mock"]


def update_config_file(path: Path, overrides: dict) -> dict:
    """读取（或创建）配置文件，更新 llm 节并写回。返回更新后的 llm 节。

    未在 overrides 中指定的字段沿用文件中的旧值，再退回该供应商的默认值；
    其他节（output/limits/evidence/quiz/profile）原样保留，注释不保留。
    """
    data: dict = {}
    if path.is_file():
        try:
            data = parse_simple_yaml(path.read_text(encoding="utf-8"))
        except OSError:
            data = {}
        if not isinstance(data, dict):
            data = {}
    base_llm = data.get("llm") if isinstance(data.get("llm"), dict) else {}
    provider = str(overrides.get("provider") or base_llm.get("provider") or "deepseek").lower()
    defaults = PROVIDER_DEFAULTS.get(provider, {})
    new_llm = {
        "provider": provider,
        "model": str(overrides.get("model") or base_llm.get("model")
                     or defaults.get("model") or ""),
        "base_url": str(overrides.get("base_url") or base_llm.get("base_url")
                        or defaults.get("base_url") or ""),
        "api_key_env": str(overrides.get("api_key_env") or base_llm.get("api_key_env")
                           or defaults.get("api_key_env") or "APR_API_KEY"),
    }
    for key in ("temperature", "max_tokens"):
        if key in base_llm:
            new_llm[key] = base_llm[key]
    data["llm"] = new_llm
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_simple_yaml(data) + "\n", encoding="utf-8")
    return new_llm


def _config_show() -> int:
    cfg = load_config(Path.cwd())
    llm = cfg.llm
    print("当前生效的 LLM 配置：")
    print(f"  provider   : {llm.provider}")
    print(f"  model      : {llm.model}")
    print(f"  base_url   : {llm.base_url or '（未设置）'}")
    print(f"  api_key_env: {llm.api_key_env}")
    if llm.api_key:
        print("  api_key    : 已提供 ✓")
    else:
        print(f"  api_key    : 未找到（请设置环境变量 {llm.api_key_env}）")
    home_cfg = Path.home() / ".apr" / "apr.yaml"
    local_cfg = Path.cwd() / "apr.yaml"
    print("配置来源：")
    print(f"  全局 {home_cfg}" + ("（存在）" if home_cfg.is_file() else "（不存在）"))
    print(f"  项目 {local_cfg}" + ("（存在）" if local_cfg.is_file() else "（不存在）"))
    print("")
    print("切换模型：apr config set --preset deepseek-flash（全局）｜加 --local 只写当前项目")
    return 0


def _config_set(args) -> int:
    overrides: dict = {}
    if getattr(args, "preset", None):
        preset = PRESETS.get(args.preset)
        if not preset:
            print(f"✖ 未知 preset：{args.preset}，可选：{'、'.join(PRESETS)}", file=sys.stderr)
            return 1
        overrides.update(preset)
    for key in ("provider", "model", "base_url", "api_key_env"):
        value = getattr(args, key, None)
        if value:
            overrides[key] = value
    if not overrides:
        print("✖ 请至少指定一个参数，例如：apr config set --preset deepseek-flash", file=sys.stderr)
        return 1
    target = (Path.cwd() if getattr(args, "local", False) else Path.home() / ".apr") / "apr.yaml"
    new_llm = update_config_file(target, overrides)
    print(f"✔ 已写入：{target}")
    print(f"  provider={new_llm['provider']}  model={new_llm['model']}")
    print("  下次运行 apr review 即生效。")
    return 0


def _config_wizard() -> int:
    if not sys.stdin.isatty():
        print("✖ 交互向导需要终端；非交互环境请用：apr config set --preset deepseek-pro",
              file=sys.stderr)
        return 1
    print("选择 LLM 供应商：")
    for i, name in enumerate(PROVIDER_CHOICES, 1):
        defaults = PROVIDER_DEFAULTS.get(name, {})
        print(f"  {i}. {name}（默认模型：{defaults.get('model') or '需填写'}）")
    raw = input("输入编号 [1]: ").strip() or "1"
    try:
        provider = PROVIDER_CHOICES[int(raw) - 1]
    except (ValueError, IndexError):
        print("✖ 无效选择", file=sys.stderr)
        return 1
    defaults = PROVIDER_DEFAULTS.get(provider, {})
    model = input(f"模型名 [{defaults.get('model') or ''}]: ").strip() or defaults.get("model") or ""
    base_url = input(f"base_url [{defaults.get('base_url') or ''}]: ").strip() or defaults.get("base_url") or ""
    api_key_env = input(f"API Key 环境变量名 [{defaults.get('api_key_env') or 'APR_API_KEY'}]: ").strip() \
        or defaults.get("api_key_env") or "APR_API_KEY"
    scope = input("写入范围：1=全局 ~/.apr/apr.yaml  2=当前项目 [1]: ").strip() or "1"
    target = (Path.cwd() if scope == "2" else Path.home() / ".apr") / "apr.yaml"
    new_llm = update_config_file(target, {
        "provider": provider, "model": model, "base_url": base_url, "api_key_env": api_key_env})
    print(f"✔ 已写入：{target}")
    print(f"  provider={new_llm['provider']}  model={new_llm['model']}")
    return 0


def cmd_config(args) -> int:
    action = getattr(args, "action", None)
    if action == "show":
        return _config_show()
    if action == "set":
        return _config_set(args)
    return _config_wizard()
