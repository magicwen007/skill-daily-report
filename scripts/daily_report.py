#!/usr/bin/env python3
"""
每日工作报告生成器 V5 - 标准环境变量版本
支持 OpenAI / Anthropic / MiniMax API
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# ============ 加载环境变量 ============
def load_env_from_shell():
    """从 ~/.zshrc 加载环境变量"""
    zshrc = Path.home() / ".zshrc"
    if zshrc.exists():
        with open(zshrc) as f:
            for line in f:
                line = line.strip()
                if line.startswith("export ") and "=" in line:
                    # 去掉 "export " 前缀
                    line = line[7:]
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key and val and key not in os.environ:
                            os.environ[key] = val

# 启动时加载环境变量
load_env_from_shell()

# ============ 配置区域 ============
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.env"

# 优先从 config.env 读取，否则使用环境变量
def load_config():
    """加载配置文件"""
    config = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    config[key.strip()] = val.strip()
    return config

CONFIG = load_config()

# 飞书配置
FEISHU_USER_ID = os.environ.get("FEISHU_USER_ID", CONFIG.get("FEISHU_USER_ID", ""))
ENABLE_FEISHU = os.environ.get("ENABLE_FEISHU", CONFIG.get("ENABLE_FEISHU", "false")).lower() == "true"

# Git 推送配置
ENABLE_GIT = os.environ.get("ENABLE_GIT", CONFIG.get("ENABLE_GIT", "false")).lower() == "true"

# 路径配置
WORKSPACE = Path.home() / ".openclaw" / "workspace"
DATA_DIR = WORKSPACE / "data" / "daily-reports"

# ============ 核心函数 ============

def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")

def get_api_config():
    """自动检测可用的 API 配置"""
    # 优先级: MiniMax > Anthropic > OpenAI
    
    # MiniMax (使用 MiniMax API)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    api_url = os.environ.get("ANTHROPIC_API_URL", "https://api.minimaxi.com")
    if api_key and "minimax" in api_url.lower():
        return {
            "provider": "minimax",
            "key": api_key,
            "url": api_url or "https://api.minimax.com",
            "model": os.environ.get("MINIMAX_MODEL", "MiniMax-M2.5")
        }
    
    # Anthropic (Claude)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "") or os.environ.get("CLAUDE_API_KEY", "")
    api_url = os.environ.get("ANTHROPIC_API_URL", "") or os.environ.get("ANTHROPIC_BASE_URL", "") or os.environ.get("CLAUDE_BASE_URL", "")
    if api_key:
        return {
            "provider": "anthropic",
            "key": api_key,
            "url": api_url or "https://api.anthropic.com",
            "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        }
    
    # OpenAI
    api_key = os.environ.get("OPENAI_API_KEY", "") or os.environ.get("OPENAI_KEY", "")
    api_url = os.environ.get("OPENAI_API_URL", "") or os.environ.get("OPENAI_BASE_URL", "") or os.environ.get("OPENAI_KEY", "")
    if api_key:
        return {
            "provider": "openai",
            "key": api_key,
            "url": api_url or "https://api.openai.com/v1",
            "model": os.environ.get("OPENAI_MODEL", "gpt-4o")
        }
    
    return None

def get_sessions_for_date(target_date_str):
    """获取指定日期的 sessions"""
    sessions_dir = Path("/Users/mymac/.openclaw/agents/main/sessions")
    
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    yesterday = target_date - timedelta(days=1)
    
    start = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 0, 0)
    end = datetime(target_date.year, target_date.month, target_date.day, 23, 0, 0)
    
    print(f"时间范围: {start} ~ {end}")
    
    all_jsonl_files = list(sessions_dir.glob("*.jsonl"))
    print(f"找到 {len(all_jsonl_files)} 个 session 文件")
    
    all_messages = []
    
    for session_file in all_jsonl_files:
        try:
            with open(session_file, 'r') as f:
                lines = f.readlines()
            
            if not lines:
                continue
            
            has_content = False
            session_content = [f"\n=== {session_file.name} ===\n"]
            
            for line in lines:
                try:
                    msg = json.loads(line)
                    ts = msg.get("timestamp", "")
                    
                    if ts:
                        msg_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        msg_time = msg_time.replace(tzinfo=None) + timedelta(hours=8)
                        
                        if start <= msg_time <= end:
                            has_content = True
                            
                            if msg.get("type") == "message":
                                message = msg.get("message", {})
                                role = message.get("role", "")
                                if role not in ("user", "assistant"):
                                    continue
                                content = message.get("content", [])
                                
                                text_parts = []
                                for c in content:
                                    if c.get("type") == "text":
                                        text = c.get("text", "")
                                        if text and not text.startswith("[toolResult]") and "[toolResult]" not in text:
                                            text_parts.append(text)
                                
                                if text_parts:
                                    text = " ".join(text_parts)[:300]
                                    if text.strip():
                                        session_content.append(f"[{role}]: {text}")
                except:
                    continue
            
            if has_content and len(session_content) > 1:
                all_messages.append("\n".join(session_content))
                
        except Exception as e:
            print(f"读取 {session_file.name} 失败: {e}")
            continue
    
    cron_runs = get_cron_runs_for_date(start, end)
    if cron_runs:
        all_messages.append(f"\n=== Cron任务执行记录 ===\n" + cron_runs)
    else:
        cron_defs = get_cron_task_definitions()
        if cron_defs:
            all_messages.append(f"\n=== Cron任务定义 ===\n" + cron_defs)
    
    return "\n\n".join(all_messages)

def get_cron_runs_for_date(start, end):
    """获取 cron 任务执行记录"""
    result = subprocess.run(
        ["openclaw", "cron", "list", "--json"],
        capture_output=True, text=True, timeout=30
    )
    
    if result.returncode != 0:
        return ""
    
    try:
        cron_list = json.loads(result.stdout)
    except:
        return ""
    
    all_runs = []
    
    for job in cron_list.get("jobs", []):
        job_id = job.get("id", "")
        job_name = job.get("name", job_id)
        
        result = subprocess.run(
            ["openclaw", "cron", "runs", "--limit", "10", "--id", job_id],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode != 0:
            continue
        
        try:
            runs_data = json.loads(result.stdout)
        except:
            continue
        
        for entry in runs_data.get("entries", []):
            ts = entry.get("ts", 0)
            run_time = datetime.fromtimestamp(ts / 1000) + timedelta(hours=8)
            
            if start <= run_time <= end:
                status = entry.get("status", "unknown")
                summary = entry.get("summary", "")[:200]
                all_runs.append(f"- [{job_name}] {status}: {summary}")
    
    return "\n".join(all_runs[:20])

def get_cron_task_definitions():
    """获取 cron 任务定义"""
    result = subprocess.run(
        ["openclaw", "cron", "list", "--json"],
        capture_output=True, text=True, timeout=30
    )
    
    if result.returncode != 0:
        return ""
    
    try:
        cron_list = json.loads(result.stdout)
    except:
        return ""
    
    tasks = []
    for job in cron_list.get("jobs", []):
        job_name = job.get("name", "未知")
        schedule = job.get("schedule", {}).get("expr", "未知")
        tasks.append(f"- {job_name}: {schedule}")
    
    return "\n".join(tasks)

def analyze_with_ai(sessions_content, target_date):
    """AI 分析生成日报"""
    import httpx
    
    api_config = get_api_config()
    if not api_config:
        return "Error: No API key found. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or MINIMAX_API_KEY"
    
    provider = api_config["provider"]
    api_key = api_config["key"]
    api_url = api_config["url"]
    model = api_config["model"]
    
    print(f"使用 API: {provider} | Model: {model}")
    
    # 提取 cron 信息
    cron_info = ""
    for marker in ["Cron任务执行记录", "Cron任务定义"]:
        if marker in sessions_content:
            idx = sessions_content.find(f"=== {marker} ===")
            end_idx = sessions_content.find("===", idx + 20)
            cron_info = "\n" + sessions_content[idx:end_idx if end_idx > 0 else len(sessions_content)][:2000]
            break
    
    prompt = f"""请分析以下 OpenClaw 对话记录和定时任务信息，生成工作日报。

**格式要求**：
- 主标题：# YYYY-MM-DD 工作日报
- 副标题使用中文数字：一、二、三、四、五
- 关键信息加粗
- 每项内容精简到1-5句话

**输出格式**：

# {target_date} 工作日报

### 一、定时任务执行记录
- 列出定时任务执行结果

### 二、代码编写
- 列出编写的代码

### 三、问题解决
- 列出解决的问题

### 四、待解决问题
- 列出待解决的问题

### 五、其他事项
- 列出其他重要事项

{cron_info}

对话记录：
{sessions_content[:25000]}
"""
    
    if provider == "minimax":
        return analyze_minimax(prompt, api_key, api_url, model)
    elif provider == "openai":
        return analyze_openai(prompt, api_key, api_url, model)
    elif provider == "anthropic":
        return analyze_anthropic(prompt, api_key, api_url, model)
    else:
        return f"Error: Unknown provider: {provider}"

def analyze_minimax(prompt, api_key, api_url, model):
    import httpx
    
    url = api_url + "/v1/text/chatcompletion_v2"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.7
    }
    
    try:
        resp = httpx.post(url, json=data, headers=headers, timeout=60)
        if resp.status_code == 200:
            result = resp.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                return content.strip()
        return f"API Error: {resp.status_code}"
    except Exception as e:
        return f"Error: {e}"

def analyze_openai(prompt, api_key, api_url, model):
    import httpx
    
    url = api_url + "/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Azure OpenAI
    if "azure" in api_url.lower():
        headers = {"api-key": api_key, "Content-Type": "application/json"}
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.7
    }
    
    try:
        resp = httpx.post(url, json=data, headers=headers, timeout=60)
        if resp.status_code == 200:
            result = resp.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                return content.strip()
        return f"API Error: {resp.status_code}"
    except Exception as e:
        return f"Error: {e}"

def analyze_anthropic(prompt, api_key, api_url, model):
    import httpx
    
    url = api_url + "/v1/messages"
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        resp = httpx.post(url, json=data, headers=headers, timeout=60)
        if resp.status_code == 200:
            result = resp.json()
            content = result.get("content", [{}])[0].get("text", "")
            if content:
                return content.strip()
        return f"API Error: {resp.status_code}"
    except Exception as e:
        return f"Error: {e}"

def save_report(content, date=None):
    """保存日报到文件"""
    if date is None:
        date = get_today_date()
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report_file = DATA_DIR / f"{date}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return report_file

def send_to_feishu(content):
    """发送到飞书"""
    if not ENABLE_FEISHU:
        print("飞书推送已禁用")
        return True
    
    try:
        cmd = [
            "openclaw", "message", "send",
            "--channel", "feishu",
            "--target", FEISHU_USER_ID,
            "--message", content[:2000]
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except Exception as e:
        print(f"飞书推送失败: {e}")
        return False

def push_to_git(target_date):
    """推送到 Git"""
    if not ENABLE_GIT:
        print("Git 推送已禁用")
        return True
    
    try:
        data_dir = DATA_DIR.parent
        
        subprocess.run(["git", "add", "."], cwd=data_dir, check=True, capture_output=True)
        result = subprocess.run(["git", "status", "--porcelain"], cwd=data_dir, capture_output=True, text=True)
        if not result.stdout.strip():
            print("没有变更需要推送")
            return True
        
        subprocess.run(["git", "commit", "-m", f"daily report: {target_date}"], cwd=data_dir, check=True, capture_output=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=data_dir, capture_output=True)
        subprocess.run(["git", "push"], cwd=data_dir, check=True, capture_output=True)
        
        print(f"已推送到 Git: {target_date}")
        return True
    except Exception as e:
        print(f"Git 推送失败: {e}")
        return False

def main():
    target_date = datetime.now().strftime("%Y-%m-%d")
    
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    
    print(f"生成 {target_date} 的工作日报...")
    print(f"飞书: {ENABLE_FEISHU} | Git: {ENABLE_GIT}")
    
    sessions_content = get_sessions_for_date(target_date)
    print(f"获取到 {len(sessions_content)} 字符")
    
    report = analyze_with_ai(sessions_content, target_date)
    
    report_file = save_report(report, target_date)
    print(f"日报已保存到: {report_file}")
    
    if ENABLE_FEISHU:
        send_to_feishu(report)
        print("日报已发送到飞书")
    
    if ENABLE_GIT:
        push_to_git(target_date)
        print("日报已推送到 Git")
    
    return report

if __name__ == "__main__":
    main()
