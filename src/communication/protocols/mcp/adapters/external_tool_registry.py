"""
外部工具注册表

提供MCP工具的统一管理和分类
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import structlog

from .tool_wrapper import MCPToolWrapper

logger = structlog.get_logger(__name__)


class ToolCategory(Enum):
    """工具分类枚举"""
    FILESYSTEM = "filesystem"
    DATABASE = "database"
    API = "api"
    COMPUTATION = "computation"
    DATA_PROCESSING = "data_processing"
    COMMUNICATION = "communication"
    SECURITY = "security"
    MONITORING = "monitoring"
    AUTOMATION = "automation"
    UNKNOWN = "unknown"


class ToolStatus(Enum):
    """工具状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"


class ExternalToolInfo:
    """外部工具信息"""
    
    def __init__(
        self,
        name: str,
        wrapper: MCPToolWrapper,
        server_name: str,
        category: ToolCategory = ToolCategory.UNKNOWN,
        tags: Optional[Set[str]] = None
    ):
        self.name = name
        self.wrapper = wrapper
        self.server_name = server_name
        self.category = category
        self.tags = tags or set()
        self.status = ToolStatus.ACTIVE
        self.registered_at = time.time()
        self.last_health_check = None
        self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "server_name": self.server_name,
            "category": self.category.value,
            "tags": list(self.tags),
            "status": self.status.value,
            "registered_at": self.registered_at,
            "last_health_check": self.last_health_check,
            "metadata": self.metadata,
            "tool_info": self.wrapper.get_info()
        }


class ExternalToolRegistry:
    """外部工具注册表"""
    
    def __init__(self):
        """初始化外部工具注册表"""
        # 工具存储
        self._tools: Dict[str, ExternalToolInfo] = {}
        self._server_tools: Dict[str, Set[str]] = {}  # server -> tool_names
        self._category_tools: Dict[ToolCategory, Set[str]] = {}  # category -> tool_names
        self._tag_tools: Dict[str, Set[str]] = {}  # tag -> tool_names
        
        # 健康检查
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_interval = 300  # 5分钟
        
        # 统计信息
        self.stats = {
            "total_tools": 0,
            "active_tools": 0,
            "inactive_tools": 0,
            "error_tools": 0,
            "servers_count": 0,
            "categories_count": 0,
            "health_checks": 0,
            "last_health_check": None
        }
        
        # 初始化分类索引
        for category in ToolCategory:
            self._category_tools[category] = set()
        
        logger.info("External tool registry initialized")
    
    async def register_mcp_tool(
        self,
        name: str,
        wrapper: MCPToolWrapper,
        server_name: str,
        category: Optional[ToolCategory] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """
        注册MCP工具
        
        Args:
            name: 工具名称
            wrapper: 工具包装器
            server_name: 服务器名称
            category: 工具分类
            tags: 工具标签
            
        Returns:
            注册是否成功
        """
        try:
            # 自动分类
            if category is None:
                category = self._auto_categorize_tool(wrapper)
            
            # 自动标签
            if tags is None:
                tags = self._auto_tag_tool(wrapper)
            
            # 创建工具信息
            tool_info = ExternalToolInfo(
                name=name,
                wrapper=wrapper,
                server_name=server_name,
                category=category,
                tags=tags
            )
            
            # 存储工具
            self._tools[name] = tool_info
            
            # 更新索引
            self._update_indexes_on_add(name, tool_info)
            
            # 更新统计
            self._update_stats()
            
            logger.info(
                "MCP tool registered",
                tool_name=name,
                server_name=server_name,
                category=category.value,
                tags=list(tags)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to register MCP tool",
                tool_name=name,
                server_name=server_name,
                error=str(e)
            )
            return False
    
    async def unregister_tool(self, name: str) -> bool:
        """
        注销工具
        
        Args:
            name: 工具名称
            
        Returns:
            注销是否成功
        """
        try:
            if name not in self._tools:
                logger.warning("Tool not found for unregistration", tool_name=name)
                return False
            
            tool_info = self._tools[name]
            
            # 更新索引
            self._update_indexes_on_remove(name, tool_info)
            
            # 移除工具
            del self._tools[name]
            
            # 更新统计
            self._update_stats()
            
            logger.info(
                "Tool unregistered",
                tool_name=name,
                server_name=tool_info.server_name
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to unregister tool",
                tool_name=name,
                error=str(e)
            )
            return False
    
    def get_tool(self, name: str) -> Optional[ExternalToolInfo]:
        """
        获取工具信息
        
        Args:
            name: 工具名称
            
        Returns:
            工具信息
        """
        return self._tools.get(name)
    
    def get_tool_wrapper(self, name: str) -> Optional[MCPToolWrapper]:
        """
        获取工具包装器
        
        Args:
            name: 工具名称
            
        Returns:
            工具包装器
        """
        tool_info = self._tools.get(name)
        return tool_info.wrapper if tool_info else None
    
    def list_tools(
        self,
        server_name: Optional[str] = None,
        category: Optional[ToolCategory] = None,
        tags: Optional[Set[str]] = None,
        status: Optional[ToolStatus] = None,
        pattern: Optional[str] = None
    ) -> List[ExternalToolInfo]:
        """
        列出工具
        
        Args:
            server_name: 过滤服务器名称
            category: 过滤分类
            tags: 过滤标签（包含任意一个标签）
            status: 过滤状态
            pattern: 搜索模式
            
        Returns:
            工具信息列表
        """
        tools = []
        
        for tool_info in self._tools.values():
            # 服务器过滤
            if server_name and tool_info.server_name != server_name:
                continue
            
            # 分类过滤
            if category and tool_info.category != category:
                continue
            
            # 标签过滤
            if tags and not tags.intersection(tool_info.tags):
                continue
            
            # 状态过滤
            if status and tool_info.status != status:
                continue
            
            # 模式匹配
            if pattern:
                pattern_lower = pattern.lower()
                if (pattern_lower not in tool_info.name.lower() and
                    pattern_lower not in tool_info.wrapper.description.lower() and
                    not any(pattern_lower in tag.lower() for tag in tool_info.tags)):
                    continue
            
            tools.append(tool_info)
        
        return tools
    
    def get_tools_by_server(self, server_name: str) -> List[ExternalToolInfo]:
        """
        获取特定服务器的工具
        
        Args:
            server_name: 服务器名称
            
        Returns:
            工具信息列表
        """
        tool_names = self._server_tools.get(server_name, set())
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def get_tools_by_category(self, category: ToolCategory) -> List[ExternalToolInfo]:
        """
        获取特定分类的工具
        
        Args:
            category: 工具分类
            
        Returns:
            工具信息列表
        """
        tool_names = self._category_tools.get(category, set())
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def get_tools_by_tag(self, tag: str) -> List[ExternalToolInfo]:
        """
        获取特定标签的工具
        
        Args:
            tag: 标签
            
        Returns:
            工具信息列表
        """
        tool_names = self._tag_tools.get(tag, set())
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    async def set_tool_status(self, name: str, status: ToolStatus) -> bool:
        """
        设置工具状态
        
        Args:
            name: 工具名称
            status: 新状态
            
        Returns:
            设置是否成功
        """
        if name not in self._tools:
            return False
        
        old_status = self._tools[name].status
        self._tools[name].status = status
        
        # 更新统计
        self._update_stats()
        
        logger.debug(
            "Tool status updated",
            tool_name=name,
            old_status=old_status.value,
            new_status=status.value
        )
        
        return True
    
    async def update_tool_metadata(
        self,
        name: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        更新工具元数据
        
        Args:
            name: 工具名称
            metadata: 元数据
            
        Returns:
            更新是否成功
        """
        if name not in self._tools:
            return False
        
        self._tools[name].metadata.update(metadata)
        
        logger.debug("Tool metadata updated", tool_name=name)
        
        return True
    
    async def health_check_all(self) -> Dict[str, bool]:
        """
        检查所有工具的健康状态
        
        Returns:
            工具健康状态映射
        """
        health_results = {}
        current_time = time.time()
        
        for name, tool_info in self._tools.items():
            try:
                # 检查工具包装器健康状态
                is_healthy = tool_info.wrapper.is_healthy()
                
                # 更新工具状态
                if is_healthy:
                    if tool_info.status == ToolStatus.ERROR:
                        tool_info.status = ToolStatus.ACTIVE
                else:
                    tool_info.status = ToolStatus.ERROR
                
                # 更新健康检查时间
                tool_info.last_health_check = current_time
                
                health_results[name] = is_healthy
                
            except Exception as e:
                logger.error(
                    "Error during tool health check",
                    tool_name=name,
                    error=str(e)
                )
                tool_info.status = ToolStatus.ERROR
                tool_info.last_health_check = current_time
                health_results[name] = False
        
        # 更新统计
        self.stats["health_checks"] += 1
        self.stats["last_health_check"] = current_time
        self._update_stats()
        
        healthy_count = sum(1 for h in health_results.values() if h)
        total_count = len(health_results)
        
        logger.info(
            "Health check completed",
            total_tools=total_count,
            healthy_tools=healthy_count,
            unhealthy_tools=total_count - healthy_count
        )
        
        return health_results
    
    async def start_health_monitoring(self) -> None:
        """开始健康监控"""
        if self._health_check_task is not None:
            logger.warning("Health monitoring already running")
            return
        
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("External tool health monitoring started")
    
    async def stop_health_monitoring(self) -> None:
        """停止健康监控"""
        if self._health_check_task is not None:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("External tool health monitoring stopped")
    
    def _auto_categorize_tool(self, wrapper: MCPToolWrapper) -> ToolCategory:
        """自动分类工具"""
        tool_name = wrapper.name.lower()
        description = (wrapper.description or "").lower()
        
        # 基于名称和描述的关键词匹配
        if any(keyword in tool_name or keyword in description 
               for keyword in ["file", "directory", "folder", "path", "fs"]):
            return ToolCategory.FILESYSTEM
        
        if any(keyword in tool_name or keyword in description 
               for keyword in ["database", "sql", "query", "db", "table"]):
            return ToolCategory.DATABASE
        
        if any(keyword in tool_name or keyword in description 
               for keyword in ["api", "http", "rest", "request", "web"]):
            return ToolCategory.API
        
        if any(keyword in tool_name or keyword in description 
               for keyword in ["calculate", "compute", "math", "algorithm"]):
            return ToolCategory.COMPUTATION
        
        if any(keyword in tool_name or keyword in description 
               for keyword in ["process", "transform", "parse", "convert"]):
            return ToolCategory.DATA_PROCESSING
        
        if any(keyword in tool_name or keyword in description 
               for keyword in ["email", "message", "send", "notify"]):
            return ToolCategory.COMMUNICATION
        
        if any(keyword in tool_name or keyword in description 
               for keyword in ["security", "auth", "encrypt", "decrypt"]):
            return ToolCategory.SECURITY
        
        if any(keyword in tool_name or keyword in description 
               for keyword in ["monitor", "watch", "check", "status"]):
            return ToolCategory.MONITORING
        
        if any(keyword in tool_name or keyword in description 
               for keyword in ["automate", "schedule", "task", "job"]):
            return ToolCategory.AUTOMATION
        
        return ToolCategory.UNKNOWN
    
    def _auto_tag_tool(self, wrapper: MCPToolWrapper) -> Set[str]:
        """自动为工具添加标签"""
        tags = set()
        
        tool_name = wrapper.name.lower()
        description = (wrapper.description or "").lower()
        server_name = wrapper.server_name.lower()
        
        # 基于服务器名称添加标签
        tags.add(f"server:{server_name}")
        
        # 基于工具名称和描述添加功能标签
        keywords_map = {
            "read": ["read", "get", "fetch", "retrieve"],
            "write": ["write", "create", "save", "store"],
            "delete": ["delete", "remove", "clear"],
            "update": ["update", "modify", "change", "edit"],
            "search": ["search", "find", "query", "lookup"],
            "analyze": ["analyze", "process", "compute", "calculate"],
            "send": ["send", "transmit", "deliver", "notify"],
            "convert": ["convert", "transform", "format", "encode"]
        }
        
        for tag, keywords in keywords_map.items():
            if any(keyword in tool_name or keyword in description 
                   for keyword in keywords):
                tags.add(tag)
        
        return tags
    
    def _update_indexes_on_add(self, name: str, tool_info: ExternalToolInfo) -> None:
        """添加工具时更新索引"""
        # 服务器索引
        if tool_info.server_name not in self._server_tools:
            self._server_tools[tool_info.server_name] = set()
        self._server_tools[tool_info.server_name].add(name)
        
        # 分类索引
        self._category_tools[tool_info.category].add(name)
        
        # 标签索引
        for tag in tool_info.tags:
            if tag not in self._tag_tools:
                self._tag_tools[tag] = set()
            self._tag_tools[tag].add(name)
    
    def _update_indexes_on_remove(self, name: str, tool_info: ExternalToolInfo) -> None:
        """移除工具时更新索引"""
        # 服务器索引
        if tool_info.server_name in self._server_tools:
            self._server_tools[tool_info.server_name].discard(name)
            if not self._server_tools[tool_info.server_name]:
                del self._server_tools[tool_info.server_name]
        
        # 分类索引
        self._category_tools[tool_info.category].discard(name)
        
        # 标签索引
        for tag in tool_info.tags:
            if tag in self._tag_tools:
                self._tag_tools[tag].discard(name)
                if not self._tag_tools[tag]:
                    del self._tag_tools[tag]
    
    def _update_stats(self) -> None:
        """更新统计信息"""
        self.stats["total_tools"] = len(self._tools)
        self.stats["servers_count"] = len(self._server_tools)
        self.stats["categories_count"] = len([c for c in self._category_tools.values() if c])
        
        # 状态统计
        status_counts = {}
        for status in ToolStatus:
            status_counts[status] = 0
        
        for tool_info in self._tools.values():
            status_counts[tool_info.status] += 1
        
        self.stats["active_tools"] = status_counts[ToolStatus.ACTIVE]
        self.stats["inactive_tools"] = status_counts[ToolStatus.INACTIVE]
        self.stats["error_tools"] = status_counts[ToolStatus.ERROR]
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        logger.debug("External tool health check loop started")
        
        try:
            while True:
                await asyncio.sleep(self._health_check_interval)
                
                try:
                    await self.health_check_all()
                except Exception as e:
                    logger.error("Error in health check loop", error=str(e))
                    
        except asyncio.CancelledError:
            logger.debug("External tool health check loop cancelled")
            raise
        except Exception as e:
            logger.error("Error in external tool health check loop", error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        
        # 添加分类分布
        category_distribution = {}
        for category, tool_names in self._category_tools.items():
            if tool_names:
                category_distribution[category.value] = len(tool_names)
        stats["category_distribution"] = category_distribution
        
        # 添加服务器分布
        server_distribution = {}
        for server_name, tool_names in self._server_tools.items():
            server_distribution[server_name] = len(tool_names)
        stats["server_distribution"] = server_distribution
        
        # 添加标签统计
        stats["total_tags"] = len(self._tag_tools)
        
        return stats
    
    def export_catalog(self) -> Dict[str, Any]:
        """导出工具目录"""
        catalog = {
            "version": "1.0",
            "exported_at": time.time(),
            "stats": self.get_stats(),
            "tools": []
        }
        
        for tool_info in self._tools.values():
            catalog["tools"].append(tool_info.to_dict())
        
        return catalog
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start_health_monitoring()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop_health_monitoring() 