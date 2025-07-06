"""
内存模板基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

class MemoryTemplateBase(ABC):
    """内存模板基类，定义所有内存模板的接口。"""
    @abstractmethod
    def encode(self, data: Any) -> Dict:
        pass

    @abstractmethod
    def decode(self, data: Dict) -> Any:
        pass 