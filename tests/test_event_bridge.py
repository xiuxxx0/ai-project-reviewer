import json
import unittest

from apr.config import LimitsConfig
from apr.evidence.agent_logs import collect_dsh_events
from apr.scanner import scan_project
from tests import fixture_dir


class EventBridgeTest(unittest.TestCase):
    def test_dsh_events_bridge_to_evidence(self):
        root = fixture_dir("knowledge")     # 项目目录
        dsh_dir = fixture_dir("dsh")        # DSH 日志目录（预创建）
        (root / "CacheHelper.java").write_text(
            "public class CacheHelper { private final RedisTemplate rt; }\n",
            encoding="utf-8")
        log = dsh_dir / "session.jsonl"
        log.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [
            {"type": "session", "id": "s1", "createdAt": 1785013630399, "cwd": str(root)},
            {"type": "user/message", "seq": 1, "time": 1785013630411,
             "data": {"content": [{"type": "text", "text": "写个缓存"}]}},
            {"type": "assistant/message", "seq": 2, "time": 1785013631500,
             "data": {"content": [
                 {"type": "tool-call", "id": "c1", "name": "write",
                  "arguments": json.dumps({"file_path": str(root) + "/CacheHelper.java",
                                           "code": "class C{}"})}]}},
        ]), encoding="utf-8")
        scan = scan_project(root, LimitsConfig())
        items, notes = collect_dsh_events(root, scan, str(dsh_dir))
        self.assertGreaterEqual(len(items), 1)
        ev = [i for i in items if i.file == "CacheHelper.java"][0]
        self.assertEqual(ev.source.value, "agent-log")
        self.assertEqual(ev.ai_score, 0.8)          # write → (0.8, 0.8)
        self.assertEqual(ev.confidence, 0.8)
        self.assertIn("dsh", ev.detail)
        self.assertTrue(any("统一事件系统" in n for n in notes))

    def test_no_matching_files(self):
        root = fixture_dir("knowledge")
        dsh_dir = fixture_dir("dsh")
        log = dsh_dir / "other.jsonl"
        log.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [
            {"type": "session", "id": "s1", "createdAt": 1, "cwd": "C:/nowhere"},
            {"type": "assistant/message", "seq": 1, "time": 2,
             "data": {"content": [
                 {"type": "tool-call", "id": "c1", "name": "write",
                  "arguments": json.dumps({"file_path": "C:/nowhere/Ghost.java"})}]}},
        ]), encoding="utf-8")
        scan = scan_project(root, LimitsConfig())
        items, _ = collect_dsh_events(root, scan, str(dsh_dir))
        self.assertEqual(items, [])                # 文件不在项目中 → 不桥接
