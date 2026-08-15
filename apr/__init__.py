"""AI Project Reviewer（AI 项目复盘助手 / RepoCourse）。

输入一个代码项目，输出：技术复盘报告 + 学习成长报告 + 知识图谱 + 学习计划。
"""
try:
    from importlib.metadata import PackageNotFoundError, version as _pkg_version
    __version__ = _pkg_version("repocourse")
except (PackageNotFoundError, ImportError):
    __version__ = "0.1.2"

