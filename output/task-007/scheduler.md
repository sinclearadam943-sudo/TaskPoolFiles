# 分布式定时任务调度器设计

## 架构设计

分布式定时任务调度器，避免单点问题，支持水平扩展：

```
┌──────────┐   ┌──────────┐   ┌──────────┐
│  Worker  │   │  Worker  │   │  Worker  │
└─────┬─────┘   └─────┬─────┘   └─────┬─────┘
      │              │              │
      └──────────────┴──────────────┘
                     │
              ┌──────▼──────┐
              │   分布式锁   │  (Redis/MySQL)
              │  任务抢锁   │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │  元数据存储  │  (任务配置、执行记录)
              └─────────────┘
```

## 核心功能

### 1. Cron 表达式支持

支持标准Cron语法：
```
*    *    *    *    *
┬ ┬ ┬ ┬ ┬ ┬ ┬ ┬ ┬ ┬
│ │ │ │ │ │ │ │ │ │
│ │ │ │ │ │ │ │ │ │
│ │ │ │ │ │ │ │ │ │
│ │ │ │ │ │ │ │ │ └───── 星期 (0 - 6) (周日到周六)
│ │ │ │ │ │ │ │ └────────── 月份 (1 - 12)
│ │ │ │ │ │ │ └─────────────── 日期 (1 - 31)
│ │ │ │ │ └──────────────────────── 小时 (0 - 23)
│ │ │ │ └───────────────────────────── 分钟 (0 - 59)
│ │ │ └───────────────────────────────── 秒 (可选，0 - 59)
│ │ └────────────────────────────────────── 年份 (1970 - 2099)
│ └────────────────────────────────────────── 特殊字符: * , - /
```

Python实现参考 `croniter` 库。

### 2. 任务分片和负载均衡

**分片策略**：
- 按任务ID哈希分片
- N个worker，每个worker只负责 `task_id % N == worker_index` 的任务
- 新增/减少worker时自动重新分片

**避免重复执行**：
每次执行前需要抢分布式锁，抢到锁的worker才能执行：

```python
def try_acquire_lock(task_id: str, execution_time: int) -> bool:
    """尝试获取锁"""
    key = f"scheduler_lock:{task_id}:{execution_time}"
    # SETNX 只有不存在才能成功
    return redis.set(key, "locked", nx=True, ex=60)
```

### 3. 动态添加和移除任务

任务配置存在数据库中，调度器定期拉取最新配置：

```python
# 后台线程定期同步
def sync_config_loop():
    while running:
        new_tasks = db.load_all_tasks()
        update_local_cache(new_tasks)
        time.sleep(10)  # 每10秒同步一次，支持动态变更
```

- 添加任务：写入数据库，10秒内被调度器发现
- 删除任务：标记为删除，下次同步后不再调度
- 修改任务：更新配置，下次生效

### 4. 执行状态跟踪

每条任务执行都记录：

| 字段 | 说明 |
|------|------|
| task_id | 任务ID |
| scheduled_time | 计划执行时间 |
| actual_start_time | 实际开始时间 |
| actual_end_time | 实际结束时间 |
| status | 状态 (success/failed/timeout) |
| result | 返回结果/错误信息 |
| worker_addr | 执行的worker地址 |

### 5. 超时处理

每个任务设置超时时间，超时后强制终止：

```python
def run_with_timeout(task, timeout):
    """带超时运行任务"""
    result = queue.get()
    thread = Thread(target=do_run, args=(task, queue))
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        # 超时了
        return Result(status="timeout")
    return result
```

## Python核心代码实现

请看 `scheduler.py`。

## 最佳实践

1. **幂等性**：定时任务一定要幂等，重复执行不会出问题
2. **错开时间**：避免大量任务同时在整点执行，分散压力
3. **监控告警**：任务失败要及时告警
4. **日志完整**：记录每个任务谁执行的、什么时候开始、结果是什么
5. **错过任务补发**：worker宕机重启后，检查有没有漏掉没执行的任务，补上

---
设计由 oc-coze 于 2026-03-16 生成
