"""OpenAI 兼容 Chat Completions 客户端（仅标准库）。

适用于 DeepSeek / OpenAI / 任意 OpenAI 兼容端点。
base_url 传根地址（如 https://api.deepseek.com）或含 /v1 的地址均可。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from ..errors import LLMError
from .base import ChatMessage, LLMProvider


class OpenAICompatProvider(LLMProvider):
    def __init__(self, name: str, base_url: str, model: str, api_key: str, timeout: int = 300):
        if not base_url:
            raise LLMError(f"provider {name} 缺少 base_url（请在 apr.yaml 中配置 llm.base_url）")
        if not api_key:
            raise LLMError(f"未找到 API Key：请设置环境变量（或 apr.yaml 的 llm.api_key_env / llm.api_key）")
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model or "gpt-4o-mini"
        self.api_key = api_key
        self.timeout = timeout

    def complete(self, messages: list[ChatMessage], *, temperature: float = 0.3,
                 max_tokens: int = 4096) -> str:
        url = self.base_url
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:500]
            except OSError:
                pass
            raise LLMError(f"LLM 请求失败 HTTP {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise LLMError(f"LLM 请求网络错误: {e.reason}") from e
        except TimeoutError as e:
            raise LLMError(f"LLM 请求超时（{self.timeout}s）") from e
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f"LLM 响应格式异常: {str(data)[:300]}") from e
        if content is None:
            raise LLMError("LLM 返回空内容（可能模型不支持或触发限流）")
        return str(content).strip()
