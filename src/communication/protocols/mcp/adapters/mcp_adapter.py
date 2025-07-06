"""
MCP适配器

与现有工具注册表集成，提供MCP工具的无缝接入
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Set
import structlog

from ..mcp_types import MCPServerConfig, MCPTool, MCPResult
from ..connection_manager import MCPConnectionManager
from ..mcp_client import MCPClient
from .tool_wrapper import MCPToolWrapper
from .external_tool_registry import ExternalToolRegistry

logger = structlog.get_logger(__name__)


class MCPAdapter:
    """MCP适配器，集成MCP工具到现有架构"""
    
    def __init__(
        self,
        tool_registry=None,
        connection_manager: Optional[MCPConnectionManager] = None
    ):
        """
        初始化MCP适配器
        
        Args:
            tool_registry: 现有工具注册表实例
            connection_manager: MCP连接管理器
        """
        self.tool_registry = tool_registry
        self.connection_manager = connection_manager or MCPConnectionManager()
        self.external_registry = ExternalToolRegistry()
        
        # MCP工具缓存
        self._mcp_tools: Dict[str, MCPToolWrapper] = {}
        self._server_tools: Dict[str, Set[str]] = {}  # server_name -> tool_names
        
        # 同步状态
        self._sync_task: Optional[asyncio.Task] = None
        self._sync_interval = 300  # 5分钟同步一次
        self._last_sync = 0
        
        # 统计信息
        self.stats = {
            "total_mcp_tools": 0,
            "registered_tools": 0,
            "sync_count": 0,
            "sync_errors": 0,
            "last_sync_time": None
        }
        
        logger.info("MCP adapter initialized")
    
    async def start(self) -> None:
        """启动MCP适配器"""
        try:
            # 启动连接管理器
            await self.connection_manager.start_health_monitoring()
            
            # 执行初始同步
            await self.sync_tools()
            
            # 启动定期同步任务
            await self.start_sync_task()
            
            logger.info("MCP adapter started successfully")
            
        except Exception as e:
            logger.error("Failed to start MCP adapter", error=str(e))
            raise
    
    async def stop(self) -> None:
        """停止MCP适配器"""
        try:
            # 停止同步任务
            await self.stop_sync_task()
            
            # 停止连接管理器
            await self.connection_manager.stop_health_monitoring()
            await self.connection_manager.close_all_connections()
            
            # 清理已注册的工具
            await self._cleanup_registered_tools()
            
            logger.info("MCP adapter stopped")
            
        except Exception as e:
            logger.error("Error stopping MCP adapter", error=str(e))
    
    async def add_mcp_server(self, server_config: MCPServerConfig) -> bool:
        """
        添加MCP服务器
        
        Args:
            server_config: 服务器配置
            
        Returns:
            添加是否成功
        """
        try:
            # 添加到连接管理器
            success = await self.connection_manager.add_server(server_config)
            
            if success:
                # 同步该服务器的工具
                await self.sync_server_tools(server_config.name)
                
                logger.info(
                    "MCP server added successfully",
                    server_name=server_config.name
                )
                return True
            else:
                logger.error(
                    "Failed to add MCP server",
                    server_name=server_config.name
                )
                return False
                
        except Exception as e:
            logger.error(
                "Error adding MCP server",
                server_name=server_config.name,
                error=str(e)
            )
            return False
    
    async def remove_mcp_server(self, server_name: str) -> bool:
        """
        移除MCP服务器
        
        Args:
            server_name: 服务器名称
            
        Returns:
            移除是否成功
        """
        try:
            # 清理该服务器的工具
            await self._cleanup_server_tools(server_name)
            
            # 从连接管理器移除
            success = await self.connection_manager.remove_server(server_name)
            
            if success:
                logger.info("MCP server removed successfully", server_name=server_name)
                return True
            else:
                logger.error("Failed to remove MCP server", server_name=server_name)
                return False
                
        except Exception as e:
            logger.error(
                "Error removing MCP server",
                server_name=server_name,
                error=str(e)
            )
            return False
    
    async def sync_tools(self) -> None:
        """同步所有MCP服务器的工具"""
        try:
            start_time = time.time()
            
            # 获取所有服务器连接
            server_names = self.connection_manager.get_server_names()
            
            # 并发同步所有服务器的工具
            sync_tasks = [
                self.sync_server_tools(server_name)
                for server_name in server_names
            ]
            
            if sync_tasks:
                results = await asyncio.gather(*sync_tasks, return_exceptions=True)
                
                # 统计结果
                success_count = sum(1 for r in results if r is True)
                error_count = len(results) - success_count
                
                logger.info(
                    "Tools sync completed",
                    total_servers=len(server_names),
                    success_count=success_count,
                    error_count=error_count,
                    duration=time.time() - start_time
                )
                
                if error_count > 0:
                    self.stats["sync_errors"] += error_count
            
            self.stats["sync_count"] += 1
            self.stats["last_sync_time"] = time.time()
            self._last_sync = time.time()
            
        except Exception as e:
            self.stats["sync_errors"] += 1
            logger.error("Error during tools sync", error=str(e))
            raise
    
    async def sync_server_tools(self, server_name: str) -> bool:
        """
        同步特定服务器的工具
        
        Args:
            server_name: 服务器名称
            
        Returns:
            同步是否成功
        """
        try:
            # 获取连接
            client = await self.connection_manager.get_connection(server_name)
            if not client:
                logger.warning(
                    "No connection available for server",
                    server_name=server_name
                )
                return False
            
            # 获取工具列表
            mcp_tools = await client.list_tools()
            
            # 清理旧工具
            await self._cleanup_server_tools(server_name)
            
            # 注册新工具
            registered_count = 0
            server_tools = set()
            
            for mcp_tool in mcp_tools:
                try:
                    # 创建工具包装器
                    tool_wrapper = MCPToolWrapper(
                        mcp_tool=mcp_tool,
                        mcp_client=client,
                        server_name=server_name
                    )
                    
                    # 生成唯一工具名称
                    unique_name = f"mcp_{server_name}_{mcp_tool.name}"
                    
                    # 缓存工具包装器
                    self._mcp_tools[unique_name] = tool_wrapper
                    server_tools.add(unique_name)
                    
                    # 注册到外部工具注册表
                    await self.external_registry.register_mcp_tool(
                        unique_name, tool_wrapper, server_name
                    )
                    
                    # 如果有现有工具注册表，也注册到那里
                    if self.tool_registry:
                        self.tool_registry.register_tool(
                            name=unique_name,
                            tool_func=tool_wrapper.execute,
                            description=mcp_tool.description or f"MCP tool from {server_name}",
                            metadata={
                                "source": "mcp",
                                "server_name": server_name,
                                "original_name": mcp_tool.name,
                                "mcp_tool": mcp_tool.to_dict()
                            }
                        )
                    
                    registered_count += 1
                    
                except Exception as e:
                    logger.error(
                        "Failed to register MCP tool",
                        server_name=server_name,
                        tool_name=mcp_tool.name,
                        error=str(e)
                    )
            
            # 更新服务器工具映射
            self._server_tools[server_name] = server_tools
            
            # 更新统计
            self.stats["total_mcp_tools"] = len(self._mcp_tools)
            self.stats["registered_tools"] = len(self._mcp_tools)
            
            logger.info(
                "Server tools synced successfully",
                server_name=server_name,
                total_tools=len(mcp_tools),
                registered_tools=registered_count
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Error syncing server tools",
                server_name=server_name,
                error=str(e)
            )
            return False
    
    async def get_mcp_tool(self, tool_name: str) -> Optional[MCPToolWrapper]:
        """
        获取MCP工具包装器
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具包装器
        """
        return self._mcp_tools.get(tool_name)
    
    async def list_mcp_tools(
        self,
        server_name: Optional[str] = None,
        pattern: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出MCP工具
        
        Args:
            server_name: 过滤服务器名称
            pattern: 搜索模式
            
        Returns:
            工具信息列表
        """
        tools = []
        
        for tool_name, wrapper in self._mcp_tools.items():
            # 服务器过滤
            if server_name and wrapper.server_name != server_name:
                continue
            
            # 模式匹配
            if pattern:
                if (pattern.lower() not in tool_name.lower() and
                    pattern.lower() not in (wrapper.mcp_tool.description or "").lower()):
                    continue
            
            tool_info = {
                "name": tool_name,
                "original_name": wrapper.mcp_tool.name,
                "server_name": wrapper.server_name,
                "description": wrapper.mcp_tool.description,
                "input_schema": wrapper.mcp_tool.inputSchema,
                "stats": await wrapper.get_stats()
            }
            tools.append(tool_info)
        
        return tools
    
    async def execute_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> MCPResult:
        """
        执行MCP工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            执行结果
        """
        tool_wrapper = self._mcp_tools.get(tool_name)
        if not tool_wrapper:
            return MCPResult.error(f"Tool not found: {tool_name}")
        
        try:
            result = await tool_wrapper.execute(**arguments)
            return MCPResult.success(result)
            
        except Exception as e:
            logger.error(
                "Error executing MCP tool",
                tool_name=tool_name,
                error=str(e)
            )
            return MCPResult.error(str(e))
    
    async def start_sync_task(self) -> None:
        """启动定期同步任务"""
        if self._sync_task is not None:
            logger.warning("Sync task already running")
            return
        
        self._sync_task = asyncio.create_task(self._sync_loop())
        logger.info("MCP tools sync task started")
    
    async def stop_sync_task(self) -> None:
        """停止定期同步任务"""
        if self._sync_task is not None:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
            self._sync_task = None
            logger.info("MCP tools sync task stopped")
    
    async def _sync_loop(self) -> None:
        """同步循环"""
        logger.debug("MCP tools sync loop started")
        
        try:
            while True:
                await asyncio.sleep(self._sync_interval)
                
                # 检查是否需要同步
                if time.time() - self._last_sync >= self._sync_interval:
                    try:
                        await self.sync_tools()
                    except Exception as e:
                        logger.error("Error in sync loop", error=str(e))
                        
        except asyncio.CancelledError:
            logger.debug("MCP tools sync loop cancelled")
            raise
        except Exception as e:
            logger.error("Error in MCP tools sync loop", error=str(e))
    
    async def _cleanup_server_tools(self, server_name: str) -> None:
        """清理服务器的工具"""
        if server_name not in self._server_tools:
            return
        
        tool_names = self._server_tools[server_name].copy()
        
        for tool_name in tool_names:
            # 从MCP工具缓存移除
            if tool_name in self._mcp_tools:
                del self._mcp_tools[tool_name]
            
            # 从外部工具注册表移除
            await self.external_registry.unregister_tool(tool_name)
            
            # 从现有工具注册表移除
            if self.tool_registry:
                self.tool_registry.unregister_tool(tool_name)
        
        # 清理服务器工具映射
        del self._server_tools[server_name]
        
        logger.debug(
            "Server tools cleaned up",
            server_name=server_name,
            tool_count=len(tool_names)
        )
    
    async def _cleanup_registered_tools(self) -> None:
        """清理所有已注册的工具"""
        for tool_name in list(self._mcp_tools.keys()):
            # 从外部工具注册表移除
            await self.external_registry.unregister_tool(tool_name)
            
            # 从现有工具注册表移除
            if self.tool_registry:
                self.tool_registry.unregister_tool(tool_name)
        
        # 清理缓存
        self._mcp_tools.clear()
        self._server_tools.clear()
        
        logger.info("All registered MCP tools cleaned up")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取适配器统计信息"""
        stats = self.stats.copy()
        
        # 添加连接管理器统计
        connection_stats = self.connection_manager.get_stats()
        stats["connection_manager"] = connection_stats
        
        # 添加外部工具注册表统计
        external_stats = self.external_registry.get_stats()
        stats["external_registry"] = external_stats
        
        # 添加服务器分布统计
        server_distribution = {}
        for server_name, tool_names in self._server_tools.items():
            server_distribution[server_name] = len(tool_names)
        stats["server_distribution"] = server_distribution
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health = {
            "adapter_status": "healthy",
            "connection_manager": "unknown",
            "external_registry": "healthy",
            "sync_task": "running" if self._sync_task and not self._sync_task.done() else "stopped",
            "last_sync_age": time.time() - self._last_sync if self._last_sync > 0 else None
        }
        
        try:
            # 检查连接管理器健康状态
            connection_health = await self.connection_manager.health_check()
            healthy_connections = sum(1 for h in connection_health.values() if h)
            total_connections = len(connection_health)
            
            if total_connections == 0:
                health["connection_manager"] = "no_connections"
            elif healthy_connections == total_connections:
                health["connection_manager"] = "healthy"
            elif healthy_connections > 0:
                health["connection_manager"] = "partial"
            else:
                health["connection_manager"] = "unhealthy"
                health["adapter_status"] = "degraded"
            
        except Exception as e:
            health["connection_manager"] = "error"
            health["adapter_status"] = "error"
            logger.error("Error during health check", error=str(e))
        
        return health
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop() 