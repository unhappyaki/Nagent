"""
MCP客户端实现

提供与MCP服务器通信的客户端接口
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
import structlog

from .mcp_types import (
    MCPMessage, MCPTool, MCPResource, MCPResourceContent, MCPResult,
    MCPServerConfig, MCPClientConfig, ConnectionStatus, Transport
)
from .protocol_handler import MCPProtocolHandler
from .transports.base_transport import BaseTransport
from .transports.stdio_transport import StdioTransport

logger = structlog.get_logger(__name__)


class MCPClient:
    """MCP协议客户端"""
    
    def __init__(
        self,
        server_config: MCPServerConfig,
        client_config: Optional[MCPClientConfig] = None
    ):
        """
        初始化MCP客户端
        
        Args:
            server_config: 服务器配置
            client_config: 客户端配置
        """
        self.server_config = server_config
        self.client_config = client_config or MCPClientConfig()
        
        # 核心组件
        self.protocol_handler = MCPProtocolHandler()
        self.transport: Optional[BaseTransport] = None
        
        # 状态管理
        self.status = ConnectionStatus.DISCONNECTED
        self.connected_at: Optional[float] = None
        self.last_activity: Optional[float] = None
        
        # 缓存
        self._tools_cache: Optional[List[MCPTool]] = None
        self._resources_cache: Optional[List[MCPResource]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl = 300  # 5分钟缓存
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tools_called": 0,
            "total_resources_read": 0,
            "connection_count": 0,
            "last_error": None
        }
        
        # 设置协议处理器的消息处理函数
        self._setup_transport()
    
    def _setup_transport(self) -> None:
        """设置传输协议"""
        if not self.server_config.transport:
            raise ValueError("No transport configuration provided")
        
        transport_config = self.server_config.transport
        
        if transport_config.type == Transport.STDIO:
            self.transport = StdioTransport(transport_config)
        elif transport_config.type == Transport.HTTP:
            # TODO: 实现HTTP传输
            raise NotImplementedError("HTTP transport not yet implemented")
        elif transport_config.type == Transport.WEBSOCKET:
            # TODO: 实现WebSocket传输
            raise NotImplementedError("WebSocket transport not yet implemented")
        else:
            raise ValueError(f"Unsupported transport type: {transport_config.type}")
        
        # 设置消息处理器
        self.transport.set_message_handler(self._handle_incoming_message)
    
    async def connect(self) -> bool:
        """
        连接到MCP服务器
        
        Returns:
            连接是否成功
        """
        if self.status == ConnectionStatus.CONNECTED:
            logger.warning("Already connected to MCP server")
            return True
        
        try:
            self.status = ConnectionStatus.CONNECTING
            logger.info(
                "Connecting to MCP server",
                server_name=self.server_config.name,
                transport_type=self.server_config.transport.type.value
            )
            
            # 建立传输连接
            if not await self.transport.connect():
                raise RuntimeError("Failed to establish transport connection")
            
            # 发送初始化请求
            await self._initialize_connection()
            
            # 更新状态
            self.status = ConnectionStatus.CONNECTED
            self.connected_at = time.time()
            self.last_activity = time.time()
            self.stats["connection_count"] += 1
            
            logger.info(
                "Successfully connected to MCP server",
                server_name=self.server_config.name
            )
            
            return True
            
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.stats["last_error"] = str(e)
            
            logger.error(
                "Failed to connect to MCP server",
                server_name=self.server_config.name,
                error=str(e)
            )
            
            # 清理连接
            await self._cleanup()
            return False
    
    async def disconnect(self) -> bool:
        """
        断开与MCP服务器的连接
        
        Returns:
            断开是否成功
        """
        try:
            logger.info(
                "Disconnecting from MCP server",
                server_name=self.server_config.name
            )
            
            await self._cleanup()
            
            logger.info(
                "Successfully disconnected from MCP server",
                server_name=self.server_config.name
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Error during disconnect",
                server_name=self.server_config.name,
                error=str(e)
            )
            return False
    
    async def list_tools(self, use_cache: bool = True) -> List[MCPTool]:
        """
        获取可用工具列表
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            工具列表
        """
        # 检查缓存
        if use_cache and self._is_cache_valid():
            return self._tools_cache or []
        
        try:
            self._update_activity()
            
            # 发送工具列表请求
            result = await self._send_request("tools/list")
            
            # 解析工具列表
            tools_data = result.get("tools", [])
            tools = [MCPTool.from_dict(tool_data) for tool_data in tools_data]
            
            # 更新缓存
            self._tools_cache = tools
            self._cache_timestamp = time.time()
            
            logger.debug(
                "Retrieved tools list",
                server_name=self.server_config.name,
                tool_count=len(tools)
            )
            
            return tools
            
        except Exception as e:
            logger.error(
                "Failed to list tools",
                server_name=self.server_config.name,
                error=str(e)
            )
            raise
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: int = 30
    ) -> MCPResult:
        """
        调用MCP工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            timeout: 超时时间
            
        Returns:
            执行结果
        """
        try:
            self._update_activity()
            start_time = time.time()
            
            logger.debug(
                "Calling MCP tool",
                server_name=self.server_config.name,
                tool_name=tool_name,
                arguments_count=len(arguments)
            )
            
            # 发送工具调用请求
            result = await self._send_request(
                "tools/call",
                {
                    "name": tool_name,
                    "arguments": arguments
                },
                timeout
            )
            
            # 更新统计
            execution_time = time.time() - start_time
            self.stats["total_tools_called"] += 1
            
            logger.debug(
                "MCP tool executed successfully",
                server_name=self.server_config.name,
                tool_name=tool_name,
                execution_time=execution_time
            )
            
            return MCPResult.success(result)
            
        except Exception as e:
            logger.error(
                "Failed to call MCP tool",
                server_name=self.server_config.name,
                tool_name=tool_name,
                error=str(e)
            )
            return MCPResult.error(str(e))
    
    async def list_resources(self, use_cache: bool = True) -> List[MCPResource]:
        """
        获取可用资源列表
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            资源列表
        """
        # 检查缓存
        if use_cache and self._is_cache_valid():
            return self._resources_cache or []
        
        try:
            self._update_activity()
            
            # 发送资源列表请求
            result = await self._send_request("resources/list")
            
            # 解析资源列表
            resources_data = result.get("resources", [])
            resources = [MCPResource.from_dict(res_data) for res_data in resources_data]
            
            # 更新缓存
            self._resources_cache = resources
            self._cache_timestamp = time.time()
            
            logger.debug(
                "Retrieved resources list",
                server_name=self.server_config.name,
                resource_count=len(resources)
            )
            
            return resources
            
        except Exception as e:
            logger.error(
                "Failed to list resources",
                server_name=self.server_config.name,
                error=str(e)
            )
            raise
    
    async def read_resource(self, resource_uri: str) -> MCPResourceContent:
        """
        读取资源内容
        
        Args:
            resource_uri: 资源URI
            
        Returns:
            资源内容
        """
        try:
            self._update_activity()
            
            logger.debug(
                "Reading MCP resource",
                server_name=self.server_config.name,
                resource_uri=resource_uri
            )
            
            # 发送资源读取请求
            result = await self._send_request(
                "resources/read",
                {"uri": resource_uri}
            )
            
            # 解析资源内容
            contents = result.get("contents", [])
            if contents:
                content_data = contents[0]  # 取第一个内容
                content = MCPResourceContent.from_dict(content_data)
                
                # 更新统计
                self.stats["total_resources_read"] += 1
                
                logger.debug(
                    "MCP resource read successfully",
                    server_name=self.server_config.name,
                    resource_uri=resource_uri
                )
                
                return content
            else:
                raise ValueError("No content in resource response")
            
        except Exception as e:
            logger.error(
                "Failed to read MCP resource",
                server_name=self.server_config.name,
                resource_uri=resource_uri,
                error=str(e)
            )
            raise
    
    async def _initialize_connection(self) -> None:
        """初始化连接"""
        # 发送初始化请求
        init_result = await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": False},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "Nagent MCP Client",
                    "version": "1.0.0"
                }
            }
        )
        
        # 发送初始化完成通知
        await self._send_notification("initialized")
        
        logger.debug(
            "MCP connection initialized",
            server_name=self.server_config.name,
            server_info=init_result.get("serverInfo", {})
        )
    
    async def _send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = None
    ) -> Any:
        """发送请求并等待响应"""
        if self.status != ConnectionStatus.CONNECTED:
            raise RuntimeError("Not connected to MCP server")
        
        timeout = timeout or self.client_config.default_timeout
        
        try:
            self.stats["total_requests"] += 1
            
            # 通过协议处理器发送请求
            request, future = await self.protocol_handler.send_request(
                method, params, timeout
            )
            
            # 通过传输层发送请求
            if not await self.transport.send_message(request):
                raise RuntimeError("Failed to send request message")
            
            # 等待响应
            result = await asyncio.wait_for(future, timeout=timeout)
            
            self.stats["successful_requests"] += 1
            return result
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            self.stats["last_error"] = str(e)
            raise
    
    async def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """发送通知（不等待响应）"""
        if self.status != ConnectionStatus.CONNECTED:
            raise RuntimeError("Not connected to MCP server")
        
        notification = MCPMessage(
            method=method,
            params=params
        )
        
        if not await self.transport.send_message(notification):
            raise RuntimeError("Failed to send notification message")
    
    def _handle_incoming_message(self, message: MCPMessage) -> None:
        """处理接收到的消息"""
        self._update_activity()
        
        # 通过协议处理器处理消息
        asyncio.create_task(self._process_incoming_message(message))
    
    async def _process_incoming_message(self, message: MCPMessage) -> None:
        """异步处理接收到的消息"""
        try:
            response = await self.protocol_handler.handle_message(message)
            
            # 如果有响应，发送回去
            if response:
                await self.transport.send_message(response)
                
        except Exception as e:
            logger.error(
                "Error processing incoming message",
                message_id=message.id,
                method=message.method,
                error=str(e)
            )
    
    def _update_activity(self) -> None:
        """更新最后活动时间"""
        self.last_activity = time.time()
    
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self._cache_timestamp:
            return False
        
        return (time.time() - self._cache_timestamp) < self._cache_ttl
    
    def _clear_cache(self) -> None:
        """清理缓存"""
        self._tools_cache = None
        self._resources_cache = None
        self._cache_timestamp = None
    
    async def _cleanup(self) -> None:
        """清理资源"""
        self.status = ConnectionStatus.DISCONNECTED
        
        # 清理协议处理器
        self.protocol_handler.cleanup_pending_requests()
        
        # 清理传输层
        if self.transport:
            await self.transport.disconnect()
        
        # 清理缓存
        self._clear_cache()
        
        self.connected_at = None
        self.last_activity = None
    
    def get_status(self) -> ConnectionStatus:
        """获取连接状态"""
        return self.status
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        
        if self.connected_at:
            stats["connected_duration"] = time.time() - self.connected_at
        
        if self.last_activity:
            stats["idle_time"] = time.time() - self.last_activity
        
        stats["pending_requests"] = self.protocol_handler.get_pending_request_count()
        stats["cache_valid"] = self._is_cache_valid()
        
        return stats
    
    def is_healthy(self) -> bool:
        """检查客户端是否健康"""
        return (
            self.status == ConnectionStatus.CONNECTED and
            self.transport is not None and
            self.transport.is_alive() if hasattr(self.transport, 'is_alive') else True
        )
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect() 