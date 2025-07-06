# 执行优化子模块

本目录包含执行域的优化相关实现。

- `optimizer_base.py`：优化器基类，定义统一接口

## 用法示例

```python
from .optimizer_base import OptimizerBase

class MyOptimizer(OptimizerBase):
    def optimize(self, plan):
        # 实现自定义优化逻辑
        pass
``` 