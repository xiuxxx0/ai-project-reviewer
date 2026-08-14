"""Phase 3：零依赖 Web 界面（stdlib http.server + 后台任务线程）。

命令：apr web [--host 127.0.0.1] [--port 8765] [--open]

接口：
- GET  /                    网页
- POST /api/preview         项目预览（扫描+技术栈，不调用 LLM）
- POST /api/review          提交复盘任务（后台线程执行，返回 job id）
- GET  /api/jobs/{id}?offset=N  轮询任务进度（增量日志）
- GET  /api/report/{id}     下载报告 Markdown
"""
from __future__ import annotations

import json
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .analyzer import Progress, run_review
from .config import load_config
from .digest import build_digest
from .errors import AprError
from .report import render_report
from .scanner import scan_project, scan_summary_text


class WebProgress(Progress):
    """把进度写入内存列表，供 Web 端轮询。"""

    def __init__(self):
        super().__init__(verbose=True, quiet=False)
        self.lines: list[str] = []
        self._lock = threading.Lock()

    def _print(self, text: str):
        with self._lock:
            self.lines.append(text.strip())

    def snapshot(self, offset: int):
        with self._lock:
            return list(self.lines[offset:]), len(self.lines)


class Job:
    def __init__(self, job_id: str, project: str):
        self.id = job_id
        self.project = project
        self.status = "running"      # running | done | failed
        self.progress = WebProgress()
        self.report_md: str | None = None
        self.out_path: str | None = None
        self.error: str | None = None
        self.started_at = time.time()
        self.finished_at: float | None = None

    def to_dict(self, short: bool = False):
        lines, total = self.progress.snapshot(0)
        d = {
            "id": self.id, "project": self.project, "status": self.status,
            "error": self.error, "out_path": self.out_path,
            "progress": {"lines": lines if not short else [], "total": total},
            "has_report": self.report_md is not None,
            "started_at": self.started_at, "finished_at": self.finished_at,
        }
        return d


class JobRegistry:
    def __init__(self, max_jobs: int = 50):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self.max_jobs = max_jobs

    def create(self, project: str) -> Job:
        job = Job(uuid.uuid4().hex[:12], project)
        with self._lock:
            self._jobs[job.id] = job
            if len(self._jobs) > self.max_jobs:
                oldest = min(self._jobs.values(), key=lambda j: j.started_at)
                self._jobs.pop(oldest.id, None)
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self):
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: j.started_at, reverse=True)
            return jobs[:20]


def _apply_llm_overrides(cfg, overrides: dict):
    for key in ("provider", "model", "base_url", "api_key"):
        value = overrides.get(key)
        if value:
            setattr(cfg.llm, key, value)
    return cfg


def _run_job(job: Job, config_path: Path | None, llm_overrides: dict):
    try:
        cfg = load_config(Path(job.project), config_path)
        cfg = _apply_llm_overrides(cfg, llm_overrides)
        # Web 端暂不做交互问答（答题升级为学习评估系统属后续迭代）
        result = run_review(Path(job.project), cfg, job.progress,
                            skip_quiz=True, use_cache=True)
        md = render_report(result)
        out = Path(job.project) / cfg.output.file
        try:
            out.write_text(md, encoding="utf-8")
        except OSError as e:
            job.progress._print(f"   ⚠ 报告写入失败：{e}")
        job.report_md = md
        job.out_path = str(out)
        job.status = "done"
    except AprError as e:
        job.status = "failed"
        job.error = str(e)
        job.progress._print(f"   ✖ 失败：{e}")
    except Exception as e:  # 兜底，避免线程静默死亡
        job.status = "failed"
        job.error = repr(e)
        job.progress._print(f"   ✖ 异常：{e}")
    finally:
        job.finished_at = time.time()


class Handler(BaseHTTPRequestHandler):
    server_version = "AIProjectReviewer/0.1"

    def _send_json(self, obj, status: int = 200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_project(self) -> tuple[str | None, str | None]:
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return None, "请求体不是合法 JSON"
        project = str((payload.get("project") or "")).strip()
        if not project:
            return None, "缺少 project 字段"
        path = Path(project).expanduser().resolve()
        if not path.is_dir():
            return None, f"路径不是目录: {path}"
        return str(path), None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html()
            return
        if parsed.path == "/api/jobs":
            self._send_json({"jobs": [j.to_dict(short=True) for j in self.server.registry.list()]})
            return
        if parsed.path.startswith("/api/jobs/"):
            job_id = parsed.path.rsplit("/", 1)[-1]
            job = self.server.registry.get(job_id)
            if not job:
                self._send_json({"error": "任务不存在"}, 404)
                return
            offset = int(parse_qs(parsed.query).get("offset", ["0"])[0] or 0)
            lines, total = job.progress.snapshot(offset)
            d = job.to_dict()
            d["progress"] = {"lines": lines, "total": total}
            self._send_json(d)
            return
        if parsed.path.startswith("/api/report/"):
            job_id = parsed.path.rsplit("/", 1)[-1]
            job = self.server.registry.get(job_id)
            if not job or job.report_md is None:
                self._send_json({"error": "报告尚未就绪"}, 404)
                return
            data = job.report_md.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="README-review.md"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/review":
            project, err = self._read_project()
            if err:
                self._send_json({"error": err}, 400)
                return
            job = self.server.registry.create(project)
            thread = threading.Thread(
                target=_run_job,
                args=(job, self.server.config_path, self.server.llm_overrides),
                daemon=True)
            thread.start()
            self._send_json({"job": {"id": job.id, "project": job.project}})
            return
        if parsed.path == "/api/preview":
            project, err = self._read_project()
            if err:
                self._send_json({"error": err}, 400)
                return
            try:
                cfg = load_config(Path(project), self.server.config_path)
                scan = scan_project(Path(project), cfg.limits)
                digest = build_digest(Path(project), scan, cfg.limits)
                text = scan_summary_text(scan) + "\n\n目录树：\n" + digest.tree_text
                if digest.stack.platforms:
                    text += "\n\n平台/框架：" + "、".join(digest.stack.platforms)
                self._send_json({"text": text, "platforms": digest.stack.platforms})
            except AprError as e:
                self._send_json({"error": str(e)}, 400)
            return
        self._send_json({"error": "not found"}, 404)

    def _send_html(self):
        data = _HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass  # 静默访问日志


def create_server(host: str, port: int, config_path: Path | None,
                  llm_overrides: dict) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), Handler)
    server.registry = JobRegistry()
    server.config_path = config_path
    server.llm_overrides = llm_overrides or {}
    return server


def run_web(host: str = "127.0.0.1", port: int = 8765, config_path: Path | None = None,
            open_browser: bool = False, llm_overrides: dict | None = None) -> None:
    server = create_server(host, port, config_path, llm_overrides)
    url = f"http://{host}:{port}"
    print(f"✔ Web 界面已启动：{url}")
    print("  在网页中输入项目路径即可复盘；Ctrl+C 停止服务。")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        server.server_close()


_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Project Reviewer</title>
<style>
body { font-family: "Segoe UI", "Microsoft YaHei", sans-serif; margin: 0; background: #0f1420; color: #e6e9f0; }
.wrap { max-width: 960px; margin: 0 auto; padding: 24px; }
h1 { font-size: 22px; margin-bottom: 4px; }
.sub { color: #8b93a7; font-size: 13px; margin-bottom: 20px; }
.card { background: #1a2130; border: 1px solid #2a3448; border-radius: 10px; padding: 18px; margin-bottom: 16px; }
label { display: block; font-size: 13px; color: #aab3c8; margin-bottom: 6px; }
input[type=text] { width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 8px; border: 1px solid #34405a; background: #0f1420; color: #e6e9f0; font-size: 14px; }
button { margin-top: 12px; margin-right: 8px; padding: 9px 18px; border-radius: 8px; border: none; cursor: pointer; font-size: 14px; background: #3b82f6; color: white; }
button.ghost { background: #2a3448; color: #cdd5e4; }
pre { background: #0d1119; border: 1px solid #2a3448; border-radius: 8px; padding: 14px; font-size: 12.5px; line-height: 1.6; overflow: auto; white-space: pre-wrap; max-height: 420px; }
.badge { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 12px; margin-left: 8px; }
.running { background: #b45309; color: #ffe9c9; }
.done { background: #15803d; color: #d9f7e2; }
.failed { background: #b91c1c; color: #ffdcdc; }
a { color: #7ab3ff; }
.hidden { display: none; }
</style>
</head>
<body>
<div class="wrap">
<h1>AI Project Reviewer</h1>
<div class="sub">输入一个代码项目路径，生成《README复盘.md》：项目介绍 / 技术栈 / 项目结构 / 核心代码分析 / AI 生成部分（多源证据）/ 我的学习盲区 / 面试问题 / 下一步练习</div>

<div class="card">
<label>项目路径（绝对路径）</label>
<input type="text" id="project" placeholder="例如 C:\Users\you\my-project">
<button id="btnPreview" class="ghost">预览项目</button>
<button id="btnReview">开始复盘</button>
</div>

<div class="card hidden" id="previewCard">
<div class="sub">项目预览</div>
<pre id="preview"></pre>
</div>

<div class="card hidden" id="jobCard">
<div class="sub">任务 <span id="jobId"></span> <span id="jobBadge" class="badge running">running</span></div>
<pre id="jobLog"></pre>
<div id="downloadWrap" class="hidden" style="margin-top: 10px;">
<a id="downloadLink" download="README-review.md">下载 README复盘.md</a>
</div>
</div>

<div class="card hidden" id="reportCard">
<div class="sub">报告预览</div>
<pre id="report"></pre>
</div>
</div>
<script>
var currentJob = null;
var pollTimer = null;
var logOffset = 0;

function show(id) { document.getElementById(id).classList.remove("hidden"); }
function hide(id) { document.getElementById(id).classList.add("hidden"); }

async function postJson(url, body) {
  var resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  return resp.json();
}

document.getElementById("btnPreview").onclick = async function () {
  var project = document.getElementById("project").value.trim();
  if (!project) { alert("请输入项目路径"); return; }
  var data = await postJson("/api/preview", { project: project });
  if (data.error) { alert(data.error); return; }
  document.getElementById("preview").textContent = data.text;
  show("previewCard");
};

document.getElementById("btnReview").onclick = async function () {
  var project = document.getElementById("project").value.trim();
  if (!project) { alert("请输入项目路径"); return; }
  var data = await postJson("/api/review", { project: project });
  if (data.error) { alert(data.error); return; }
  currentJob = data.job.id;
  logOffset = 0;
  document.getElementById("jobId").textContent = currentJob;
  var badge = document.getElementById("jobBadge");
  badge.textContent = "running";
  badge.className = "badge running";
  document.getElementById("jobLog").textContent = "";
  hide("reportCard");
  hide("downloadWrap");
  show("jobCard");
  clearInterval(pollTimer);
  pollTimer = setInterval(poll, 900);
  poll();
};

async function poll() {
  if (!currentJob) return;
  var resp = await fetch("/api/jobs/" + currentJob + "?offset=" + logOffset);
  var job = await resp.json();
  if (job.error) { clearInterval(pollTimer); return; }
  var logEl = document.getElementById("jobLog");
  for (var i = 0; i < job.progress.lines.length; i++) {
    logEl.textContent += job.progress.lines[i] + "\n";
  }
  logOffset = job.progress.total;
  logEl.scrollTop = logEl.scrollHeight;
  var badge = document.getElementById("jobBadge");
  if (job.status === "done") {
    clearInterval(pollTimer);
    badge.textContent = "done";
    badge.className = "badge done";
    document.getElementById("downloadLink").href = "/api/report/" + currentJob;
    show("downloadWrap");
    var resp2 = await fetch("/api/report/" + currentJob);
    var md = await resp2.text();
    document.getElementById("report").textContent = md;
    show("reportCard");
  } else if (job.status === "failed") {
    clearInterval(pollTimer);
    badge.textContent = "failed";
    badge.className = "badge failed";
  }
}
</script>
</body>
</html>
"""
