"""
n8n工作流引擎适配器

提供与n8n工作流引擎的集成接口。
"""

import aiohttp
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .base_adapter import (
    WorkflowEngineAdapter, 
    WorkflowEngineType, 
    WorkflowDefinition, 
    ExecutionResult, 
    WorkflowStatus, 
    WorkflowInfo
)


@dataclass
class N8nConfig:
    """n8n配置"""
    base_url: str
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30


@dataclass
class N8nWorkflow:
    """n8n工作流"""
    id: str
    name: str
    active: bool
    nodes: List[Dict[str, Any]]
    connections: Dict[str, Any]
    settings: Dict[str, Any]
    static_data: Optional[Dict[str, Any]] = None


@dataclass
class TriggerResult:
    """触发结果"""
    execution_id: str
    status: str
    data: Dict[str, Any]


@dataclass
class ExecutionLog:
    """执行日志"""
    execution_id: str
    node_name: str
    status: str
    data: Dict[str, Any]
    timestamp: str
    error_message: Optional[str] = None


class N8nAdapter(WorkflowEngineAdapter):
    """
    n8n工作流引擎适配器
    
    提供与n8n工作流引擎的完整集成功能。
    """
    
    def __init__(self, config: N8nConfig):
        """
        初始化n8n适配器
        
        Args:
            config: n8n配置
        """
        super().__init__(WorkflowEngineType.N8N, config.__dict__)
        self.n8n_config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._headers = {}
    
    async def connect(self) -> bool:
        """
        连接到n8n
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.n8n_config.timeout)
            )
            
            # 设置认证头
            if self.n8n_config.api_key:
                self._headers = {"X-N8N-API-KEY": self.n8n_config.api_key}
            elif self.n8n_config.username and self.n8n_config.password:
                # 基本认证
                import base64
                credentials = f"{self.n8n_config.username}:{self.n8n_config.password}"
                encoded_credentials = base64.b64encode(credentials.encode()).decode()
                self._headers = {"Authorization": f"Basic {encoded_credentials}"}
            
            # 测试连接
            async with self.session.get(
                f"{self.n8n_config.base_url}/api/v1/health",
                headers=self._headers
            ) as response:
                if response.status == 200:
                    self._connected = True
                    return True
                else:
                    return False
                    
        except Exception as e:
            print(f"连接n8n失败: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """
        断开与n8n的连接
        
        Returns:
            bool: 断开是否成功
        """
        try:
            if self.session:
                await self.session.close()
            self._connected = False
            return True
        except Exception as e:
            print(f"断开n8n连接失败: {e}")
            return False
    
    async def create_workflow(self, workflow_definition: WorkflowDefinition) -> WorkflowDefinition:
        """
        在n8n中创建工作流
        
        Args:
            workflow_definition: 工作流定义
            
        Returns:
            WorkflowDefinition: 创建的工作流
        """
        if not self._connected:
            raise ConnectionError("未连接到n8n")
        
        try:
            # 构建n8n工作流格式
            n8n_workflow = {
                "name": workflow_definition.name,
                "active": False,  # 默认不激活
                "nodes": workflow_definition.definition.get("nodes", []),
                "connections": workflow_definition.definition.get("connections", {}),
                "settings": workflow_definition.definition.get("settings", {}),
                "staticData": workflow_definition.definition.get("staticData", None)
            }
            
            async with self.session.post(
                f"{self.n8n_config.base_url}/api/v1/workflows",
                headers=self._headers,
                json=n8n_workflow
            ) as response:
                if response.status == 201:
                    result = await response.json()
                    workflow_definition.id = result["id"]
                    workflow_definition.created_at = datetime.now().isoformat()
                    workflow_definition.updated_at = datetime.now().isoformat()
                    return workflow_definition
                else:
                    error_text = await response.text()
                    raise Exception(f"创建工作流失败: {error_text}")
                    
        except Exception as e:
            raise Exception(f"创建n8n工作流失败: {e}")
    
    async def execute_workflow(self, workflow_id: str, input_data: Dict[str, Any]) -> ExecutionResult:
        """
        执行n8n工作流
        
        Args:
            workflow_id: 工作流ID
            input_data: 输入数据
            
        Returns:
            ExecutionResult: 执行结果
        """
        if not self._connected:
            raise ConnectionError("未连接到n8n")
        
        try:
            execution_id = str(uuid.uuid4())
            
            # 触发工作流执行
            trigger_data = {
                "workflowId": workflow_id,
                "data": input_data
            }
            
            async with self.session.post(
                f"{self.n8n_config.base_url}/api/v1/workflows/{workflow_id}/trigger",
                headers=self._headers,
                json=trigger_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return ExecutionResult(
                        execution_id=execution_id,
                        workflow_id=workflow_id,
                        status="running",
                        result=result,
                        execution_time=None
                    )
                else:
                    error_text = await response.text()
                    return ExecutionResult(
                        execution_id=execution_id,
                        workflow_id=workflow_id,
                        status="failed",
                        result={},
                        error_message=error_text,
                        execution_time=None
                    )
                    
        except Exception as e:
            return ExecutionResult(
                execution_id=str(uuid.uuid4()),
                workflow_id=workflow_id,
                status="failed",
                result={},
                error_message=str(e),
                execution_time=None
            )
    
    async def get_workflow_status(self, execution_id: str) -> WorkflowStatus:
        """
        获取n8n工作流执行状态
        
        Args:
            execution_id: 执行ID
            
        Returns:
            WorkflowStatus: 工作流状态
        """
        if not self._connected:
            raise ConnectionError("未连接到n8n")
        
        try:
            async with self.session.get(
                f"{self.n8n_config.base_url}/api/v1/executions/{execution_id}",
                headers=self._headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return WorkflowStatus(
                        execution_id=execution_id,
                        status=result.get("status", "unknown"),
                        progress=result.get("progress", 0.0),
                        current_step=result.get("currentStep", ""),
                        error_message=result.get("errorMessage")
                    )
                else:
                    return WorkflowStatus(
                        execution_id=execution_id,
                        status="unknown",
                        progress=0.0,
                        current_step="",
                        error_message="无法获取执行状态"
                    )
                    
        except Exception as e:
            return WorkflowStatus(
                execution_id=execution_id,
                status="error",
                progress=0.0,
                current_step="",
                error_message=str(e)
            )
    
    async def list_workflows(self) -> List[WorkflowInfo]:
        """
        列出所有n8n工作流
        
        Returns:
            List[WorkflowInfo]: 工作流列表
        """
        if not self._connected:
            raise ConnectionError("未连接到n8n")
        
        try:
            async with self.session.get(
                f"{self.n8n_config.base_url}/api/v1/workflows",
                headers=self._headers
            ) as response:
                if response.status == 200:
                    workflows = await response.json()
                    return [
                        WorkflowInfo(
                            id=wf["id"],
                            name=wf["name"],
                            description=wf.get("description", ""),
                            engine_type=WorkflowEngineType.N8N,
                            is_active=wf.get("active", False),
                            last_execution=wf.get("updatedAt")
                        )
                        for wf in workflows
                    ]
                else:
                    return []
                    
        except Exception as e:
            print(f"获取n8n工作流列表失败: {e}")
            return []
    
    async def delete_workflow(self, workflow_id: str) -> bool:
        """
        删除n8n工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 删除是否成功
        """
        if not self._connected:
            raise ConnectionError("未连接到n8n")
        
        try:
            async with self.session.delete(
                f"{self.n8n_config.base_url}/api/v1/workflows/{workflow_id}",
                headers=self._headers
            ) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"删除n8n工作流失败: {e}")
            return False
    
    async def update_workflow(self, workflow_id: str, workflow_definition: WorkflowDefinition) -> WorkflowDefinition:
        """
        更新n8n工作流
        
        Args:
            workflow_id: 工作流ID
            workflow_definition: 工作流定义
            
        Returns:
            WorkflowDefinition: 更新后的工作流
        """
        if not self._connected:
            raise ConnectionError("未连接到n8n")
        
        try:
            n8n_workflow = {
                "name": workflow_definition.name,
                "active": workflow_definition.definition.get("active", False),
                "nodes": workflow_definition.definition.get("nodes", []),
                "connections": workflow_definition.definition.get("connections", {}),
                "settings": workflow_definition.definition.get("settings", {}),
                "staticData": workflow_definition.definition.get("staticData", None)
            }
            
            async with self.session.put(
                f"{self.n8n_config.base_url}/api/v1/workflows/{workflow_id}",
                headers=self._headers,
                json=n8n_workflow
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    workflow_definition.updated_at = datetime.now().isoformat()
                    return workflow_definition
                else:
                    error_text = await response.text()
                    raise Exception(f"更新工作流失败: {error_text}")
                    
        except Exception as e:
            raise Exception(f"更新n8n工作流失败: {e}")
    
    async def get_execution_logs(self, execution_id: str) -> List[ExecutionLog]:
        """
        获取执行日志
        
        Args:
            execution_id: 执行ID
            
        Returns:
            List[ExecutionLog]: 执行日志列表
        """
        if not self._connected:
            raise ConnectionError("未连接到n8n")
        
        try:
            async with self.session.get(
                f"{self.n8n_config.base_url}/api/v1/executions/{execution_id}/logs",
                headers=self._headers
            ) as response:
                if response.status == 200:
                    logs = await response.json()
                    return [
                        ExecutionLog(
                            execution_id=execution_id,
                            node_name=log.get("nodeName", ""),
                            status=log.get("status", ""),
                            data=log.get("data", {}),
                            timestamp=log.get("timestamp", ""),
                            error_message=log.get("errorMessage")
                        )
                        for log in logs
                    ]
                else:
                    return []
                    
        except Exception as e:
            print(f"获取n8n执行日志失败: {e}")
            return []
    
    async def activate_workflow(self, workflow_id: str) -> bool:
        """
        激活工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 激活是否成功
        """
        if not self._connected:
            raise ConnectionError("未连接到n8n")
        
        try:
            async with self.session.post(
                f"{self.n8n_config.base_url}/api/v1/workflows/{workflow_id}/activate",
                headers=self._headers
            ) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"激活n8n工作流失败: {e}")
            return False
    
    async def deactivate_workflow(self, workflow_id: str) -> bool:
        """
        停用工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 停用是否成功
        """
        if not self._connected:
            raise ConnectionError("未连接到n8n")
        
        try:
            async with self.session.post(
                f"{self.n8n_config.base_url}/api/v1/workflows/{workflow_id}/deactivate",
                headers=self._headers
            ) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"停用n8n工作流失败: {e}")
            return False 