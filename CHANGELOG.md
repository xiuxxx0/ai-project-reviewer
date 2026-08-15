# Changelog

本项目的所有重要变更都会记录在此文件中。

## [0.1.1] - 2026-08-15

### 新增

- 网页答题挑战（apr web）：AI 出题 → 点选立即判对错 + 解析 → 交卷出总分与薄弱主题
  （/api/quiz/start、/api/quiz/check、/api/quiz/finish）

## [0.1.0] - 2026-08-15

首个正式版本：AI 时代的项目学习复盘助手。

### 核心能力

- 项目扫描与技术栈识别（.gitignore 语义、大项目限额保护）
- 核心代码理解（多 LLM 供应商：DeepSeek / OpenAI / 兼容端点 / Ollama / mock）
- AI 协作分析（Git 提交 / Agent 日志 / 代码标记多源证据融合，逐文件 AI 贡献度）
- 统一 Agent Event 系统（DSH JSONL / 通用 JSONL 适配器）
- 知识图谱（JSON + Obsidian 风格 HTML + Canvas 四列画布 + Mermaid 导图 + 游戏技能树）
- 技能评估（档案 × 项目证据 × Quiz × AI 贡献 → 等级与置信度）
- 学习盲区证据引擎（五路信号计算，非 AI 猜测）
- Learning Coach 学习计划（优先级 / 原因 / 行动 / 下一步项目）
- 双报告：output/README复盘.md（技术复盘）+ output/learning_report.md（学习成长反馈）
- 实践验证 Quiz（AI 出题 / 终端作答 / 批改评分）
- 零依赖 Web 界面（apr web）
- 一键切换 LLM（apr config，预设 + 交互向导）
- 新版 profile.yaml 技能档案（mastered/learning/target 结构）

### 工程

- 零第三方运行时依赖，Python ≥ 3.10
- 114 个单元/集成测试
- PyPI 发布（pip install repocourse）
- post-commit 自动推送钩子

[0.1.1]: https://github.com/xiuxxx0/ai-project-reviewer/releases/tag/v0.1.1
[0.1.0]: https://github.com/xiuxxx0/ai-project-reviewer/releases/tag/v0.1.0
