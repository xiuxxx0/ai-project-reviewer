"""多源证据采集与融合。

证据源：Git 提交历史 / Agent 对话记录 / 代码标记 / 变更轨迹。
"""
from .base import EvidenceItem, EvidenceReport, EvidenceSource, FileVerdict
from .fusion import fuse

__all__ = ["EvidenceItem", "EvidenceReport", "EvidenceSource", "FileVerdict", "fuse"]
