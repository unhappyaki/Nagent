"""
Agent注册器
基础设施层组件，支持metadata注入、权限绑定、TraceWriter注入器
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger(__name__)


class AgentType:
    """智能体类型"""
    TASK_AGENT = "task_agent"
    CHAT_AGENT = "chat_agent"
    WORKFLOW_AGENT = "workflow_agent"
    REASONING_AGENT = "reasoning_agent"
    TOOL_AGENT = "tool_agent"


class AgentCapability:
    """智能体能力"""
    REASONING = "reasoning"
    TOOL_CALLING = "tool_calling"
    MEMORY_MANAGEMENT = "memory_management"
    WORKFLOW_EXECUTION = "workflow_execution"
    MULTI_MODAL = "multi_modal"


class AgentRegistration:
    """Agent 注册信息占位实现"""
    pass


class AgentStatus:
    """Agent 状态占位实现"""
    pass


class AgentRegistry:
    """
    智能体注册器
    
    基础设施层组件，负责：
    - Metadata注入：自动为智能体注入增强元数据
    - 权限绑定：为每个智能体配置细粒度权限
    - TraceWriter注入器：为智能体创建专用追踪器
    - 智能体生命周期管理：注册、注销、配置更新
    """
    
    def __init__(self, parent_registry):
        """
        初始化智能体注册器
        
        Args:
            parent_registry: 父注册中心
        """
        self.parent_registry = parent_registry
        self.registered_agents = {}
        self.agent_metadata = {}
        self.agent_permissions = {}
        self.trace_writers = {}
        self.agent_capabilities = {}
        
        logger.info("AgentRegistry initialized")
    
    async def register(
        self,
        agent_id: str,
        agent_config: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        注册智能体
        
        Args:
            agent_id: 智能体唯一标识
            agent_config: 智能体配置
            metadata: 元数据
            
        Returns:
            str: 注册成功的智能体ID
        """
        try:
            # 1. Metadata注入
            enhanced_metadata = {
                "agent_id": agent_id,
                "agent_type": agent_config.get("agent_type", AgentType.TASK_AGENT),
                "model": agent_config.get("model", "gpt-3.5-turbo"),
                "model_provider": agent_config.get("model_provider", "openai"),
                "capabilities": agent_config.get("capabilities", []),
                "version": agent_config.get("version", "1.0.0"),
                "description": agent_config.get("description", ""),
                "tags": agent_config.get("tags", []),
                "max_tokens": agent_config.get("max_tokens", 4096),
                "temperature": agent_config.get("temperature", 0.7),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "status": "active",
                **(metadata or {})
            }
            self.agent_metadata[agent_id] = enhanced_metadata
            
            # 2. 权限绑定
            permissions = agent_config.get("permissions", [
                "agent.execute",
                "tool.call",
                "memory.read",
                "memory.write"
            ])
            self.agent_permissions[agent_id] = permissions
            
            # 3. 能力配置
            capabilities = agent_config.get("capabilities", [])
            self.agent_capabilities[agent_id] = capabilities
            
            # 4. TraceWriter注入器
            trace_writer = None
            if self.parent_registry.trace_writer:
                trace_writer = await self._create_agent_tracer(agent_id)
                self.trace_writers[agent_id] = trace_writer
            
            # 5. Agent实例化配置
            agent_instance_config = {
                "agent_id": agent_id,
                "agent_class": agent_config.get("agent_class"),
                "agent_module": agent_config.get("agent_module"),
                "init_params": agent_config.get("init_params", {}),
                "metadata": enhanced_metadata,
                "permissions": permissions,
                "capabilities": capabilities,
                "trace_writer": trace_writer,
                "config": agent_config
            }
            
            self.registered_agents[agent_id] = agent_instance_config
            
            # 6. 通知配置管理器更新
            if self.parent_registry.config_manager:
                await self.parent_registry.config_manager.update_agent_config(
                    agent_id, agent_instance_config
                )
            
            logger.info(
                "Agent registered successfully",
                agent_id=agent_id,
                agent_type=enhanced_metadata["agent_type"],
                permissions=permissions,
                capabilities=capabilities
            )
            
            return agent_id
            
        except Exception as e:
            logger.error(
                "Failed to register agent",
                agent_id=agent_id,
                error=str(e)
            )
            raise
    
    async def unregister(self, agent_id: str) -> bool:
        """
        注销智能体
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            bool: 注销是否成功
        """
        try:
            if agent_id not in self.registered_agents:
                return False
            
            # 清理相关数据
            self.registered_agents.pop(agent_id, None)
            self.agent_metadata.pop(agent_id, None)
            self.agent_permissions.pop(agent_id, None)
            self.agent_capabilities.pop(agent_id, None)
            self.trace_writers.pop(agent_id, None)
            
            # 通知配置管理器
            if self.parent_registry.config_manager:
                await self.parent_registry.config_manager.remove_agent_config(agent_id)
            
            logger.info("Agent unregistered successfully", agent_id=agent_id)
            return True
            
        except Exception as e:
            logger.error(
                "Failed to unregister agent",
                agent_id=agent_id,
                error=str(e)
            )
            return False
    
    async def get_agent_config(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取智能体配置
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            Optional[Dict[str, Any]]: 智能体配置
        """
        return self.registered_agents.get(agent_id)
    
    async def get_agent_tracer(self, agent_id: str):
        """
        获取Agent专用追踪器
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            TraceWriter: 追踪器实例
        """
        return self.trace_writers.get(agent_id)
    
    async def get_agent_permissions(self, agent_id: str) -> List[str]:
        """
        获取Agent权限
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            List[str]: 权限列表
        """
        return self.agent_permissions.get(agent_id, [])
    
    async def get_agent_capabilities(self, agent_id: str) -> List[str]:
        """
        获取Agent能力
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            List[str]: 能力列表
        """
        return self.agent_capabilities.get(agent_id, [])
    
    async def update_agent_permissions(
        self,
        agent_id: str,
        permissions: List[str]
    ) -> bool:
        """
        更新智能体权限
        
        Args:
            agent_id: 智能体ID
            permissions: 新的权限列表
            
        Returns:
            bool: 更新是否成功
        """
        try:
            if agent_id not in self.registered_agents:
                return False
            
            self.agent_permissions[agent_id] = permissions
            self.registered_agents[agent_id]["permissions"] = permissions
            
            # 更新元数据
            self.agent_metadata[agent_id]["updated_at"] = datetime.utcnow().isoformat()
            
            # 通知配置管理器
            if self.parent_registry.config_manager:
                await self.parent_registry.config_manager.update_agent_config(
                    agent_id, self.registered_agents[agent_id]
                )
            
            logger.info(
                "Agent permissions updated",
                agent_id=agent_id,
                permissions=permissions
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to update agent permissions",
                agent_id=agent_id,
                error=str(e)
            )
            return False
    
    async def update_agent_capabilities(
        self,
        agent_id: str,
        capabilities: List[str]
    ) -> bool:
        """
        更新智能体能力
        
        Args:
            agent_id: 智能体ID
            capabilities: 新的能力列表
            
        Returns:
            bool: 更新是否成功
        """
        try:
            if agent_id not in self.registered_agents:
                return False
            
            self.agent_capabilities[agent_id] = capabilities
            self.registered_agents[agent_id]["capabilities"] = capabilities
            
            # 更新元数据
            self.agent_metadata[agent_id]["updated_at"] = datetime.utcnow().isoformat()
            self.agent_metadata[agent_id]["capabilities"] = capabilities
            
            # 通知配置管理器
            if self.parent_registry.config_manager:
                await self.parent_registry.config_manager.update_agent_config(
                    agent_id, self.registered_agents[agent_id]
                )
            
            logger.info(
                "Agent capabilities updated",
                agent_id=agent_id,
                capabilities=capabilities
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to update agent capabilities",
                agent_id=agent_id,
                error=str(e)
            )
            return False
    
    async def list(self, filter_by: Dict[str, Any] = None) -> List[str]:
        """
        列出智能体
        
        Args:
            filter_by: 过滤条件
            
        Returns:
            List[str]: 智能体ID列表
        """
        if not filter_by:
            return list(self.registered_agents.keys())
        
        # 根据过滤条件返回智能体列表
        filtered_agents = []
        for agent_id, config in self.registered_agents.items():
            if self._matches_filter(config, filter_by):
                filtered_agents.append(agent_id)
        
        return filtered_agents
    
    async def search_agents(
        self,
        query: str = None,
        agent_type: str = None,
        capabilities: List[str] = None,
        model: str = None,
        status: str = None
    ) -> List[Dict[str, Any]]:
        """
        搜索智能体
        
        Args:
            query: 搜索关键词
            agent_type: 智能体类型
            capabilities: 能力列表
            model: 模型名称
            status: 状态
            
        Returns:
            List[Dict[str, Any]]: 匹配的智能体信息
        """
        results = []
        
        for agent_id, config in self.registered_agents.items():
            metadata = self.agent_metadata.get(agent_id, {})
            agent_capabilities = self.agent_capabilities.get(agent_id, [])
            
            # 文本搜索
            if query:
                text_fields = [
                    metadata.get("description", ""),
                    agent_id,
                    str(metadata.get("tags", []))
                ]
                if not any(query.lower() in field.lower() for field in text_fields):
                    continue
            
            # 类型过滤
            if agent_type and metadata.get("agent_type") != agent_type:
                continue
            
            # 能力过滤
            if capabilities:
                if not any(cap in agent_capabilities for cap in capabilities):
                    continue
            
            # 模型过滤
            if model and metadata.get("model") != model:
                continue
            
            # 状态过滤
            if status and metadata.get("status") != status:
                continue
            
            results.append({
                "agent_id": agent_id,
                "config": config,
                "metadata": metadata,
                "permissions": self.agent_permissions.get(agent_id, []),
                "capabilities": agent_capabilities,
                "trace_writer": self.trace_writers.get(agent_id)
            })
        
        return results
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """
        获取智能体统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        total_agents = len(self.registered_agents)
        
        # 按类型统计
        type_stats = {}
        for agent_id in self.registered_agents:
            metadata = self.agent_metadata.get(agent_id, {})
            agent_type = metadata.get("agent_type", "unknown")
            type_stats[agent_type] = type_stats.get(agent_type, 0) + 1
        
        # 按模型统计
        model_stats = {}
        for agent_id in self.registered_agents:
            metadata = self.agent_metadata.get(agent_id, {})
            model = metadata.get("model", "unknown")
            model_stats[model] = model_stats.get(model, 0) + 1
        
        # 能力统计
        capability_stats = {}
        for capabilities in self.agent_capabilities.values():
            for cap in capabilities:
                capability_stats[cap] = capability_stats.get(cap, 0) + 1
        
        # 状态统计
        status_stats = {}
        for agent_id in self.registered_agents:
            metadata = self.agent_metadata.get(agent_id, {})
            status = metadata.get("status", "unknown")
            status_stats[status] = status_stats.get(status, 0) + 1
        
        return {
            "total_agents": total_agents,
            "type_distribution": type_stats,
            "model_distribution": model_stats,
            "capability_distribution": capability_stats,
            "status_distribution": status_stats,
            "trace_enabled_count": len(self.trace_writers),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _create_agent_tracer(self, agent_id: str):
        """
        创建智能体专用追踪器
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            TraceWriter: 追踪器实例
        """
        if hasattr(self.parent_registry.trace_writer, 'create_agent_tracer'):
            return await self.parent_registry.trace_writer.create_agent_tracer(agent_id)
        elif hasattr(self.parent_registry.trace_writer, 'create_tracer'):
            return self.parent_registry.trace_writer.create_tracer(f"agent_{agent_id}")
        else:
            # 如果没有专用方法，返回原始追踪器
            return self.parent_registry.trace_writer
    
    def _matches_filter(self, config: Dict[str, Any], filter_by: Dict[str, Any]) -> bool:
        """
        检查配置是否匹配过滤条件
        
        Args:
            config: 智能体配置
            filter_by: 过滤条件
            
        Returns:
            bool: 是否匹配
        """
        for key, value in filter_by.items():
            if key in config:
                if isinstance(value, list):
                    if not any(v in config[key] for v in value):
                        return False
                else:
                    if config[key] != value:
                        return False
            else:
                return False


class ACPAgentRegistry:
    """ACP Agent 注册中心占位实现"""
    pass
 