# ai-project-reviewer · 项目复盘

> 由 **AI Project Reviewer v0.1.0** 自动生成
> 生成时间：2026-08-15T18:03:44 ｜ 模型：deepseek/deepseek-v4-pro ｜ 语言：zh
> 项目路径：C:\Users\MAO0909\Documents\DSH\ai-project-reviewer

## 目录

1. [项目介绍](#项目介绍)
2. [技术栈](#技术栈)
3. [项目结构](#项目结构)
4. [核心代码分析](#核心代码分析)
5. [AI 生成部分](#AI 生成部分)
6. [我的学习盲区](#我的学习盲区)
7. [面试问题](#面试问题)
8. [下一步练习](#下一步练习)
9. [我的技能评估](#我的技能评估)
10. [下一阶段学习路线](#下一阶段学习路线)
11. [附录 A：AI 生成证据明细](#附录-aai-生成证据明细)
12. [附录 B：实践验证记录](#附录-b实践验证记录)

---

## 项目介绍

**一句话定位**：AI Project Reviewer（AI 项目复盘助手）是一个命令行/Web 工具，输入一个代码项目，自动生成结构化复盘报告《README复盘.md》，帮助用户理解项目、识别 AI 生成代码、发现个人学习盲区并准备面试。

**主要功能/特性**：
- 一键生成 8 大板块复盘报告，覆盖项目介绍、技术栈、项目结构、核心代码分析、AI 生成部分、学习盲区、面试问题和下一步练习，支持中英文配置。
- 多源证据融合判定 AI 生成部分：综合 Git 提交历史、Agent 会话日志、代码内标记和变更轨迹，输出逐文件 AI 贡献度与置信度。
- 个性化学习盲区：结合个人技能档案（profile.yaml）、项目能力需求和实践问答验证，动态生成盲区清单与学习路径。
- 实践验证：AI 根据项目出题，用户在终端作答，AI 批改评分并计入报告。
- 多 LLM 供应商支持：DeepSeek、OpenAI、任意 OpenAI 兼容端点、本地 Ollama 以及 mock（离线演示）。
- 零第三方依赖：纯 Python 标准库实现（含内置简化 YAML 解析器），要求 Python ≥ 3.10。
- 结果缓存、.gitignore 尊重、大项目限额保护，避免超限扫描。
- Web 界面（基于标准库 http.server）支持项目预览、后台任务、实时进度日志、报告预览与下载。

**目标用户与典型使用场景**（推测）：主要面向希望系统复盘代码项目的开发者、学习者，尤其是需要评估项目中 AI 生成代码占比、识别自身技能盲区、准备技术面试的用户。典型场景包括：学习开源项目或自己项目后生成复盘报告；在 AI 辅助开发后审计 AI 贡献度；利用问答功能自测对项目的理解程度。

**运行方式**：
- 依赖：无第三方依赖，Python ≥ 3.10（依据 pyproject.toml 中 `requires-python = ">=3.10"` 和 `dependencies = []`）。
- 安装：`pip install -e .`（安装后可通过 `apr` 命令使用），或不安装直接运行 `python -m apr ...`。
- 启动与使用：通过 CLI 子命令执行，如 `apr review .` 生成复盘报告，`apr scan .` 只扫描并预览技术栈，`apr quiz .` 运行实践验证问答，`apr init .` 初始化配置文件，`apr graph .` 生成知识图谱，`apr web` 启动 Web 界面，`apr config` 查看/切换 LLM 配置。具体参数见 README 中的命令说明。

**项目规模速览**：扫描统计文件数 70（排除 19 项），主要语言为 Python（60 个文件），总大小 299.1KB。

---

## 技术栈

### 技术栈总览

| 类别 | 技术 | 用途说明 |
|------|------|----------|
| 语言 | Python | 全部核心实现，要求 Python ≥ 3.10，纯标准库 |
| 构建工具 | setuptools（≥68） | `pyproject.toml` 声明构建后端，生成 `apr` 命令入口 |
| CLI 框架 | argparse（标准库） | `review/scan/quiz/init/graph/config/web` 子命令解析 |
| Web 服务 | http.server（标准库） | Web 界面：项目预览、后台任务、进度轮询、报告预览/下载 |
| LLM 接入 | DeepSeek / OpenAI / OpenAI 兼容端点 / Ollama / mock | 多供应商切换，CLI 参数与环境变量覆盖 |
| 配置格式 | YAML | `apr.yaml`、`profile.yaml`；由内置简化解析器解析 |
| 配置/元数据 | TOML | `pyproject.toml` 项目元数据与构建配置 |
| 文档格式 | Markdown | README、复盘报告、知识图谱 mindmap、示例说明 |
| 证据采集 | Git + Agent 日志 + 代码标记 | 多源证据融合，判定 AI 贡献度 |
| 开发自动化 | Git `post-commit` 钩子 | 提交后自动推送 GitHub |
| 测试框架 | 未明确（推测为标准库 `unittest`） | `tests/` 含 17 个 `test_*.py`，但运行时依赖为空 |

### 关键技术与用途

- **Python（≥3.10）**  
  `pyproject.toml` 明确 `requires-python = ">=3.10"`。README 声明“纯标准库实现（含内置简化 YAML 解析器），Python ≥ 3.10”。`apr/` 下所有核心模块如 `cli.py`、

---



---



---

## AI 生成部分

### 判定总览

材料共覆盖 **27 个有证据文件**，判定分布如下：

| 判定 | 文件数 | 在有证据文件中的占比 | 在全部扫描文件中的占比 |
| --- | --- | --- | --- |
| AI 主导 | 0 | 0.0% | 0.0% |
| AI 辅助 | 3 | 11.1% | 4.3% |
| 疑似人工 | 24 | 88.9% | 34.3% |
| 证据不足 | 0 | 0.0% | 0.0% |

有证据文件的平均 AI 贡献度为 **7%**，整体处于偏低水平。其余未列入证据清单的文件没有可用的 AI 参与证据，不纳入判定统计。

### 证据表格

按 AI 贡献度从高到低排列：

| 文件 | AI 贡献度 | 置信度 | 判定 |
| --- | --- | --- | --- |
| examples/demo-project/utils.py | 62% | 90% | AI 辅助 |
| apr/evidence/markers.py | 53% | 65% | AI 辅助 |
| tests/test_markers.py | 52% | 65% | AI 辅助 |
| README.md | 27% | 72% | 疑似人工 |
| apr/_yaml.py | 0% | 70% | 疑似人工 |
| apr/analyzer.py | 0% | 60% | 疑似人工 |
| apr/assessment/skill.py | 0% | 60% | 疑似人工 |
| apr/cli.py | 0% | 75% | 疑似人工 |
| apr/config.py | 0% | 50% | 疑似人工 |
| apr/events/base.py | 0% | 50% | 疑似人工 |
| apr/events/dsh.py | 0% | 50% | 疑似人工 |
| apr/events/generic.py | 0% | 50% | 疑似人工 |
| apr/knowledge/knowledge.py | 0% | 75% | 疑似人工 |
| apr/profile.py | 0% | 50% | 疑似人工 |
| apr/report.py | 0% | 70% | 疑似人工 |
| apr/scanner.py | 0% | 50% | 疑似人工 |
| apr/templates.py | 0% | 60% | 疑似人工 |
| knowledge_graph-mindmap.md | 0% | 50% | 疑似人工 |
| profile.yaml.example | 0% | 50% | 疑似人工 |
| pyproject.toml | 0% | 60% | 疑似人工 |
| tests/__init__.py | 0% | 50% | 疑似人工 |
| tests/test_blindspot.py | 0% | 50% | 疑似人工 |
| tests/test_config.py | 0% | 60% | 疑似人工 |
| tests/test_events.py | 0% | 50% | 疑似人工 |
| tests/test_knowledge.py | 0% | 75% | 疑似人工 |

### AI 贡献度 ≥70% 的文件说明

**不存在 AI 贡献度 ≥70% 的文件。** 证据材料中没有任何文件被判定为「AI 主导」。

整体证据库的最高 AI 贡献度为 `examples/demo-project/utils.py` 的 **62%**，属于「AI 辅助」层级。该项目不存在大块 AI 主导生成的源代码文件。

### 典型 AI 代码特征分析

以下内容依据现有证据进行推测，**属于推测**：

1. **AI 参与的分布集中于示例与辅助文件，而非核心逻辑**。  
   唯一具有明确 AI 生成标记的文件位于 `examples/demo-project/`，即示例项目中的工具函数。主包 `apr/` 下的核心模块（如 `cli.py`、`analyzer.py`、`report.py`、`scanner.py`）在 Git 证据中 AI 相关新增行占比均为 0%，首次提交均非 AI。

2. **推测：AI 被用于局部辅助或片段生成，而非整体生成**。  
   在 `apr/evidence/markers.py` 与 `tests/test_markers.py` 中同时存在 AI 标记与人工标记，说明这些文件经过混合编辑，AI 生成的代码块与人工编写的内容并存。

3. **风格统一度与注释习惯无法从材料中充分判断**。  
   材料未提供关键文件的代码摘录或注释样本，无法对风格统一度、注释密度、错误处理模式等做出有依据的观察。标记证据仅能说明 AI 参与的事实，不能推及具体风格特征。

4. **推测：README.md 的 AI 标记与人工标记混合**，可能由 AI 生成初稿后经人工修改，或针对个别章节由 AI 辅助撰写。

### 质量评估与人工复核清单

**有证据的结论：**

- 该项目 AI 参与度较低，没有 AI 主导的文件。
- 仅有 3 个文件被判定为 AI 辅助，且其中两个位于非核心路径（示例项目、测试）。
- 唯一位于主包内的 AI 辅助文件为 `apr/evidence/markers.py`（贡献度 53%，置信度 65%），它本身负责检测代码中的 AI 生成标记，其中同时存在 AI 标记与人工标记。

**人工应重点复核的文件清单：**

| 优先等级 | 文件 | 复核要点 |
| --- | --- | --- |
| 高 | apr/evidence/markers.py | AI 贡献度 53%，主包核心文件之一；需核对 AI 生成部分与人工部分的边界、标记判定逻辑是否会因自身混编而引入偏差 |
| 高 | tests/test_markers.py | AI 贡献度 52%，与 `markers.py` 形成验证闭环；需确认测试是否能真实覆盖所有实现路径，避免 AI 生成测试与实现逻辑脱节 |
| 中 | examples/demo-project/utils.py | AI 贡献度 62%、置信度 90%，虽然位于示例项目，但作为 AI 参与度最高的文件，建议检查函数行为是否符合示例项目预期 |
| 中 | README.md | AI 贡献度 27%，存在 2 处 AI 标记与 2 处人工标记；需确认技术描述与实际实现的一致性 |

**推测：** 核心逻辑模块（`cli.py`、`analyzer.py`、`report.py`、`scanner.py` 等）无 AI 参与证据，说明项目主体由人工完成，AI 仅在小范围、低风险路径中起到辅助作用。

---

## 我的学习盲区

> 由证据引擎计算：项目需求 × 技能档案 × Quiz × AI 贡献 × 知识图谱关联，非 AI 猜测。

### REST API

- **等级**：高风险盲区
- **证据**：
    - 项目核心依赖 REST API（2 个文件使用）
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
    - 项目核心依赖 MySQL（2 个文件使用）
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
    - 项目核心依赖 Redis（5 个文件使用）
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
    - 项目核心依赖 Python（60 个文件使用）
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



---

## 下一步练习

> 说明：以下练习基于项目当前目录结构与文件命名设计。由于未读取源码内容，凡涉及“现有模块是否已具备某接口”“CLI 命令格式”等判断均为推测，动手前应先阅读对应文件确认。测试运行命令基于项目使用 pytest 的推测，若 `pyproject.toml` 中配置了其他 runner，以项目实际配置为准。

### 练习 1：跑通最小分析流程（预计难度：★☆☆☆☆）

**任务描述**  
在 `examples/demo-project` 上运行一次完整分析，产出报告。阅读 `apr/cli.py`、`apr/analyzer.py`、`apr/report.py` 的调用链，画出从项目扫描到报告生成的数据流草图。

**涉及文件/技术**  
`examples/demo-project/apr.yaml`、`examples/demo-project/main.py`、`apr/cli.py`、`apr/analyzer.py`、`apr/report.py`、`README.md`

**完成标准**  
- 能无报错完成一次示例项目分析并生成报告文件。  
- 命令格式以 `README.md` 为准，若未文档化，则使用推测命令 `python -m apr analyze examples/demo-project` 并验证。  
- 数据流草图中能标出 `scanner → evidence → analyzer → report` 的主链路。

### 练习 2：为扫描排除规则补充测试（预计难度：★★☆☆☆）

**任务描述**  
项目画像显示扫描过程中排除了 19 项内容。阅读 `apr/scanner.py` 与 `tests/test_scanner.py`，为扫描器的排除逻辑补充边界测试，例如大写扩展名、隐藏目录、超大文件、符号链接等场景。若测试中发现某排除规则未实现或行为不符合预期，先补实现再补测试。

**涉及文件/技术**  
`apr/scanner.py`、`tests/test_scanner.py`、`.gitignore`

**完成标准**  
- `pytest tests/test_scanner.py -q` 通过。  
- 新增至少 3 个扫描排除相关测试用例，且能清晰验证排除逻辑。  
- 不依赖真实外部路径，使用 `tmp_path` 构造临时目录。

### 练习 3：增强配置文件的

---

## 我的技能评估

### Python

- **自评**：beginner
- **项目证据**：
    - 使用 Python 编写 60 个文件
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
- 项目使用REST API
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
- 项目使用MySQL
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
| 疑似人工 | 24 |
| 证据不足 | 0 |

**有证据文件的平均 AI 贡献度**：7%

### 文件级证据明细

| 文件 | AI 贡献度 | 置信度 | 判定 | 证据摘要 |
| --- | --- | --- | --- | --- |
| examples/demo-project/utils.py | 62% | 90% | AI 辅助 | [marker] 检测到 1 处 AI 生成标记，如：# AI-GENERATED: 此函数由 Claude 编写 |
| apr/evidence/markers.py | 53% | 65% | AI 辅助 | [marker] 同时存在 AI 标记(2)与人工标记(4) |
| tests/test_markers.py | 52% | 65% | AI 辅助 | [marker] 同时存在 AI 标记(1)与人工标记(1) |
| README.md | 27% | 72% | 疑似人工 | [marker] 同时存在 AI 标记(2)与人工标记(2)；[git] @2026-08-14 0/5 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/_yaml.py | 0% | 70% | 疑似人工 | [git] @2026-08-14 0/4 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/analyzer.py | 0% | 60% | 疑似人工 | [git] @2026-08-14 0/3 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/assessment/skill.py | 0% | 60% | 疑似人工 | [git] @2026-08-15 0/3 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/cli.py | 0% | 75% | 疑似人工 | [git] @2026-08-14 0/7 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/config.py | 0% | 50% | 疑似人工 | [git] @2026-08-14 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/events/base.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/events/dsh.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/events/generic.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/knowledge/knowledge.py | 0% | 75% | 疑似人工 | [git] @2026-08-15 0/6 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/profile.py | 0% | 50% | 疑似人工 | [git] @2026-08-14 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/report.py | 0% | 70% | 疑似人工 | [git] @2026-08-14 0/4 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/scanner.py | 0% | 50% | 疑似人工 | [git] @2026-08-14 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/templates.py | 0% | 60% | 疑似人工 | [git] @2026-08-14 0/3 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| knowledge_graph-mindmap.md | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| profile.yaml.example | 0% | 50% | 疑似人工 | [git] @2026-08-14 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| pyproject.toml | 0% | 60% | 疑似人工 | [git] @2026-08-14 0/3 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| tests/__init__.py | 0% | 50% | 疑似人工 | [git] @2026-08-14 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| tests/test_blindspot.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| tests/test_config.py | 0% | 60% | 疑似人工 | [git] @2026-08-14 0/3 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| tests/test_events.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| tests/test_knowledge.py | 0% | 75% | 疑似人工 | [git] @2026-08-15 0/5 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| tests/test_report.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| tests/test_skill.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |

---

## 附录 B：实践验证记录

### 作答记录

| 题目 | 我的答案 | 得分 | 点评 |
| --- | --- | --- | --- |
| 根据项目画像中的技术栈检测，本项目主要使用哪种编程语言实现？ | Python（参考：Python） | 100 | 回答正确，技术栈识别准确。 |
| apr/llm/ 目录下包含 factory.py、ollama.py 和 openai_compat.py，这说明项目 | Ollama 与 OpenAI 兼容 API（参考：Ollama 与 OpenAI 兼容 API） | 100 | 回答正确，LLM 后端支持识别准确。 |
| 在 apr/evidence/ 中，fusion.py 最可能负责什么职责？ | 融合多个证据来源形成统一评审依据（参考：融合多个证据来源形成统一评审依据） | 100 | 回答正确，fusion.py 职责理解准确。 |
| apr/events/ 下同时存在 base.py、dsh.py 和 generic.py，这种结构最可能体现什么架构意 | 提供统一事件抽象并适配 dsh 与通用事件源（参考：提供统一事件抽象并适配 dsh 与通用事件源） | 100 | 回答正确，事件抽象与多源适配架构理解准确。 |

**简答题回答**：不清楚

**总体评分**：80/100

**薄弱主题**：架构决策

---

*本报告由 AI Project Reviewer 自动生成，仅供学习复盘参考；标注「推测」的内容未经证据证实。*