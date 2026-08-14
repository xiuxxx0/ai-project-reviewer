"""测试公共工具。

沙箱限制说明：Python 进程只能向「进程启动前已存在」的目录写文件，
因此测试使用 pwsh 预创建的固定目录（.test-tmp/t-*），不做动态创建。
运行测试前请先执行（或由运行脚本负责）：

    New-Item -Force -ItemType Directory -Path .test-tmp/t-scanner/src, ...

ensure_fixtures() 可幂等补齐目录，但目录由 Python 新建时沙箱下仍不可写。
"""
import shutil
from pathlib import Path

_TMP_ROOT = Path(__file__).resolve().parent.parent / ".test-tmp"

_FIXTURES = {
    "scanner": ["src", "vendor", "node_modules"],
    "config": [],
    "markers": [],
    "digest": [],
    "quiz": [],
    "web": [],
}


def ensure_fixtures():
    """幂等补齐预创建目录（沙箱下由 Python 新建的目录不可写文件，慎用）。"""
    for name, subdirs in _FIXTURES.items():
        base = _TMP_ROOT / ("t-" + name)
        base.mkdir(parents=True, exist_ok=True)
        for s in subdirs:
            (base / s).mkdir(exist_ok=True)


def fixture_dir(name: str) -> Path:
    """返回预创建的固定测试目录，并清空其中的文件（目录结构保留）。"""
    base = _TMP_ROOT / ("t-" + name)
    base.mkdir(parents=True, exist_ok=True)
    for child in base.iterdir():
        try:
            if child.is_dir():
                for sub in child.iterdir():
                    if sub.is_dir():
                        shutil.rmtree(sub, ignore_errors=True)
                    else:
                        sub.unlink(missing_ok=True)
            else:
                child.unlink()
        except OSError:
            pass
    for s in _FIXTURES.get(name, []):
        (base / s).mkdir(exist_ok=True)
    return base
