# AI Project Reviewer（AI 项目复盘助手）

> 输入一个代码项目，输出一份《README复盘.md》：
> 项目介绍、技术栈、项目结构、核心代码分析、AI 生成部分（多源证据）、
> 我的学习盲区、面试问题、下一步练习。

## 特性

- 📄 **8 大板块复盘报告**：一键生成结构化 Markdown 复盘，中文/英文可配置。
- 🔍 **多源证据判定 AI 生成部分**：Git 提交历史（作者/Co-author）＋ Agent 会话日志
  （Claude Code / 手动导入 / DSH / Cursor）＋ 代码内标记 ＋ 变更轨迹 → 逐文件 AI 贡献度与置信度。
- 🎯 **个性化学习盲区**：个人技能档案（profile.yaml）× 项目能力需求 × 实践问答验证
  → 动态盲区清单与学习路径。
- 🧪 **实践验证**：AI 根据项目出题，终端作答，AI 批改评分并计入报告。
- 🔌 **多 LLM 供应商**：DeepSeek / OpenAI / 任意 OpenAI 兼容端点 / 本地 Ollama / mock（离线演示）。
- ⚡ **零第三方依赖**：纯标准库实现（含内置简化 YAML 解析器），Python ≥ 3.10。
- ♻️ 结果缓存、.gitignore 尊重、大项目限额保护。

## 安装

    pip install -e .

或不用安装，直接运行：

    python -m apr review .

## 快速开始

1. 在目标项目根目录初始化配置：

       apr init

2. 设置 API Key（以 DeepSeek 为例）：

       set DEEPSEEK_API_KEY=sk-xxx        （Windows）
       export DEEPSEEK_API_KEY=sk-xxx     （macOS/Linux）

3. 编辑 profile.yaml，填写你的技能档案。
4. 生成复盘报告：

       apr review .

   生成的《README复盘.md》位于项目根目录。

## 报告结构

| # | 板块 | 数据来源 |
|---|------|---------|
| 1 | 项目介绍 | 项目画像 |
| 2 | 技术栈 | 清单文件检测（package.json / requirements.txt / pyproject.toml / go.mod / Cargo.toml / pom.xml …）|
| 3 | 项目结构 | 目录树 + LLM 分析 |
| 4 | 核心代码分析 | 关键文件摘录 + LLM |
| 5 | AI 生成部分 | **多源证据融合**（见下）|
| 6 | 我的学习盲区 | 技能档案 + 项目需求 + 问答验证 |
| 7 | 面试问题 | 项目画像 + LLM |
| 8 | 下一步练习 | 以上全部 |
| 附录A | AI 生成证据明细 | 逐文件证据表 |
| 附录B | 实践验证记录 | 问答得分 |

## 证据体系

「AI 生成部分」采用多源证据融合，按权重合并为文件级「AI 贡献度」：

| 证据源 | 权重 | 说明 |
|-------|------|------|
| 代码标记 | 1.0 | # AI-GENERATED: … / # HAND-WRITTEN 等注释 |
| Agent 日志 | 0.9 | Claude Code 工具调用（Edit/Write）；手动导入的对话记录；DSH/Cursor 目录 |
| Git 历史 | 0.8 | 提交作者/邮箱、Co-authored-by 信息、逐文件 AI 提交占比与新增行占比 |
| 变更轨迹 | 0.8 | 由 Agent 编辑事件与 Git numstat 构成 |

判定：AI 贡献度 ≥ 70% 为「AI 主导」，40%~70% 为「AI 辅助」，置信度 < 30% 为「证据不足」。
报告中严格区分「有证据的结论」与「推测」。

### 如何提供 Agent 日志

- **手动导入（通用）**：把任意 Agent 的对话记录（txt/md/log/jsonl）放到
  <项目>/.apr/logs/ 下。
- **Claude Code**：自动解析 ~/.claude/projects/*.jsonl。
- **DSH / Cursor**：在 apr.yaml 配置 evidence.dsh_logs_dir / evidence.cursor_logs_dir。

### 如何标记代码

在文件中加入注释即可被识别：

- # AI-GENERATED: 这段由 Claude 编写
- # HAND-WRITTEN（否定标记）

## 命令

    apr review <项目路径>        # 生成复盘报告（默认 README复盘.md）
    apr scan <项目路径>          # 只扫描并预览技术栈，不调用 LLM
    apr quiz <项目路径>          # 只运行实践验证问答
    apr init <项目路径>          # 生成 apr.yaml 与 profile.yaml 模板
    apr web                      # 启动 Web 界面（http://127.0.0.1:8765）
    apr config                   # 交互向导：切换 LLM 供应商/模型
    apr config show              # 查看当前生效配置
    apr config set --preset deepseek-flash   # 一键切换预设（写全局）
    apr config set --preset deepseek-flash --local   # 只写当前项目

常用参数：--provider mock（离线演示）、--skip-quiz、--no-cache、--output 路径、
--language en、--dry-run、-v。

### Web 界面

    apr web --port 8765 --open

零第三方依赖（stdlib http.server），功能：输入项目路径 → 项目预览 → 一键复盘 →
实时进度日志 → 报告预览与下载。Web 端默认跳过交互问答（答题升级为学习评估系统
属 Phase 4）。

## 切换模型（apr config）

    apr config set --preset deepseek-pro     # DeepSeek V4 Pro（默认）
    apr config set --preset deepseek-flash   # DeepSeek V4 Flash（更便宜）
    apr config set --preset openai-mini      # OpenAI GPT-4o-mini
    apr config set --preset ollama-qwen      # 本地 Ollama
    apr config set --model deepseek-v4-flash # 只改模型，其余不变
    apr config                               # 交互式向导

默认写入全局 ~/.apr/apr.yaml（所有项目生效）；加 --local 只写当前项目 apr.yaml。
配置优先级：命令行参数 > 环境变量 > 项目 apr.yaml > 全局 ~/.apr/apr.yaml > 内置默认。

## 配置

项目根目录 apr.yaml（可用 apr init 生成），环境变量可覆盖：
APR_PROVIDER、APR_MODEL、APR_BASE_URL、APR_API_KEY。

## 路线图

- [x] Phase 1：核心引擎（扫描 / 证据 / 画像 / 8 板块 / CLI）
- [x] Phase 2：大项目保护、缓存、多源证据融合、实践验证
- [x] Phase 3：Web 界面（零依赖 http.server：项目预览、后台任务、进度轮询、报告预览/下载）
- [ ] Phase 4：打包发布、Web 端答题学习评估系统、更多 Agent 适配器（Cursor 原生索引等）

## 开发与同步

本仓库配置了 post-commit 自动推送钩子（.githooks/post-commit，经 core.hooksPath 启用）：
每次 git commit 成功后自动推送 GitHub。在新克隆的仓库中执行
git config core.hooksPath .githooks 即可启用。

## 免责声明

报告由 AI 自动生成，仅供学习复盘参考；标注「推测」的内容未经证据证实。
