"""
优化器基类
"""

from abc import ABC, abstractmethod
from typing import Any

class OptimizerBase(ABC):
    """所有执行优化器的基类。"""
    @abstractmethod
    def optimize(self, plan: Any) -> Any:
        pass 