# TaskPool 任务池标准执行流程（oc-coze Agent）

> 统一SOP，每次严格按照此流程执行

---

## 标准流程

### 1. 更新分支
```bash
git checkout main
git pull origin main
git checkout -B oc-coze  # 创建/重置 oc-coze 分支
```

### 2. 查找任务
打开 `tasks/tasks.json`，筛选满足以下条件的任务：
- `status` == `"assigned"`
- `assignee` == `"oc-coze"`

**规则：**
- 只执行分配给 `oc-coze` 的任务，其他 Agent 的任务跳过不处理
- 如果没有找到，直接结束等待下次

### 3. 开始执行任务
对于每个找到的任务：
1. 修改任务状态为 `in_progress`
2. 添加历史记录：
   ```json
   {
     "action": "in_progress",
     "timestamp": "ISO时间",
     "operator": "oc-coze"
   }
   ```
3. 添加 `started_at` 字段为当前时间

### 4. 执行任务内容
1. 读取源文件 `tasks-md/{task-id}.md` 获取任务要求
2. 根据任务类型执行（写作/编码/调研）
3. 创建输出目录 `output/{task-id}/`
4. 写入结果文件：
   - `output/{task-id}/result.json`：结果元数据
   - `output/{task-id}/{output-file}`：实际产出文件

### 5. 提交结果
1. 修改任务状态为 `review`
2. 添加 `completed_at` 和 `output_path`
3. 添加历史记录：
   ```json
   {
     "action": "review",
     "timestamp": "ISO时间",
     "operator": "oc-coze",
     "output_path": "output/{task-id}"
   }
   ```

### 6. 推送分支
```bash
git add .
git commit -m "agent oc-coze: complete {task-id} - {task-title}"
git push -f origin oc-coze
```

### 7. 等待审核合并
Manager 审核后会合并到 main 分支，流程结束。

---

## 当前任务分配

| Task ID | Title | Assignee | Status |
|---------|-------|----------|--------|
| task-001 | 编写AI科普文章 | oc-kimi | review |
| task-002 | Python代码优化任务 | oc-ecs | assigned |
| task-003 | 市场调研报告 | oc-step | assigned |

**当前没有分配给 oc-coze 的任务，等待下一轮。**

---

## 本次记录
- 执行时间：2026-03-16
- 执行人：oc-coze (小巴)
- 说明：SOP 文档初始化，完成流程演练
