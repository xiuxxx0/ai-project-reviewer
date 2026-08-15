"""本地 Ollama 客户端（原生 /api/chat，仅标准库）。"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from ..errors import LLMError
from .base import ChatMessage, LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, timeout: int = 600):
        if not base_url:
            raise LLMError("ollama 缺少 base_url（默认 http://localhost:11434）")
        self.name = "ollama"
        self.base_url = base_url.rstrip("/")
        self.model = model or "qwen2.5:7b"
        self.timeout = timeout

    def complete(self, messages: list[ChatMessage], *, temperature: float = 0.3,
                 max_tokens: int = 4096) -> str:
        url = self.base_url + "/api/chat"
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        req = urllib.request.Request(
            url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        try:
            from .openai_compat import _urlopen_with_fallback
            with _urlopen_with_fallback(req, self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:500]
            except OSError:
                pass
            raise LLMError(f"Ollama 请求失败 HTTP {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise LLMError(f"Ollama 连接失败（服务是否已启动？）: {e.reason}") from e
        except TimeoutError as e:
            raise LLMError(f"Ollama 请求超时（{self.timeout}s）") from e
        try:
            content = data["message"]["content"]
        except (KeyError, TypeError) as e:
            raise LLMError(f"Ollama 响应格式异常: {str(data)[:300]}") from e
        return str(content).strip()
