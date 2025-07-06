# 通信域路由器子模块

本目录包含通信域的消息路由相关实现。

- `router_base.py`：路由器基类，定义统一接口

## 用法示例

```python
from .router_base import RouterBase

class MyRouter(RouterBase):
    def route(self, message):
        # 实现自定义路由逻辑
        pass
``` 