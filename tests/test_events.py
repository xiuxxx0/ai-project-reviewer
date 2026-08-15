import json
import unittest

from apr.events import ADAPTERS, DSHAdapter, GenericAdapter, load_events
from tests import fixture_dir

DSH_LINES = [
    {"type": "user", "timestamp": "2026-08-15T10:00:00Z", "cwd": "C:/proj",
     "message": {"role": "user", "content": "帮我写个缓存工具类"}},
    {"type": "assistant", "timestamp": "2026-08-15T10:01:00Z", "cwd": "C:/proj",
     "message": {"role": "assistant", "content": [
         {"type": "tool_use", "name": "Edit",
          "input": {"file_path": "C:/proj/src/CacheHelper.java",
                    "old_string": "x", "new_string": "y"}}]}},
    {"type": "assistant", "timestamp": "2026-08-15T10:02:00Z",
     "message": {"role": "assistant", "content": [
         {"type": "text", "text": "已完成。"},
         {"type": "text", "text": "请检查。"}]}},
]


class EventsTest(unittest.TestCase):
    def test_dsh_user_message(self):
        adapter = DSHAdapter()
        event = adapter.parse(DSH_LINES[0], "dsh")
        self.assertIsNotNone(event)
        self.assertEqual(event.actor, "user")
        self.assertEqual(event.event_type, "message")
        self.assertEqual(event.content, "帮我写个缓存工具类")
        self.assertEqual(event.timestamp, "2026-08-15T10:00:00Z")
        self.assertEqual(event.source, "dsh")
        self.assertIsNone(event.file)

    def test_dsh_tool_edit_normalizes_file(self):
        adapter = DSHAdapter()
        event = adapter.parse(DSH_LINES[1], "dsh")
        self.assertEqual(event.actor, "assistant")
        self.assertEqual(event.event_type, "edit")
        self.assertEqual(event.file, "src/CacheHelper.java")
        self.assertIn("Edit", event.content)

    def test_dsh_text_blocks_joined(self):
        adapter = DSHAdapter()
        event = adapter.parse(DSH_LINES[2], "dsh")
        self.assertEqual(event.event_type, "message")
        self.assertEqual(event.content, "已完成。\n请检查。")

    def test_dsh_invalid_line_skipped(self):
        adapter = DSHAdapter()
        self.assertIsNone(adapter.parse_line("not json at all", "dsh"))
        self.assertIsNone(adapter.parse_line('["a", "b"]', "dsh"))

    def test_generic_openai_style(self):
        adapter = GenericAdapter()
        event = adapter.parse({"role": "user", "content": "hello"}, "generic")
        self.assertEqual(event.actor, "user")
        self.assertEqual(event.event_type, "message")
        self.assertEqual(event.content, "hello")

    def test_generic_structured_record(self):
        adapter = GenericAdapter()
        event = adapter.parse({"timestamp": "2026-08-15T11:00:00Z", "type": "assistant",
                               "text": "I wrote the code", "file_path": "src/main.py"},
                              "generic")
        self.assertEqual(event.actor, "assistant")
        self.assertEqual(event.file, "src/main.py")
        self.assertEqual(event.content, "I wrote the code")

    def test_generic_fallback_record(self):
        adapter = GenericAdapter()
        event = adapter.parse({"hello": "world"}, "generic")
        self.assertEqual(event.actor, "unknown")
        self.assertEqual(event.event_type, "record")
        self.assertIn("world", event.content)

    def test_load_events_from_file(self):
        root = fixture_dir("knowledge")
        path = root / "session.jsonl"
        path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in DSH_LINES),
                        encoding="utf-8")
        events = load_events(path, source="dsh")
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].source, "dsh")
        self.assertEqual(events[1].file, "src/CacheHelper.java")
        # 缺省 source → generic 适配器（OpenAI 风格行仍可解析）
        path.write_text('{"role": "user", "content": "hi"}\n', encoding="utf-8")
        events = load_events(path)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].actor, "user")

    def test_to_dict_round_trip(self):
        event = ADAPTERS["dsh"].parse(DSH_LINES[1], "dsh")
        d = event.to_dict()
        self.assertEqual(set(d.keys()),
                         {"timestamp", "source", "actor", "event_type", "file", "content"})
        self.assertEqual(d["file"], "src/CacheHelper.java")

    def test_adapters_registered(self):
        self.assertIn("dsh", ADAPTERS)
        self.assertIn("generic", ADAPTERS)
        self.assertNotIn("cursor", ADAPTERS)   # 暂不实现
