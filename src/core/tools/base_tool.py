"""
工具基类

定义工具的通用接口和基础功能
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseTool(ABC):
    """
    工具基类
    
    定义所有工具的通用接口
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        初始化工具
        
        Args:
            name: 工具名称
            description: 工具描述
        """
        self.name = name
        self.description = description
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            执行结果
        """
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取工具信息
        
        Returns:
            工具信息
        """
        return {
            "name": self.name,
            "description": self.description
        } 