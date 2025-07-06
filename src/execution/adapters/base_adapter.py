"""
执行适配器基类
"""

from abc import ABC, abstractmethod
from typing import Any

class ExecutionAdapterBase(ABC):
    """所有执行适配器的基类。"""
    @abstractmethod
    def execute(self, task: Any) -> Any:
        pass 