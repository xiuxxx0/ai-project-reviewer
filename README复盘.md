# ai-project-reviewer · 项目复盘

> 由 **AI Project Reviewer v0.1.0** 自动生成
> 生成时间：2026-08-15T18:50:33 ｜ 模型：deepseek/deepseek-v4-pro ｜ 语言：zh
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

### 一句话定位

**ai-project-reviewer** 是一个 AI 项目复盘助手：输入一个代码项目，自动生成《README复盘.md》、知识图谱与个性化学习计划，形成「复盘 → 证据 → 盲区 → 技能评估 → 学习路线」的完整学习闭环。

### 主要功能/特性

- **12 节复盘报告**：涵盖项目介绍、技术栈、结构分析、核心代码、AI 协作、学习盲区、面试问题、技能评估、学习路线等 8 大板块，中英文可配置。
- **多源证据判定 AI 生成部分**：融合 Git 提交历史、Agent 会话日志（Claude Code / 手动导入 / DSH / Cursor）、代码内标记与变更轨迹，按权重计算逐文件 AI 贡献度与置信度，生成证据明细表。
- **统一 Agent Event 系统**（`apr/events/`）：将 DSH JSONL / 通用 JSONL 经适配器转为规范事件，桥接进证据层。
- **知识图谱**（`apr graph`）：构建「文件 ─uses→ 技术 ─covers→ 知识点 ─assesses→ 用户技能」四层图谱，输出 JSON、HTML（Obsidian 关系图谱风格）、Obsidian Canvas 与 Mermaid 思维导图四种可视化格式。
- **学习盲区证据引擎**：由项目需求、技能档案、Quiz、AI 贡献度与知识图谱五路信号计算判定，非 AI 猜测。
- **Learning Coach 学习计划**（`apr plan`）：基于五类数据生成优先级与下一步实践项目，纯确定性规划器，不调用 LLM。
- **实践验证问答**（`apr quiz`）：AI 根据项目出题，终端作答并批改评分，结果计入报告。
- **多 LLM 供应商支持**：DeepSeek / OpenAI / 任意 OpenAI 兼容端点 / 本地 Ollama / mock（离线演示）。
- **零第三方依赖**：纯标准库实现（含内置简化 YAML 解析器），Python ≥ 3.10；另支持结果缓存、.gitignore 尊重与大项目限额保护。

### 目标用户与典型使用场景

**目标用户**（推测）：正在学习编程、需要通过项目复盘巩固知识并识别技能盲区的开发者或学习者；同时因其生成面向开发者/面试的技术复盘与面试问题，也适合准备技术面试的求职者。

**典型使用场景**（推测）：

- 学习者完成一个项目后，运行 `apr review` 生成复盘报告，了解项目中哪些部分是 AI 主导、哪些是手写，并识别自己的知识盲区。
- 通过 `apr graph` 生成知识图谱，直观看到文件到技术、知识点、技能的覆盖关系，辅助查漏。
- 通过 `apr plan` 获取个性化学习路线与下一步实践项目建议，持续迭代学习闭环。
- 面试前快速生成项目复盘与面试问题清单，梳理项目亮点与盲区。

### 运行方式

**安装**（依据 README 与 pyproject.toml）：

- 方式一：`pip install -e .`（Python ≥ 3.10，零第三方依赖）。
- 方式二：无需安装，直接 `python -m apr review .`。

**启动入口**：`pyproject.toml` 注册命令行入口 `apr = "apr.cli:main"`，入口实现在 `apr/cli.py`。

**基本使用流程**（依据 README）：

1. `apr init` 在项目根目录生成 `apr.yaml` 与 `profile.yaml` 模板。
2. 设置 API Key 环境变量（如 DeepSeek 的 `DEEPSEEK_API_KEY`）。
3. 编辑 `profile.yaml` 填写技能档案。
4. `apr review .` 生成复盘报告（输出至 `output/README复盘.md` 与 `output/learning_report.md`）。

**主要子命令**（依据 CLI 参数定义与 README）：

| 命令 | 功能 |
|------|------|
| `apr review <路径>` | 生成复盘报告 |
| `apr scan <路径>` | 仅扫描技术栈，不调用 LLM |
| `apr graph <路径>` | 生成知识图谱 |
| `apr plan <路径>` | 生成学习计划 `learning_plan.json` |
| `apr quiz <路径>` | 仅运行实践验证问答 |
| `apr init <路径>` | 生成配置模板 |
| `apr web` | 启动 Web 界面（http://127.0.0.1:8765） |
| `apr config` | 交互式切换 LLM 供应商/模型 |

### 项目规模速览

- **文件数**：79 个（扫描时排除 22 项）。
- **主要语言**：Python（67 个文件），另有 Markdown、示例项目、Canvas、JSON、TOML、YAML 等。
- **总大小**：约 377.1 KB。
- **项目结构**：核心代码集中在 `apr/` 包内，按子模块划分为 `assessment/`（技能评估与盲区）、`llm/`（多供应商适配）、`evidence/`（多源证据融合）、`knowledge/`（知识图谱与学习画布）、`events/`（统一事件系统）、`coach/`（学习规划器）等；另有 `tests/` 测试目录（20 个测试文件）与 `examples/demo-project/` 示例项目。

---

## 技术栈

### 技术栈总览

| 类别 | 技术 | 用途说明 |
|------|------|----------|
| 语言 | Python（≥ 3.10） | 项目全部核心逻辑使用 Python 实现，`pyproject.toml` 中声明 `requires-python = ">=3.10"`。 |
| 运行时/标准库 | argparse、dataclasses、pathlib、os 等 | CLI 参数解析、配置数据模型、文件路径处理等均基于 Python 标准库，项目声称零第三方依赖。 |
| 构建/打包 | setuptools（≥ 68） + pyproject.toml | 通过 `pyproject.toml` 定义构建系统和包元数据，`[project.scripts]` 暴露 `apr` 命令，支持 `pip install -e .` 安装。 |
| 配置解析 | 自制简化 YAML 解析器（`apr/_yaml.py`） | 解析 `apr.yaml`、`profile.yaml` 等项目配置文件。注释与 README 均明确使用内置简化解析器，不依赖 PyYAML。 |
| 配置/数据格式 | YAML、TOML、JSON | YAML 用于项目与用户配置，TOML 用于 Python 包元数据，JSON 用于知识图谱（`knowledge_graph.json`）和学习计划（`learning_plan.json`）输出。 |
| LLM 集成 | DeepSeek、OpenAI、OpenAI 兼容端点、Ollama、mock | 通过统一 provider 接口（`apr/llm/`）调用外部大模型，用于报告生成、问答批改等；`mock` 用于离线演示。 |
| 可视化输出 | HTML（Obsidian 风格关系图）、Obsidian Canvas、Mermaid | 知识图谱支持三种可视化导出：交互式 HTML（拖拽/缩放/悬停高亮）、Obsidian Canvas 文件、Mermaid 思维导图 Markdown。报告本身输出为 Markdown。 |
| Web 界面 | 未披露具体实现（命令 `apr web`） | 提供本地 Web 界面，默认地址 `http://127.0.0.1:8765`，材料仅给出启动命令和访问地址，未说明所用 Web 框架或服务器。 |

### 关键技术与用途说明

- **Python 3.10+**：项目以 Python 包形式组织，核心模块包括 `apr/cli.py`、`apr/analyzer.py`、`apr/scanner.py`、`apr/report.py` 等，全部使用 Python 编写。README 声明 Python ≥ 3.10，`pyproject.toml` 中 `requires-python = ">=3.10"`。
- **零第三方依赖**：`pyproject.toml` 中 `dependencies = []`，README 明确“纯标准库实现（含内置简化 YAML 解析器）”。配置加载、目录扫描、报告渲染等均基于标准库完成。
- **setuptools 构建系统**：`pyproject.toml` 指定 `setuptools>=68` 作为构建后端，并通过 `[project.scripts]` 将 `apr = "apr.cli:main"` 注册为命令行入口，使项目既可通过 `pip install -e .` 安装，也可直接执行 `python -m apr review .`。
- **自制 YAML 解析器**：位于 `apr/_yaml.py`，负责解析项目配置文件。材料中注释说明“YAML 解析使用内置简化解析器（apr._yaml），零第三方依赖”，配置文件按“节”整体覆盖，不做深合并。
- **多 LLM 供应商适配**：`apr/config.py` 定义 `PROVIDER_DEFAULTS`，支持 `deepseek`、`openai`、`openai-compatible`、`ollama`、`mock` 五种 provider，统一封装在 `apr/llm/factory.py` 中。API Key 可通过环境变量或 CLI 参数提供。
- **知识图谱可视化**：`apr graph` 命令生成 `knowledge_graph.json`、`knowledge_graph.html`、`knowledge_graph.canvas`、`knowledge_graph-mindmap.md` 四种格式输出，覆盖数据结构、交互式图形、Obsidian 画布和 Mermaid 导图。
- **配置文件格式**：YAML 用于 `apr.yaml` 和 `profile.yaml`；TOML 用于 `pyproject.toml`；JSON 用于图谱数据与学习计划。三者分别担任运行时配置、包元数据、结构化输出的角色。

### 主依赖版本

- **Python**：≥ 3.10（`pyproject.toml` 与 README 一致声明）
- **setuptools**：≥ 68（`pyproject.toml` 的 `build-system.requires`）
- **第三方运行时依赖**：无（`dependencies = []`）

### 选型点评

- **零第三方依赖策略（证据支持）**：项目刻意避免外部包，安装门槛极低，适合作为分发给其他开发者的分析工具。  
  **（推测）**：自制 YAML 解析器可能仅覆盖项目自身用到的子集，对复杂 YAML 语法或边界场景的兼容性可能有限。
- **多 LLM 供应商统一适配（证据支持）**：通过 `factory.py` 和 `PROVIDER_DEFAULTS` 实现多供应商切换，用户可根据成本、可用性灵活选择，且 `mock` 支持无网络演示。  
  **（推测）**：不同供应商的模型能力差异可能直接导致报告质量波动，未在材料中看到针对各模型的输出一致性校验。
- **使用 pyproject.toml + setuptools（证据支持）**：采用现代 Python 项目打包规范，并配置了 CLI 入口，便于标准安装和命令行调用。  
  **（推测）**：未提供依赖锁定文件（如 `requirements.txt` 或 `poetry.lock`），在需要复现环境时可能缺少版本确定性，但因当前零第三方依赖，影响较有限。
- **标准库 Web 服务（推测）**：材料显示 `apr web` 启动本地界面，但未披露 Web 框架或服务器实现。结合“零第三方依赖”的声明，推测很可能基于 `http.server` 等标准库模块实现，但证据不足，仅作推测。

---



---

## 核心代码分析

本节基于项目画像中提供的文件摘录进行分析。需要先说明一个材料边界：摘录覆盖较充分的是 `apr/cli.py`、`apr/config.py`、`pyproject.toml`，而 `apr/analyzer.py`、`apr/report.py`、`apr/digest.py`、`apr/scanner.py`、`apr/_yaml.py` 等文件虽然能从导入关系、README 和文件大小中获知部分职责，但缺少实现细节。下文对材料不足的部分明确标注，不编造。

### 1. `apr/cli.py` — CLI 命令入口

**职责**  
该文件是命令行入口，通过 `argparse` 定义并分发 `review`、`scan`、`quiz`、`init`、`graph`、`plan`、`config` 等子命令。从导入语句看，它聚合了配置、扫描、分析、报告渲染、LLM Provider 工厂等模块，是用户操作与核心流程之间的外壳层。

**关键实现**

- `build_parser()` 使用 `subparsers` 构建子命令体系，并在 `review`、`quiz` 子命令上复用 `_add_llm_options()`，避免重复定义 LLM 相关参数。
- `_reconfigure_stdout()` 强制将 `sys.stdout`、`sys.stderr` 重新配置为 UTF-8，并使用 `errors="replace"`，这是面向 Windows 中文输出场景的现实处理。
- `_add_llm_options()` 暴露 `--provider`、`--model`、`--base-url`、`--api-key`，使 CLI 参数可以覆盖配置文件与环境变量。
- `BANNER` 使用 `f"AI Project Reviewer v{__version__} — AI 项目复盘助手"` 统一版本展示。

**设计模式/架构思想**  
这是一个典型的“门面 + 命令分发”结构：`cli.py` 不承载业务逻辑，只负责参数解析、配置注入和调用下游函数。`_add_llm_options` 的复用体现了 DRY 原则。该模式适合 CLI 工具，因为参数层与业务层解耦，便于单独测试各子命令。

**可改进点**

- `build_parser()` 已经比较长，后续若继续增加子命令，可考虑把各子命令的解析器构造拆成独立函数或命令注册表，避免单一函数持续膨胀。
- `_reconfigure_stdout()` 使用 `errors="replace"` 会静默替换无法编码的字符；在 `--verbose` 或调试场景下，这可能掩盖输出问题。可以让 `--verbose` 时改为更严格或可观测的处理。
- 摘录中 `config` 子命令通过 `from .configure import PRESETS` 引入预设，但该段被截断，无法确认预设加载是否会失败终止。若 `configure` 模块缺少 `PRESETS`，会在 `cli.py` 导入期直接出错，建议确认模块边界。

---

### 2. `apr/config.py` — 配置加载与合并

**职责**  
负责加载和合并多级配置，并构造 `LLMConfig`、`OutputConfig`、`LimitsConfig`、`EvidenceConfig` 等数据类。文件头部注释明确说明优先级：

> 内置默认 ← `~/.apr/apr.yaml` ← 项目根 `apr.yaml` ← 环境变量 ← CLI 参数

同时说明 YAML 解析使用内置简化解析器 `apr._yaml`，各配置文件按“节”整体覆盖，不做深合并。

**关键实现**

- `PROVIDER_DEFAULTS` 为 DeepSeek、OpenAI、OpenAI 兼容端点、Ollama、mock 提供集中默认值，包括 `base_url`、`api_key_env`、`model`。
- `_get(mapping, key, default)` 对非 dict 输入做了防御，避免在配置缺失时直接抛异常。
- `LLMConfig.from_mapping()` 从映射构造配置，并从环境变量读取 API Key：

    ```python
    api_key = os.environ.get(str(api_key_env), "")
    ```

- `OutputConfig.from_mapping()` 对 `language` 做了白名单校验，只允许 `zh` 或 `en`，否则抛出 `ConfigError`。
- `LimitsConfig.from_mapping()` 对 `extra_ignores` 做了列表类型校验，并将元素统一转为字符串。
- `EvidenceConfig.from_mapping()` 内部使用局部辅助函数 `_b()`、`_s()` 分别处理布尔和字符串默认值，减少重复代码。

**设计模式/架构思想**  
该类使用 `dataclass` 加 `from_mapping()` 类方法作为工厂，将“外部配置映射”转换为类型化对象，属于数据类工厂模式。相比直接在业务代码里散落 `mapping.get(...)`，这种设计提高了配置的可读性和可测试性。优先级在文件头明确写出，是配置模块中很重要的可维护性实践。

**可改进点**

- `LLMConfig.from_mapping()` 直接读取环境变量，使工厂方法带有副作用。虽然当前场景合理，但会让单元测试依赖环境变量状态。可改为注入 `env` 参数，或把环境变量读取移到独立的 `resolve_api_key()` 函数中。
- 默认模型 `deepseek-v4-pro` 在注释中被描述为可选项，并提到旧模型名已于 2026-07-24 停用。建议在配置层增加默认模型有效性提示或启动时校验，避免默认值失效时用户直接遇到远端 API 错误。
- “按节整体覆盖”是明确设计，但它可能让用户感到反直觉：在项目级 `apr.yaml` 只想覆盖 `evidence.git` 时，也必须写全整个 `evidence` 节。可在文档中增加示例，或者提供浅合并配置说明，降低配置门槛。

---

### 3. `pyproject.toml` — 打包与入口声明

**职责**  
定义项目元数据、构建系统、入口命令和打包范围。

**关键实现**

- `dependencies = []` 明确项目零第三方依赖，与 README 中“纯标准库实现”一致。
- `requires-python = ">=3.10"` 明确了最低 Python 版本。
- `[project.scripts]` 中声明 `apr = "apr.cli:main"`，使安装后可以直接运行 `apr`。
- `[tool.setuptools]` 手动列出包清单：

    ```toml
    packages = ["apr", "apr.llm", "apr.evidence", "apr.assessment",
                "apr.prompts", "apr.knowledge", "apr.events", "apr.coach"]
    ```

**设计模式/架构思想**  
采用现代 Python 打包标准 `pyproject.toml`，并将入口点指向 `apr.cli:main`。对纯标准库项目来说，这种声明式打包方案依赖少、部署简单。

**可改进点**

- 手动维护 `packages` 列表容易在新增子包时遗漏。例如未来增加 `apr.exporters` 或 `apr.plugins` 时，构建包不会自动包含。可替换为 `[tool.setuptools.packages.find]` 或引入 `find` 规则。
- `version = "0.1.0"` 写死在 `pyproject.toml` 中，而 `cli.py` 又导入 `

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
- 自己设计模块（27 个文件判定人工编写）

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
    - 项目核心依赖 REST API（4 个文件使用）
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
    - 项目核心依赖 Redis（8 个文件使用）
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
    - 项目核心依赖 Python（67 个文件使用）
    - profile 自评 basic
    - 暂无 Quiz 验证
    - 代码以人工编写为主（AI 贡献 6%）
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
- canvas：档案声明但项目未使用，不计入盲区
- 数据库设计：档案声明但项目未使用，不计入盲区
- 项目使用但风险低、未列为盲区：Vue


---



---



---

## 我的技能评估

### Python

- **自评**：beginner
- **项目证据**：
    - 使用 Python 编写 67 个文件
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

### canvas

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
| 疑似人工 | 27 |
| 证据不足 | 0 |

**有证据文件的平均 AI 贡献度**：6%

### 文件级证据明细

| 文件 | AI 贡献度 | 置信度 | 判定 | 证据摘要 |
| --- | --- | --- | --- | --- |
| examples/demo-project/utils.py | 62% | 90% | AI 辅助 | [marker] 检测到 1 处 AI 生成标记，如：# AI-GENERATED: 此函数由 Claude 编写 |
| apr/evidence/markers.py | 53% | 65% | AI 辅助 | [marker] 同时存在 AI 标记(2)与人工标记(4) |
| tests/test_markers.py | 52% | 65% | AI 辅助 | [marker] 同时存在 AI 标记(1)与人工标记(1) |
| README.md | 27% | 72% | 疑似人工 | [marker] 同时存在 AI 标记(2)与人工标记(2)；[git] @2026-08-14 0/8 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/_yaml.py | 0% | 70% | 疑似人工 | [git] @2026-08-14 0/4 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/analyzer.py | 0% | 70% | 疑似人工 | [git] @2026-08-14 0/4 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/assessment/skill.py | 0% | 60% | 疑似人工 | [git] @2026-08-15 0/3 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/cli.py | 0% | 75% | 疑似人工 | [git] @2026-08-14 0/10 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/config.py | 0% | 50% | 疑似人工 | [git] @2026-08-14 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/events/base.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/events/dsh.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/events/generic.py | 0% | 50% | 疑似人工 | [git] @2026-08-15 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/evidence/agent_logs.py | 0% | 50% | 疑似人工 | [git] @2026-08-14 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/knowledge/knowledge.py | 0% | 75% | 疑似人工 | [git] @2026-08-15 0/8 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/profile.py | 0% | 50% | 疑似人工 | [git] @2026-08-14 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/prompts/sections.py | 0% | 50% | 疑似人工 | [git] @2026-08-14 0/2 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/report.py | 0% | 75% | 疑似人工 | [git] @2026-08-14 0/5 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/scanner.py | 0% | 60% | 疑似人工 | [git] @2026-08-14 0/3 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| apr/templates.py | 0% | 60% | 疑似人工 | [git] @2026-08-14 0/3 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
| knowledge_graph-mindmap.md | 0% | 70% | 疑似人工 | [git] @2026-08-15 0/4 次提交疑似 AI 参与，AI 相关新增行占比 0%，首次提交非 AI |
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