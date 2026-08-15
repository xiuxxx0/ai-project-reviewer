"""极简 YAML 子集解析器（零依赖）。

支持 apr.yaml / profile.yaml 需要的语法：
- 注释（# 开头或行内）
- 嵌套映射（空格缩进）
- 标量列表（- item，归属其上方最近的键）
- 映射列表（- key: value 及其缩进后续键，如 profile.yaml 的 skills）
- 标量值：字符串 / 整数 / 浮点数 / true|false|null / []

不支持：锚点、多行字符串、流式集合（{...}）、引号内转义、无缩进列表。
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
    """解析简化 YAML（递归下降：映射、标量列表、映射列表）。"""
    entries: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if "#" in line:
            line = line.split("#", 1)[0].rstrip()
        if not line:
            continue
        entries.append((indent, line))
    if not entries:
        return {}

    def parse_block(index: int, min_indent: int):
        """解析一个块。返回 (值, 下一个待处理下标)。"""
        if index >= len(entries):
            return {}, index
        indent, line = entries[index]

        if line.startswith("- "):
            items: list = []
            while (index < len(entries) and entries[index][0] == indent
                   and entries[index][1].startswith("- ")):
                _, item_line = entries[index]
                rest = item_line[2:].strip()
                if ":" in rest:
                    # 映射列表项：首个键与 - 同行，其余键缩进对齐
                    key, _, val = rest.partition(":")
                    key = key.strip().strip("\"'")
                    val = val.strip()
                    item: dict = {}
                    index += 1
                    if val:
                        item[key] = _scalar(val.strip("\"'"))
                    else:
                        if index < len(entries) and entries[index][0] > indent:
                            sub, index = parse_block(index, entries[index][0])
                            item[key] = sub
                        else:
                            item[key] = {}
                    while (index < len(entries) and entries[index][0] > indent
                           and not entries[index][1].startswith("- ")):
                        k, _, v = entries[index][1].partition(":")
                        k = k.strip().strip("\"'")
                        v = v.strip()
                        prev_indent = entries[index][0]
                        index += 1
                        if v:
                            item[k] = _scalar(v.strip("\"'"))
                        else:
                            if index < len(entries) and entries[index][0] > prev_indent:
                                sub, index = parse_block(index, entries[index][0])
                                item[k] = sub
                            else:
                                item[k] = {}
                    items.append(item)
                else:
                    items.append(_scalar(rest.strip("\"'")))
                    index += 1
            return items, index

        # 映射
        result: dict = {}
        while (index < len(entries) and entries[index][0] >= min_indent
               and not entries[index][1].startswith("- ")):
            i2, line2 = entries[index]
            key, _, val = line2.partition(":")
            key = key.strip().strip("\"'")
            val = val.strip()
            index += 1
            if val:
                result[key] = _scalar(val.strip("\"'"))
            else:
                if index < len(entries) and entries[index][0] > i2:
                    sub, index = parse_block(index, entries[index][0])
                    result[key] = sub
                else:
                    result[key] = {}
        return result, index

    value, _ = parse_block(0, entries[0][0])
    return value if isinstance(value, dict) else {}


def _dump_scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return str(value)


def dump_simple_yaml(data: dict, _indent: int = 0) -> str:
    """把嵌套 dict/list 序列化为本解析器可读回的 YAML（注释不会被保留）。"""
    lines: list[str] = []
    pad = "  " * _indent
    for key, value in data.items():
        k = str(key)
        if isinstance(value, dict):
            if not value:
                lines.append(f"{pad}{k}: {{}}")
            else:
                lines.append(f"{pad}{k}:")
                lines.append(dump_simple_yaml(value, _indent + 1))
        elif isinstance(value, list):
            lines.append(f"{pad}{k}:")
            for item in value:
                if isinstance(item, dict) and item:
                    # 续行必须比 "- " 更深一级，才能被解析器识别为同一映射项
                    sub = dump_simple_yaml(item, _indent + 2)
                    first, _, rest = sub.partition("\n")
                    lines.append(pad + "  - " + first.strip())
                    if rest:
                        lines.append(rest)
                else:
                    lines.append(f"{pad}  - {_dump_scalar(item)}")
        else:
            lines.append(f"{pad}{k}: {_dump_scalar(value)}")
    return "\n".join(lines)
