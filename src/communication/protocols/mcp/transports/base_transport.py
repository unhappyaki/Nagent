"""
MCP传输协议基类

定义传输协议的通用接口
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Callable, Any
import structlog

from ..mcp_types import MCPMessage, ConnectionStatus

logger = structlog.get_logger(__name__)


class BaseTransport(ABC):
    """传输协议基类"""
    
    def __init__(self, timeout: int = 30):
        """
        初始化传输协议
        
        Args:
            timeout: 超时时间（秒）
        """
        self.timeout = timeout
        self.status = ConnectionStatus.DISCONNECTED
        self.message_handler: Optional[Callable[[MCPMessage], None]] = None
        self._read_task: Optional[asyncio.Task] = None
        
    @abstractmethod
    async def connect(self) -> bool:
        """
        建立连接
        
        Returns:
            连接是否成功
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        断开连接
        
        Returns:
            断开是否成功
        """
        pass
    
    @abstractmethod
    async def send_message(self, message: MCPMessage) -> bool:
        """
        发送消息
        
        Args:
            message: 要发送的消息
            
        Returns:
            发送是否成功
        """
        pass
    
    @abstractmethod
    async def _read_messages(self) -> None:
        """读取消息的内部方法"""
        pass
    
    def set_message_handler(self, handler: Callable[[MCPMessage], None]) -> None:
        """
        设置消息处理器
        
        Args:
            handler: 消息处理函数
        """
        self.message_handler = handler
    
    def get_status(self) -> ConnectionStatus:
        """获取连接状态"""
        return self.status
    
    async def start_reading(self) -> None:
        """开始读取消息"""
        if self._read_task is None or self._read_task.done():
            self._read_task = asyncio.create_task(self._read_messages())
    
    async def stop_reading(self) -> None:
        """停止读取消息"""
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
    
    def _handle_message(self, message: MCPMessage) -> None:
        """处理接收到的消息"""
        if self.message_handler:
            try:
                self.message_handler(message)
            except Exception as e:
                logger.warning(
                    "Message handler error",
                    error=str(e),
                    message_id=message.id
                )
        else:
            logger.warning("No message handler set", message_id=message.id)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect() 