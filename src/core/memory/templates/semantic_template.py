"""
语义内存模板实现
"""

from .template_base import MemoryTemplateBase
from typing import Any, Dict

class SemanticMemoryTemplate(MemoryTemplateBase):
    """语义内存模板，适用于文本、知识等结构化语义信息。"""
    def encode(self, data: Any) -> Dict:
        # 假设data为文本，简单结构化
        return {"type": "semantic", "content": str(data)}

    def decode(self, data: Dict) -> Any:
        return data.get("content", "") 