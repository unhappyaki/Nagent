# 执行域适配器子模块

本目录包含执行域的适配器实现，支持多种外部系统或平台的任务适配。

- `base_adapter.py`：适配器基类，定义统一接口

## 用法示例

```python
from .base_adapter import ExecutionAdapterBase

class MyAdapter(ExecutionAdapterBase):
    def execute(self, task):
        # 实现自定义执行逻辑
        pass
``` 