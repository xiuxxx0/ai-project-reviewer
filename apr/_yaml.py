"""极简 YAML 子集解析器（零依赖）。

支持 apr.yaml / profile.yaml 需要的语法：
- 注释（# 开头或行内）
- 嵌套映射（空格缩进）
- 标量列表（- item）
- 标量值：字符串 / 整数 / 浮点数 / true|false|null / []

不支持：锚点、多行字符串、流式集合（{...}）、引号内转义。
"""
from __future__ import annotations


def _scalar(text: str):
    t = text.strip()
    low = t.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("null", "none", "~"):
        return None
    if t in ("[]", "{}"):
        return [] if t == "[]" else {}
    if len(t) >= 2 and t[0] == t[-1] and t[0] in ("\"", "'"):
        return t[1:-1]
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        pass
    return t


def parse_simple_yaml(text: str) -> dict:
    root: dict = {}
    stack: list[tuple[dict, int, str | None]] = []   # (容器, 缩进, 最近键)
    cur: dict = root
    cur_indent = -1
    last_key: str | None = None
    active_list: list | None = None

    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if "#" in line:
            line = line.split("#", 1)[0].rstrip()
        if not line:
            continue

        is_item = line.startswith("- ")
        if not is_item:
            active_list = None
        while stack and indent <= stack[-1][1]:
            cur, cur_indent, last_key = stack.pop()

        if is_item:
            value = _scalar(line[2:].strip().strip("\"'").strip())
            if active_list is not None:
                active_list.append(value)
                continue
            if isinstance(cur, dict) and last_key is not None:
                holder = cur.get(last_key)
                if isinstance(holder, list):
                    holder.append(value)
                    active_list = holder
                elif isinstance(holder, dict) and not holder:
                    active_list = [value]
                    cur[last_key] = active_list
                else:
                    active_list = [value]
                    cur[last_key] = active_list
                # 列表项归属于父级键，回到父级容器
                cur, cur_indent, last_key = stack[-1] if stack else (root, -1, None)
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip().strip("\"'")
            val = val.strip()
            if val == "":
                child: dict = {}
                cur[key] = child
                stack.append((cur, cur_indent, last_key))
                cur, cur_indent, last_key = child, indent, key
            else:
                cur[key] = _scalar(val.strip("\"'"))
                last_key = key
    return root
