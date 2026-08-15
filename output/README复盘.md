# ai-project-reviewer · 项目复盘

> 由 **AI Project Reviewer v0.1.0** 自动生成
> 生成时间：2026-08-15T18:33:06 ｜ 模型：deepseek/deepseek-v4-pro ｜ 语言：zh
> 项目路径：C:\Users\MAO0909\Documents\DSH\ai-project-reviewer

## 目录

1. [项目介绍](#项目介绍)
2. [技术栈](#技术栈)
3. [项目结构](#项目结构)
4. [核心代码分析](#核心代码分析)
5. [AI 协作分析](#AI 协作分析)
6. [我的学习盲区](#我的学习盲区)
7. [面试问题](#面试问题)
8. [下一步练习](#下一步练习)
9. [我的技能评估](#我的技能评估)
10. [下一阶段学习路线](#下一阶段学习路线)
11. [附录 A：AI 生成证据明细](#附录-aai-生成证据明细)

---

## 项目介绍

**一句话定位**：ai-project-reviewer 是一个 AI 项目复盘助手，输入一个代码项目后自动生成《README复盘.md》报告、知识图谱和个性化学习计划，形成“复盘 → 证据 → 盲区 → 技能评估 → 学习路线”的完整学习闭环。

**主要功能/特性**：
- 生成 12 节结构化复盘报告，涵盖 8 大板块、技能评估、学习路线及证据/问答附录，支持中文/英文。
- 基于多源证据（Git 提交历史、Agent 会话日志、代码内标记、变更轨迹）逐文件判定 AI 贡献度与置信度。
- 通过统一 Agent Event 系统接入 DSH、通用 JSONL 日志，桥接进证据层（Cursor 适配器暂未实现）。
- 输出知识图谱（JSON + HTML + Obsidian Canvas + Mermaid 导图），展示“文件→技术→知识点→用户技能”四层关系及 AI 贡献徽标。
- 由学习盲区证据引擎结合项目需求、技能档案、Quiz、AI 贡献和知识图谱五路信号计算盲区，非 AI 猜测。
- 提供确定性 Learning Coach 学习计划生成器（`apr plan`），不调用 LLM，输出优先级与下一步实践项目。
- 支持实践验证问答（`apr quiz`）：AI 出题、终端作答、AI 批改并计入报告。
- 支持多 LLM 供应商（DeepSeek / OpenAI / OpenAI 兼容 / Ollama / mock），零第三方依赖，Python ≥ 3.10。

**目标用户与典型使用场景**（推测）：目标用户是有代码项目复盘需求的开发者或学习者，可能用于个人项目总结、面试准备、识别自身技能盲区，或在 AI 辅助开发后回顾人与 AI 的协作分工。典型场景包括：对已完成的项目生成复盘报告以查漏补缺；通过知识图谱与技能评估定位“纸面掌握”；根据学习计划进行后续练习。

**运行方式**：
- 安装：`pip install -e .`（或无需安装，直接运行 `python -m apr review .`）。
- 初始化项目配置：`apr init`。
- 设置 LLM API Key（例如 `DEEPSEEK_API_KEY` 环境变量）。
- 生成复盘报告：`apr review <项目路径>`，默认在项目根目录 `output/` 下产出 `README复盘.md` 和 `learning_report.md`。
- 其他命令：`apr scan`（只扫描技术栈）、`apr graph`（生成知识图谱）、`apr plan`（生成学习计划）、`apr quiz`（只运行问答）、`apr web`（启动 Web 界面）、`apr config`（交互式配置 LLM）。

**项目规模速览**：共 76 个文件（扫描排除 22 项），主要语言为 Python（65 个文件），项目总大小 346.3KB。

---

## 技术栈

### 技术栈总览

| 类别 | 技术 | 用途说明 |
|------|------|----------|
| 语言 | Python | 项目主要开发语言，代码统计显示 Python 文件占绝大多数（65 个）；`pyproject.toml` 和 `README.md` 均要求 Python ≥ 3.10 |
| 构建工具 | setuptools | `pyproject.toml` 的 `[build-system]` 声明 `requires = ["setuptools>=68"]`，用于项目的打包与构建 |
| 包管理 | pip | `README.md` 安装说明为 `pip install -e .`，采用可编辑安装；同时通过 `pyproject.toml` 暴露命令行入口 `apr = "apr.cli:main"` |
| CLI 框架 | argparse | `apr/cli.py` 导入 `argparse` 实现命令解析，包含 `review`、`scan`、`quiz`、`init`、`graph`、`plan`、`web`、`config` 等子命令 |
| 配置解析 | 自研简化 YAML 解析器（`apr/_yaml.py`） | `README.md` 声明“含内置简化 YAML 解析器”；`apr/config.py` 导入 `parse_simple_yaml` 解析全局及项目级 `apr.yaml`、`profile.yaml`，实现零第三方依赖 |
| 配置模板 | 内置字符串模板（`apr/templates.py`） | `apr/cli.py` 导入 `APR_YAML_TEMPLATE` 和 `PROFILE_YAML_TEMPLATE`，用于 `apr init` 生成默认配置文件 |
| LLM 供应商集成 | DeepSeek / OpenAI / OpenAI 兼容端点 / Ollama / mock | `README.md` 列出多供应商支持；`apr/config.py` 中 `PROVIDER_DEFAULTS` 定义各供应商的默认 base_url、api_key_env、model；`apr/llm/` 目录包含 `base.py`、`factory.py`、`ollama.py`、`openai_compat.py`，采用统一工厂模式创建 provider。（具体 HTTP 客户端实现未展示，推测使用 Python 标准库） |
| Web 界面 | Python 标准库 HTTP 服务器（推测） | `README.md` 提供 `apr web` 命令启动本地界面（http://127.0.0.1:8765），`apr/web.py` 文件存在；材料未展示实现细节，因项目零第三方依赖，推测使用标准库 `http.server` 实现 |
| 数据输出格式 | JSON | 生成 `knowledge_graph.json` 标准图数据（README 说明）；根目录存在 `learning_plan.json` 示例 |
| 文档格式 | Markdown | 生成 `README复盘.md` 报告；项目文档（README 等）及知识图谱导出的 `knowledge_graph-mindmap.md` 使用 Markdown |
| 可视化输出 | HTML / Obsidian Canvas / Mermaid | `README.md` 描述知识图谱可导出 `knowledge_graph.html`（拖拽/缩放/悬停高亮）、`knowledge_graph.canvas`（Obsidian 分层画布）、`knowledge_graph-mindmap.md`（Mermaid 思维导图），均为自研导出，无第三方前端依赖 |
| 测试 | Python 标准库 `unittest`（推测） | `tests/` 目录包含 20 个 `test_*.py` 文件；材料未显示导入 pytest 等第三方测试框架，结合零第三方依赖声明，推测使用标准库 `unittest` |

### 主要依赖版本

- Python：≥ 3.10（依据 `pyproject.toml` 的 `requires-python`）
- setuptools：≥ 68（依据 `pyproject.toml` 的 `build-system.requires`）
- 第三方运行时依赖：无（`pyproject.toml` 中 `dependencies = []`；`README.md` 声明“零第三方依赖”）

### 技术选型点评

1. **零第三方依赖是显著的技术选型**：项目通过标准库实现全部功能（包括自研简化 YAML 解析器），显著降低安装门槛和分发复杂度，适合作为通用 CLI 工具；但自研解析器可能仅支持 YAML 子集，对复杂配置（如锚点、多行字符串等）的支持可能有限（

---

## 项目结构

```text
ai-project-reviewer/
│   .githooks/
│       post-commit
│   apr/
│   │   assessment/
│   │   │   __init__.py
│   │   │   blindspot.py
│   │   │   collab.py
│   │   │   quiz.py
│   │       skill.py
│   │   coach/
│   │   │   __init__.py
│   │       planner.py
│   │   events/
│   │   │   __init__.py
│   │   │   base.py
│   │   │   dsh.py
│   │       generic.py
│   │   evidence/
│   │   │   __init__.py
│   │   │   agent_logs.py
│   │   │   base.py
│   │   │   fusion.py
│   │   │   git.py
│   │       markers.py
│   │   knowledge/
│   │   │   __init__.py
│   │       knowledge.py
│   │   llm/
│   │   │   __init__.py
│   │   │   base.py
│   │   │   factory.py
│   │   │   ollama.py
│   │       openai_compat.py
│   │   prompts/
│   │   │   __init__.py
│   │       sections.py
│   │   __init__.py
│   │   __main__.py
│   │   _yaml.py
│   │   analyzer.py
│   │   cache.py
│   │   cli.py
│   │   config.py
│   │   configure.py
│   │   digest.py
│   │   errors.py
│   │   learning_report.py
│   │   profile.py
│   │   report.py
│   │   scanner.py
│   │   templates.py
│       web.py
│   examples/
│       demo-project/
│       │   apr.yaml
│       │   main.py
│       │   README.md
│           utils.py
│   tests/
│   │   __init__.py
│   │   test_blindspot.py
│   │   test_coach.py
│   │   test_collab.py
│   │   test_config.py
│   │   test_configure.py
│   │   test_digest.py
│   │   test_event_bridge.py
│   │   test_events.py
│   │   test_fusion.py
│   │   test_knowledge.py
│   │   test_learning_report.py
│   │   test_llm.py
│   │   test_markers.py
│   │

---

## 核心代码分析

以下分析仅基于项目画像中提供的内容摘录。`apr/cli.py` 与 `apr/config.py` 的摘录在关键处被截断，因此对未展示部分不做事后编造；对只能从 README、目录树或导入关系推断的内容，均明确标注为「推测」。

### 1. `pyproject.toml`

**职责**  
定义项目的打包元数据、Python 版本约束、零第三方依赖以及命令行入口点。

**关键实现**  
- `[project]` 中声明 `dependencies = []`，与 README 所述「零第三方依赖，纯标准库实现」一致。
- `requires-python = ">=3.10"` 明确最低 Python 版本。
- `[project.scripts] apr = "apr.cli:main"` 将 `apr` 命令映射到 `apr/cli.py` 的 `main` 函数。
- `[tool.setuptools] packages` 显式列出 `apr` 及其子包，避免自动发现遗漏。

**设计模式/架构思想**  
采用 PEP 621 声明式打包配置，显式包列表降低打包不确定性。零依赖策略适合 CLI 工具的分发，但代价是需要自行实现 YAML 解析、HTTP 调用等能力。

**可改进点**  
- 未声明 `license` 字段，虽然仓库根目录有 `LICENSE`，可在 `[project]` 中加入 `license = { file = "LICENSE" }`。
- 缺少 `[project.optional-dependencies]` 或开发依赖组，测试依赖（如 pytest）无法通过 `pip install -e ".[dev]"` 一键安装。
- `version = "0.1.0"` 为静态值，后续发布需要手动维护。

### 2. `apr/cli.py`

**职责**  
CLI 入口，构造 `argparse` 解析器，定义 `review/scan/quiz/init/graph/plan/config` 等子命令，并统一处理 Windows 下的 UTF-8 输出。

**关键实现**  
- `_reconfigure_stdout()` 对 `sys.stdout` 和 `sys.stderr` 调用 `reconfigure(encoding="utf-8", errors="replace")`，避免中文报告在 Windows 控制台乱码。
- `_add_llm_options(p)` 为多个子命令统一添加 `--provider/--model/--base-url/--api-key` 覆盖参数。
- `build_parser()` 创建子命令，`review` 子命令参数最丰富：`--skip-quiz`、`--force-quiz`、`--quiz-count`、`--dry-run`、`--output`、`--language` 等。
- 导入关系显示该模块依赖 `analyzer.run_review`、`digest.build_digest`、`llm.factory.create_provider`、`report.render_report`、`scanner.scan_project` 等。
- 材料摘录止于 `p_config` 参数定义，未展示 `main` 函数与命令分发逻辑。

**设计模式/架构思想**  
典型的命令行门面模式：CLI 层只负责参数解析、配置加载、流程编排，具体业务由 `analyzer`、`scanner`、`report` 等模块完成。`_add_llm_options` 的抽取避免了参数定义重复。

**可改进点**  
- `_reconfigure_stdout` 使用 `errors="replace"` 会静默替换无法编码的字符，可能导致报告内容丢失；可考虑 `backslashreplace` 或仅对 Windows 启用。
- `build_parser` 会随着子命令增加持续膨胀，可拆分为每个命令一个注册函数，例如 `_add_review_parser(sub)`、`_add_graph_parser(sub)` 等。
- 材料未展示 `main` 中命令分发方式；若存在长串 `if command == "review": ...`，建议改为命令名到处理函数的字典映射（该点仅为假设，材料不足以确认）。

### 3. `apr/config.py`

**职责**  
加载并合并配置，定义 LLM、输出、限额、证据四类配置对象，从 YAML mapping 解析并读取环境变量。

**关键实现**  
- 优先级链：内置默认 ← `~/.apr/apr.yaml` ← 项目根 `apr.yaml` ← 环境变量 ← CLI 参数；各配置文件按「节」整体覆盖，不做深合并。
- `PROVIDER_DEFAULTS` 提供 `deepseek/openai/openai-compatible/ollama/mock` 五套预设，包含 `base_url`、`api_key_env`、`model`。
- `LLMConfig.from_mapping` 根据 `provider` 查预设默认值，API key 从 `api_key_env` 对应的环境变量读取，并回退到 `APR_API_KEY`。
- `OutputConfig.from_mapping` 对 `language` 做枚举校验，非法值抛 `ConfigError`。
- `LimitsConfig.from_mapping` 校验 `

---

## AI 协作分析

> 本节分析你与 AI 如何共同完成这个项目（基于 Git / Agent 日志 / 代码标记证据，不是作弊检测，而是协作复盘）。

本项目 AI 协作情况：

**AI 参与比例**：

| AI 代码生成 | AI 辅助修改 | 人工设计 |
| --- | --- | --- |
| 0% | 10% | 90% |

**AI 主要用于**：

- ✓ 代码生成（3 个文件由 AI 主导或辅助）

**你的参与**：

- 修改 AI 代码（3 个文件在 AI 基础上人工修改）
- 自己设计模块（26 个文件判定人工编写）

**你的优势**：

- 能够修改和整合 AI 代码
- 保持了较高的人工参与比例
- 项目主体为独立设计

**提升建议**：

- 保持当前协作方式，定期复盘巩固。

---

## 我的学习盲区

> 由证据引擎计算：项目需求 × 技能档案 × Quiz × AI 贡献 × 知识图谱关联，非 AI 猜测。

### REST API

- **等级**：高风险盲区
- **证据**：
    - 项目核心依赖 REST API（3 个文件使用）
    - 用户 profile 未掌握 REST API
    - 暂无 Quiz 验证
    - 代码以人工编写为主（AI 贡献 0%）
- **建议**：
    - 系统学习 REST API 基础
    - 用 apr quiz 验证 REST API
    - 学习 资源设计 基础
    - 掌握 HTTP 语义

### React

- **等级**：高风险盲区
- **证据**：
    - 项目核心依赖 React（2 个文件使用）
    - 用户 profile 未掌握 React
    - 暂无 Quiz 验证
    - 代码以人工编写为主（AI 贡献 0%）
- **建议**：
    - 系统学习 React 基础
    - 用 apr quiz 验证 React
    - 学习 组件 基础
    - 掌握 Hooks

### Spring

- **等级**：高风险盲区
- **证据**：
    - 项目核心依赖 Spring（3 个文件使用）
    - 用户 profile 未掌握 Spring
    - 暂无 Quiz 验证
    - 代码以人工编写为主（AI 贡献 0%）
- **建议**：
    - 系统学习 Spring 基础
    - 用 apr quiz 验证 Spring
    - 学习 IoC/DI 基础
    - 掌握 AOP

### MySQL

- **等级**：中风险盲区
- **证据**：
    - 项目核心依赖 MySQL（3 个文件使用）
    - profile 标注正在学习
    - 暂无 Quiz 验证
    - 代码以人工编写为主（AI 贡献 0%）
- **建议**：
    - 按学习计划推进 MySQL
    - 用 apr quiz 验证 MySQL
    - 学习 表设计 基础
    - 掌握 索引

### Django

- **等级**：中风险盲区
- **证据**：
    - 项目使用 Django（1 个文件）
    - 用户 profile 未掌握 Django
    - 暂无 Quiz 验证
    - 代码以人工编写为主（AI 贡献 0%）
- **建议**：
    - 系统学习 Django 基础
    - 用 apr quiz 验证 Django
    - 学习 MTV 架构 基础
    - 掌握 ORM

### Elasticsearch

- **等级**：中风险盲区
- **证据**：
    - 项目使用 Elasticsearch（1 个文件）
    - 用户 profile 未掌握 Elasticsearch
    - 暂无 Quiz 验证
    - 代码以人工编写为主（AI 贡献 0%）
- **建议**：
    - 系统学习 Elasticsearch 基础
    - 用 apr quiz 验证 Elasticsearch
    - 学习 倒排索引 基础
    - 掌握 DSL 查询

### FastAPI

- **等级**：中风险盲区
- **证据**：
    - 项目使用 FastAPI（1 个文件）
    - 用户 profile 未掌握 FastAPI
    - 暂无 Quiz 验证
    - 代码以人工编写为主（AI 贡献 0%）
- **建议**：
    - 系统学习 FastAPI 基础
    - 用 apr quiz 验证 FastAPI
    - 学习 路由 基础
    - 掌握 依赖注入

### JWT

- **等级**：中风险盲区
- **证据**：
    - 项目使用 JWT（1 个文件）
    - 用户 profile 未掌握 JWT
    - 暂无 Quiz 验证
    - 代码以人工编写为主（AI 贡献 0%）
- **建议**：
    - 系统学习 JWT 基础
    - 用 apr quiz 验证 JWT
    - 学习 令牌结构 基础
    - 掌握 签名验证

### Kafka

- **等级**：中风险盲区
- **证据**：
    - 项目使用 Kafka（1 个文件）
    - 用户 profile 未掌握 Kafka
    - 暂无 Quiz 验证
    - 代码以人工编写为主（AI 贡献 0%）
- **建议**：
    - 系统学习 Kafka 基础
    - 用 apr quiz 验证 Kafka
    - 学习 生产者/消费者 基础
    - 掌握 分区与偏移

### MongoDB

- **等级**：中风险盲区
- **证据**：
    - 项目使用 MongoDB（1 个文件）
    - 用户 profile 未掌握 MongoDB
    - 暂无 Quiz 验证
    - 代码以人工编写为主（AI 贡献 0%）
- **建议**：
    - 系统学习 MongoDB 基础
    - 用 apr quiz 验证 MongoDB
    - 学习 文档模型 基础
    - 掌握 聚合查询

### MyBatis

- **等级**：中风险盲区
- **证据**：
    - 项目使用 MyBatis（1 个文件）
    - 用户 profile 未掌握 MyBatis
    - 暂无 Quiz 验证
    - 代码以人工编写为主（AI 贡献 0%）
- **建议**：
    - 系统学习 MyBatis 基础
    - 用 apr quiz 验证 MyBatis
    - 学习 SQL 映射 基础
    - 掌握 动态 SQL

### Redis

- **等级**：中风险盲区
- **证据**：
    - 项目核心依赖 Redis（7 个文件使用）
    - 学习目标（优先级 medium）
    - 暂无 Quiz 验证
    - 代码以人工编写为主（AI 贡献 0%）
- **建议**：
    - 按学习目标推进 Redis
    - 用 apr quiz 验证 Redis
    - 学习 缓存 基础
    - 掌握 Key 设计

### Python

- **等级**：中风险盲区
- **证据**：
    - 项目核心依赖 Python（65 个文件使用）
    - profile 自评 basic
    - 暂无 Quiz 验证
    - 代码以人工编写为主（AI 贡献 7%）
- **建议**：
    - 通过实战项目巩固 Python
    - 用 apr quiz 验证 Python

### Spring Boot

- **等级**：中风险盲区
- **证据**：
    - 项目使用 Spring Boot（1 个文件）
    - profile 标注正在学习
    - 暂无 Quiz 验证
    - 代码以人工编写为主（AI 贡献 0%）
- **建议**：
    - 按学习计划推进 Spring Boot
    - 用 apr quiz 验证 Spring Boot
    - 学习 自动配置 基础
    - 掌握 起步依赖


- AI Agent：档案声明但项目未使用，不计入盲区
- AI Agent工程：档案声明但项目未使用，不计入盲区
- C：档案声明但项目未使用，不计入盲区
- Docker：档案声明但项目未使用，不计入盲区
- Git：档案声明但项目未使用，不计入盲区
- HTML/CSS：档案声明但项目未使用，不计入盲区
- Java：档案声明但项目未使用，不计入盲区
- JavaScript：档案声明但项目未使用，不计入盲区
- Java后端开发：档案声明但项目未使用，不计入盲区
- MCP：档案声明但项目未使用，不计入盲区
- Spring生态：档案声明但项目未使用，不计入盲区
- 数据库设计：档案声明但项目未使用，不计入盲区
- 项目使用但风险低、未列为盲区：Vue


---

## 面试问题

### 基础

**1. 题目**：在 `apr/config.py` 中，配置加载的优先级顺序是什么？这种设计有什么好处？  
- **考察点**：配置管理、多层配置合并机制。  
- **参考回答要点**：  
  - 优先级从低到高：内置默认值 → `~/.apr/apr.yaml`（全局）→ 项目根目录 `apr.yaml`（项目级）→ 环境变量 → CLI 参数。  
  - 各配置文件按“节”整体覆盖，不做深合并（例如 `llm` 节整体替换）。  
  - 好处：允许用户设置全局偏好，项目可覆盖，命令行临时调整最高优先级，灵活且可预测。  
  - 环境变量（如 `DEEPSEEK_API_KEY`）在加载 LLM 配置时直接读取，避免密钥硬编码。

**2. 题目**：项目宣称“零第三方依赖”，它如何实现 YAML 解析？这样做有什么代价？  
- **考察点**：对自研解析器的理解、依赖取舍。  
- **参考回答要点**：  
  - 在 `apr/_yaml.py` 中实现了一个简化 YAML 解析器，标准库纯 Python。  
  - 只支持项目所需的简单结构（如键值对、列表、嵌套字典等）。  
  - 代价：无法处理复杂 YAML 特性（如锚点、多行字符串、类型标签等），容错性较弱。  
  - 好处：安装门槛极低（`pip install -e .` 无额外依赖），部署简单。

**3. 题目**：`apr/cli.py` 中通过 `argparse` 定义了哪些子命令？请列举并说明各自功能。  
- **考察点**：对 CLI 设计及项目功能的整体把握。  
- **参考回答要点**：  
  - `review`：生成复盘报告（默认 `README复盘.md`），支持 `--skip-quiz`、`--language` 等参数。  
  - `scan`：只扫描项目并预览技术栈，不调用 LLM。  
  - `graph`：生成知识图谱（JSON/HTML/Canvas/Mindmap）。  
  - `plan`：生成个性化学习计划 `learning_plan.json`（不调用 LLM）。  
  - `quiz`：只运行实践验证问答。  
  - `init`：生成 `apr.yaml` 与 `profile.yaml` 模板。  
  - `web`：启动 Web 界面（`http://127.0.0.1:8765`）。  
  - `config`：交互式或子命令方式切换 LLM 供应商/模型。

**4. 题目**：README 中描述的多源证据融合权重分别是多少？AI 贡献度的判定阈值是什么？  
- **考察点**：对证据引擎核心规则的理解。  
- **参考回答要点**：  
  - 代码标记权重 1.0（`# AI-GENERATED` / `# HAND-WRITTEN`）。  
  - Agent 日志权重 0.9（Claude Code / DSH / 手动导入）。  
  - Git 历史权重 0.8（作者、Co-authored-by、新增行占比）。  
  - 变更轨迹权重 0.8（Agent 编辑事件与 Git numstat）。  
  - 判定：AI 贡献度 ≥ 70% 为“AI 主导”，40%–70% 为“AI 辅助”，置信度 < 30% 为“证据不足”。

**5. 题目**：`apr/config.py` 的 `PROVIDER_DEFAULTS` 支持哪些 LLM 提供商？如何快速切换预设？  
- **考察点**：多提供商配置机制。  
- **参考回答要点**：  
  - 支持 `deepseek`、`openai`、`openai-compatible`、`ollama`、`mock`。  
  - 每个预设包含 `base_url`、`api_key_env`、`model` 等字段。  
  - 通过 `apr config set --preset deepseek-flash` 一键切换（写全局配置）。  
  - 使用 `--local` 参数可只写当前项目配置；`apr config show` 查看当前生效配置。

### 进阶

**6. 题目**：`apr/evidence/fusion.py` 负责多源证据融合，请推测其可能的工作流程，并说明当不同证据源结论冲突时可能如何处理？  
- **考察点**：证据融合算法设计、冲突处理策略。  
- **参考回答要点**：  
  - 推测流程：从各证据源获取文件级贡献度，按权重加权求和得到综合 AI 贡献度。  
  - 同时结合置信度信息（如证据源覆盖度、标记强度）决定最终置信度。  
  - 冲突处理：可能采用高权重证据优先原则，或取加权结果并降低置信度。  
  - 最终报告严格区分“有证据的结论”与“推测”，证据不足时明确标注。

**7. 题目**：`apr/events/` 目录下包含 `base.py`、`dsh.py`、`generic.py`，请解释统一 Agent Event 系统的设计目的，以及如何桥接进证据层。  
- **考察点**：适配器模式、事件驱动架构。  
- **参考回答要点**：  
  - 定义规范事件基类（`base.py`），各适配器将不同格式日志（DSH JSONL、通用 JSONL）转为统一事件结构。  
  - 证据层只依赖规范事件接口，不关心来源格式，降低耦合。  
  - 桥接方式：事件经适配器解析后进入证据层，与 Git 历史、代码标记等一起融合计算 AI 贡献度。  
  - 扩展新来源只需新增适配器，无需改动 fusion 核心逻辑（推测）。

**8. 题目**：知识图谱的四层结构是“文件 → 技术 → 知识点 → 技能”，请解释各层含义以及“AI 贡献徽标”的作用。  
- **考察点**：知识图谱建模、学习评估可视化。  
- **参考回答要点**：  
  - 文件节点通过 `uses` 关系指向技术节点，技术通过 `covers` 关系指向知识点，知识点通过 `assesses` 关系评估用户技能。  
  - 技能节点带掌握程度百分比（来自 `profile.yaml`）。  
  - 文件节点和技术节点带 AI 贡献徽标，可直观看出哪些技术/文件主要由 AI 完成。  
  - 作用：识别“纸面掌握”——即 AI 贡献高但用户技能评估低的项目，帮助定位真实盲区。

**9. 题目**：`apr/coach/planner.py` 实现 Learning Coach，为什么设计为纯确定性规划器而不调用 LLM？这种设计的优缺点是什么？  
- **考察点**：架构决策、确定性 vs 生成式。  
- **参考回答要点**：  
  - 优点：速度极快（`apr plan` 几秒出结果）、结果可复现、无 API 成本、无网络依赖。  
  - 基于五类数据（项目需求、技能档案、Quiz、AI 贡献、知识图谱）按规则计算优先级。  
  - 缺点：无法理解复杂语义或生成个性化建议，只能依赖预定义规则。  
  - 适用于学习计划这种结构化输出场景，LLM 更适合生成自然语言报告内容。

**10. 题目**：项目在 `apr/cache.py` 和 `LimitsConfig` 中实现了哪些工程保护措施？它们分别解决什么问题？  
- **考察点**：缓存机制、资源保护。  
- **参考回答要点**：  
  - `cache.py` 实现结果缓存，避免重复调用 LLM，节省时间与费用。  
  - `LimitsConfig` 限制扫描文件数（`max_files=300`）、单文件大小（`max_file_kb=200`）、总大小（`max_total_kb=2000`）等。  
  - 额外忽略规则（`extra_ignores`）与 `.gitignore` 配合，防止扫描无关大文件（如 `node_modules`）。  
  - 这些措施保证工具在大型项目上也能稳定运行，避免资源耗尽。

### 开放

**11. 题目**：多源证据体系（代码标记、Agent 日志、Git 历史、变更轨迹）对 AI 贡献度的判定是否可靠？你认为有哪些潜在漏洞或改进方向？  
- **考察点**：批判性思维、证据可靠性评估。  
- **参考回答要点**：  
  - 现有信号可能遗漏无标记的 AI 生成代码（例如开发者手动复制 AI 输出且未加注释）。

---

## 下一步练习

以下练习基于当前项目结构与测试覆盖情况设计，按由易到难排序。练习 3 专门用于补齐“学习盲区”中的高优先级盲区；由于材料未给出“学习盲区”章节原文，该盲区基于 `tests/` 目录缺失 `test_git.py` 这一可见事实进行推测，并在任务中标注。

### 练习 1：跑通现有测试并阅读测试命名约定

- **难度：★**
- **任务描述**：在项目根目录运行 `pytest -q`，确认全部现有测试通过。然后阅读 `tests/test_config.py`、`tests/test_scanner.py`，理解项目如何组织测试文件、如何构造 fixture 以及如何模拟外部依赖。
- **涉及文件/技术**：`pytest`、`tests/` 目录下全部 `test_*.py`、`pyproject.toml`
- **完成标准**：`pytest -q` 无失败；能口头或书面说明至少 3 个测试文件分别覆盖的模块，以及其中 1 个 fixture 的用途。

### 练习 2：对示例项目完成一次端到端分析

- **难度：★★**
- **任务描述**：先查看 `apr/cli.py` 的参数说明，然后使用 CLI 对 `examples/demo-project` 运行一次完整分析，生成报告。观察报告中哪些章节有实际内容，哪些章节为空或缺失，并记录从扫描到报告输出的关键步骤。
- **涉及文件/技术**：`apr/cli.py`、`apr/analyzer.py`、`apr/report.py`、`examples/demo-project/apr.yaml`、`apr/config.py`
- **完成标准**：成功生成至少一份报告（控制台或文件）；能用自己的话复述“扫描 → 提取证据 → 生成报告”的主流程，并指出示例项目中哪一部分

---

## 我的技能评估

### Python

- **自评**：beginner
- **项目证据**：
    - 使用 Python 编写 65 个文件
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：90%

### AI Agent

- **自评**：beginner
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：39%

### C

- **自评**：beginner
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：39%

### Git

- **自评**：beginner
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：39%

### HTML/CSS

- **自评**：beginner
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：39%

### Java

- **自评**：beginner
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：39%

### JavaScript

- **自评**：beginner
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：39%

### MySQL

- **自评**：beginner
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：39%

### Spring Boot

- **自评**：beginner
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：39%

### Vue

- **自评**：beginner
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：39%

### AI Agent工程

- **自评**：未标注
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：35%

### Docker

- **自评**：未标注
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：35%

### Java后端开发

- **自评**：未标注
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：35%

### MCP

- **自评**：未标注
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：35%

### Redis

- **自评**：未标注
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：35%

### Spring生态

- **自评**：未标注
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：35%

### 数据库设计

- **自评**：未标注
- **项目证据**：
    - （无项目证据）
- **Quiz 表现**：未验证
- **最终等级**：入门（beginner）
- **可信度**：35%


---

## 下一阶段学习路线

> 由 Learning Coach 基于五类数据生成：技能评估 × 知识图谱 × Quiz × 技术栈 × AI 贡献。

### REST API

**原因**：
- 项目大量使用REST API
- 技能档案尚未掌握

**学习路线**：
1. 学习资源设计基础
2. 实现 REST API 练习 Demo
3. 重构项目中 REST API 相关模块

### React

**原因**：
- 项目使用React
- 技能档案尚未掌握

**学习路线**：
1. 学习组件基础
2. 实现 React 练习 Demo
3. 重构项目中 React 相关模块

### Spring

**原因**：
- 项目大量使用Spring
- 技能档案尚未掌握

**学习路线**：
1. 学习IoC/DI基础
2. 实现 Spring 练习 Demo
3. 重构项目中 Spring 相关模块

### MySQL

**原因**：
- 项目大量使用MySQL
- 正在学习中
- 用户技能等级 入门

**学习路线**：
1. 学习表设计基础
2. 实现 MySQL 练习 Demo
3. 重构项目中 MySQL 相关模块

### Django

**原因**：
- 项目使用Django
- 技能档案尚未掌握

**学习路线**：
1. 学习MTV 架构基础
2. 实现 Django 练习 Demo
3. 在项目中扩展 Django 的应用

### Elasticsearch

**原因**：
- 项目使用Elasticsearch
- 技能档案尚未掌握

**学习路线**：
1. 学习倒排索引基础
2. 实现 Elasticsearch 练习 Demo
3. 在项目中扩展 Elasticsearch 的应用

### FastAPI

**原因**：
- 项目使用FastAPI
- 技能档案尚未掌握

**学习路线**：
1. 学习路由基础
2. 实现 FastAPI 练习 Demo
3. 在项目中扩展 FastAPI 的应用

### JWT

**原因**：
- 项目使用JWT
- 技能档案尚未掌握

**学习路线**：
1. 学习令牌结构基础
2. 实现 JWT 练习 Demo
3. 在项目中扩展 JWT 的应用

### Kafka

**原因**：
- 项目使用Kafka
- 技能档案尚未掌握

**学习路线**：
1. 学习生产者/消费者基础
2. 实现 Kafka 练习 Demo
3. 在项目中扩展 Kafka 的应用

### MongoDB

**原因**：
- 项目使用MongoDB
- 技能档案尚未掌握

**学习路线**：
1. 学习文档模型基础
2. 实现 MongoDB 练习 Demo
3. 在项目中扩展 MongoDB 的应用

### MyBatis

**原因**：
- 项目使用MyBatis
- 技能档案尚未掌握

**学习路线**：
1. 学习SQL 映射基础
2. 实现 MyBatis 练习 Demo
3. 在项目中扩展 MyBatis 的应用

### Redis

**原因**：
- 项目大量使用Redis
- 学习目标（优先级medium）
- 用户技能等级 入门

**学习路线**：
1. 学习缓存基础
2. 实现 Redis 练习 Demo
3. 重构项目中 Redis 相关模块

### Python

**原因**：
- 项目大量使用Python
- 用户技能等级 入门

**学习路线**：
1. 学习 Python 基础
2. 实现 Python 练习 Demo
3. 重构项目中 Python 相关模块

### Spring Boot

**原因**：
- 项目使用Spring Boot
- 正在学习中
- 用户技能等级 入门

**学习路线**：
1. 学习自动配置基础
2. 实现 Spring Boot 练习 Demo
3. 在项目中扩展 Spring Boot 的应用

**实践项目**：
- REST API 实战练习
- React 实战练习
- Spring 实战练习
- Java后端开发 Demo 项目


---

## 附录 A：AI 生成证据明细

### 判定总览

| 判定 | 文件数 |
| --- | --- |
| AI 主导 | 0 |
| AI 辅助 | 3 |
| 疑似人工 | 26 |
| 证据不足 | 0 |

**有证据文件的平均 AI 贡献度**：7%

### 文件级证据明细

| 文件 | AI 贡献度 | 置信度 | 判定 | 证据摘要 |
| --- | --- | --- | --- | --- |
| examples/demo-project/utils.py | 62% | 90% | AI 辅助 | [marker] 检测到 1 处 AI 生成标记，如：# AI-GENERATED: 此函数由 Claude 编写 |
| apr/evidence/markers.py | 53% | 65% | AI 辅助 | [marker] 同时存在 AI 标记(2)与人工标记(4) |
| tests/test_markers.py | 52% | 65% | AI 辅助 | [marker] 同时存在 AI 标记(1)与人工标记(1) |
| README.md | 27% | 72% | 疑似人工 | [marker] 同时存在 AI 标记(2)与人工标记(2)；[git] @2026-08-14 0/7 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/_yaml.py | 0% | 70% | 疑似人工 | [git] @2026-08-14 0/4 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/analyzer.py | 0% | 60% | 疑似人工 | [git] @2026-08-14 0/3 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/assessment/skill.py | 0% | 60% | 疑似人工 | [git] @2026-08-15 0/3 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/cli.py | 0% | 75% | 疑似人工 | [git] @2026-08-14 0/9 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/config.py | 0% | 50% | 疑似人工 | [git] @2026-08-14 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/events/base.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/events/dsh.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/events/generic.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/evidence/agent_logs.py | 0% | 50% | 疑似人工 | [git] @2026-08-14 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/knowledge/knowledge.py | 0% | 75% | 疑似人工 | [git] @2026-08-15 0/7 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/profile.py | 0% | 50% | 疑似人工 | [git] @2026-08-14 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/report.py | 0% | 70% | 疑似人工 | [git] @2026-08-14 0/4 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/scanner.py | 0% | 60% | 疑似人工 | [git] @2026-08-14 0/3 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/templates.py | 0% | 60% | 疑似人工 | [git] @2026-08-14 0/3 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| knowledge_graph-mindmap.md | 0% | 60% | 疑似人工 | [git] @2026-08-15 0/3 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| profile.yaml.example | 0% | 50% | 疑似人工 | [git] @2026-08-14 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| pyproject.toml | 0% | 60% | 疑似人工 | [git] @2026-08-14 0/3 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| tests/__init__.py | 0% | 70% | 疑似人工 | [git] @2026-08-14 0/4 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| tests/test_blindspot.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| tests/test_coach.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| tests/test_config.py | 0% | 60% | 疑似人工 | [git] @2026-08-14 0/3 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| tests/test_events.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| tests/test_knowledge.py | 0% | 75% | 疑似人工 | [git] @2026-08-15 0/6 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| tests/test_report.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| tests/test_skill.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |

---

*本报告由 AI Project Reviewer 自动生成，仅供学习复盘参考；标注「推测」的内容未经证据证实。*