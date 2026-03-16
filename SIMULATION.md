# GitHub任务协作系统 - 模拟运行演示

> 本文模拟5个OC（oc-step, oc-kimi, oc-ecs, oc-coze, oc-qclaw）在GitHub任务管理系统中协作完成任务的全过程。

---

## 系统参与者

| 角色 | ID | 能力 | 说明 |
|------|-----|------|------|
| Manager | - | 任务管理 | 负责创建和分配任务 |
| Agent 1 | `oc-step` | reasoning, analysis, math | 推理专家 |
| Agent 2 | `oc-kimi` | writing, reading, summary | 写作专家 |
| Agent 3 | `oc-ecs` | coding, devops, cloud | 编码专家 |
| Agent 4 | `oc-coze` | workflow, automation, integration | 自动化专家 |
| Agent 5 | `oc-qclaw` | legal, compliance, review | 法务专家 |

---

## 初始状态

### 仓库文件

```
task-repo/
├── tasks-md/          # 任务源文件
│   ├── task-001-ai-article.md
│   ├── task-002-python-optimize.md
│   └── task-003-research-report.md
├── tasks/
│   └── tasks.json    # 空任务清单
├── agents/
│   └── agents.json   # 5个Agent已注册
└── output/           # 空
```

---

## 流程一：Manager同步任务

### Step 1: Manager拉取仓库

```bash
git pull
```

### Step 2: Manager扫描MD文件

读取 `tasks-md/` 下的3个MD文件，解析任务信息：

| 文件 | 标题 | 标签 |
|------|------|------|
| task-001-ai-article.md | 编写AI科普文章 | [writing], [high] |
| task-002-python-optimize.md | Python代码优化 | [coding], [medium] |
| task-003-research-report.md | 市场调研报告 | [research], [normal] |

### Step 3: Manager更新任务清单

更新 `tasks/tasks.json`：

```json
{
  "version": "1.0",
  "updated_at": "2026-03-16T10:05:00Z",
  "tasks": [
    {
      "id": "task-001",
      "title": "编写AI科普文章",
      "labels": ["writing", "high"],
      "status": "pending",
      "assignee": null,
      "source_file": "tasks-md/task-001-ai-article.md",
      "created_at": "2026-03-16T10:00:00Z",
      "history": [
        {"action": "created", "timestamp": "2026-03-16T10:00:00Z", "operator": "manager"}
      ]
    },
    {
      "id": "task-002",
      "title": "Python代码优化任务",
      "labels": ["coding", "medium"],
      "status": "pending",
      "assignee": null,
      "source_file": "tasks-md/task-002-python-optimize.md",
      "created_at": "2026-03-16T10:00:00Z",
      "history": [
        {"action": "created", "timestamp": "2026-03-16T10:00:00Z", "operator": "manager"}
      ]
    },
    {
      "id": "task-003",
      "title": "市场调研报告",
      "labels": ["research", "normal"],
      "status": "pending",
      "assignee": null,
      "source_file": "tasks-md/task-003-research-report.md",
      "created_at": "2026-03-16T10:00:00Z",
      "history": [
        {"action": "created", "timestamp": "2026-03-16T10:00:00Z", "operator": "manager"}
      ]
    }
  ]
}
```

### Step 4: Manager提交

```bash
git add tasks/tasks.json
git commit -m "sync: 3 tasks from md files"
git push
```

---

## 流程二：Manager分配任务

### 分配策略：能力匹配

- task-001 (writing) → oc-kimi
- task-002 (coding) → oc-ecs
- task-003 (research) → oc-step

### 更新tasks.json

**task-001 分配给 oc-kimi:**

```json
{
  "id": "task-001",
  "status": "assigned",
  "assignee": "oc-kimi",
  "assigned_at": "2026-03-16T10:10:00Z",
  "history": [
    {"action": "created", "timestamp": "2026-03-16T10:00:00Z", "operator": "manager"},
    {"action": "assigned", "timestamp": "2026-03-16T10:10:00Z", "operator": "manager", "target": "oc-kimi"}
  ]
}
```

**task-002 分配给 oc-ecs:**

```json
{
  "id": "task-002",
  "status": "assigned",
  "assignee": "oc-ecs",
  "assigned_at": "2026-03-16T10:10:00Z",
  "history": [
    {"action": "created", "timestamp": "2026-03-16T10:00:00Z", "operator": "manager"},
    {"action": "assigned", "timestamp": "2026-03-16T10:10:00Z", "operator": "manager", "target": "oc-ecs"}
  ]
}
```

**task-003 分配给 oc-step:**

```json
{
  "id": "task-003",
  "status": "assigned",
  "assignee": "oc-step",
  "assigned_at": "2026-03-16T10:10:00Z",
  "history": [
    {"action": "created", "timestamp": "2026-03-16T10:00:00Z", "operator": "manager"},
    {"action": "assigned", "timestamp": "2026-03-16T10:10:00Z", "operator": "manager", "target": "oc-step"}
  ]
}
```

### 提交

```bash
git add tasks/tasks.json
git commit -m "assign: tasks to agents (capability match)"
git push
```

---

## 流程三：Agent执行任务

### ===== oc-kimi 执行 task-001 =====

**1. 拉取最新**

```bash
git pull
```

**2. 查找任务**

在 `tasks/tasks.json` 找到 task-001，状态为 `assigned`，assignee 为 `oc-kimi`

**3. 开始执行**

修改状态为 `in_progress`：

```json
{
  "id": "task-001",
  "status": "in_progress",
  "started_at": "2026-03-16T10:15:00Z",
  "history": [
    {"action": "created", "timestamp": "2026-03-16T10:00:00Z", "operator": "manager"},
    {"action": "assigned", "timestamp": "2026-03-16T10:10:00Z", "operator": "manager", "target": "oc-kimi"},
    {"action": "in_progress", "timestamp": "2026-03-16T10:15:00Z", "operator": "oc-kimi"}
  ]
}
```

**4. 执行任务**

读取 `tasks-md/task-001-ai-article.md`，撰写AI科普文章

**5. 提交结果**

创建输出文件：

`output/task-001/result.json`:
```json
{
  "task_id": "task-001",
  "status": "success",
  "executed_by": "oc-kimi",
  "executed_at": "2026-03-16T10:25:00Z",
  "summary": "已撰写AI科普文章，约900字，包含3个实际应用案例",
  "output_files": ["article.md"]
}
```

`output/task-001/article.md`:
```markdown
# 人工智能入门指南

## 引言
人工智能（AI）正在改变我们的生活方式...

## 实际应用案例
1. 智能语音助手
2. 自动驾驶
3. 医疗诊断

## 结论
AI未来发展潜力巨大...
```

修改状态为 `review`：

```json
{
  "id": "task-001",
  "status": "review",
  "completed_at": "2026-03-16T10:25:00Z",
  "output_path": "output/task-001",
  "result": {...}
}
```

**6. 推送**

```bash
git add .
git commit -m "agent oc-kimi: complete task-001"
git push
```

---

### ===== oc-ecs 执行 task-002 =====

**1. 拉取最新**

```bash
git pull
```

**2. 查找任务**

找到 task-002，assignee 为 `oc-ecs`

**3. 开始执行**

修改状态为 `in_progress`

**4. 执行任务**

读取 `tasks-md/task-002-python-optimize.md`，优化代码

**5. 提交结果**

创建 `output/task-002/fibonacci.py`:

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def fibonacci(n):
    """使用迭代和缓存优化"""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b

if __name__ == "__main__":
    for i in range(100):
        print(f"fib({i}) = {fibonacci(i)}")
```

创建 `output/task-002/result.json`

修改状态为 `review`

**6. 推送**

```bash
git add .
git commit -m "agent oc-ecs: complete task-002"
git push
```

---

### ===== oc-step 执行 task-003 =====

**1. 拉取最新**

```bash
git pull
```

**2. 查找任务**

找到 task-003，assignee 为 `oc-step`

**3. 开始执行**

修改状态为 `in_progress`

**4. 执行任务**

读取 `tasks-md/task-003-research-report.md`，撰写调研报告

**5. 提交结果**

创建 `output/task-003/report.md`:

```markdown
# 2026年AI助手市场调研报告

## 主流产品分析

### 1. GPT系列
- 优势：生态完善，插件丰富
- 劣势：成本较高

### 2. Claude
- 优势：长文本处理能力强
- 劣势：生态较新

### 3. Gemini
- 优势：多模态能力强
- 劣势：区域限制

## 未来趋势
1. AI Agent普及
2. 多模态交互
3. 个性化定制
```

创建 `output/task-003/result.json`

修改状态为 `review`

**6. 推送**

```bash
git add .
git commit -m "agent oc-step: complete task-003"
git push
```

---

## 流程四：Manager审核

### 拉取所有Agent的提交

```bash
git pull
```

### 检查任务状态

所有任务状态已变为 `review`

### 审核通过

更新 tasks.json，状态改为 `completed`：

```json
{
  "id": "task-001",
  "status": "completed",
  "history": [
    ...,
    {"action": "completed", "timestamp": "2026-03-16T10:30:00Z", "operator": "manager"}
  ]
}
```

### 提交

```bash
git add tasks/tasks.json
git commit -m "approve: all tasks completed"
git push
```

---

## 最终状态

### tasks/tasks.json

```json
{
  "tasks": [
    {
      "id": "task-001",
      "status": "completed",
      "assignee": "oc-kimi",
      "completed_at": "2026-03-16T10:30:00Z"
    },
    {
      "id": "task-002", 
      "status": "completed",
      "assignee": "oc-ecs",
      "completed_at": "2026-03-16T10:28:00Z"
    },
    {
      "id": "task-003",
      "status": "completed", 
      "assignee": "oc-step",
      "completed_at": "2026-03-16T10:26:00Z"
    }
  ]
}
```

### output目录结构

```
output/
├── task-001/
│   ├── result.json
│   └── article.md
├── task-002/
│   ├── result.json
│   └── fibonacci.py
└── task-003/
    ├── result.json
    └── report.md
```

---

## 完整流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub 仓库                               │
│  tasks/tasks.json  │  agents/agents.json  │  output/           │
└─────────────────────────────────────────────────────────────────┘
        ▲                  ▲                       ▲
        │                  │                       │
    Manager            Agent                   Agent
        │                  │                       │
    1. sync           1. pull                 1. pull
    2. assign          2. find my task         2. find my task
       │               3. in_progress            │
       │               4. execute                  │
       ▼               5. submit result ▼       6. review
   assigned              │                    │
                          │               Manager
                          ▼                  │
                      review  ──────────→ completed
```

---

**运行时间线：**

| 时间 | 操作者 | 操作 |
|------|--------|------|
| 10:00 | Manager | 创建任务 |
| 10:05 | Manager | 同步到tasks.json |
| 10:10 | Manager | 分配任务 |
| 10:15 | oc-kimi | 开始task-001 |
| 10:16 | oc-ecs | 开始task-002 |
| 10:17 | oc-step | 开始task-003 |
| 10:25 | oc-kimi | 完成task-001 |
| 10:26 | oc-step | 完成task-003 |
| 10:28 | oc-ecs | 完成task-002 |
| 10:30 | Manager | 审核通过 |
