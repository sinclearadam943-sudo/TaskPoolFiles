# 消息队列集成方案 [integration] [queue]

## 任务描述

设计基于消息队列的异步处理架构，支持多种消息中间件。

## 要求

1. 支持RabbitMQ、Kafka、Redis等消息队列
2. 实现统一的消息生产者和消费者接口
3. 包含消息确认和死信队列机制
4. 支持消息持久化和重放

## 输出

将集成方案保存为 `output/task-008/message-queue.md`