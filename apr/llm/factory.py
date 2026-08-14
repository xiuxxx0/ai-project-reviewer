"""按配置创建 LLM Provider。"""
from __future__ import annotations

from ..errors import LLMError
from .base import LLMProvider, MockProvider
from .ollama import OllamaProvider
from .openai_compat import OpenAICompatProvider


def create_provider(cfg) -> LLMProvider:
    provider = (cfg.provider or "deepseek").lower()
    if provider == "mock":
        return MockProvider()
    if provider == "ollama":
        return OllamaProvider(cfg.base_url, cfg.model)
    if provider in ("deepseek", "openai", "openai-compatible"):
        return OpenAICompatProvider(provider, cfg.base_url, cfg.model, cfg.api_key)
    raise LLMError(f"未知 provider {provider}，支持：deepseek / openai / openai-compatible / ollama / mock")
