"""分板块结果缓存（默认位置 ~/.apr/cache.json）。"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


class SectionCache:
    def __init__(self, enabled: bool = True, path: Path | None = None):
        self.enabled = enabled
        self.path = path or (Path.home() / ".apr" / "cache.json")
        self._data: dict | None = None

    def _load(self) -> dict:
        if self._data is None:
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._data = {}
            if not isinstance(self._data, dict):
                self._data = {}
        return self._data

    def key(self, *parts) -> str:
        text = "\x1f".join(str(p) for p in parts)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]

    def get(self, key: str) -> str | None:
        if not self.enabled:
            return None
        return self._load().get(key)

    def put(self, key: str, value: str) -> None:
        if not self.enabled:
            return
        data = self._load()
        if len(data) > 200:
            data.pop(next(iter(data)))  # 简单容量控制
        data[key] = value
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:
            pass
