# Python代码优化任务 [coding] [medium]

## 任务描述

优化以下Python代码的性能：

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

for i in range(100):
    print(fibonacci(i))
```

## 要求

1. 使用迭代代替递归
2. 添加缓存机制
3. 保持代码可读性

## 输出

将优化后的代码保存为 `output/task-002/fibonacci.py`
