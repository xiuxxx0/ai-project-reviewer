import json
import unittest

from apr.events import ADAPTERS, DSHAdapter, GenericAdapter, load_events
from tests import fixture_dir

# 真实 DSH 格式（与 harness 会话日志一致）
REAL_DSH = [
    {"type": "session", "version": 0, "id": "s1", "createdAt": 1785013630399, "cwd": "C:/workspace"},
    {"type": "user/message", "seq": 1, "time": 1785013630411,
     "data": {"content": [{"type": "text", "text": "帮我写个缓存工具类"}]}},
    {"type": "assistant/message", "seq": 2, "time": 1785013631500,
     "data": {"content": [
         {"type": "reasoning", "text": "用户需要缓存工具。"},
         {"type": "tool-call", "id": "call_1", "name": "write",
          "arguments": "{\"file_path\": \"C:/workspace/src/CacheHelper.java\", \"code\": \"class C{}\", \"description\": \"write cache helper\"}"}]}},
    {"type": "tool/result", "seq": 3, "time": 1785013632100,
     "data": {"callId": "call_1", "isError": False,
              "content": [{"type": "text", "text": "已写入 src/CacheHelper.java"}]}},
    {"type": "session/title", "seq": 4, "time": 1785013632200, "data": {"title": "缓存"}},
]

# 旧假设格式（Claude 风格，宽容兼容）
LEGACY = [
    {"type": "user", "timestamp": "2026-08-15T10:00:00Z", "cwd": "C:/proj",
     "message": {"role": "user", "content": "hello"}},
    {"type": "assistant", "timestamp": "2026-08-15T10:01:00Z", "cwd": "C:/proj",
     "message": {"role": "assistant", "content": [
         {"type": "tool_use", "name": "Edit",
          "input": {"file_path": "C:/proj/src/X.java", "old_string": "x", "new_string": "y"}}]}},
]


class EventsTest(unittest.TestCase):
    def test_real_dsh_user_message(self):
        events = DSHAdapter().parse(REAL_DSH[1], "dsh")
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual(e.actor, "user")
        self.assertEqual(e.event_type, "message")
        self.assertEqual(e.content, "帮我写个缓存工具类")
        self.assertIsNotNone(e.timestamp)          # 毫秒 → ISO
        self.assertIn("T", e.timestamp)

    def test_real_dsh_assistant_tool_call(self):
        adapter = DSHAdapter()
        adapter.parse(REAL_DSH[0], "dsh")           # session 行携带 cwd
        events = adapter.parse(REAL_DSH[2], "dsh")
        self.assertGreaterEqual(len(events), 2)    # tool_call + 文本
        tool = [e for e in events if e.event_type == "write"][0]
        self.assertEqual(tool.actor, "assistant")
        self.assertEqual(tool.file, "src/CacheHelper.java")   # 盘符 + cwd 归一化
        self.assertIn("write", tool.content)
        msg = [e for e in events if e.event_type == "message"][0]
        self.assertIn("缓存工具", msg.content)      # reasoning 并入 message

    def test_real_dsh_tool_result(self):
        events = DSHAdapter().parse(REAL_DSH[3], "dsh")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].actor, "tool")
        self.assertEqual(events[0].event_type, "tool_result")
        self.assertIn("已写入", events[0].content)

    def test_real_dsh_session_lines_skipped(self):
        self.assertEqual(DSHAdapter().parse(REAL_DSH[0], "dsh"), [])
        self.assertEqual(DSHAdapter().parse(REAL_DSH[4], "dsh"), [])

    def test_legacy_format_tolerated(self):
        adapter = DSHAdapter()
        e1 = adapter.parse(LEGACY[0], "dsh")[0]
        self.assertEqual(e1.actor, "user")
        self.assertEqual(e1.content, "hello")
        e2 = adapter.parse(LEGACY[1], "dsh")[0]
        self.assertEqual(e2.event_type, "edit")
        self.assertEqual(e2.file, "src/X.java")

    def test_generic_openai_style(self):
        events = GenericAdapter().parse({"role": "user", "content": "hi"}, "generic")
        self.assertEqual(events[0].actor, "user")
        self.assertEqual(events[0].event_type, "message")

    def test_generic_fallback_record(self):
        events = GenericAdapter().parse({"hello": "world"}, "generic")
        self.assertEqual(events[0].event_type, "record")
        self.assertIn("world", events[0].content)

    def test_invalid_lines_skipped(self):
        adapter = DSHAdapter()
        self.assertEqual(adapter.parse_line("not json", "dsh"), [])
        self.assertEqual(adapter.parse_line('["a"]', "dsh"), [])

    def test_load_events_real_dsh_file(self):
        root = fixture_dir("knowledge")
        path = root / "session.jsonl"
        path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in REAL_DSH),
                        encoding="utf-8")
        events = load_events(path, source="dsh")   # 顺序解析，cwd 由 session 行提供
        # 4 条产出：user message + write tool_call + assistant text + tool_result
        self.assertEqual(len(events), 4)
        self.assertEqual(events[0].source, "dsh")
        self.assertEqual(events[1].event_type, "write")
        self.assertEqual(events[1].file, "src/CacheHelper.java")

    def test_to_dict_fields(self):
        events = DSHAdapter().parse(REAL_DSH[2], "dsh")
        d = events[0].to_dict()
        self.assertEqual(set(d.keys()),
                         {"timestamp", "source", "actor", "event_type", "file", "content"})

    def test_adapters_registered(self):
        self.assertIn("dsh", ADAPTERS)
        self.assertIn("generic", ADAPTERS)
        self.assertNotIn("cursor", ADAPTERS)
