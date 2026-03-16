# 工作流编排系统设计

## 系统概述

工作流编排系统用于管理和执行复杂的业务流程，将大任务拆解成多个子任务，定义依赖关系，自动调度执行。支持失败重试、超时处理、运行时监控。

## 核心概念

| 概念 | 说明 |
|------|------|
| **Workflow** | 一个完整的业务流程，由多个Task组成 |
| **Task** | 工作流中的一个执行步骤 |
| **DAG** | 有向无环图，描述任务之间的依赖关系 |
| **Dependency** | 任务依赖，只有依赖完成才能开始执行 |
| **Executor** | 任务执行器，负责实际运行任务 |
| **Scheduler** | 调度器，决定下一步该执行什么任务 |

## DAG 定义示例

定义一个简单的数据处理工作流：

```python
from workflow import DAG, Task

with DAG("data_processing_pipeline") as dag:
    task_download = Task("download_data", executor="http", url="...")
    task_parse = Task("parse_data", executor="python", script="parse.py")
    task_clean = Task("clean_data", executor="python", script="clean.py")
    task_analyze = Task("analyze", executor="spark", config="analyze.py")
    task_export = Task("export_result", executor="s3", path="s3://output/")
    
    # 定义依赖关系
    task_parse.set_upstream(task_download)  # 下载完才能解析
    task_clean.set_upstream(task_parse)
    task_analyze.set_upstream(task_clean)
    task_export.set_upstream([task_analyze])
    
    # 并行执行示例
    # task_a >> [task_b, task_c]  task_a完成后并行执行task_b和task_c
```

可视化：

```
download_data → parse_data → clean_data → analyze → export_result
```

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                  API 层                                    │
│  - 提交工作流 / 终止工作流 / 查询状态                         │
├─────────────────────────────────────────────────────────────┤
│              DAG 解析层                                    │
│  - 验证DAG合法性（检测环）                                   │
│  - 拓扑排序确定执行顺序                                     │
├─────────────────────────────────────────────────────────────┤
│              调度器 Scheduler                               │
│  - 扫描就绪任务（所有依赖已完成）                            │
│  - 发送到执行队列                                           │
├─────────────────────────────────────────────────────────────┤
│              执行器 Worker Pool                            │
│  - 取出任务执行                                            │
│  - 处理成功/失败                                           │
│  - 失败重试                                               │
│  - 超时中断                                               │
├─────────────────────────────────────────────────────────────┤
│              状态存储                                      │
│  - 工作流/任务状态持久化 (数据库)                            │
│  - 任务输出结果存储                                         │
├─────────────────────────────────────────────────────────────┤
│              监控日志                                      │
│  - 每个任务执行日志                                         │
│  - 工作流执行进度                                          │
└─────────────────────────────────────────────────────────────┘
```

## 依赖管理和并行执行

### 判断任务是否可执行

一个任务满足以下条件即可执行：
- 任务状态为 `pending`
- **所有**上游依赖任务都成功完成
- 没有被标记为失败

### 并行执行

多个任务如果没有互相依赖，可以同时并行执行，提高整体效率：

```
        A
       ↙ ↘
      B   C
       ↘ ↙
        D
```

B和C可以并行执行，都完成后才执行D。

## 失败处理机制

### 重试策略

每个任务可以配置独立的重试参数：

```python
task = Task(
    "process_data",
    max_retries=3,          # 最大重试次数
    retry_delay=60,        # 重试间隔（秒）
    retry_backoff=True,    # 是否指数退避
    timeout=300,          # 超时时间（秒）
)
```

### 失败策略

当一个任务失败且超过重试次数后，怎么办？

| 策略 | 说明 |
|------|------|
| `fail_fast` | 立刻失败整个工作流，停止所有后续任务 |
| `continue` | 继续执行其他不依赖它的任务 |
| `block` | 阻塞在这里，等待人工处理 |

## 状态机

工作流状态流转：

```
   ┌─────────┐
   │ pending│
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │running │
   └────┬────┘
        ├─────────────┐
        ▼             ▼
  ┌──────────┐  ┌──────────┐
  │success  │  │  failed  │
  └────┬─────┘  └────┬─────┘
       │             │
       │             ├───────────┐
       │             │ retry < max│
       │             ▼           │
       │         ┌─────────┐     │
       │         │retrying│─────┘
       │         └────┬─────┘
       │             │
       │             ▼
       │         ┌─────────┐
       │         │timeout  │
       │         └────┬─────┘
       │             │
       ▼             ▼
  ┌──────────┐
  │finished │
  └──────────┘
```

## 存储设计

### 工作流表

| 字段 | 类型 | 说明 |
|------|------|------|
| workflow_id | UUID | 工作流ID |
| name | string | 工作流名称 |
| status | enum | 状态 |
| created_at | timestamp | 创建时间 |
| started_at | timestamp | 开始时间 |
| finished_at | timestamp | 结束时间 |
| created_by | string | 创建人 |

### 任务表

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | UUID | 任务ID |
| workflow_id | UUID | 所属工作流 |
| name | string | 任务名称 |
| status | enum | 状态 |
| attempt | int | 当前重试次数 |
| max_retries | int | 最大重试次数 |
| started_at | timestamp | 开始时间 |
| finished_at | timestamp | 结束时间 |
| result | JSON | 任务输出结果 |
| error | string | 错误信息 |

## 调度实现（伪代码）

```python
class Scheduler:
    def schedule_once(self):
        """一次调度循环"""
        # 获取所有工作流中就绪的任务
        ready_tasks = self.find_ready_tasks()
        
        for task in ready_tasks:
            if self.worker_pool.acquire():
                self.worker_pool.submit(task)
            else:
                # 工作池满了，下次再试
                break
    
    def find_ready_tasks(self):
        """找到所有可以执行的任务"""
        ready = []
        for task in get_pending_tasks():
            if all(dep.status == SUCCESS for dep in task.upstream_deps):
                ready.append(task)
        return ready
```

## 支持多种执行器

| 执行器类型 | 用途 |
|------------|------|
| `python` | 执行本地Python函数 |
| `http` | 调用HTTP webhook |
| `docker` | 在Docker容器中执行 |
| `spark` | 提交Spark任务 |
| `kubernetes` | 提交K8s Job |

## 监控和可见性

### 必选监控指标

- 工作流总数 / 成功数 / 失败数
- 每个任务的平均执行时间
- 队列中等待的任务数
- 失败率
- 重试次数统计

### 日志

每个任务的：
- 标准输出和标准错误完整日志
- 开始/结束时间戳
- 入口参数
- 返回结果

### 可视化

可以在Web界面上看到：
- DAG图，每个节点当前颜色表示状态（绿色成功/黄色运行/红色失败）
- 时间线，显示每个任务什么时候开始什么时候结束
- 整个工作流的耗时分布

## 最佳实践

1. **任务幂等**：尽量保证任务是幂等的，重试不会产生副作用
2. **粒度合适**：不要太细（调度开销大）也不要太粗（失败影响大）
3. **及时持久化**：每一步状态都保存，系统重启后可以恢复
4. **超时必须中断**：卡住的任务要强行终止，释放资源
5. **可观测性**：日志和监控要完善，出问题能快速定位

---
设计由 oc-coze 于 2026-03-16 生成
