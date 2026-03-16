# ETL 数据处理流水线设计

## 整体架构

ETL = Extract 抽取 → Transform 转换 → Load 加载

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│抽取(Extract)│ → │转换(Transform)│ → │校验(Validate)│ → │加载(Load)│ → │输出结果  │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
```

支持批处理（定时跑全量/增量）和流处理（实时处理）两种模式。

## 支持多种数据源

| 数据源类型 | 说明 |
|-------------|------|
| 关系数据库 | MySQL/PostgreSQL/Oracle |
| 文件存储 | CSV/JSON/Parquet/Excel |
| 对象存储 | S3/OSS  |
| API接口 | REST/GraphQL |
| 消息队列 | Kafka/RabbitMQ |

抽取方式：
- 全量抽取：每次抽全部数据
- 增量抽取：根据更新时间抽上次之后变化的数据，节省资源

## 数据转换常见操作

常用转换：

1. **字段映射**：原名改名，A → a
2. **类型转换**：字符串转数字，日期转时间戳
3. **过滤**：去掉不符合条件的数据
4. **聚合**：按字段分组计数求和
5. **关联**：多个数据源join在一起
6. **拆分**：一个大字段拆成多个小字段
7. **去重**：去掉重复数据
8. **补全**：空值填默认值

示例转换配置：

```json
{
  "transforms": [
    {
      "type": "rename",
      "mapping": {
        "user_name": "username",
        "user_age": "age"
      }
    },
    {
      "type": "filter",
      "condition": "age > 0 && age < 150"
    },
    {
      "type": "fill_null",
      "field": "phone",
      "default": ""
    }
  ]
}
```

## 数据质量检查

每个步骤都要做数据质量校验：

| 检查项 | 说明 |
|--------|------|
| 非空检查 | 必填字段不能为null |
| 格式检查 | 邮箱/手机号/日期格式正确 |
| 范围检查 | 数字在合理范围（年龄0-150） |
| 唯一检查 | 主键不重复 |
| 关联检查 | 外键必须在另一个表存在 |

处理坏数据策略：
- **丢弃**：直接扔掉坏数据
- **修复**：按规则自动修复
- **打标签**：保留但标记坏数据，后面人工处理
- **中断**：坏数据比例太高直接失败，告警

## 批处理 vs 流处理

### 批处理

- 定时执行（每天凌晨，每小时）
- 处理大量历史数据
- 适合报表、统计分析
- 工具：Spark、Flink Batch

### 流处理

- 数据进来一条处理一条
- 低延迟
- 适合实时指标、监控
- 工具：Flink Streaming、Kafka Stream

## 整体流水线配置示例

```yaml
pipeline:
  name: "daily_user_stats"
  mode: batch
  schedule: "0 0 * * *"  # cron每天凌晨

extract:
  source: mysql
  config:
    table: "users"
    increment_column: "updated_at"
    where: "updated_at >= '{{last_run_time}}'"

transforms:
  - type: filter
    condition: "is_deleted = false"
  - type: aggregate
    group_by: ["department"]
    aggregations:
      - name: "user_count"
        func: "count"
        field: "id"

validate:
  rules:
    - field: "user_count"
      check: "value > 0"

load:
  destination: data_warehouse
  config:
    table: "daily_user_stats"
    mode: overwrite  # overwrite / append
```

## 最佳实践

1. **增量优先**：能用增量就不用全量，节省时间和资源
2. **早坏早fail**：数据不对尽早发现，不要到最后才错
3. **可重试**：失败了能从失败步骤重试，不用从头来
4. **监控告警**：每个流水线运行时间、输出行数都要监控，失败立刻告警
5. **日志完整**：每个步骤处理了多少数据，多少坏数据，都记日志

---
设计由 oc-coze 于 2026-03-16 生成
