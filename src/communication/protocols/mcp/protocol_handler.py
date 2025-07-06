"""
MCP协议处理器

负责处理MCP协议消息的路由和响应
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional, Callable, Awaitable
import structlog

from .mcp_types import (
    MCPMessage, MCPTool, MCPResource, MCPResult, 
    MCPError, MCPErrorCode, ConnectionStatus
)

logger = structlog.get_logger(__name__)


class MCPProtocolHandler:
    """MCP协议处理器"""
    
    def __init__(self):
        """初始化协议处理器"""
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._request_id_counter = 0
        
        # 消息处理器映射
        self._method_handlers: Dict[str, Callable] = {
            # 工具相关
            "tools/list": self._handle_list_tools,
            "tools/call": self._handle_call_tool,
            
            # 资源相关
            "resources/list": self._handle_list_resources,
            "resources/read": self._handle_read_resource,
            
            # 初始化
            "initialize": self._handle_initialize,
            
            # 通知
            "initialized": self._handle_initialized,
            "progress": self._handle_progress,
        }
        
        # 外部处理器
        self.tool_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[Any]]] = None
        self.resource_handler: Optional[Callable[[str], Awaitable[Any]]] = None
        
    def set_tool_handler(self, handler: Callable[[str, Dict[str, Any]], Awaitable[Any]]) -> None:
        """设置工具调用处理器"""
        self.tool_handler = handler
    
    def set_resource_handler(self, handler: Callable[[str], Awaitable[Any]]) -> None:
        """设置资源访问处理器"""
        self.resource_handler = handler
    
    def generate_request_id(self) -> str:
        """生成请求ID"""
        self._request_id_counter += 1
        return f"req_{self._request_id_counter}_{uuid.uuid4().hex[:8]}"
    
    async def handle_message(self, message: MCPMessage) -> Optional[MCPMessage]:
        """
        处理接收到的消息
        
        Args:
            message: 接收到的消息
            
        Returns:
            响应消息（如果需要）
        """
        try:
            # 如果是响应消息，处理pending request
            if message.id and message.method is None:
                await self._handle_response(message)
                return None
            
            # 如果是请求消息，调用相应的处理器
            if message.method:
                handler = self._method_handlers.get(message.method)
                if handler:
                    response = await handler(message)
                    return response
                else:
                    # 未知方法
                    return self._create_error_response(
                        message.id,
                        MCPErrorCode.METHOD_NOT_FOUND,
                        f"Unknown method: {message.method}"
                    )
            
            # 通知消息，不需要响应
            return None
            
        except Exception as e:
            logger.error(
                "Error handling MCP message",
                message_id=message.id,
                method=message.method,
                error=str(e)
            )
            
            if message.id:
                return self._create_error_response(
                    message.id,
                    MCPErrorCode.INTERNAL_ERROR,
                    f"Internal error: {str(e)}"
                )
            
            return None
    
    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Any:
        """
        发送请求并等待响应
        
        Args:
            method: 方法名
            params: 参数
            timeout: 超时时间
            
        Returns:
            响应结果
        """
        request_id = self.generate_request_id()
        
        # 创建请求消息
        request = MCPMessage(
            id=request_id,
            method=method,
            params=params
        )
        
        # 创建Future等待响应
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        try:
            # 这里需要外部传输层发送消息
            # 返回请求消息让调用方发送
            return request, future
            
        except Exception as e:
            # 清理Future
            self._pending_requests.pop(request_id, None)
            raise e
    
    async def _handle_response(self, message: MCPMessage) -> None:
        """处理响应消息"""
        request_id = str(message.id)
        future = self._pending_requests.pop(request_id, None)
        
        if future and not future.done():
            if message.error:
                future.set_exception(
                    Exception(f"MCP Error {message.error.code}: {message.error.message}")
                )
            else:
                future.set_result(message.result)
        else:
            logger.warning(
                "Received response for unknown or completed request",
                request_id=request_id
            )
    
    async def _handle_initialize(self, message: MCPMessage) -> MCPMessage:
        """处理初始化请求"""
        # 返回服务器能力
        return MCPMessage(
            id=message.id,
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "logging": {}
                },
                "serverInfo": {
                    "name": "Nagent MCP Client",
                    "version": "1.0.0"
                }
            }
        )
    
    async def _handle_initialized(self, message: MCPMessage) -> None:
        """处理初始化完成通知"""
        logger.info("MCP server initialized")
    
    async def _handle_progress(self, message: MCPMessage) -> None:
        """处理进度通知"""
        params = message.params or {}
        logger.info(
            "MCP progress update",
            progress_token=params.get("progressToken"),
            progress=params.get("progress"),
            total=params.get("total")
        )
    
    async def _handle_list_tools(self, message: MCPMessage) -> MCPMessage:
        """处理工具列表请求"""
        # 这里应该返回可用的工具列表
        # 实际实现中会从工具注册表获取
        return MCPMessage(
            id=message.id,
            result={
                "tools": []  # 暂时返回空列表
            }
        )
    
    async def _handle_call_tool(self, message: MCPMessage) -> MCPMessage:
        """处理工具调用请求"""
        try:
            params = message.params or {}
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if not tool_name:
                return self._create_error_response(
                    message.id,
                    MCPErrorCode.INVALID_PARAMS,
                    "Missing tool name"
                )
            
            # 调用外部工具处理器
            if self.tool_handler:
                result = await self.tool_handler(tool_name, arguments)
                return MCPMessage(
                    id=message.id,
                    result={
                        "content": [
                            {
                                "type": "text",
                                "text": str(result)
                            }
                        ]
                    }
                )
            else:
                return self._create_error_response(
                    message.id,
                    MCPErrorCode.INTERNAL_ERROR,
                    "No tool handler configured"
                )
                
        except Exception as e:
            return self._create_error_response(
                message.id,
                MCPErrorCode.INTERNAL_ERROR,
                f"Tool execution error: {str(e)}"
            )
    
    async def _handle_list_resources(self, message: MCPMessage) -> MCPMessage:
        """处理资源列表请求"""
        return MCPMessage(
            id=message.id,
            result={
                "resources": []  # 暂时返回空列表
            }
        )
    
    async def _handle_read_resource(self, message: MCPMessage) -> MCPMessage:
        """处理资源读取请求"""
        try:
            params = message.params or {}
            uri = params.get("uri")
            
            if not uri:
                return self._create_error_response(
                    message.id,
                    MCPErrorCode.INVALID_PARAMS,
                    "Missing resource URI"
                )
            
            # 调用外部资源处理器
            if self.resource_handler:
                content = await self.resource_handler(uri)
                return MCPMessage(
                    id=message.id,
                    result={
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "text/plain",
                                "text": str(content)
                            }
                        ]
                    }
                )
            else:
                return self._create_error_response(
                    message.id,
                    MCPErrorCode.INTERNAL_ERROR,
                    "No resource handler configured"
                )
                
        except Exception as e:
            return self._create_error_response(
                message.id,
                MCPErrorCode.INTERNAL_ERROR,
                f"Resource access error: {str(e)}"
            )
    
    def _create_error_response(
        self,
        request_id: Optional[str],
        error_code: MCPErrorCode,
        error_message: str,
        error_data: Any = None
    ) -> MCPMessage:
        """创建错误响应"""
        return MCPMessage(
            id=request_id,
            error=MCPError(
                code=error_code.value,
                message=error_message,
                data=error_data
            )
        )
    
    def cleanup_pending_requests(self) -> None:
        """清理所有待处理的请求"""
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()
    
    def get_pending_request_count(self) -> int:
        """获取待处理请求数量"""
        return len(self._pending_requests) 