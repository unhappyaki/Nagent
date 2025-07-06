"""
工具执行器基类
"""

from abc import ABC, abstractmethod
from typing import Any

class ToolExecutor(ABC):
    """所有工具执行器的基类。"""
    @abstractmethod
    def run(self, tool: Any, *args, **kwargs) -> Any:
        pass 