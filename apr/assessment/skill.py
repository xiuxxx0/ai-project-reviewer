"""Skill Assessment：综合判断用户真实技能水平。

输入四类信号，输出 SkillAssessment 数据结构（逐技能条目）：

1. profile.yaml 技能档案（Profile 对象；known_skills 支持内联等级标注
   "Python: intermediate"，也支持纯名字 "Python"）
2. 项目扫描结果（ScanResult → 经 digest 复用语言/平台/依赖检测）
3. Quiz 评分结果（QuizResult → 按 question.topic 匹配技能聚合得分）
4. AI 贡献证据（EvidenceReport → 该技能文件的平均 AI 贡献度，
   AI 占比过高时下调等级与置信度：代码大半是 AI 写的，真实掌握存疑）

本模块只新增不改旧：不修改 profile/scanner/quiz/report/analyzer 等已有文件；
未来接入报告时，在 analyzer.run_review 的 quiz 之后、8 大板块之前调用
assess_skills(profile, scan, quiz, evidence) 即可。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..digest import EXT_LANGUAGE, detect_tech_stack
from ..evidence.base import EvidenceReport
from ..profile import Profile
from ..scanner import ScanResult
from .quiz import QuizResult

LEVELS = ["beginner", "intermediate", "advanced", "expert"]

# 报告中展示用的中文等级标签
LEVEL_LABELS = {"beginner": "入门", "intermediate": "掌握", "advanced": "熟练", "expert": "精通"}

_LEVEL_ALIASES = {
    "初级": "beginner", "入门": "beginner", "beginner": "beginner", "novice": "beginner",
    "basic": "beginner", "了解": "beginner",
    "中级": "intermediate", "intermediate": "intermediate",
    "高级": "advanced", "advanced": "advanced",
    "专家": "expert", "expert": "expert", "精通": "expert",
}


def _normalize_level(level: str | None) -> str | None:
    """等级归一化：basic→beginner、中文别名→英文标准等级。"""
    if not level:
        return None
    return _LEVEL_ALIASES.get(str(level).strip().lower())

# 作为平台标签出现但不构成独立技能项的噪声标签
_SKIP_PLATFORMS = {"文档"}

# 配置/文档类"技能"噪声（复用 digest 检测时会出现），不进入技能评估
_SKIP_SKILLS = {"other", "example", "文档", "toml", "yaml", "yml", "json",
                "markdown", "text", "ini", "cfg"}


@dataclass
class SkillAssessmentEntry:
    skill: str
    claimed_level: str | None
    evidence: list[str]
    quiz_score: int | None
    final_level: str
    confidence: float
    project_evidence: list[str] = field(default_factory=list)  # 项目使用证据（报告中单独展示）

    def to_dict(self) -> dict:
        return {
            "claimed_level": self.claimed_level,
            "evidence": list(self.evidence),
            "quiz_score": self.quiz_score,
            "final_level": self.final_level,
            "confidence": self.confidence,
        }


@dataclass
class SkillAssessment:
    entries: dict[str, SkillAssessmentEntry] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """输出与设计示例一致的 JSON 结构：{技能名: {claimed_level, evidence, quiz_score, final_level, confidence}}"""
        return {skill: entry.to_dict() for skill, entry in self.entries.items()}

    def sorted_entries(self) -> list[SkillAssessmentEntry]:
        """按等级（高→低）再按置信度（高→低）排序。"""
        return sorted(self.entries.values(),
                      key=lambda e: (-LEVELS.index(e.final_level), -e.confidence, e.skill))

    def weakest(self) -> list[SkillAssessmentEntry]:
        """薄弱技能：等级为 beginner 或 quiz 低于 60，按置信度从低到高。"""
        weak = [e for e in self.entries.values()
                if e.final_level == "beginner" or (e.quiz_score is not None and e.quiz_score < 60)]
        return sorted(weak, key=lambda e: (e.confidence, e.skill))

    def render_text(self) -> str:
        lines = ["## 技能水平评估"]
        for e in self.sorted_entries():
            quiz = f"{e.quiz_score}/100" if e.quiz_score is not None else "未验证"
            claimed = e.claimed_level or "未标注"
            lines.append(f"- {e.skill}：档案 {claimed} → 综合 {e.final_level}"
                         f"（置信度 {e.confidence:.0%}，quiz {quiz}）")
            for ev in e.evidence:
                lines.append(f"    · {ev}")
        return "\n".join(lines)

    def render_markdown(self) -> str:
        lines = [
            "## 技能水平评估",
            "",
            "| 技能 | 档案声明 | Quiz | 综合判定 | 置信度 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for e in self.sorted_entries():
            quiz = str(e.quiz_score) if e.quiz_score is not None else "—"
            claimed = e.claimed_level or "未标注"
            lines.append(f"| {e.skill} | {claimed} | {quiz} | {e.final_level} | {e.confidence:.0%} |")
        for e in self.sorted_entries():
            if e.evidence:
                lines += ["", f"**{e.skill}**"]
                lines += [f"- {ev}" for ev in e.evidence]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _parse_claimed(entry: str) -> tuple[str, str | None]:
    """解析 known_skills 条目：纯名字 "Python" 或内联等级 "Python: intermediate"。

    等级支持半角/全角冒号与等号分隔，并支持中文别名（中级→intermediate 等）。
    """
    name = entry.strip()
    level = None
    for sep in (":", "=", "："):
        if sep in name:
            left, _, right = name.partition(sep)
            alias = right.strip().lower()
            if alias in _LEVEL_ALIASES:
                name = left.strip()
                level = _LEVEL_ALIASES[alias]
                break
    return name, level


def _core(name: str) -> str:
    """技能名核心部分："TypeScript/React" → "TypeScript"。"""
    return name.split("/")[0]


def _normalize_dep(dep: str) -> str | None:
    """依赖名 → 技能名："@scope/pkg" → "Pkg"；不合法返回 None。"""
    name = dep.strip().split("/")[-1]
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.\-]*", name):
        return None
    if len(name) < 2 or len(name) > 30:
        return None
    return name[0].upper() + name[1:]


def _quiz_score_for(skill: str, quiz: QuizResult | None) -> tuple[int | None, int]:
    """按 question.topic 匹配技能，聚合平均得分。返回 (平均分或 None, 匹配题数)。"""
    if quiz is None:
        return None, 0
    core = _core(skill).lower()
    scores: list[int] = []
    for q, g in zip(quiz.questions, quiz.grades):
        topic = (q.topic or "").strip().lower()
        topic_core = topic.split("/")[0]
        if core and (core in topic or topic in core or topic_core == core):
            try:
                scores.append(int(g.get("score", 0)))
            except (TypeError, ValueError):
                continue
    if not scores:
        return None, 0
    return round(sum(scores) / len(scores)), len(scores)


def _files_for_skill(skill: str, scan: ScanResult | None) -> list:
    """该技能对应的项目文件（仅语言类技能可按扩展名匹配）。"""
    if scan is None:
        return []
    core = _core(skill)
    return [f for f in scan.files
            if _core(EXT_LANGUAGE.get(f.ext, "")) == core]


def _ai_stats(skill: str, scan: ScanResult | None, evidence: EvidenceReport | None):
    """该技能文件的 AI 贡献统计。返回 (平均 AI 贡献度或 None, 参与判定的文件数)。"""
    if evidence is None:
        return None, 0
    scores: list[float] = []
    for f in _files_for_skill(skill, scan):
        verdict = evidence.per_file.get(f.rel)
        if verdict and verdict.score is not None and verdict.confidence >= 0.3:
            scores.append(verdict.score)
    if not scores:
        return None, 0
    return sum(scores) / len(scores), len(scores)


def _infer_usage_level(files: int) -> str:
    """无档案声明时按项目使用规模推断等级。"""
    if files >= 30:
        return "advanced"
    if files >= 10:
        return "intermediate"
    return "beginner"


def _final_level(claimed: str | None, files: int, quiz_score: int | None,
                 ai_share: float | None) -> str:
    if claimed:
        base = claimed
    elif files > 0:
        base = _infer_usage_level(files)
    else:
        base = "beginner"
    idx = LEVELS.index(base)
    if quiz_score is not None:
        if quiz_score >= 80:
            idx += 1
        elif quiz_score < 60:
            idx -= 1
    if ai_share is not None and ai_share > 0.6:
        idx -= 1  # 代码大半由 AI 生成，真实掌握水平下调一档
    idx = max(0, min(len(LEVELS) - 1, idx))
    return LEVELS[idx]


def _confidence(claimed: str | None, files: int, used: bool, quiz_score: int | None,
                ai_share: float | None, ai_n: int) -> float:
    conf = 0.35
    if claimed:
        conf += 0.20
    if files > 0:
        conf += 0.15
    if used:
        conf += 0.10
    if quiz_score is not None:
        conf += 0.20
    if ai_n > 0:
        conf += 0.10
    if ai_share is not None and ai_share > 0.6:
        conf *= 0.7
    if claimed and files == 0 and not used:
        conf *= 0.7  # 只有档案声明、项目未使用
    return round(min(0.95, max(0.15, conf)), 2)


def _collect_skills(profile: Profile | None, scan: ScanResult | None,
                    quiz: QuizResult | None) -> dict:
    """技能集合与元信息：{技能名: {claimed, files, used, learning, topics, priority}}。"""
    skills: dict = {}

    def entry_for(name: str) -> dict:
        return skills.setdefault(name, {"claimed": None, "files": 0, "used": False,
                                        "learning": False, "topics": [], "priority": ""})

    if profile is not None:
        # 新格式：mastered / learning 条目（带 level 与 topics）
        for claim in profile.mastered:
            name = str(claim.name).strip()
            if not name:
                continue
            entry = entry_for(name)
            if _normalize_level(claim.level):
                entry["claimed"] = _normalize_level(claim.level)
            entry["topics"] = [str(t) for t in claim.topics if t]
        for claim in profile.learning:
            name = str(claim.name).strip()
            if not name:
                continue
            entry = entry_for(name)
            if _normalize_level(claim.level):
                entry["claimed"] = _normalize_level(claim.level)
            entry["learning"] = True
            entry["topics"] = [str(t) for t in claim.topics if t]
        # 新格式：target 目标条目（无自评，只有优先级）
        for target in profile.targets:
            name = str(target.name).strip()
            if not name:
                continue
            entry = entry_for(name)
            entry["priority"] = str(target.priority or "")
        # 旧格式：known_skills 字符串（可带内联等级）
        for raw in profile.known_skills:
            name, level = _parse_claimed(str(raw))
            if not name:
                continue
            entry = entry_for(name)
            if level:
                entry["claimed"] = level
    if scan is not None:
        stack = detect_tech_stack(scan.files, scan.root)
        for lang, count in stack.languages.items():
            name = _core(lang)
            if name.lower() in _SKIP_SKILLS:
                continue
            entry = skills.setdefault(name, {"claimed": None, "files": 0, "used": False})
            entry["files"] = count
        for platform in stack.platforms:
            if platform in _SKIP_PLATFORMS:
                continue
            name = _core(platform)
            entry = skills.setdefault(name, {"claimed": None, "files": 0, "used": False})
            entry["used"] = True
        for deps in stack.dependencies.values():
            for dep in deps:
                name = _normalize_dep(dep)
                if not name or name.lower() in _SKIP_SKILLS:
                    continue
                # 与已有技能名大小写不敏感合并
                existing = next((k for k in skills if k.lower() == name.lower()), None)
                if existing:
                    skills[existing]["used"] = True
                else:
                    skills[name] = {"claimed": None, "files": 0, "used": True}
    return skills


def assess_skills(profile: Profile | None = None,
                  scan: ScanResult | None = None,
                  quiz: QuizResult | None = None,
                  evidence: EvidenceReport | None = None) -> SkillAssessment:
    """综合四类信号，输出逐技能的 SkillAssessment。

    参数均可为 None（对应信号缺失），结果中会体现在 evidence 与 confidence 上。
    """
    assessment = SkillAssessment()
    skills = _collect_skills(profile, scan, quiz)

    for skill, meta in sorted(skills.items()):
        files = _files_for_skill(skill, scan)
        ai_share, ai_n = _ai_stats(skill, scan, evidence)
        quiz_score, quiz_n = _quiz_score_for(skill, quiz)
        evidence_lines: list[str] = []

        claimed = meta["claimed"]
        if claimed:
            evidence_lines.append(f"技能档案自评（{claimed}）")
        elif profile is not None and (profile.known_skills or profile.mastered or profile.learning):
            evidence_lines.append("技能档案未声明")
        if meta.get("learning"):
            evidence_lines.append("档案标注：正在学习")
        if meta.get("topics"):
            evidence_lines.append("档案关注主题：" + "、".join(meta["topics"]))
        if meta.get("priority"):
            evidence_lines.append(f"学习目标（优先级 {meta['priority']}）")

        project_lines: list[str] = []
        if files:
            line = f"使用 {skill} 编写 {len(files)} 个文件"
            evidence_lines.append(f"项目使用 {skill} {len(files)} 个文件")
            project_lines.append(line)
        elif meta.get("used"):
            evidence_lines.append(f"项目依赖/平台声明使用 {skill}")
            project_lines.append(f"项目依赖/平台声明使用 {skill}")
        else:
            assessment.notes.append(f"{skill}：档案声明但项目未实际使用")

        if quiz_score is not None:
            evidence_lines.append(f"用户完成 Quiz：{quiz_n} 题平均得分 {quiz_score}")

        if ai_n > 0:
            ai_pct = ai_share * 100
            if ai_pct > 60:
                evidence_lines.append(
                    f"AI 贡献证据：{ai_n} 个文件参与判定，平均 AI 贡献度 {ai_pct:.0f}%（AI 占主导）")
            else:
                evidence_lines.append(
                    f"AI 贡献证据：{ai_n} 个文件参与判定，平均 AI 贡献度 {ai_pct:.0f}%（人工为主）")

        assessment.entries[skill] = SkillAssessmentEntry(
            skill=skill,
            claimed_level=claimed,
            evidence=evidence_lines,
            quiz_score=quiz_score,
            final_level=_final_level(claimed, len(files), quiz_score, ai_share),
            confidence=_confidence(claimed, len(files), bool(meta.get("used")),
                                   quiz_score, ai_share, ai_n),
            project_evidence=project_lines,
        )
    return assessment
