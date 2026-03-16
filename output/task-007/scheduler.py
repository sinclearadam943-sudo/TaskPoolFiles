#!/usr/bin/env python3
"""
分布式定时任务调度器核心实现
"""

import time
import hashlib
import threading
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Callable, Dict, Optional

import croniter
import redis

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class ScheduledTask:
    task_id: str
    cron_expr: str
    handler: Callable
    timeout_seconds: int = 60
    enabled: bool = True
    max_retries: int = 3
    metadata: Dict = field(default_factory=dict)

@dataclass
class TaskExecution:
    task_id: str
    scheduled_time: int
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    status: TaskStatus = TaskStatus.PENDING
    worker: str = ""
    error: Optional[str] = None
    result: Optional[str] = None

class DistributedScheduler:
    def __init__(
        self,
        redis_url: str,
        worker_id: str,
        worker_index: int,
        total_workers: int,
        sync_interval: int = 10,
    ):
        self.redis = redis.from_url(redis_url)
        self.worker_id = worker_id
        self.worker_index = worker_index
        self.total_workers = total_workers
        self.sync_interval = sync_interval
        
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self._sync_thread: Optional[threading.Thread] = None
        self._scheduler_thread: Optional[threading.Thread] = None
    
    def get_task_shard(self, task_id: str) -> int:
        """计算任务属于哪个分片"""
        h = int(hashlib.md5(task_id.encode()).hexdigest(), 16)
        return h % self.total_workers
    
    def is_my_task(self, task_id: str) -> bool:
        """判断这个任务是否该我执行"""
        shard = self.get_task_shard(task_id)
        return shard == self.worker_index
    
    def try_acquire_lock(self, task_id: str, scheduled_ts: int) -> bool:
        """尝试获取分布式锁，防止重复执行"""
        lock_key = f"scheduler:lock:{task_id}:{scheduled_ts}"
        # 锁过期时间 60秒，防止死锁
        return self.redis.set(lock_key, self.worker_id, nx=True, ex=60)
    
    def get_next_run_time(self, cron_expr: str, after_time: datetime) -> datetime:
        """计算下一次执行时间"""
        cron = croniter.croniter(cron_expr, after_time)
        return cron.get_next(datetime)
    
    def sync_tasks_from_db(self):
        """从数据库同步最新任务配置"""
        # 这里替换成你实际的数据库查询
        # new_tasks = db.query("SELECT * FROM scheduled_tasks WHERE enabled = true")
        # 简化示例，实际就是更新self.tasks
        logger.debug("Syncing tasks from database...")
        # 这里保留实现占位，实际使用替换成数据库加载
        pass
    
    def execute_task(self, task: ScheduledTask) -> TaskExecution:
        """执行单个任务，带超时"""
        execution = TaskExecution(
            task_id=task.task_id,
            scheduled_time=int(time.time()),
            worker=self.worker_id,
            status=TaskStatus.RUNNING
        )
        
        execution.start_time = int(time.time())
        
        def run():
            try:
                result = task.handler()
                execution.status = TaskStatus.SUCCESS
                execution.result = str(result)
            except Exception as e:
                execution.status = TaskStatus.FAILED
                execution.error = str(e)
                logger.error(f"Task {task.task_id} failed: {e}")
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        thread.join(task.timeout_seconds)
        
        execution.end_time = int(time.time())
        
        if thread.is_alive():
            execution.status = TaskStatus.TIMEOUT
            execution.error = f"Timeout after {task.timeout_seconds} seconds"
            logger.error(f"Task {task.task_id} timeout")
        
        # 保存执行记录到数据库
        # self.save_execution(execution)
        
        return execution
    
    def scheduler_loop(self):
        """调度主循环"""
        while self.running:
            for task_id, task in self.tasks.items():
                if not task.enabled:
                    continue
                if not self.is_my_task(task_id):
                    continue
                
                now = datetime.now()
                next_run = self.get_next_run_time(task.cron_expr, now)
                seconds_to_next = (next_run - now).total_seconds()
                
                # 如果预定执行时间在一分钟以内，就抢锁执行
                if seconds_to_next <= 60:
                    scheduled_ts = int(next_run.timestamp())
                    if self.try_acquire_lock(task_id, scheduled_ts):
                        logger.info(f"Executing task {task_id} scheduled at {scheduled_ts}")
                        self.execute_task(task)
            
            time.sleep(10)  # 每10秒检查一次
    
    def start(self):
        """启动调度器"""
        self.running = True
        
        # 启动配置同步线程
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        
        # 启动调度主循环
        self._scheduler_thread = threading.Thread(target=self.scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        
        logger.info("Scheduler started")
    
    def _sync_loop(self):
        """配置同步循环"""
        while self.running:
            try:
                self.sync_tasks_from_db()
            except Exception as e:
                logger.error(f"Sync tasks failed: {e}")
            time.sleep(self.sync_interval)
    
    def stop(self):
        """停止调度器"""
        self.running = False
        logger.info("Scheduler stopping")
    
    def add_task(self, task: ScheduledTask):
        """手动添加任务（动态添加）"""
        self.tasks[task.task_id] = task
        logger.info(f"Added task {task.task_id}")
    
    def remove_task(self, task_id: str):
        """移除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"Removed task {task_id}")
    
    def list_tasks(self) -> List[ScheduledTask]:
        """列出所有任务"""
        return list(self.tasks.values())

if __name__ == "__main__":
    # 使用示例
    logging.basicConfig(level=logging.INFO)
    
    scheduler = DistributedScheduler(
        redis_url="redis://localhost:6379/0",
        worker_id="worker-1",
        worker_index=0,
        total_workers=3,  # 3个worker分片
    )
    
    # 添加一个任务：每天凌晨1点执行
    def hello_task():
        print("Hello from scheduled task!")
        return "ok"
    
    scheduler.add_task(ScheduledTask(
        task_id="daily_hello",
        cron_expr="0 1 * * *",
        handler=hello_task,
        timeout_seconds=30,
    ))
    
    scheduler.start()
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.stop()
