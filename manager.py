#!/usr/bin/env python3
"""
GitHub任务系统 - Manager脚本
用法: python manager.py sync --repo owner/repo
"""
import json
import os
import subprocess
import re
from datetime import datetime, timezone
from pathlib import Path

# ============ 配置 ============
REPO_URL = None  # GitHub仓库URL
REPO_PATH = "."  # 本地路径
AGENT_FILE = "agents/agents.json"
TASKS_FILE = "tasks/tasks.json"
TASKS_MD_DIR = "tasks-md"

# ============ 工具函数 ============
def run(cmd):
    """执行shell命令"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] {cmd}\n{result.stderr}")
    return result

def now():
    """当前时间ISO格式"""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

def load_json(path):
    """加载JSON文件"""
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    """保存JSON文件"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def git_push(msg):
    """推送更改"""
    print(f"[GIT] committing: {msg}")
    run("git add .")
    run(f'git commit -m "{msg}"')
    run("git push")

# ============ Manager功能 ============
def clone_or_pull(repo_url):
    """克隆或更新仓库"""
    repo_name = repo_url.split("/")[-1]
    
    if os.path.exists(repo_name):
        print(f"[INFO] 仓库已存在: {repo_name}")
        os.chdir(repo_name)
        run("git pull")
    else:
        print(f"[INFO] 克隆仓库: {repo_url}")
        run(f"git clone {repo_url}")
        os.chdir(repo_name)

def scan_md_files():
    """扫描tasks-md目录，生成任务清单"""
    print(f"[SCAN] 扫描 {TASKS_MD_DIR}/ 目录...")
    
    tasks = []
    md_files = sorted(Path(TASKS_MD_DIR).glob("*.md"))
    
    for md_file in md_files:
        # 从文件名提取task ID
        task_id = md_file.stem  # 例如 task-001-ai-article
        
        # 读取文件内容，提取标题和标签
        content = md_file.read_text(encoding='utf-8')
        
        # 提取标题 (第一个 # 开头的内容)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else task_id
        
        # 提取标签
        tags = []
        tag_match = re.search(r'tags:\s*\[([^\]]+)\]', content)
        if tag_match:
            tags = [t.strip() for t in tag_match.group(1).split(",")]
        
        # 提取任务类型
        task_type = "general"
        type_match = re.search(r'type:\s*(\w+)', content)
        if type_match:
            task_type = type_match.group(1)
        
        task = {
            "id": task_id,
            "title": title,
            "type": task_type,
            "tags": tags,
            "source_file": f"{TASKS_MD_DIR}/{md_file.name}",
            "status": "pending",
            "created_at": now()
        }
        
        tasks.append(task)
        print(f"  [NEW] {task_id}: {title} ({task_type})")
    
    return tasks

def sync_tasks():
    """同步任务：从MD文件生成tasks.json"""
    # 加载现有任务
    existing_data = load_json(TASKS_FILE)
    existing_tasks = {t["id"]: t for t in existing_data.get("tasks", [])} if existing_data else {}
    
    # 扫描新任务
    new_tasks = scan_md_files()
    
    # 合并：保留已存在的任务状态
    for task in new_tasks:
        task_id = task["id"]
        if task_id in existing_tasks:
            existing = existing_tasks[task_id]
            # 保留已有字段
            task["status"] = existing.get("status", "pending")
            task["assignee"] = existing.get("assignee")
            task["assigned_at"] = existing.get("assigned_at")
            task["history"] = existing.get("history", [])
    
    # 保存
    save_json(TASKS_FILE, {"tasks": new_tasks})
    print(f"[OK] 已同步 {len(new_tasks)} 个任务到 {TASKS_FILE}")

def list_agents():
    """列出所有注册的Agent"""
    data = load_json(AGENT_FILE)
    if not data:
        print(f"[ERROR] Agent文件不存在: {AGENT_FILE}")
        return
    
    agents = data.get("agents", [])
    print(f"[AGENTS] 共 {len(agents)} 个Agent:")
    
    for agent in agents:
        print(f"  - {agent['id']}: {agent.get('capabilities', [])}")

def list_tasks():
    """列出所有任务"""
    data = load_json(TASKS_FILE)
    if not data:
        print("[ERROR] 任务文件不存在")
        return
    
    tasks = data.get("tasks", [])
    print(f"[TASKS] 共 {len(tasks)} 个任务:")
    
    for task in tasks:
        status = task.get("status", "pending")
        assignee = task.get("assignee", "-")
        print(f"  - {task['id']}: {task['title']} [{status}] → {assignee}")

def assign_task(task_id, agent_id):
    """手动分配任务"""
    data = load_json(TASKS_FILE)
    if not data:
        print("[ERROR] 任务文件不存在")
        return
    
    # 查找任务
    task = None
    for t in data["tasks"]:
        if t["id"] == task_id:
            task = t
            break
    
    if not task:
        print(f"[ERROR] 任务 {task_id} 不存在")
        return
    
    # 检查Agent是否存在
    agents_data = load_json(AGENT_FILE)
    agent_exists = any(a["id"] == agent_id for a in agents_data.get("agents", []))
    if not agent_exists:
        print(f"[ERROR] Agent {agent_id} 不存在")
        return
    
    # 分配
    task["status"] = "assigned"
    task["assignee"] = agent_id
    task["assigned_at"] = now()
    task.setdefault("history", []).append({
        "action": "assigned",
        "timestamp": now(),
        "operator": "manager",
        "target": agent_id
    })
    
    save_json(TASKS_FILE, data)
    print(f"[OK] 任务 {task_id} 已分配给 {agent_id}")

def auto_assign(strategy="capability_match"):
    """自动分配任务"""
    data = load_json(TASKS_FILE)
    agents_data = load_json(AGENT_FILE)
    
    if not data or not agents_data:
        print("[ERROR] 任务或Agent文件不存在")
        return
    
    tasks = [t for t in data["tasks"] if t.get("status") == "pending"]
    agents = {a["id"]: a.get("capabilities", []) for a in agents_data.get("agents", [])}
    
    assigned_count = 0
    
    for task in tasks:
        task_id = task["id"]
        task_tags = task.get("tags", [])
        task_type = task.get("type", "")
        
        # 策略：能力匹配
        best_agent = None
        best_score = 0
        
        for agent_id, capabilities in agents.items():
            score = 0
            # 标签匹配
            for tag in task_tags:
                if tag in capabilities:
                    score += 1
            # 类型匹配
            if task_type in capabilities:
                score += 2
            
            if score > best_score:
                best_score = score
                best_agent = agent_id
        
        if best_agent:
            task["status"] = "assigned"
            task["assignee"] = best_agent
            task["assigned_at"] = now()
            task.setdefault("history", []).append({
                "action": "assigned",
                "timestamp": now(),
                "operator": "manager",
                "target": best_agent,
                "strategy": strategy
            })
            print(f"[AUTO] {task_id} → {best_agent} (score: {best_score})")
            assigned_count += 1
    
    save_json(TASKS_FILE, data)
    print(f"[OK] 自动分配完成，成功分配 {assigned_count} 个任务")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GitHub任务系统Manager")
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # sync命令
    sync_parser = subparsers.add_parser("sync", help="同步任务")
    sync_parser.add_argument("-r", "--repo", help="GitHub仓库URL")
    
    # list命令
    subparsers.add_parser("list", help="列出Agent")
    subparsers.add_parser("tasks", help="列出任务")
    
    # assign命令
    assign_parser = subparsers.add_parser("assign", help="分配任务")
    assign_parser.add_argument("--task", required=True, help="任务ID")
    assign_parser.add_argument("--agent", required=True, help="Agent ID")
    
    # auto命令
    auto_parser = subparsers.add_parser("auto", help="自动分配")
    auto_parser.add_argument("-s", "--strategy", default="capability_match", help="分配策略")
    
    # push命令
    subparsers.add_parser("push", help="推送更改")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 如果指定了repo，先克隆
    if args.command == "sync" and args.repo:
        clone_or_pull(args.repo)
    
    # 执行命令
    if args.command == "sync":
        sync_tasks()
    elif args.command == "list":
        list_agents()
    elif args.command == "tasks":
        list_tasks()
    elif args.command == "assign":
        assign_task(args.task, args.agent)
    elif args.command == "auto":
        auto_assign(args.strategy)
    elif args.command == "push":
        git_push("manager: update tasks")

if __name__ == "__main__":
    main()
