"""
统一模块注册中心
基础设施层核心组件，提供Tool、Agent、Memory、Reasoner策略的统一注册管理
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import structlog

from .tool_registry import ToolRegistry
from .agent_registry import AgentRegistry
from .memory_registry import MemoryRegistry
from .reasoner_registry import ReasonerRegistry
from .protocol_registry import ProtocolServiceRegistry


logger = structlog.get_logger(__name__)


class ModuleType:
    """模块类型常量"""
    TOOL = "tool"
    AGENT = "agent"
    MEMORY = "memory"
    REASONER = "reasoner"
    PROTOCOL = "protocol"


class RegistrationResult:
    """注册结果"""
    
    def __init__(self, success: bool, module_id: str, message: str = "", metadata: Dict[str, Any] = None):
        self.success = success
        self.module_id = module_id
        self.message = message
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()


class UnifiedModuleRegistry:
    """
    统一模块注册中心
    
    基础设施层核心组件，负责：
    - Tool注册：动态权限绑定、Trace策略注入
    - Agent注册：metadata注入、权限绑定、TraceWriter注入器
    - Memory注册：短时/长时/冻结/加密模式配置
    - Reasoner策略注册：prompt-template/RL-policy/flow-based推理器切换
    - Protocol服务注册：四大协议服务统一管理
    """
    
    def __init__(self, config_manager=None, auth_manager=None, trace_writer=None):
        """
        初始化统一注册中心
        
        Args:
            config_manager: 配置管理器
            auth_manager: 认证管理器  
            trace_writer: 追踪写入器
        """
        self.config_manager = config_manager
        self.auth_manager = auth_manager
        self.trace_writer = trace_writer
        
        # 四大核心注册器
        self.tool_registry = ToolRegistry(self)
        self.agent_registry = AgentRegistry(self)
        self.memory_registry = MemoryRegistry(self)
        self.reasoner_registry = ReasonerRegistry(self)
        
        # 协议服务注册器
        self.protocol_registry = ProtocolServiceRegistry(self)
        
        # 注册统计
        self.registration_stats = {
            ModuleType.TOOL: 0,
            ModuleType.AGENT: 0,
            ModuleType.MEMORY: 0,
            ModuleType.REASONER: 0,
            ModuleType.PROTOCOL: 0
        }
        
        # 注册历史
        self.registration_history = []
        
        logger.info("UnifiedModuleRegistry initialized")
    
    async def register_module(
        self,
        module_type: str,
        module_id: str,
        module_config: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> RegistrationResult:
        """
        统一模块注册入口
        
        Args:
            module_type: 模块类型 (tool/agent/memory/reasoner/protocol)
            module_id: 模块唯一标识
            module_config: 模块配置
            metadata: 元数据
            
        Returns:
            RegistrationResult: 注册结果
        """
        try:
            # 1. 参数验证
            if not module_type or not module_id:
                return RegistrationResult(
                    success=False,
                    module_id=module_id,
                    message="Module type and ID are required"
                )
            
            # 2. 权限验证
            if self.auth_manager:
                has_permission = await self.auth_manager.validate_registration_permission(
                    module_type, module_id
                )
                if not has_permission:
                    return RegistrationResult(
                        success=False,
                        module_id=module_id,
                        message=f"No permission to register {module_type}: {module_id}"
                    )
            
            # 3. 获取对应注册器
            registry = self._get_registry(module_type)
            if not registry:
                return RegistrationResult(
                    success=False,
                    module_id=module_id,
                    message=f"Unsupported module type: {module_type}"
                )
            
            # 4. 执行注册
            result_id = await registry.register(module_id, module_config, metadata)
            
            # 5. 更新统计
            self.registration_stats[module_type] += 1
            
            # 6. 记录注册事件
            if self.trace_writer:
                await self._record_registration_event(
                    module_type, module_id, module_config, metadata
                )
            
            # 7. 记录注册历史
            self.registration_history.append({
                "module_type": module_type,
                "module_id": module_id,
                "timestamp": datetime.utcnow().isoformat(),
                "config": module_config,
                "metadata": metadata
            })
            
            logger.info(
                "Module registered successfully",
                module_type=module_type,
                module_id=module_id
            )
            
            return RegistrationResult(
                success=True,
                module_id=result_id,
                message=f"Successfully registered {module_type}: {module_id}",
                metadata={"registration_stats": self.registration_stats}
            )
            
        except Exception as e:
            logger.error(
                "Failed to register module",
                module_type=module_type,
                module_id=module_id,
                error=str(e)
            )
            return RegistrationResult(
                success=False,
                module_id=module_id,
                message=f"Registration failed: {str(e)}"
            )
    
    async def unregister_module(
        self,
        module_type: str,
        module_id: str
    ) -> RegistrationResult:
        """
        注销模块
        
        Args:
            module_type: 模块类型
            module_id: 模块ID
            
        Returns:
            RegistrationResult: 注销结果
        """
        try:
            # 权限验证
            if self.auth_manager:
                has_permission = await self.auth_manager.validate_unregistration_permission(
                    module_type, module_id
                )
                if not has_permission:
                    return RegistrationResult(
                        success=False,
                        module_id=module_id,
                        message=f"No permission to unregister {module_type}: {module_id}"
                    )
            
            # 获取注册器并注销
            registry = self._get_registry(module_type)
            if not registry:
                return RegistrationResult(
                    success=False,
                    module_id=module_id,
                    message=f"Unsupported module type: {module_type}"
                )
            
            success = await registry.unregister(module_id)
            
            if success:
                self.registration_stats[module_type] = max(0, self.registration_stats[module_type] - 1)
                
                # 记录注销事件
                if self.trace_writer:
                    await self._record_unregistration_event(module_type, module_id)
                
                logger.info(
                    "Module unregistered successfully",
                    module_type=module_type,
                    module_id=module_id
                )
                
                return RegistrationResult(
                    success=True,
                    module_id=module_id,
                    message=f"Successfully unregistered {module_type}: {module_id}"
                )
            else:
                return RegistrationResult(
                    success=False,
                    module_id=module_id,
                    message=f"Failed to unregister {module_type}: {module_id}"
                )
                
        except Exception as e:
            logger.error(
                "Failed to unregister module",
                module_type=module_type,
                module_id=module_id,
                error=str(e)
            )
            return RegistrationResult(
                success=False,
                module_id=module_id,
                message=f"Unregistration failed: {str(e)}"
            )
    
    async def get_module_config(
        self,
        module_type: str,
        module_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取模块配置
        
        Args:
            module_type: 模块类型
            module_id: 模块ID
            
        Returns:
            Optional[Dict[str, Any]]: 模块配置
        """
        registry = self._get_registry(module_type)
        if not registry:
            return None
        
        if hasattr(registry, 'get_config'):
            return await registry.get_config(module_id)
        elif hasattr(registry, 'get_tool_config'):
            return await registry.get_tool_config(module_id)
        elif hasattr(registry, 'get_agent_config'):
            return await registry.get_agent_config(module_id)
        elif hasattr(registry, 'get_memory_config'):
            return await registry.get_memory_config(module_id)
        elif hasattr(registry, 'get_reasoner_config'):
            return await registry.get_reasoner_config(module_id)
        
        return None
    
    async def list_modules(
        self,
        module_type: str = None,
        filter_by: Dict[str, Any] = None
    ) -> List[str]:
        """
        列出模块
        
        Args:
            module_type: 模块类型过滤
            filter_by: 过滤条件
            
        Returns:
            List[str]: 模块ID列表
        """
        if module_type:
            registry = self._get_registry(module_type)
            if registry and hasattr(registry, 'list'):
                return await registry.list(filter_by)
            return []
        
        # 列出所有模块
        all_modules = []
        for mtype in [ModuleType.TOOL, ModuleType.AGENT, ModuleType.MEMORY, ModuleType.REASONER, ModuleType.PROTOCOL]:
            registry = self._get_registry(mtype)
            if registry and hasattr(registry, 'list'):
                modules = await registry.list(filter_by)
                all_modules.extend([f"{mtype}:{mid}" for mid in modules])
        
        return all_modules
    
    def get_registration_stats(self) -> Dict[str, Any]:
        """
        获取注册统计
        
        Returns:
            Dict[str, Any]: 注册统计信息
        """
        return {
            "stats": self.registration_stats.copy(),
            "total": sum(self.registration_stats.values()),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_registration_history(
        self,
        module_type: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取注册历史
        
        Args:
            module_type: 模块类型过滤
            limit: 返回条数限制
            
        Returns:
            List[Dict[str, Any]]: 注册历史记录
        """
        history = self.registration_history
        
        if module_type:
            history = [h for h in history if h["module_type"] == module_type]
        
        # 按时间倒序返回最新的记录
        history = sorted(history, key=lambda x: x["timestamp"], reverse=True)
        
        return history[:limit]
    
    def _get_registry(self, module_type: str):
        """获取对应的注册器"""
        registry_map = {
            ModuleType.TOOL: self.tool_registry,
            ModuleType.AGENT: self.agent_registry,
            ModuleType.MEMORY: self.memory_registry,
            ModuleType.REASONER: self.reasoner_registry,
            ModuleType.PROTOCOL: self.protocol_registry
        }
        return registry_map.get(module_type)
    
    async def _record_registration_event(
        self,
        module_type: str,
        module_id: str,
        module_config: Dict[str, Any],
        metadata: Dict[str, Any]
    ):
        """记录注册事件"""
        trace_id = f"reg_{module_type}_{module_id}_{uuid.uuid4().hex[:8]}"
        
        if hasattr(self.trace_writer, 'record_event'):
            await self.trace_writer.record_event(
                trace_id=trace_id,
                event_type="MODULE_REGISTERED",
                payload={
                    "module_type": module_type,
                    "module_id": module_id,
                    "config": module_config,
                    "metadata": metadata,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        elif hasattr(self.trace_writer, 'record'):
            self.trace_writer.record(
                trace_id=trace_id,
                event_type="MODULE_REGISTERED",
                data={
                    "module_type": module_type,
                    "module_id": module_id,
                    "config": module_config,
                    "metadata": metadata
                }
            )
    
    async def _record_unregistration_event(
        self,
        module_type: str,
        module_id: str
    ):
        """记录注销事件"""
        trace_id = f"unreg_{module_type}_{module_id}_{uuid.uuid4().hex[:8]}"
        
        if hasattr(self.trace_writer, 'record_event'):
            await self.trace_writer.record_event(
                trace_id=trace_id,
                event_type="MODULE_UNREGISTERED",
                payload={
                    "module_type": module_type,
                    "module_id": module_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        elif hasattr(self.trace_writer, 'record'):
            self.trace_writer.record(
                trace_id=trace_id,
                event_type="MODULE_UNREGISTERED",
                data={
                    "module_type": module_type,
                    "module_id": module_id
                }
            ) 