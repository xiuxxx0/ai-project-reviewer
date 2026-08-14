"""个人技能档案：解析与渲染。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Profile:
    name: str = ""
    background: str = ""
    known_skills: list[str] = field(default_factory=list)
    learning_goals: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.name or self.background or self.known_skills or self.learning_goals)

    def render_text(self) -> str:
        lines = ["## 个人技能档案"]
        if self.name or self.background:
            lines.append(f"- 姓名/背景：{self.name}；{self.background}".rstrip("；"))
        lines.append(("- 已掌握：" + "、".join(self.known_skills)) if self.known_skills else "- 已掌握：（未填写）")
        lines.append(("- 学习目标：" + "、".join(self.learning_goals)) if self.learning_goals else "- 学习目标：（未填写）")
        return "\n".join(lines)


def load_profile(path: Path) -> Profile | None:
    """加载技能档案；不存在或解析失败返回 None。"""
    if not path.is_file():
        return None
    try:
        from ._yaml import parse_simple_yaml
        data = parse_simple_yaml(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    if not isinstance(data, dict):
        return None

    def _list(v):
        return [str(x) for x in v] if isinstance(v, list) else []

    return Profile(
        name=str(data.get("name") or ""),
        background=str(data.get("background") or ""),
        known_skills=_list(data.get("known_skills")),
        learning_goals=_list(data.get("learning_goals")),
    )
