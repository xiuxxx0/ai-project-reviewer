"""实践验证：AI 出题 → 用户终端作答 → AI 批改评分。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..errors import LLMError, QuizAborted
from ..llm.base import ChatMessage, LLMProvider


@dataclass
class Question:
    id: str
    question: str
    options: list[str]
    answer_index: int
    explanation: str
    topic: str


@dataclass
class QuizResult:
    questions: list[Question] = field(default_factory=list)
    essay: str = ""
    user_answers: list[str] = field(default_factory=list)   # 与 questions 对齐（选项内容）
    user_essay: str = ""
    grades: list[dict] = field(default_factory=list)
    overall: int = 0
    weakest_topics: list[str] = field(default_factory=list)

    def render_text(self) -> str:
        if not self.questions:
            return "（无问答验证数据）"
        lines = ["## 实践验证结果", f"- 总体评分：{self.overall}/100"]
        for q, a, g in zip(self.questions, self.user_answers, self.grades):
            lines.append(f"- 题「{q.question[:60]}」：我的答案 {a}，得分 {g.get('score', 0)}，点评：{g.get('comment', '')}")
        if self.user_essay:
            lines.append(f"- 简答题回答：{self.user_essay[:200]}")
        if self.weakest_topics:
            lines.append("- 薄弱主题：" + "、".join(self.weakest_topics))
        return "\n".join(lines)

    def render_markdown(self) -> str:
        if not self.questions:
            return "（无问答验证数据）"
        lines = [
            "### 作答记录",
            "",
            "| 题目 | 我的答案 | 得分 | 点评 |",
            "| --- | --- | --- | --- |",
        ]
        for q, a, g in zip(self.questions, self.user_answers, self.grades):
            correct = q.options[q.answer_index] if 0 <= q.answer_index < len(q.options) else ""
            lines.append(f"| {q.question[:60]} | {a}（参考：{correct[:30]}） | {g.get('score', 0)} | {g.get('comment', '')} |")
        if self.user_essay:
            lines += ["", f"**简答题回答**：{self.user_essay}"]
        lines += ["", f"**总体评分**：{self.overall}/100"]
        if self.weakest_topics:
            lines += ["", f"**薄弱主题**：{'、'.join(self.weakest_topics)}"]
        return "\n".join(lines)


def _complete_json_retry(llm: LLMProvider, system: str, user: str,
                             max_tokens: int = 8192):
    """JSON 输出 + 解析失败时纠错重试一次（推理模型思考过程可能截断 JSON）。"""
    messages = [ChatMessage("system", system), ChatMessage("user", user)]
    try:
        return llm.complete_json(messages, max_tokens=max_tokens)
    except LLMError:
        messages.append(ChatMessage("assistant", "（上一次输出不是合法 JSON）"))
        messages.append(ChatMessage(
            "user", "请只输出符合要求的 JSON，不要任何额外文字、不要截断。"))
        return llm.complete_json(messages, max_tokens=max_tokens)


def generate_questions(llm: LLMProvider, digest_text: str, count: int) -> tuple[list[Question], str]:
    system = (
        "[TASK: quiz-generate]\n"
        "你是 AI Project Reviewer 的实践验证出题人。你根据项目画像出题，"
        "用于检验项目作者对自家项目的真实理解。输出必须是严格 JSON。"
    )
    user = (
        "【项目画像】\n" + digest_text[:12000] + "\n\n"
        + f"出 {count} 道单选题 + 1 道简答题：\n"
        + "- 选择题考察项目技术栈、核心实现、架构决策，必须贴合材料中的真实细节；\n"
        + "- 每题 4 个选项，正确答案位置随机；\n"
        + "- 输出 JSON 结构：\n"
        + '{"questions": [{"id": "q1", "question": "题目", "options": ["选项1", "选项2", "选项3", "选项4"], '
        + '"answer_index": 0, "explanation": "解析", "topic": "主题"}], "essay": "简答题题目"}\n'
        + "只输出 JSON，不要其他文字。"
    )
    data = _complete_json_retry(llm, system, user)
    questions = []
    for q in (data.get("questions") or [])[:count]:
        try:
            questions.append(Question(
                id=str(q.get("id") or f"q{len(questions) + 1}"),
                question=str(q["question"]),
                options=[str(o) for o in q["options"]],
                answer_index=int(q.get("answer_index", 0)),
                explanation=str(q.get("explanation", "")),
                topic=str(q.get("topic", "")),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    if not questions:
        raise LLMError("出题失败：模型未返回有效题目")
    essay = str(data.get("essay") or "")
    return questions, essay


def ask_questions(questions: list[Question], essay: str,
                  input_fn=input, print_fn=print) -> tuple[list[str], str]:
    answers: list[str] = []
    print_fn("")
    print_fn("=" * 60)
    print_fn("  实践验证 · 交互问答（检验真实掌握程度，输入 q 退出）")
    print_fn("=" * 60)
    for q in questions:
        print_fn("")
        print_fn(f"【{q.topic}】{q.question}")
        for i, opt in enumerate(q.options, 1):
            print_fn(f"  {i}. {opt}")
        answered = False
        for _ in range(3):
            raw = input_fn("你的答案（1-4）: ").strip()
            if raw.lower() == "q":
                raise QuizAborted("用户退出问答")
            if raw.isdigit() and 1 <= int(raw) <= len(q.options):
                answers.append(q.options[int(raw) - 1])
                answered = True
                break
        if not answered:
            answers.append("（未作答）")
    print_fn("")
    user_essay = ""
    if essay:
        print_fn(f"【简答】{essay}")
        raw = input_fn("你的回答（q 退出）: ").strip()
        if raw.lower() == "q":
            raise QuizAborted("用户退出问答")
        user_essay = raw
    return answers, user_essay


def grade_answers(llm: LLMProvider, questions: list[Question], answers: list[str],
                  essay: str, user_essay: str) -> dict:
    system = (
        "[TASK: quiz-grade]\n"
        "你是 AI Project Reviewer 的阅卷人。对比标准答案与用户答案，客观评分。"
        "输出必须是严格 JSON。"
    )
    qas = []
    for q, a in zip(questions, answers):
        qas.append({"id": q.id, "question": q.question, "options": q.options,
                    "correct_index": q.answer_index, "explanation": q.explanation,
                    "topic": q.topic, "user_answer": a})
    payload = json.dumps({"questions": qas, "essay": essay, "user_essay": user_essay[:500]},
                         ensure_ascii=False)
    user = (
        "【试卷与作答】\n" + payload + "\n\n"
        + "评分规则：选择题答对得 100，答错或未答得 0（对比 user_answer 与 correct_index 对应选项）；"
        + "简答题按理解深度给 0-100。\n"
        + "输出 JSON 结构：\n"
        + '{"items": [{"id": "q1", "score": 100, "comment": "点评"}], '
        + '"overall": 80, "weakest_topics": ["主题"]}\n'
        + "overall 为加权总分（选择题 80% + 简答 20%，未答按 0 分）。只输出 JSON。"
    )
    data = _complete_json_retry(llm, system, user, max_tokens=4096)
    items = data.get("items") or []
    overall = int(data.get("overall") or 0)
    weakest = [str(t) for t in (data.get("weakest_topics") or [])]
    return {"items": items, "overall": overall, "weakest_topics": weakest}


def run_quiz(llm: LLMProvider, digest_text: str, count: int,
             input_fn=input, print_fn=print) -> QuizResult:
    print_fn("正在出题…")
    questions, essay = generate_questions(llm, digest_text, count)
    answers, user_essay = ask_questions(questions, essay, input_fn, print_fn)
    print_fn("正在批改…")
    graded = grade_answers(llm, questions, answers, essay, user_essay)
    result = QuizResult(questions=questions, essay=essay, user_answers=answers,
                        user_essay=user_essay, grades=graded["items"],
                        overall=graded["overall"], weakest_topics=graded["weakest_topics"])
    print_fn(f"总体评分：{result.overall}/100")
    return result
