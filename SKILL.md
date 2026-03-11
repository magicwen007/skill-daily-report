---
name: daily-report
description: 生成每日工作日报。从 OpenClaw sessions 提取对话记录，结合定时任务执行历史，用 AI 分析生成结构化的工作日报并推送到飞书。当用户请求以下内容时触发：(1) 生成工作日报 (2) 生成日报 (3) 日报 (4) daily report (5) 工作总结
---

# 工作日报 (Daily Report)

自动生成每日工作日报，推送到飞书。

## 快速使用

```bash
python3 ~/.openclaw/workspace/skills/daily-report/scripts/daily_report.py
```

## 配置

在 `scripts/config.env` 中配置（脚本会自动加载）：

```bash
# 飞书推送
FEISHU_USER_ID=
ENABLE_FEISHU=true

# Git 推送
ENABLE_GIT=true

# API 配置（自动检测）
# MINIMAX_API_KEY=
# ANTHROPIC_API_KEY=
# OPENAI_API_KEY=
```

### 获取飞书用户 ID

1. 打开飞书网页版 https://www.feishu.cn
2. F12 打开开发者工具 → Network
3. 发送任意消息
4. 在请求中查找 `open_id` 或 `user_id`
5. 将 ID 填入 `config.env` 的 `FEISHU_USER_ID`

## API 自动检测

优先级：MiniMax → Anthropic → OpenAI

| 环境变量 | 说明 |
|----------|------|
| `MINIMAX_API_KEY` / `MINIMAX_API_URL` | MiniMax |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` | Claude |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` | OpenAI / Azure |

## 定时任务

```bash
openclaw cron add --name "工作日报" --cron "0 23 * * *" --message "python3 ~/.openclaw/workspace/skills/daily-report/scripts/daily_report.py"
```
