# Manager（任务分配者）操作手册

> 本手册供任务分配者（Manager）使用，指导如何管理任务仓库和分配任务。

---

## 1. 仓库结构

```
task-repo/
├── tasks-md/          # 任务源文件（MD格式）
│   ├── task-001-xxx.md
│   └── task-002-xxx.md
├── tasks/             # 任务清单
│   └── tasks.json    # 任务数据库
├── agents/            # Agent注册表
│   └── agents.json   # Agent数据库
└── output/           # 任务产出目录
    └── {task-id}/
        └── result.json
```

---

## 2. 任务管理流程

### 2.1 创建任务

**步骤：**

1. 在 `tasks-md/` 目录创建MD文件
2. 文件命名格式：`task-{编号}-{描述}.md`
3. 文件内容格式：

```markdown
# 任务标题 [标签1] [标签2]

## 任务描述

详细描述...

## 要求

1. 要求1
2. 要求2

## 输出

将结果保存为 `output/{task-id}/文件名`
```

### 2.2 同步任务到清单

**操作：** 将MD文件信息同步到 `tasks/tasks.json`

**步骤：**

1. 读取 `tasks-md/` 下所有MD文件
2. 解析每个文件的标题、标签、描述
3. 在 `tasks/tasks.json` 的 `tasks` 数组中添加新任务
4. 设置初始状态：`"status": "pending"`
5. 提交更改：`git commit -m "add: task-001"`

### 2.3 查看Agent列表

**操作：** 查看已注册的Agent

**文件：** `agents/agents.json`

```json
{
  "agents": [
    {
      "id": "oc-step",
      "capabilities": ["reasoning", "analysis"],
      "status": "idle"
    },
    {
      "id": "oc-kimi",
      "capabilities": ["writing", "reading"],
      "status": "idle"
    },
    {
      "id": "oc-ecs",
      "capabilities": ["coding", "devops"],
      "status": "idle"
    }
  ]
}
```

### 2.4 分配任务

**方式一：手动分配**

1. 打开 `tasks/tasks.json`
2. 找到目标任务，修改以下字段：
   - `"status": "assigned"`
   - `"assignee": "oc-kimi"`
   - `"assigned_at": "2026-03-16T10:00:00Z"`
3. 添加历史记录：
```json
{
  "action": "assigned",
  "timestamp": "2026-03-16T10:00:00Z",
  "operator": "manager",
  "target": "oc-kimi"
}
```
4. 提交：`git commit -m "assign: task-001 to oc-kimi"`

**方式二：自动分配**

| 策略 | 说明 |
|------|------|
| `round_robin` | 轮询分配给idle状态的Agent |
| `capability_match` | 根据任务标签匹配Agent能力 |
| `load_balance` | 分配给当前任务最少的Agent |

---

## 3. 任务状态

| 状态 | 说明 | 参与者 |
|------|------|--------|
| `pending` | 待分配 | Manager |
| `assigned` | 已分配给Agent | Agent |
| `in_progress` | Agent正在执行 | Agent |
| `review` | 待审核 | Manager |
| `completed` | 审核通过 | Manager |
| `failed` | 执行失败 | Agent |

---

## 4. 审核任务

Agent完成任务后，状态变为 `review`。

**审核步骤：**

1. 查看 `output/{task-id}/result.json`
2. 检查产出文件是否符合要求
3. 决定：
   - **通过**：状态改为 `completed`
   - **拒绝**：状态改为 `failed`，说明原因

---

## 5. Git操作命令

```bash
# 拉取最新
git pull

# 添加任务文件
git add tasks-md/
git commit -m "add: new task"

# 更新任务清单
git add tasks/tasks.json
git commit -m "sync: tasks"

# 分配任务
git add tasks/tasks.json
git commit -m "assign: task-001 to oc-kimi"

# 推送
git push
```

---

## 6. 完整示例

### Step 1: 创建任务

创建文件 `tasks-md/task-001-ai-article.md`

### Step 2: 同步任务

更新 `tasks/tasks.json`:

```json
{
  "id": "task-001",
  "title": "编写AI科普文章",
  "labels": ["writing", "high"],
  "status": "pending",
  "assignee": null,
  "source_file": "tasks-md/task-001-ai-article.md",
  "history": [
    {"action": "created", "timestamp": "2026-03-16T10:00:00Z", "operator": "manager"}
  ]
}
```

### Step 3: 分配任务

更新任务状态:

```json
{
  "status": "assigned",
  "assignee": "oc-kimi",
  "assigned_at": "2026-03-16T10:30:00Z",
  "history": [
    {"action": "created", "timestamp": "2026-03-16T10:00:00Z", "operator": "manager"},
    {"action": "assigned", "timestamp": "2026-03-16T10:30:00Z", "operator": "manager", "target": "oc-kimi"}
  ]
}
```

### Step 4: 推送

```bash
git add . && git commit -m "workflow: create and assign task-001" && git push
```
