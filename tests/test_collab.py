import re
import unittest

from apr.assessment.collab import AIContributionReport, build_ai_collab_report
from apr.evidence.base import EvidenceItem, EvidenceReport, EvidenceSource, FileVerdict


def _evidence(verdicts, items=None, participation=None):
    return EvidenceReport(items=items or [], per_file=verdicts,
                            participation=participation or [])


def _verdict(file, cls, items=None):
    score = {"AI 主导": 0.85, "AI 辅助": 0.5, "疑似人工": 0.1}[cls]
    return FileVerdict(file=file, score=score, confidence=0.7, items=items or [])


class CollabTest(unittest.TestCase):
    def test_ratios_sum_to_100(self):
        verdicts = {
            "a.java": _verdict("a.java", "AI 主导"),
            "b.java": _verdict("b.java", "AI 主导"),
            "c.java": _verdict("c.java", "AI 主导"),
            "d.java": _verdict("d.java", "AI 辅助"),
            "e.java": _verdict("e.java", "AI 辅助"),
            "f.java": _verdict("f.java", "AI 辅助"),
            "g.java": _verdict("g.java", "AI 辅助"),
            "h.java": _verdict("h.java", "疑似人工"),
            "i.java": _verdict("i.java", "疑似人工"),
            "j.java": _verdict("j.java", "疑似人工"),
        }
        r = build_ai_collab_report(_evidence(verdicts))
        self.assertEqual(r.ai_generation_pct, 30)
        self.assertEqual(r.ai_assist_pct, 40)
        self.assertEqual(r.human_pct, 30)
        self.assertEqual(r.ai_generation_pct + r.ai_assist_pct + r.human_pct, 100)

    def test_participation_types(self):
        items = [
            EvidenceItem(EvidenceSource.AGENT_LOG, "a.py", "claude-code: Claude Code 工具调用 Edit 修改 a.py"),
            EvidenceItem(EvidenceSource.AGENT_LOG, "b.py", "manual: 对话文本提及 b.py"),
        ]
        verdicts = {
            "a.py": _verdict("a.py", "AI 主导"),
            "doc.md": _verdict("doc.md", "AI 辅助"),
        }
        r = build_ai_collab_report(_evidence(verdicts, items))
        joined = "\n".join(r.participation_types)
        self.assertIn("代码生成", joined)
        self.assertIn("Debug辅助", joined)
        self.assertIn("架构讨论", joined)
        self.assertIn("文档生成", joined)

    def test_user_behaviors(self):
        git_mixed = EvidenceItem(EvidenceSource.GIT, "x.java", "1/3 次提交疑似 AI 参与", ai_score=0.3, confidence=0.5)
        verdicts = {
            "ai.java": _verdict("ai.java", "AI 主导"),
            "mix.java": _verdict("mix.java", "疑似人工", [git_mixed]),
            "human.java": _verdict("human.java", "疑似人工"),
        }
        r = build_ai_collab_report(_evidence(verdicts))
        joined = "\n".join(r.user_behaviors)
        self.assertIn("直接接受 AI 代码", joined)
        self.assertIn("重构 AI 代码", joined)
        self.assertIn("自己设计模块", joined)

    def test_strengths_and_suggestions(self):
        verdicts = {
            "a.java": _verdict("a.java", "AI 主导"),
            "b.java": _verdict("b.java", "AI 主导"),
            "c.java": _verdict("c.java", "AI 主导"),
            "d.java": _verdict("d.java", "疑似人工"),
        }
        r = build_ai_collab_report(_evidence(verdicts))
        self.assertTrue(any("减少直接复制" in s for s in r.suggestions))
        self.assertTrue(any("代码评审" in s for s in r.suggestions))

    def test_empty_evidence(self):
        r = build_ai_collab_report(EvidenceReport())
        self.assertEqual(r.ai_generation_pct + r.ai_assist_pct + r.human_pct, 0)
        md = r.render_markdown()
        self.assertIn("## AI 协作分析", md)
        self.assertIn("证据不足", md)

    def test_render_markdown_fields(self):
        verdicts = {"a.java": _verdict("a.java", "AI 辅助")}
        r = build_ai_collab_report(_evidence(verdicts))
        md = r.render_markdown()
        self.assertIn("AI 参与比例", md)
        self.assertIn("AI 主要用于", md)
        self.assertIn("你的参与", md)
        self.assertIn("你的优势", md)
        self.assertIn("提升建议", md)
        self.assertIn("不是作弊检测", md)

    def test_to_dict(self):
        r = build_ai_collab_report(EvidenceReport())
        d = r.to_dict()
        self.assertEqual(set(d.keys()), {"participation", "ai_participation_types",
                                          "user_behaviors", "strengths", "suggestions"})
        self.assertEqual(d["participation"]["ai_generation"], 0)

    def test_report_integration(self):
        from pathlib import Path
        from apr.analyzer import ReviewResult
        from apr.config import Config
        from apr.digest import ProjectDigest, TechStack
        from apr.report import render_report
        from apr.scanner import ScanResult
        root = Path("C:/fake/proj")
        scan = ScanResult(root=root, files=[])
        digest = ProjectDigest(root=root, scan=scan,
                               stack=TechStack(languages={}, platforms=[], dependencies={}),
                               key_files=[], tree_text="")
        sections = [(t, "## " + t + "\n\n（测试内容）") for t in
                    ("项目介绍", "技术栈", "项目结构", "核心代码分析", "AI 协作分析",
                     "我的学习盲区", "面试问题", "下一步练习")]
        result = ReviewResult(project=root, config=Config(), scan=scan, digest=digest,
                              evidence=EvidenceReport(), profile=None, quiz=None,
                              sections=sections, git_head=None,
                              started_at="2026-01-01T00:00:00", notes=[])
        text = render_report(result)
        self.assertIn("## AI 协作分析", text)
        self.assertIn("5. [AI 协作分析](#AI 协作分析)", text)
        self.assertNotIn("## AI 生成部分", text)
        self.assertNotIn("（测试内容）", text[text.find("## AI 协作分析"):text.find("---", text.find("## AI 协作分析"))])
