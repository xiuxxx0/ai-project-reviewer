import json
import threading
import time
import unittest
import urllib.request

from apr.web import create_server
from tests import fixture_dir


class WebTest(unittest.TestCase):
    def test_review_job_flow(self):
        root = fixture_dir("web")
        (root / "main.py").write_text("print('hi')\n", encoding="utf-8")
        (root / "apr.yaml").write_text(
            "llm:\n  provider: mock\nquiz:\n  enabled: false\n", encoding="utf-8")
        server = create_server("127.0.0.1", 0, None, {})
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{port}"

        def post(path: str, payload: dict):
            req = urllib.request.Request(
                base + path, data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))

        try:
            preview = post("/api/preview", {"project": str(root)})
            self.assertIn("目录树", preview["text"])
            created = post("/api/review", {"project": str(root)})
            job_id = created["job"]["id"]
            status = "running"
            job = {}
            for _ in range(150):
                with urllib.request.urlopen(base + "/api/jobs/" + job_id, timeout=15) as resp:
                    job = json.loads(resp.read().decode("utf-8"))
                status = job["status"]
                if status != "running":
                    break
                time.sleep(0.1)
            self.assertEqual(status, "done", job.get("error"))
            self.assertTrue(job["has_report"])
            with urllib.request.urlopen(base + "/api/report/" + job_id, timeout=15) as resp:
                md = resp.read().decode("utf-8")
            self.assertIn("## 项目介绍", md)
            self.assertIn("## 下一步练习", md)
        finally:
            server.shutdown()
            server.server_close()
