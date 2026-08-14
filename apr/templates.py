"""apr init 生成的配置模板。"""

APR_YAML_TEMPLATE = '''# AI Project Reviewer 配置 —— 由 apr init 生成
llm:
  provider: deepseek            # deepseek | openai | openai-compatible | ollama | mock
  model: deepseek-v4-pro        # 或 deepseek-v4-flash（更便宜）
  base_url: https://api.deepseek.com   # openai-compatible 时必填（需含 /v1）
  api_key_env: DEEPSEEK_API_KEY        # API Key 所在的环境变量名
  temperature: 0.3
  max_tokens: 4096

output:
  file: README复盘.md
  language: zh                  # zh | en

profile: profile.yaml           # 个人技能档案（用于「我的学习盲区」）

limits:
  max_files: 300                # 最多纳入分析的文件数
  max_file_kb: 200              # 单个文件读取上限（KB），超限只统计不读内容
  max_total_kb: 2000            # 累计读取上限（KB）
  max_dir_tree_entries: 400     # 目录树展示条数上限
  extra_ignores: []             # 额外忽略模式（gitignore 风格）

evidence:
  markers: true                 # 扫描代码内 AI 标记注释
  git: true                     # Git 提交历史：作者 / Co-author / 变更轨迹
  agent_logs: true              # Agent 对话与行为记录
  manual_logs_dir: .apr/logs    # 手动导入的对话记录目录（项目内）
  claude_projects_dir: ~/.claude/projects
  dsh_logs_dir: null            # 可选：DSH 会话日志目录
  cursor_logs_dir: null         # 可选：Cursor 日志/导出目录

quiz:
  enabled: true
  question_count: 4             # 选择题数量（另含 1 道简答题）
'''

PROFILE_YAML_TEMPLATE = '''# 个人技能档案 —— 用于「我的学习盲区」板块
name: 你的名字            # 可选
background: 一句话介绍你的技术背景   # 可选
known_skills:             # 已掌握的技术/领域
  - Python
  - Git
learning_goals:           # 想提升的方向
  - 系统设计
'''
