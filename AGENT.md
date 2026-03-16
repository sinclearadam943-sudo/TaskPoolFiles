# Agent（任务执行者）操作手册

> 本手册供Agent（OC - Operation Agent）使用，指导如何拉取任务、执行任务、提交结果。

---

## 1. Agent身份

每个Agent有唯一ID，例如：
- `oc-step` - 推理Agent
- `oc-kimi` - 写作Agent
- `oc-ecs` - 编码Agent
- `oc-coze` - 自动化Agent
- `oc-qclaw` - 法务Agent

你的ID是：**请在运行时指定**

---

## 2. 工作流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ 1.拉取最新  │ ──→ │ 2.查找任务  │ ──→ │ 3.开始执行  │
│  (git pull) │     │ (assigned)  │     │(in_progress)│
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                    ┌─────────────┐              │ submit
                    │ 6.推送结果  │              ▼
                    │ (git push)  │       ┌─────────────┐
                    └─────────────┘       │ 4.提交结果  │
                         ↑                │  (review)   │
                         │                └─────────────┘
                    push
```

---

## 3. 操作步骤

### Step 1: 拉取最新代码

```bash
git pull
```

### Step 2: 查找分配给自己的任务

**文件：** `tasks/tasks.json`

查找满足以下条件的任务：
- `assignee` 等于你的Agent ID
- `status` 等于 `"assigned"`

示例：

```json
{
  "tasks": [
    {
      "id": "task-001",
      "title": "编写AI科普文章",
      "status": "assigned",
      "assignee": "oc-kimi",
      "source_file": "tasks-md/task-001-ai-article.md"
    }
  ]
}
```

### Step 3: 开始执行

**操作：修改任务状态为 `in_progress`**

1. 打开 `tasks/tasks.json`
2. 找到对应任务，修改：
   ```json
   {
     "status": "in_progress",
     "started_at": "2026-03-16T10:35:00Z"
   }
   ```
3. 添加历史：
   ```json
   {
     "action": "in_progress",
     "timestamp": "2026-03-16T10:35:00Z",
     "operator": "oc-kimi"
   }
   ```

### Step 4: 执行任务

1. 读取源文件：`tasks-md/task-001-ai-article.md`
2. 根据任务要求执行
3. 准备产出文件

### Step 5: 提交结果

**操作：**

1. **创建输出目录**
   ```
   output/{task-id}/
   ```

2. **写入结果文件**

   文件1: `output/{task-id}/result.json`
   ```json
   {
     "task_id": "task-001",
     "status": "success",
     "executed_by": "oc-kimi",
     "executed_at": "2026-03-16T10:40:00Z",
     "summary": "任务已完成",
     "output_files": ["article.md"]
   }
   ```

   文件2: `output/{task-id}/article.md` (实际产出)

3. **更新任务状态为 `review`**
   ```json
   {
     "status": "review",
     "completed_at": "2026-03-16T10:40:00Z",
     "output_path": "output/task-001",
     "result": {...}
   }
   ```

### Step 6: 推送更改

```bash
git add .
git commit -m "agent oc-kimi: complete task-001"
git push
```

---

## 4. 状态流转规则

| 当前状态 | 下一状态 | 操作 |
|----------|----------|------|
| `assigned` | `in_progress` | Agent开始执行 |
| `in_progress` | `review` | Agent提交结果 |
| `review` | `completed` | Manager审核通过 |
| `review` | `failed` | Manager审核拒绝 |

---

## 5. 定时任务（循环模式）

如需持续监听任务，可以循环执行：

```
while true:
    git pull
    查找 assigned 且 assignee=自己的任务
    如果有新任务，执行任务
    等待60秒
```

---

## 6. 完整示例

假设你是 `oc-kimi`，任务 `task-001` 已分配给你。

### 1. 拉取最新

```bash
git pull
```

### 2. 查找任务

在 `tasks/tasks.json` 找到：

```json
{
  "id": "task-001",
  "title": "编写AI科普文章",
  "status": "assigned",
  "assignee": "oc-kimi",
  "source_file": "tasks-md/task-001-ai-article.md"
}
```

### 3. 开始执行

修改状态为 `in_progress`：

```json
{
  "status": "in_progress",
  "started_at": "2026-03-16T10:35:00Z",
  "history": [
    {"action": "created", "timestamp": "2026-03-16T10:00:00Z", "operator": "manager"},
    {"action": "assigned", "timestamp": "2026-03-16T10:30:00Z", "operator": "manager", "target": "oc-kimi"},
    {"action": "in_progress", "timestamp": "2026-03-16T10:35:00Z", "operator": "oc-kimi"}
  ]
}
```

### 4. 执行任务

读取 `tasks-md/task-001-ai-article.md`，撰写文章

### 5. 提交结果

创建 `output/task-001/article.md`

写入 `output/task-001/result.json`：

```json
{
  "task_id": "task-001",
  "status": "success",
  "executed_by": "oc-kimi",
  "executed_at": "2026-03-16T10:40:00Z",
  "summary": "已撰写AI科普文章，约900字，包含3个案例"
}
```

修改状态为 `review`：

```json
{
  "status": "review",
  "completed_at": "2026-03-16T10:40:00Z",
  "output_path": "output/task-001"
}
```

### 6. 推送

```bash
git add .
git commit -m "agent oc-kimi: complete task-001"
git push
```

---

## 7. 错误处理

| 错误 | 处理 |
|------|------|
| 没有找到分配给我的任务 | 等待后重新拉取 |
| 任务状态不是assigned | 跳过，可能已被其他Agent处理 |
| Git冲突 | 先 `git pull` 解决冲突 |

---

## 8. 注意事项

1. **每次执行前先 `git pull`** - 确保获取最新任务
2. **原子性操作** - 修改JSON和创建output文件要在一次commit中完成
3. **状态准确** - 确保状态流转正确，否则流程会混乱
4. **提交信息清晰** - 使用格式：`agent {ID}: {动作} {task-id}`

---

## 9. 范例代码

以下是Python实现的任务执行脚本，可直接使用：

```python
#!/usr/bin/env python3
"""
GitHub任务系统 - Agent执行脚本
用法: python agent.py --id oc-kimi --mode once
"""
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

# ============ 配置 ============
REPO_PATH = "."  # 本地仓库路径
AGENT_ID = None  # 通过 --id 参数指定
INTERVAL = 60    # 循环模式间隔(秒)

TASKS_FILE = "tasks/tasks.json"
OUTPUT_DIR = "output"

# ============ 工具函数 ============
def run(cmd):
    """执行shell命令"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] {cmd}\n{result.stderr}")
    return result

def git_pull():
    """拉取最新代码"""
    print("[GIT] pulling...")
    run("git pull")
    run("git fetch --all")

def git_push(msg):
    """推送更改"""
    print(f"[GIT] committing: {msg}")
    run("git add .")
    run(f'git commit -m "{msg}"')
    run("git push")

def load_json(path):
    """加载JSON文件"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    """保存JSON文件"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def now():
    """当前时间ISO格式"""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

# ============ 核心逻辑 ============
def find_my_tasks(agent_id):
    """查找分配给自己的任务"""
    if not os.path.exists(TASKS_FILE):
        return []
    
    data = load_json(TASKS_FILE)
    tasks = data.get("tasks", [])
    
    # 过滤: status=assigned 且 assignee=自己
    my_tasks = [
        t for t in tasks 
        if t.get("status") == "assigned" and t.get("assignee") == agent_id
    ]
    
    print(f"[TASK] 发现 {len(my_tasks)} 个任务分配给 {agent_id}")
    return my_tasks

def update_task_status(task_id, new_status, extra=None):
    """更新任务状态"""
    data = load_json(TASKS_FILE)
    
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["status"] = new_status
            task.setdefault("history", [])
            
            # 添加历史记录
            history_entry = {
                "action": new_status,
                "timestamp": now(),
                "operator": AGENT_ID
            }
            if extra:
                history_entry.update(extra)
            task["history"].append(history_entry)
            
            if new_status == "in_progress":
                task["started_at"] = now()
            elif new_status == "review":
                task["completed_at"] = now()
            
            break
    
    save_json(TASKS_FILE, data)

def read_task_source(source_file):
    """读取任务源文件"""
    if os.path.exists(source_file):
        with open(source_file, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def execute_task_logic(task):
    """
    执行任务的核心逻辑
    根据任务类型调用不同的处理函数
    """
    task_id = task["id"]
    task_type = task.get("type", "general")
    source_file = task.get("source_file", f"tasks-md/{task_id}.md")
    
    # 读取源文件内容
    content = read_task_source(source_file)
    print(f"[EXEC] 读取源文件: {source_file}")
    
    # 创建输出目录
    output_path = Path(OUTPUT_DIR) / task_id
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 根据任务类型执行
    result_summary = ""
    
    if task_type == "writing" or "writing" in task.get("tags", []):
        # 写作任务
        result_summary = execute_writing_task(task, content, output_path)
    
    elif task_type == "coding" or "coding" in task.get("tags", []):
        # 编码任务
        result_summary = execute_coding_task(task, content, output_path)
    
    elif task_type == "research" or "research" in task.get("tags", []):
        # 调研任务
        result_summary = execute_research_task(task, content, output_path)
    
    else:
        # 默认处理
        result_summary = f"任务 {task_id} 已完成处理"
        (output_path / "result.txt").write_text(content or "无内容", encoding='utf-8')
    
    return result_summary

def execute_writing_task(task, content, output_path):
    """执行写作任务"""
    print("[EXEC] 执行写作任务...")
    # TODO: 在这里调用实际的AI写作接口
    # 例如: article = call_ai_write(content)
    
    # 模拟产出
    article_content = f"""# {task.get('title', '文章')}

{content or '文章内容...'}

---
本文由 {AGENT_ID} 于 {now()} 生成
"""
    (output_path / "article.md").write_text(article_content, encoding='utf-8')
    return "写作任务已完成"

def execute_coding_task(task, content, output_path):
    """执行编码任务"""
    print("[EXEC] 执行编码任务...")
    # TODO: 在这里调用实际的AI编码接口
    # 例如: code = call_ai_code(content)
    
    # 模拟产出
    code_content = f"""# {task.get('title', '代码')}

# 原始需求:
# {content or '无'}

# 生成的代码:
def solution():
    # TODO: 实现逻辑
    pass

if __name__ == "__main__":
    solution()

---
代码由 {AGENT_ID} 于 {now()} 生成
"""
    (output_path / "code.py").write_text(code_content, encoding='utf-8')
    return "编码任务已完成"

def execute_research_task(task, content, output_path):
    """执行调研任务"""
    print("[EXEC] 执行调研任务...")
    # TODO: 在这里调用实际的AI调研接口
    # 例如: report = call_ai_research(content)
    
    # 模拟产出
    report_content = f"""# {task.get('title', '调研报告')}

## 调研内容

{content or '调研主题...'}

## 结论

1. 关键发现A
2. 关键发现B
3. 关键发现C

---
报告由 {AGENT_ID} 于 {now()} 生成
"""
    (output_path / "report.md").write_text(report_content, encoding='utf-8')
    return "调研任务已完成"

def submit_result(task_id, summary):
    """提交任务结果"""
    output_path = Path(OUTPUT_DIR) / task_id
    
    # 写入结果JSON
    result_json = {
        "task_id": task_id,
        "status": "success",
        "executed_by": AGENT_ID,
        "executed_at": now(),
        "summary": summary,
        "output_files": [f.name for f in output_path.glob("*")]
    }
    
    (output_path / "result.json").write_text(
        json.dumps(result_json, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    
    # 更新任务状态为 review
    update_task_status(task_id, "review", {"output_path": str(output_path)})
    
    print(f"[OK] 任务 {task_id} 已提交，结果在 output/{task_id}/")

def run_one_cycle():
    """执行一轮任务检查和执行"""
    git_pull()
    tasks = find_my_tasks(AGENT_ID)
    
    if not tasks:
        print(f"[IDLE] 没有分配给 {AGENT_ID} 的任务")
        return
    
    for task in tasks:
        task_id = task["id"]
        print(f"[EXEC] 开始执行任务: {task_id}")
        
        # 1. 状态: assigned → in_progress
        update_task_status(task_id, "in_progress")
        
        # 2. 执行任务
        try:
            summary = execute_task_logic(task)
        except Exception as e:
            print(f"[ERROR] 执行任务失败: {e}")
            summary = f"执行失败: {e}"
        
        # 3. 提交结果
        submit_result(task_id, summary)
        
        # 4. 推送
        git_push(f"agent {AGENT_ID}: complete {task_id}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GitHub任务系统Agent")
    parser.add_argument("--id", required=True, help="Agent ID")
    parser.add_argument("--mode", choices=["once", "loop"], default="once", help="运行模式")
    parser.add_argument("--interval", type=int, default=60, help="循环间隔(秒)")
    args = parser.parse_args()
    
    global AGENT_ID, INTERVAL
    AGENT_ID = args.id
    INTERVAL = args.interval
    
    print(f"[START] Agent {AGENT_ID} 启动，模式: {args.mode}")
    
    if args.mode == "once":
        run_one_cycle()
    else:
        while True:
            run_one_cycle()
            print(f"[WAIT] 等待 {INTERVAL} 秒后再次检查...")
            time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
```

### 使用方法

```bash
# 单次执行
python agent.py --id oc-kimi --mode once

# 循环模式（每60秒检查一次）
python agent.py --id oc-kimi --mode loop --interval 60

# 指定任务执行
python agent.py --id oc-kimi --task task-001 --mode once
```

### 核心流程图

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent 执行流程                           │
├─────────────────────────────────────────────────────────────┤
│  1. git pull                                                │
│         ↓                                                   │
│  2. 读取 tasks/tasks.json                                  │
│         ↓                                                   │
│  3. 筛选: status=assigned AND assignee=自己的ID            │
│         ↓                                                   │
│  4. for each task:                                         │
│      ├─ 状态 → in_progress                                  │
│      ├─ 读取 tasks-md/{id}.md                              │
│      ├─ execute_task_logic() # 根据类型执行                 │
│      ├─ 创建 output/{id}/                                   │
│      ├─ 写入 result.json                                    │
│      ├─ 状态 → review                                       │
│      └─ git push                                            │
└─────────────────────────────────────────────────────────────┘
```
