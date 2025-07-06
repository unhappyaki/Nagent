"""
路由器基类
"""

from abc import ABC, abstractmethod
from typing import Any

class RouterBase(ABC):
    """所有通信路由器的基类。"""
    @abstractmethod
    def route(self, message: Any) -> Any:
        pass 