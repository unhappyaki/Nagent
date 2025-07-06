"""
向量内存模板实现
"""

from .template_base import MemoryTemplateBase
from typing import Any, Dict, List

class VectorMemoryTemplate(MemoryTemplateBase):
    """向量内存模板，适用于嵌入向量等结构化数据。"""
    def encode(self, data: List[float]) -> Dict:
        return {"type": "vector", "vector": data}

    def decode(self, data: Dict) -> Any:
        return data.get("vector", []) 