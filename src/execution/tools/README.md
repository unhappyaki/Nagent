# 工具执行子模块

本目录包含执行域的工具执行相关实现。

- `tool_executor.py`：工具执行器基类，定义统一接口

## 用法示例

```python
from .tool_executor import ToolExecutor

class MyToolExecutor(ToolExecutor):
    def run(self, tool, *args, **kwargs):
        # 实现自定义工具执行逻辑
        pass
``` 