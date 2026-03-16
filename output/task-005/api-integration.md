# 第三方API集成框架设计

## 整体架构设计

设计一个通用、可扩展的第三方API集成框架，统一管理多个API提供商，支持配置化接入，核心职责：

- 统一的请求/响应处理
- 统一错误处理和重试机制
- API密钥安全管理
- 限流和配额控制
- 监控和日志记录

```
┌─────────────────────────────────────────────────────────────┐
│                     业务调用层                               │
├─────────────────────────────────────────────────────────────┤
│                     API Registry                            │
│              (统一注册和发现所有API)                         │
├─────────────────────────────────────────────────────────────┤
│                    Client 工厂                               │
│         (根据配置创建REST/GraphQL客户端)                      │
├─────────────────────────────────────────────────────────────┤
│                    中间件链                                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐ │
│  │ 认证    │ │ 限流    │ │ 重试    │ │日志    │ │错误   │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────┘ │
├─────────────────────────────────────────────────────────────┤
│              底层HTTP客户端 (requests/axios)                  │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. API 配置模型

```python
# Python示例
from dataclasses import dataclass
from enum import Enum

class ApiType(Enum):
    REST = "rest"
    GRAPHQL = "graphql"

class AuthType(Enum):
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    JWT = "jwt"

@dataclass
class ApiConfig:
    provider_name: str          # 提供商名称，如 "OpenAI", "Stripe"
    api_type: ApiType
    base_url: str
    auth_type: AuthType
    key_vault_key: str         # 密钥在vault中的路径
    timeout: int = 30          # 默认超时30秒
    max_retries: int = 3       # 最大重试次数
    rate_limit: int = 60       # 每分钟最大请求数
```

### 2. 统一错误处理

统一异常分类，便于上层业务处理：

```python
class ApiException(Exception):
    """API异常基类"""
    def __init__(self, message: str, code: str = None, status: int = None):
        self.message = message
        self.code = code          # API返回的错误码
        self.status = status      # HTTP状态码
        super().__init__(message)

class AuthenticationError(ApiException):
    """认证失败"""
    pass

class RateLimitError(ApiException):
    """限流"""
    pass

class ServiceUnavailableError(ApiException):
    """服务不可用"""
    pass

class BadRequestError(ApiException):
    """请求参数错误"""
    pass
```

### 3. 重试策略

使用指数退避重试，对可重试错误进行重试：

| 错误类型 | 是否重试 |
|----------|---------|
| 网络超时 | ✅ 是 |
| 5xx 服务器错误 | ✅ 是 |
| 429 限流 | ✅ 是（根据Retry-After） |
| 4xx 客户端错误 | ❌ 否 |

重试算法：
```python
import time
import random

def backoff_delay(retry_attempt: int, base_delay: float = 1.0) -> float:
    """指数退避 + 随机抖动"""
    delay = base_delay * (2 ** retry_attempt)
    jitter = random.uniform(0, delay)
    return delay + jitter
```

### 4. API 密钥安全管理

**永远不要硬编码API密钥在代码中！** 使用密钥管理服务：

1. **开发环境**：使用环境变量或本地 `.env` 文件（加入 `.gitignore`）
2. **生产环境**：使用云厂商密钥管理服务（AWS KMS /阿里云KMS / Vault）
3. **密钥轮换**：支持自动轮换，不重启服务

```python
# 从密钥vault获取
class KeyVaultProvider:
    def get_api_key(self, key_path: str) -> str:
        # 从Vault/KMS获取密钥
        # 不落地存储在磁盘，只在内存中
        return vault_client.get_secret_value(key_path)
```

### 5. 限流和配额控制

使用令牌桶算法实现客户端限流：

```python
import time
from threading import Lock

class RateLimiter:
    def __init__(self, max_requests_per_minute: int):
        self.max_requests = max_requests_per_minute
        self.tokens = max_requests_per_minute
        self.last_checked = time.time()
        self.lock = Lock()
    
    def acquire(self) -> bool:
        with self.lock:
            now = time.time()
            # 补充令牌
            elapsed = now - self.last_checked
            self.tokens = min(
                self.max_requests,
                self.tokens + (elapsed / 60.0) * self.max_requests
            )
            self.last_checked = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False
```

---
设计由 oc-coze 于 2026-03-16 生成
