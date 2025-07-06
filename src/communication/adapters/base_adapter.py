"""
工作流引擎适配器基类

提供统一的工作流引擎接口抽象，支持多种工作流引擎的集成。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class WorkflowEngineType(Enum):
    """工作流引擎类型枚举"""
    N8N = "n8n"
    DIFY = "dify"
    ZAPIER = "zapier"
    MAKE = "make"


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    id: str
    name: str
    description: str
    definition: Dict[str, Any]
    engine_type: WorkflowEngineType
    created_at: str
    updated_at: str


@dataclass
class ExecutionResult:
    """执行结果"""
    execution_id: str
    workflow_id: str
    status: str
    result: Dict[str, Any]
    error_message: Optional[str] = None
    execution_time: Optional[float] = None


@dataclass
class WorkflowStatus:
    """工作流状态"""
    execution_id: str
    status: str
    progress: float
    current_step: str
    error_message: Optional[str] = None


@dataclass
class WorkflowInfo:
    """工作流信息"""
    id: str
    name: str
    description: str
    engine_type: WorkflowEngineType
    is_active: bool
    last_execution: Optional[str] = None


class WorkflowEngineAdapter(ABC):
    """
    工作流引擎适配器基类
    
    提供统一的工作流引擎接口，支持多种工作流引擎的集成。
    """
    
    def __init__(self, engine_type: WorkflowEngineType, config: Dict[str, Any]):
        """
        初始化工作流引擎适配器
        
        Args:
            engine_type: 工作流引擎类型
            config: 配置信息
        """
        self.engine_type = engine_type
        self.config = config
        self._connected = False
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        连接到工作流引擎
        
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        断开与工作流引擎的连接
        
        Returns:
            bool: 断开是否成功
        """
        pass
    
    @abstractmethod
    async def create_workflow(self, workflow_definition: WorkflowDefinition) -> WorkflowDefinition:
        """
        创建工作流
        
        Args:
            workflow_definition: 工作流定义
            
        Returns:
            WorkflowDefinition: 创建的工作流
        """
        pass
    
    @abstractmethod
    async def execute_workflow(self, workflow_id: str, input_data: Dict[str, Any]) -> ExecutionResult:
        """
        执行工作流
        
        Args:
            workflow_id: 工作流ID
            input_data: 输入数据
            
        Returns:
            ExecutionResult: 执行结果
        """
        pass
    
    @abstractmethod
    async def get_workflow_status(self, execution_id: str) -> WorkflowStatus:
        """
        获取工作流执行状态
        
        Args:
            execution_id: 执行ID
            
        Returns:
            WorkflowStatus: 工作流状态
        """
        pass
    
    @abstractmethod
    async def list_workflows(self) -> List[WorkflowInfo]:
        """
        列出所有工作流
        
        Returns:
            List[WorkflowInfo]: 工作流列表
        """
        pass
    
    @abstractmethod
    async def delete_workflow(self, workflow_id: str) -> bool:
        """
        删除工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 删除是否成功
        """
        pass
    
    @abstractmethod
    async def update_workflow(self, workflow_id: str, workflow_definition: WorkflowDefinition) -> WorkflowDefinition:
        """
        更新工作流
        
        Args:
            workflow_id: 工作流ID
            workflow_definition: 工作流定义
            
        Returns:
            WorkflowDefinition: 更新后的工作流
        """
        pass
    
    def is_connected(self) -> bool:
        """
        检查是否已连接
        
        Returns:
            bool: 是否已连接
        """
        return self._connected
    
    def get_engine_type(self) -> WorkflowEngineType:
        """
        获取引擎类型
        
        Returns:
            WorkflowEngineType: 引擎类型
        """
        return self.engine_type
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取配置信息
        
        Returns:
            Dict[str, Any]: 配置信息
        """
        return self.config.copy() 