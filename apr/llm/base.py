"""LLM 抽象层与 JSON 解析工具。"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..errors import LLMError


@dataclass
class ChatMessage:
    role: str   # system | user | assistant
    content: str


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def complete(self, messages: list[ChatMessage], *, temperature: float = 0.3,
                 max_tokens: int = 4096) -> str: ...

    def complete_json(self, messages: list[ChatMessage], *, temperature: float = 0.3,
                      max_tokens: int = 4096):
        text = self.complete(messages, temperature=temperature, max_tokens=max_tokens)
        return extract_json(text)


def extract_json(text: str):
    """从模型输出中尽力提取 JSON（直接解析 / 代码围栏 / 平衡括号扫描）。"""
    candidates = [text.strip()]
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        candidates.append(fence.group(1).strip())
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start = text.find(open_c)
        while start != -1:
            depth = 0
            end = -1
            for i in range(start, len(text)):
                ch = text[i]
                if ch == open_c:
                    depth += 1
                elif ch == close_c:
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            if end != -1:
                candidates.append(text[start:end + 1])
            start = text.find(open_c, start + 1)
    for cand in candidates:
        try:
            return json.loads(cand)
        except (json.JSONDecodeError, ValueError):
            continue
    raise LLMError("无法从模型输出中解析 JSON")


class MockProvider(LLMProvider):
    """离线 Mock：不联网，返回固定内容，用于演示与测试。"""

    name = "mock"

    def complete(self, messages: list[ChatMessage], *, temperature: float = 0.3,
                 max_tokens: int = 4096) -> str:
        task = "unknown"
        for m in messages:
            if m.role == "system":
                match = re.search(r"\[TASK:\s*([\w\-]+)\]", m.content)
                if match:
                    task = match.group(1)
                break
        if task == "quiz-generate":
            return json.dumps({
                "questions": [
                    {"id": "q1", "question": "（Mock）这个项目的主要用途是什么？",
                     "options": ["A. 数据备份", "B. 项目复盘分析", "C. 图像识别", "D. 游戏引擎"],
                     "answer_index": 1, "explanation": "Mock 示例题。", "topic": "项目定位"},
                    {"id": "q2", "question": "（Mock）项目的主要入口文件是？",
                     "options": ["A. main.py", "B. utils.py", "C. README.md", "D. 以上都不是"],
                     "answer_index": 0, "explanation": "Mock 示例题。", "topic": "项目结构"},
                ],
                "essay": "（Mock）简述你对该项目核心流程的理解。",
            }, ensure_ascii=False)
        if task == "quiz-grade":
            return json.dumps({
                "items": [{"id": "q1", "score": 70, "comment": "Mock 评分示例。"},
                          {"id": "q2", "score": 70, "comment": "Mock 评分示例。"}],
                "overall": 70, "weakest_topics": ["Mock 示例主题"],
            }, ensure_ascii=False)
        titles = {
            "section-1": "项目介绍", "section-2": "技术栈", "section-3": "项目结构",
            "section-4": "核心代码分析", "section-5": "AI 生成部分",
            "section-6": "我的学习盲区", "section-7": "面试问题", "section-8": "下一步练习",
        }
        title = titles.get(task, "示例章节")
        return (f"## {title}\n\n"
                f"（Mock 输出）本内容由 mock provider 生成，用于离线演示流程。"
                f"配置真实 LLM（如 deepseek）后此处将输出真实分析。\n")
