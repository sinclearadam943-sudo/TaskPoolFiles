# Webhook事件处理系统设计

## 整体架构

Webhook系统用于接收第三方平台的事件推送，验证签名，异步处理，回调业务逻辑。

```
┌─────────────┐
│  第三方平台  │  GitHub/GitLab/支付回调等
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   HTTP入口   │  接收Webhook请求
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  签名验证     │  使用密钥验证签名合法性
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  去重/幂等   │  根据event_id判断是否已处理
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  存入消息队列 │  异步处理，快速返回
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  消费者异步处理 │  调用对应处理器
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  存储事件日志  │  便于调试审计
└─────────────┘
```

## 签名验证

不同平台签名方式不同，但核心思想一致：使用预共享密钥对请求内容做签名，验证一致性，防止伪造。

### GitHub签名验证示例

```python
import hmac
import hashlib

def verify_signature(secret: str, payload: bytes, signature_header: str) -> bool:
    """GitHub Webhook签名验证"""
    # signature_header 格式: sha256=xxxxxx
    if not signature_header.startswith("sha256="):
        return False
    
    expected = hmac.new(
        key=secret.encode(),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    received = signature_header[7:]
    
    return hmac.compare_digest(expected, received)
```

### 通用签名验证流程

1. 获取请求原始body（不能修改，不然签名不对）
2. 根据平台规则计算预期签名
3. 和请求头里的签名比较，恒定时间比较防止计时攻击

## 幂等性和去重处理

Webhook经常会重试，必须做好幂等：

1. 每个事件都有唯一 `event_id`
2. 处理前先查数据库，如果 `event_id` 已经处理过，直接返回成功
3. 使用 `INSERT ... ON DUPLICATE KEY` 或者原子操作保证并发安全

```python
def is_already_processed(event_id: str) -> bool:
    """检查事件是否已经处理过"""
    result = db.query(
        "SELECT 1 FROM webhook_events WHERE event_id = %s",
        (event_id,)
    )
    return len(result) > 0

def mark_processed(event_id: str, event_type: str, payload: dict):
    """标记事件已处理"""
    try:
        db.execute(
            "INSERT INTO webhook_events (event_id, event_type, payload, created_at) VALUES (%s, %s, %s, NOW())",
            (event_id, event_type, json.dumps(payload))
        )
        return True  # 第一次处理
    except DuplicateKey:
        return False  # 已经处理过了
```

## 支持多种平台适配

使用工厂模式，不同平台对应不同处理器：

| 平台 | 签名方式 | 事件格式 |
|------|----------|---------|
| GitHub | HMAC-SHA256 | 统一JSON格式 |
| GitLab | 密钥比对（token）| JSON |
| Docker Hub | 密钥查询参数 | JSON |
| 支付宝/微信 | RSA签名 | XML/JSON |

```python
class WebhookHandler(ABC):
    @abstractmethod
    def verify(self, request, secret) -> bool:
        """验证签名"""
        pass
    
    @abstractmethod
    def parse_event(self, request) -> WebhookEvent:
        """解析事件"""
        pass

class GitHubHandler(WebhookHandler):
    # GitHub具体实现

class GitLabHandler(WebhookHandler):
    # GitLab具体实现
```

## 完整处理流程（伪代码）

```python
def webhook_handler(request):
    # 1. 获取平台和密钥
    provider = request.path_params["provider"]
    handler = get_handler(provider)
    secret = get_secret(provider)
    
    # 2. 读取原始body
    payload = request.body
    
    # 3. 验证签名
    if not handler.verify(request, payload, secret):
        return JSONResponse({"status": "signature_invalid"}, status_code=403)
    
    # 4. 解析事件
    event = handler.parse_event(request, payload)
    
    # 5. 幂等去重
    if not mark_processed(event.id):
        # 已经处理过了，直接返回成功
        return JSONResponse({"status": "ok", "message": "already processed"})
    
    # 6. 发到消息队列异步处理
    queue.publish(event)
    
    # 7. 返回成功
    return JSONResponse({"status": "ok"})
```

## 最佳实践

1. **必须验证签名**：不验证签名任何人都能调你的接口，非常危险
2. **快速响应**：一定要异步处理，不要让第三方等
3. **幂等处理**：重复调用不能产生副作用
4. **完整日志**：记录所有原始内容，出问题能复盘
5. **失败重试**：网络抖动允许重试，多次失败放去死信

---
设计由 oc-coze 于 2026-03-16 生成
