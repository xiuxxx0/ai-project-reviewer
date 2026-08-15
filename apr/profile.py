"""个人技能档案：解析与渲染。

支持两种格式：
1. 旧扁平格式（兼容保留）：name / background / known_skills / learning_goals
2. RepoCourse 新格式：profile{name, role, goal} / skills{mastered, learning, target} /
   learning_preferences，技能条目带 level 与 topics。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SkillClaim:
    """新格式的技能条目（mastered / learning）。"""
    name: str = ""
    level: str | None = None       # basic/beginner/intermediate/advanced/expert（或中文）
    topics: list[str] = field(default_factory=list)


@dataclass
class TargetSkill:
    """新格式的学习目标条目（target）。"""
    name: str = ""
    priority: str = ""             # high / medium / low


@dataclass
class Profile:
    name: str = ""
    background: str = ""
    known_skills: list[str] = field(default_factory=list)      # 旧格式：技能名（可带 "name: level"）
    learning_goals: list[str] = field(default_factory=list)    # 旧格式
    role: str = ""
    goals: list[str] = field(default_factory=list)             # 新格式：职业/学习目标
    mastered: list[SkillClaim] = field(default_factory=list)   # 新格式：已掌握
    learning: list[SkillClaim] = field(default_factory=list)   # 新格式：正在学
    targets: list[TargetSkill] = field(default_factory=list)   # 新格式：想学
    preferences: dict = field(default_factory=dict)            # 新格式：学习偏好

    @property
    def is_empty(self) -> bool:
        return not (self.name or self.background or self.role or self.goals
                    or self.known_skills or self.learning_goals
                    or self.mastered or self.learning or self.targets)

    def all_claims(self) -> list[SkillClaim]:
        """mastered + learning 合并（供技能评估使用）。"""
        return list(self.mastered) + list(self.learning)

    def render_text(self) -> str:
        lines = ["## 个人技能档案"]
        if self.name or self.role:
            head = f"{self.name}" + (f"（{self.role}）" if self.role else "")
            lines.append(f"- 姓名/身份：{head}")
        if self.goals:
            lines.append("- 目标：" + "、".join(self.goals))
        mastered_lines = []
        for c in self.mastered:
            level = c.level or "未标注"
            topics = f"（主题：{'、'.join(c.topics)}）" if c.topics else ""
            mastered_lines.append(f"{c.name} [{level}]{topics}")
        learning_lines = []
        for c in self.learning:
            level = c.level or "未标注"
            topics = f"（主题：{'、'.join(c.topics)}）" if c.topics else ""
            learning_lines.append(f"{c.name} [{level}]{topics}")
        if mastered_lines:
            lines.append("- 已掌握：" + "；".join(mastered_lines))
        elif self.known_skills:
            lines.append("- 已掌握：" + "、".join(self.known_skills))
        else:
            lines.append("- 已掌握：（未填写）")
        if learning_lines:
            lines.append("- 正在学习：" + "；".join(learning_lines))
        if self.targets:
            lines.append("- 学习目标：" + "；".join(
                f"{t.name}（优先级 {t.priority or '未标注'}）" for t in self.targets))
        elif self.learning_goals:
            lines.append("- 学习目标：" + "、".join(self.learning_goals))
        prefs = [k for k, v in self.preferences.items() if v]
        if prefs:
            lines.append("- 学习偏好：" + "、".join(prefs))
        return "\n".join(lines)


def _str_list(value) -> list[str]:
    """列表 → 字符串列表；单键映射还原为 "key: value"（旧格式内联等级标注）。"""
    if not isinstance(value, list):
        return []
    result = []
    for x in value:
        if isinstance(x, dict) and len(x) == 1:
            key, val = next(iter(x.items()))
            if isinstance(val, str):
                result.append(f"{key}: {val}")
                continue
        result.append(str(x))
    return result


def _claims(value) -> list[SkillClaim]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        level = item.get("level")
        result.append(SkillClaim(
            name=str(item.get("name") or "").strip(),
            level=str(level).strip() if level else None,
            topics=_str_list(item.get("topics")),
        ))
    return [c for c in result if c.name]


def _targets(value) -> list[TargetSkill]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        result.append(TargetSkill(
            name=str(item.get("name") or "").strip(),
            priority=str(item.get("priority") or "").strip(),
        ))
    return [t for t in result if t.name]


def load_profile(path: Path) -> Profile | None:
    """加载技能档案；不存在或解析失败返回 None。自动识别新旧格式。"""
    if not path.is_file():
        return None
    try:
        from ._yaml import parse_simple_yaml
        data = parse_simple_yaml(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    if not isinstance(data, dict):
        return None

    block = data.get("profile") if isinstance(data.get("profile"), dict) else {}
    skills_block = data.get("skills") if isinstance(data.get("skills"), dict) else {}
    prefs = data.get("learning_preferences") if isinstance(data.get("learning_preferences"), dict) else {}

    return Profile(
        name=str(block.get("name") or data.get("name") or ""),
        background=str(data.get("background") or ""),
        role=str(block.get("role") or ""),
        goals=_str_list(block.get("goal")),
        known_skills=_str_list(data.get("known_skills")),
        learning_goals=_str_list(data.get("learning_goals")),
        mastered=_claims(skills_block.get("mastered")),
        learning=_claims(skills_block.get("learning")),
        targets=_targets(skills_block.get("target")),
        preferences={str(k): v for k, v in prefs.items()},
    )
