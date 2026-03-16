# 消息队列集成方案设计

## 架构设计

面向接口设计，统一抽象生产者和消费者，支持多种消息中间件切换：

```
┌─────────────────────────────────────────────────────────────┐
│                业务层                                       │
├─────────────────────────────────────────────────────────────┤
│                QueueFactory 工厂                            │
│              根据配置创建具体队列客户端                        │
├─────────────────────────────────────────────────────────────┤
│              Abstraction 接口层                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Producer  生产者接口  │  Consumer  消费者接口        │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│              具体实现                                       │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │  RabbitMQ │ │   Kafka   │ │   Redis   │              │
│  └────────────┘ └────────────┘ └────────────┘              │
├─────────────────────────────────────────────────────────────┤
│              通用能力                                       │
│  - 消息确认 (ack/nack)                                      │
│  - 死信队列 (处理失败消息)                                   │
│  - 消息持久化                                               │
│  - 重试机制                                                 │
└─────────────────────────────────────────────────────────────┘
```

## 统一接口定义

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar('T')

class Producer(ABC):
    """消息生产者抽象"""
    
    @abstractmethod
    def publish(self, topic: str, message: bytes, key: str = None) -> bool:
        """发布消息到topic"""
        pass
    
    @abstractmethod
    def close(self):
        """关闭连接"""
        pass

class Consumer(ABC):
    """消息消费者抽象"""
    
    @abstractmethod
    def consume(self, topic: str, handler: callable[[bytes], bool]) -> None:
        """开始消费，handler处理消息返回True表示成功，False表示失败"""
        pass
    
    @abstractmethod
    def ack(self):
        """确认消息"""
        pass
    
    @abstractmethod
    def nack(self, requeue: bool = False):
        """拒绝消息"""
        pass
    
    @abstractmethod
    def close(self):
        """关闭连接"""
        pass
```

## 消息确认机制

| 方案 | 说明 |
|------|------|
| 自动确认 | 消息发出去就确认，消费者宕机可能丢消息 |
| 手动确认 | 消费者处理成功才确认，保证不丢，但要做好重试去重 |

生产环境推荐**手动确认**：
- 处理成功 → ack 消息移除
- 处理失败 → nack，不重新入队 → 进入死信队列
- 处理失败，可以重试几次再进死信

## 死信队列设计

死信队列用于存放处理失败的消息，避免一直阻塞正常消费：

什么时候进入死信：
1. 消息处理失败（返回False）
2. 消息重试超过最大次数
3. 消息过期
4. 队列满了

死信队列处理：
- 单独存放到死信队列
- 人工后续处理，排查问题后可以重放

## 不同MQ选型对比

| 特性 | RabbitMQ | Kafka | Redis |
|------|----------|-------|-------|
| 消息吞吐量 | 中 (~万级) | 高 (~百万级) | 低 (~千级) |
| 消息延迟 | 低 | 中 | 很低 |
| 持久化 | 支持 | 支持 | 可选 |
| 路由功能 | 丰富 (direct/topic/fanout) | 简单按partition | 基于list |
| 适用场景 | 业务异步解耦 | 大数据日志/流 | 简单队列/缓存 |

## 消息持久化

| 持久化级别 | 说明 | 性能 | 可靠性 |
|-------------|------|------|--------|
| 不持久化 | 存在内存 | 快 | 宕机丢消息 |
| 持久化到磁盘 | 消息刷盘 | 慢 | 不丢消息 |

生产环境关键业务一定要开启持久化。

## 消息重放

支持根据offset重放消息：
- Kafka 天然支持按offset消费
- RabbitMQ可以用延迟队列+死信实现
- 重放入口给运维人员，可以指定从某个时间点/offset开始重放

## 使用示例

```python
# 初始化
from queue import get_producer, get_consumer

# 创建生产者
producer = get_producer("rabbitmq", config={
    "url": "amqp://guest:guest@localhost:5672/",
})

# 发布消息
producer.publish("order_created", b'{"order_id": 123, "user_id": 456}')

# 创建消费者
def handle_order_created(message):
    data = json.loads(message)
    # 处理业务逻辑
    try:
        process_order(data)
        return True  # 成功
    except Exception:
        return False  # 失败，进死信

consumer = get_consumer("rabbitmq", config={...})
consumer.consume("order_created", handle_order_created)
```

## 最佳实践

1. **异步化解耦**：把不需要同步返回的操作丢去队列，加快接口响应
2. **幂等消费**：消费者一定要实现幂等，同一条消息处理多次结果一样
3. **监控队列长度**：队列长度持续增长说明消费速度跟不上生产速度，要扩容
4. **失败不丢消息**：处理不了的进死信，不要直接丢
5. **合理批量**：Kafka适合批量生产消费提高吞吐
6. **做好限流**：不要让消费峰值把系统打垮

---
设计由 oc-coze 于 2026-03-16 生成
