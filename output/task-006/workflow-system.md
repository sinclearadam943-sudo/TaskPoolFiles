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
│              DAG 解析层                                   │
│  - 验证DAG合法性（检测环）                                   │
│  - 拓扑排序确定执行顺序                                     │
├─────────────────────────────────────────────────────────────┤
│              调度器 Scheduler                              │
│  - 扫描就绪任务（所有依赖已完成）                            │
│  - 发送到执行队列                                           │
├─────────────────────────────────────────────────────────────┤
│              执行器 Worker Pool                             │
│  - 取出任务执行                                            │
│  - 处理成功/失败                                           │
│  - 失败重试                                               │
│  - 超时中断                                               │
├─────────────────────────────────────────────────────────────┤
│              状态存储                                       │
│  - 工作流/任务状态持久化 (数据库)                            │
│  - 任务输出结果存储                                         │
├─────────────────────────────────────────────────────────────┤
│              监控日志                                       │
│  - 每个任务执行日志                                         │
│  - 工作流执行进度                                          │
└─────────────────────────────────────────────────────────────┘
```

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

## 支持多种执行器

| 执行器类型 | 用途 |
|------------|------|
| `python` | 执行本地Python函数 |
| `http` | 调用HTTP webhook |
| `docker` | 在Docker容器中执行 |
| `spark` | 提交Spark任务 |
| `kubernetes` | 提交K8s Job |

---
设计由 oc-coze 于 2026-03-16 生成
