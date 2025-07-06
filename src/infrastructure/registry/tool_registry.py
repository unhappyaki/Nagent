"""
Tool注册器
基础设施层组件，支持动态权限绑定、Trace策略注入
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger(__name__)


class ToolPermission:
    """工具权限"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class TraceLevel:
    """追踪级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ToolRegistry:
    """
    工具注册器
    
    基础设施层组件，负责：
    - 动态权限绑定：为每个工具配置细粒度权限
    - Trace策略注入：自动为工具注入追踪策略
    - 工具生命周期管理：注册、注销、配置更新
    """
    
    def __init__(self, parent_registry):
        """
        初始化工具注册器
        
        Args:
            parent_registry: 父注册中心
        """
        self.parent_registry = parent_registry
        self.registered_tools = {}
        self.tool_permissions = {}
        self.tool_trace_policies = {}
        self.tool_metadata = {}
        
        logger.info("ToolRegistry initialized")
    
    async def register(
        self,
        tool_id: str,
        tool_config: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        注册工具
        
        Args:
            tool_id: 工具唯一标识
            tool_config: 工具配置
            metadata: 元数据
            
        Returns:
            str: 注册成功的工具ID
        """
        try:
            # 1. 动态权限绑定
            permissions = tool_config.get("permissions", [ToolPermission.READ, ToolPermission.EXECUTE])
            self.tool_permissions[tool_id] = permissions
            
            # 2. Trace策略注入
            trace_policy = tool_config.get("trace_policy", {
                "enabled": True,
                "level": TraceLevel.INFO,
                "include_input": True,
                "include_output": True,
                "include_errors": True,
                "sampling_rate": 1.0
            })
            self.tool_trace_policies[tool_id] = trace_policy
            
            # 3. 元数据增强
            enhanced_metadata = {
                "tool_id": tool_id,
                "tool_type": tool_config.get("tool_type", "generic"),
                "version": tool_config.get("version", "1.0.0"),
                "description": tool_config.get("description", ""),
                "tags": tool_config.get("tags", []),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
            self.tool_metadata[tool_id] = enhanced_metadata
            
            # 4. 工具实例化配置
            tool_instance_config = {
                "tool_id": tool_id,
                "tool_class": tool_config.get("tool_class"),
                "tool_module": tool_config.get("tool_module"),
                "init_params": tool_config.get("init_params", {}),
                "permissions": permissions,
                "trace_policy": trace_policy,
                "metadata": enhanced_metadata,
                "config": tool_config
            }
            
            self.registered_tools[tool_id] = tool_instance_config
            
            # 5. 通知配置管理器更新
            if self.parent_registry.config_manager:
                await self.parent_registry.config_manager.update_tool_config(
                    tool_id, tool_instance_config
                )
            
            logger.info(
                "Tool registered successfully",
                tool_id=tool_id,
                permissions=permissions,
                trace_enabled=trace_policy["enabled"]
            )
            
            return tool_id
            
        except Exception as e:
            logger.error(
                "Failed to register tool",
                tool_id=tool_id,
                error=str(e)
            )
            raise
    
    async def unregister(self, tool_id: str) -> bool:
        """
        注销工具
        
        Args:
            tool_id: 工具ID
            
        Returns:
            bool: 注销是否成功
        """
        try:
            if tool_id not in self.registered_tools:
                return False
            
            # 清理相关数据
            self.registered_tools.pop(tool_id, None)
            self.tool_permissions.pop(tool_id, None)
            self.tool_trace_policies.pop(tool_id, None)
            self.tool_metadata.pop(tool_id, None)
            
            # 通知配置管理器
            if self.parent_registry.config_manager:
                await self.parent_registry.config_manager.remove_tool_config(tool_id)
            
            logger.info("Tool unregistered successfully", tool_id=tool_id)
            return True
            
        except Exception as e:
            logger.error(
                "Failed to unregister tool",
                tool_id=tool_id,
                error=str(e)
            )
            return False
    
    async def get_tool_config(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工具配置
        
        Args:
            tool_id: 工具ID
            
        Returns:
            Optional[Dict[str, Any]]: 工具配置
        """
        return self.registered_tools.get(tool_id)
    
    async def get_tool_permissions(self, tool_id: str) -> List[str]:
        """
        获取工具权限
        
        Args:
            tool_id: 工具ID
            
        Returns:
            List[str]: 权限列表
        """
        return self.tool_permissions.get(tool_id, [])
    
    async def get_tool_trace_policy(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工具追踪策略
        
        Args:
            tool_id: 工具ID
            
        Returns:
            Optional[Dict[str, Any]]: 追踪策略
        """
        return self.tool_trace_policies.get(tool_id)
    
    async def update_tool_permissions(
        self,
        tool_id: str,
        permissions: List[str]
    ) -> bool:
        """
        更新工具权限
        
        Args:
            tool_id: 工具ID
            permissions: 新的权限列表
            
        Returns:
            bool: 更新是否成功
        """
        try:
            if tool_id not in self.registered_tools:
                return False
            
            self.tool_permissions[tool_id] = permissions
            self.registered_tools[tool_id]["permissions"] = permissions
            
            # 更新元数据
            self.tool_metadata[tool_id]["updated_at"] = datetime.utcnow().isoformat()
            
            # 通知配置管理器
            if self.parent_registry.config_manager:
                await self.parent_registry.config_manager.update_tool_config(
                    tool_id, self.registered_tools[tool_id]
                )
            
            logger.info(
                "Tool permissions updated",
                tool_id=tool_id,
                permissions=permissions
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to update tool permissions",
                tool_id=tool_id,
                error=str(e)
            )
            return False
    
    async def update_tool_trace_policy(
        self,
        tool_id: str,
        trace_policy: Dict[str, Any]
    ) -> bool:
        """
        更新工具追踪策略
        
        Args:
            tool_id: 工具ID
            trace_policy: 新的追踪策略
            
        Returns:
            bool: 更新是否成功
        """
        try:
            if tool_id not in self.registered_tools:
                return False
            
            self.tool_trace_policies[tool_id] = trace_policy
            self.registered_tools[tool_id]["trace_policy"] = trace_policy
            
            # 更新元数据
            self.tool_metadata[tool_id]["updated_at"] = datetime.utcnow().isoformat()
            
            # 通知配置管理器
            if self.parent_registry.config_manager:
                await self.parent_registry.config_manager.update_tool_config(
                    tool_id, self.registered_tools[tool_id]
                )
            
            logger.info(
                "Tool trace policy updated",
                tool_id=tool_id,
                trace_enabled=trace_policy.get("enabled", True)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to update tool trace policy",
                tool_id=tool_id,
                error=str(e)
            )
            return False
    
    async def list(self, filter_by: Dict[str, Any] = None) -> List[str]:
        """
        列出工具
        
        Args:
            filter_by: 过滤条件
            
        Returns:
            List[str]: 工具ID列表
        """
        if not filter_by:
            return list(self.registered_tools.keys())
        
        # 根据过滤条件返回工具列表
        filtered_tools = []
        for tool_id, config in self.registered_tools.items():
            if self._matches_filter(config, filter_by):
                filtered_tools.append(tool_id)
        
        return filtered_tools
    
    async def search_tools(
        self,
        query: str = None,
        tool_type: str = None,
        tags: List[str] = None,
        permissions: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索工具
        
        Args:
            query: 搜索关键词
            tool_type: 工具类型
            tags: 标签列表
            permissions: 权限列表
            
        Returns:
            List[Dict[str, Any]]: 匹配的工具信息
        """
        results = []
        
        for tool_id, config in self.registered_tools.items():
            metadata = self.tool_metadata.get(tool_id, {})
            tool_permissions = self.tool_permissions.get(tool_id, [])
            
            # 文本搜索
            if query:
                text_fields = [
                    metadata.get("description", ""),
                    tool_id,
                    str(metadata.get("tags", []))
                ]
                if not any(query.lower() in field.lower() for field in text_fields):
                    continue
            
            # 类型过滤
            if tool_type and metadata.get("tool_type") != tool_type:
                continue
            
            # 标签过滤
            if tags:
                tool_tags = metadata.get("tags", [])
                if not any(tag in tool_tags for tag in tags):
                    continue
            
            # 权限过滤
            if permissions:
                if not any(perm in tool_permissions for perm in permissions):
                    continue
            
            results.append({
                "tool_id": tool_id,
                "config": config,
                "metadata": metadata,
                "permissions": tool_permissions,
                "trace_policy": self.tool_trace_policies.get(tool_id, {})
            })
        
        return results
    
    def get_tool_stats(self) -> Dict[str, Any]:
        """
        获取工具统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        total_tools = len(self.registered_tools)
        
        # 按类型统计
        type_stats = {}
        for tool_id in self.registered_tools:
            metadata = self.tool_metadata.get(tool_id, {})
            tool_type = metadata.get("tool_type", "unknown")
            type_stats[tool_type] = type_stats.get(tool_type, 0) + 1
        
        # 权限统计
        permission_stats = {}
        for permissions in self.tool_permissions.values():
            for perm in permissions:
                permission_stats[perm] = permission_stats.get(perm, 0) + 1
        
        # 追踪策略统计
        trace_enabled_count = sum(
            1 for policy in self.tool_trace_policies.values()
            if policy.get("enabled", True)
        )
        
        return {
            "total_tools": total_tools,
            "type_distribution": type_stats,
            "permission_distribution": permission_stats,
            "trace_enabled_count": trace_enabled_count,
            "trace_disabled_count": total_tools - trace_enabled_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _matches_filter(self, config: Dict[str, Any], filter_by: Dict[str, Any]) -> bool:
        """
        检查配置是否匹配过滤条件
        
        Args:
            config: 工具配置
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
        
        return True 