"""
MCP连接管理器

管理多个MCP服务器连接的生命周期
"""

import asyncio
from typing import Dict, List, Optional, Set
import structlog

from .mcp_types import MCPServerConfig, MCPClientConfig, ConnectionStatus
from .mcp_client import MCPClient

logger = structlog.get_logger(__name__)


class MCPConnectionManager:
    """MCP连接管理器"""
    
    def __init__(self, client_config: Optional[MCPClientConfig] = None):
        """
        初始化连接管理器
        
        Args:
            client_config: 客户端配置
        """
        self.client_config = client_config or MCPClientConfig()
        
        # 连接池
        self.connections: Dict[str, MCPClient] = {}
        self.server_configs: Dict[str, MCPServerConfig] = {}
        
        # 健康检查
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_interval = 60  # 每60秒检查一次
        
        # 统计信息
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "failed_connections": 0,
            "total_reconnects": 0
        }
        
        logger.info("MCP connection manager initialized")
    
    async def add_server(self, server_config: MCPServerConfig) -> bool:
        """
        添加MCP服务器配置
        
        Args:
            server_config: 服务器配置
            
        Returns:
            添加是否成功
        """
        try:
            server_name = server_config.name
            
            if server_name in self.server_configs:
                logger.warning(
                    "MCP server already exists",
                    server_name=server_name
                )
                return False
            
            # 保存配置
            self.server_configs[server_name] = server_config
            
            # 如果服务器启用，立即创建连接
            if server_config.enabled:
                await self.create_connection(server_config)
            
            logger.info(
                "MCP server added",
                server_name=server_name,
                enabled=server_config.enabled
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to add MCP server",
                server_name=server_config.name,
                error=str(e)
            )
            return False
    
    async def remove_server(self, server_name: str) -> bool:
        """
        移除MCP服务器
        
        Args:
            server_name: 服务器名称
            
        Returns:
            移除是否成功
        """
        try:
            # 关闭连接
            if server_name in self.connections:
                await self.close_connection(server_name)
            
            # 移除配置
            if server_name in self.server_configs:
                del self.server_configs[server_name]
            
            logger.info("MCP server removed", server_name=server_name)
            return True
            
        except Exception as e:
            logger.error(
                "Failed to remove MCP server",
                server_name=server_name,
                error=str(e)
            )
            return False
    
    async def create_connection(self, server_config: MCPServerConfig) -> Optional[MCPClient]:
        """
        创建MCP连接
        
        Args:
            server_config: 服务器配置
            
        Returns:
            MCP客户端实例
        """
        server_name = server_config.name
        
        try:
            # 检查是否已存在连接
            if server_name in self.connections:
                existing_client = self.connections[server_name]
                if existing_client.is_healthy():
                    logger.debug(
                        "MCP connection already exists and healthy",
                        server_name=server_name
                    )
                    return existing_client
                else:
                    # 关闭不健康的连接
                    await self._cleanup_connection(server_name)
            
            # 创建新的客户端
            client = MCPClient(server_config, self.client_config)
            
            # 尝试连接
            if await client.connect():
                self.connections[server_name] = client
                self.stats["total_connections"] += 1
                self.stats["active_connections"] += 1
                
                logger.info(
                    "MCP connection created successfully",
                    server_name=server_name
                )
                
                return client
            else:
                self.stats["failed_connections"] += 1
                logger.error(
                    "Failed to connect to MCP server",
                    server_name=server_name
                )
                return None
                
        except Exception as e:
            self.stats["failed_connections"] += 1
            logger.error(
                "Error creating MCP connection",
                server_name=server_name,
                error=str(e)
            )
            return None
    
    async def get_connection(self, server_name: str) -> Optional[MCPClient]:
        """
        获取MCP连接
        
        Args:
            server_name: 服务器名称
            
        Returns:
            MCP客户端实例
        """
        # 检查是否存在连接
        if server_name not in self.connections:
            # 尝试创建连接
            if server_name in self.server_configs:
                server_config = self.server_configs[server_name]
                if server_config.enabled:
                    return await self.create_connection(server_config)
            return None
        
        client = self.connections[server_name]
        
        # 检查连接健康状态
        if not client.is_healthy():
            logger.warning(
                "MCP connection unhealthy, attempting reconnect",
                server_name=server_name
            )
            
            # 尝试重新连接
            if server_name in self.server_configs:
                server_config = self.server_configs[server_name]
                if server_config.enabled:
                    await self._cleanup_connection(server_name)
                    return await self.create_connection(server_config)
            
            return None
        
        return client
    
    async def close_connection(self, server_name: str) -> bool:
        """
        关闭MCP连接
        
        Args:
            server_name: 服务器名称
            
        Returns:
            关闭是否成功
        """
        try:
            if server_name in self.connections:
                client = self.connections[server_name]
                await client.disconnect()
                await self._cleanup_connection(server_name)
                
                logger.info("MCP connection closed", server_name=server_name)
                return True
            else:
                logger.debug(
                    "MCP connection not found",
                    server_name=server_name
                )
                return False
                
        except Exception as e:
            logger.error(
                "Error closing MCP connection",
                server_name=server_name,
                error=str(e)
            )
            return False
    
    async def close_all_connections(self) -> None:
        """关闭所有MCP连接"""
        logger.info("Closing all MCP connections")
        
        # 获取所有连接名称的副本
        server_names = list(self.connections.keys())
        
        # 并发关闭所有连接
        tasks = [
            self.close_connection(server_name)
            for server_name in server_names
        ]
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("All MCP connections closed")
    
    async def health_check(self) -> Dict[str, bool]:
        """
        检查所有连接的健康状态
        
        Returns:
            连接健康状态映射
        """
        health_status = {}
        
        for server_name, client in self.connections.items():
            try:
                healthy = client.is_healthy()
                health_status[server_name] = healthy
                
                if not healthy:
                    logger.warning(
                        "MCP connection unhealthy",
                        server_name=server_name,
                        status=client.get_status().value
                    )
                    
            except Exception as e:
                health_status[server_name] = False
                logger.error(
                    "Error checking MCP connection health",
                    server_name=server_name,
                    error=str(e)
                )
        
        return health_status
    
    async def start_health_monitoring(self) -> None:
        """开始健康监控"""
        if self._health_check_task is not None:
            logger.warning("Health monitoring already started")
            return
        
        self._health_check_task = asyncio.create_task(self._health_monitoring_loop())
        logger.info("Health monitoring started")
    
    async def stop_health_monitoring(self) -> None:
        """停止健康监控"""
        if self._health_check_task is not None:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Health monitoring stopped")
    
    async def _health_monitoring_loop(self) -> None:
        """健康监控循环"""
        logger.debug("Health monitoring loop started")
        
        try:
            while True:
                await asyncio.sleep(self._health_check_interval)
                
                # 检查所有连接健康状态
                health_status = await self.health_check()
                
                # 尝试重新连接不健康的连接
                for server_name, healthy in health_status.items():
                    if not healthy and server_name in self.server_configs:
                        server_config = self.server_configs[server_name]
                        if server_config.enabled:
                            logger.info(
                                "Attempting to reconnect unhealthy MCP connection",
                                server_name=server_name
                            )
                            
                            await self._cleanup_connection(server_name)
                            await self.create_connection(server_config)
                            self.stats["total_reconnects"] += 1
                
        except asyncio.CancelledError:
            logger.debug("Health monitoring loop cancelled")
            raise
        except Exception as e:
            logger.error("Error in health monitoring loop", error=str(e))
    
    async def _cleanup_connection(self, server_name: str) -> None:
        """清理连接"""
        if server_name in self.connections:
            client = self.connections[server_name]
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(
                    "Error during connection cleanup",
                    server_name=server_name,
                    error=str(e)
                )
            finally:
                del self.connections[server_name]
                self.stats["active_connections"] = max(0, self.stats["active_connections"] - 1)
    
    def get_connection_names(self) -> List[str]:
        """获取所有连接名称"""
        return list(self.connections.keys())
    
    def get_server_names(self) -> List[str]:
        """获取所有服务器名称"""
        return list(self.server_configs.keys())
    
    def get_stats(self) -> Dict[str, any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats["configured_servers"] = len(self.server_configs)
        stats["active_connections"] = len(self.connections)
        
        # 添加每个连接的统计
        connection_stats = {}
        for server_name, client in self.connections.items():
            connection_stats[server_name] = client.get_stats()
        
        stats["connections"] = connection_stats
        return stats
    
    async def reload_configuration(self, new_configs: List[MCPServerConfig]) -> None:
        """
        重新加载配置
        
        Args:
            new_configs: 新的服务器配置列表
        """
        logger.info("Reloading MCP server configurations")
        
        # 构建新配置映射
        new_config_map = {config.name: config for config in new_configs}
        
        # 移除不再存在的服务器
        current_servers = set(self.server_configs.keys())
        new_servers = set(new_config_map.keys())
        
        # 移除的服务器
        for server_name in current_servers - new_servers:
            await self.remove_server(server_name)
        
        # 添加或更新服务器
        for server_name, config in new_config_map.items():
            if server_name in self.server_configs:
                # 检查配置是否有变化
                old_config = self.server_configs[server_name]
                if old_config.to_dict() != config.to_dict():
                    # 配置有变化，重新创建连接
                    logger.info(
                        "MCP server configuration changed, recreating connection",
                        server_name=server_name
                    )
                    await self.remove_server(server_name)
                    await self.add_server(config)
                elif old_config.enabled != config.enabled:
                    # 只是启用状态变化
                    if config.enabled and server_name not in self.connections:
                        await self.create_connection(config)
                    elif not config.enabled and server_name in self.connections:
                        await self.close_connection(server_name)
                    self.server_configs[server_name] = config
            else:
                # 新增服务器
                await self.add_server(config)
        
        logger.info("MCP server configurations reloaded")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start_health_monitoring()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop_health_monitoring()
        await self.close_all_connections() 