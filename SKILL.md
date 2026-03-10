---
name: daily-report
description: 生成每日工作日报。从 OpenClaw sessions 提取对话记录，结合定时任务执行历史，用 AI 分析生成结构化的工作日报并推送到飞书。当用户请求以下内容时触发：(1) 生成工作日报 (2) 生成日报 (3) 日报 (4) daily report (5) 工作总结
---

# 工作日报 (Daily Report)

自动生成每日工作日报，推送到飞书。

## 快速使用

```bash
python3 /Users/mymac/.openclaw/workspace/skills/daily-report/scripts/daily_report.py
```

## 配置

在 `scripts/config.env` 中配置：

```bash
# 飞书推送（默认开启）
FEISHU_USER_ID=ou_385eb38d334f82a901667e2c81ccdc5c
ENABLE_FEISHU=true

# Git 推送（默认关闭）
ENABLE_GIT=false

# API 配置（自动检测）
# MINIMAX_API_KEY=
# ANTHROPIC_API_KEY=
# OPENAI_API_KEY=
```

运行前加载配置：
```bash
source /Users/mymac/.openclaw/workspace/skills/daily-report/scripts/config.env
python3 /Users/mymac/.openclaw/workspace/skills/daily-report/scripts/daily_report.py
```

## API 自动检测

优先级：MiniMax → Anthropic → OpenAI

| 环境变量 | 说明 |
|----------|------|
| `MINIMAX_API_KEY` / `MINIMAX_API_URL` | MiniMax |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` | Claude |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` | OpenAI / Azure |
