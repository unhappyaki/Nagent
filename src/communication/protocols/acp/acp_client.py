"""
ACP (Model Context Protocol) 客户端
实现行为数据的封装与追踪核心，负责Client与Server之间的协议交互
"""

import json
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
import logging

from ...dispatcher.bir_router import BehaviorPackage
from .message_schema import ACPMessage


class ACPCommandType(Enum):
    """ACP命令类型"""
    CALL = "call"           # 调用命令
    LIST = "list"           # 列表命令
    READ = "read"           # 读取命令
    WRITE = "write"         # 写入命令
    DELETE = "delete"       # 删除命令
    SUBSCRIBE = "subscribe" # 订阅命令


@dataclass
class ACPPayload:
    """ACP载荷结构"""
    command: str                    # 命令类型
    meta: Dict[str, Any]           # 元数据
    permissions: List[str]         # 权限列表
    context: Dict[str, Any]        # 上下文数据
    trace_id: str                  # 追踪ID
    context_id: str                # 上下文ID
    timestamp: int                 # 时间戳
    source_id: str                 # 源ID


class ACPClient:
    """
    ACP客户端
    负责封装行为请求包，与ACP服务器进行通信
    """
    
    def __init__(self, server_url: str = "http://localhost:8000", trace_writer=None):
        """
        初始化ACP客户端
        
        Args:
            server_url: ACP服务器URL
            trace_writer: 追踪写入器
        """
        self.server_url = server_url
        self.trace_writer = trace_writer
        self.session_id = self._generate_session_id()
        self.logger = logging.getLogger(__name__)
        
        # 连接状态
        self.connected = False
        self.connection_retries = 3
        
        # 消息队列
        self.message_queue = []
        self.callback_handlers = {}
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return f"session-{uuid.uuid4().hex[:8]}"
    
    async def connect(self) -> bool:
        """
        连接到ACP服务器
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 这里应该实现实际的连接逻辑
            # 比如WebSocket连接或HTTP长连接
            self.connected = True
            self.logger.info(f"Connected to ACP server: {self.server_url}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to ACP server: {e}")
            return False
    
    def send_behavior_package(self, behavior_package: BehaviorPackage) -> bool:
        """
        发送行为指令包到ACP服务器
        
        Args:
            behavior_package: 行为指令包
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 构建ACP载荷
            acp_payload = self._build_acp_payload(behavior_package)
            
            # 发送到服务器
            return self._send_payload(acp_payload)
        except Exception as e:
            self.logger.error(f"Failed to send behavior package: {e}")
            return False
    
    def _build_acp_payload(self, behavior_package: BehaviorPackage) -> ACPPayload:
        """
        构建ACP载荷
        
        Args:
            behavior_package: 行为指令包
            
        Returns:
            ACPPayload: ACP载荷
        """
        return ACPPayload(
            command=ACPCommandType.CALL.value,
            meta={
                "intent": behavior_package.intent,
                "intent_type": behavior_package.intent_type.value,
                "from_agent": behavior_package.from_agent,
                "to_agent": behavior_package.to_agent,
                "priority": behavior_package.priority
            },
            permissions=["read", "write", "execute"],
            context={
                "session_id": self.session_id,
                "user_context": behavior_package.payload
            },
            trace_id=behavior_package.trace_id,
            context_id=behavior_package.context_id,
            timestamp=behavior_package.timestamp,
            source_id=behavior_package.from_agent
        )
    
    def send_acp_message(self, acp_message: ACPMessage) -> bool:
        """
        发送标准ACPMessage消息
        Args:
            acp_message: 标准化ACP消息
        Returns:
            bool: 发送是否成功
        """
        try:
            message_dict = acp_message.to_dict()
            message = json.dumps(message_dict, ensure_ascii=False)
            # 记录追踪信息
            if self.trace_writer:
                self.trace_writer.record_acp_message(
                    trace_id=acp_message.meta.trace_id,
                    context_id=acp_message.context.session_id,
                    message_type="client_send",
                    payload=message_dict
                )
            self.message_queue.append({
                "timestamp": time.time(),
                "payload": message_dict,
                "status": "pending"
            })
            self.logger.info(f"Sent ACPMessage: {acp_message.meta.trace_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send ACPMessage: {e}")
            return False

    def _send_payload(self, payload) -> bool:
        """
        兼容老接口，支持直接发送ACPMessage或dict结构
        """
        if isinstance(payload, ACPMessage):
            return self.send_acp_message(payload)
        # 兼容老的ACPPayload结构
        try:
            payload_dict = asdict(payload)
            message = json.dumps(payload_dict, ensure_ascii=False)
            if self.trace_writer:
                self.trace_writer.record_acp_message(
                    trace_id=payload_dict.get("trace_id"),
                    context_id=payload_dict.get("context_id"),
                    message_type="client_send",
                    payload=payload_dict
                )
            self.message_queue.append({
                "timestamp": time.time(),
                "payload": payload_dict,
                "status": "pending"
            })
            self.logger.info(f"Sent legacy payload: {payload_dict.get('trace_id')}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send legacy payload: {e}")
            return False
    
    async def call_tool(self, 
                       tool_name: str, 
                       parameters: Dict[str, Any],
                       context_id: str,
                       trace_id: str) -> Dict[str, Any]:
        """
        调用工具
        
        Args:
            tool_name: 工具名称
            parameters: 参数
            context_id: 上下文ID
            trace_id: 追踪ID
            
        Returns:
            Dict[str, Any]: 调用结果
        """
        try:
            payload = ACPPayload(
                command=ACPCommandType.CALL.value,
                meta={
                    "tool_name": tool_name,
                    "parameters": parameters
                },
                permissions=["execute"],
                context={},
                trace_id=trace_id,
                context_id=context_id,
                timestamp=int(time.time()),
                source_id=self.session_id
            )
            
            # 发送调用请求
            success = self._send_payload(payload)
            if not success:
                return {"error": "Failed to send tool call request"}
            
            # 等待响应（这里应该实现异步等待）
            # 实际实现中应该使用WebSocket或消息队列
            await asyncio.sleep(0.1)  # 模拟等待
            
            return {"status": "success", "tool": tool_name}
            
        except Exception as e:
            self.logger.error(f"Tool call failed: {e}")
            return {"error": str(e)}
    
    def register_callback(self, trace_id: str, callback_func):
        """
        注册回调函数
        
        Args:
            trace_id: 追踪ID
            callback_func: 回调函数
        """
        self.callback_handlers[trace_id] = callback_func
    
    def handle_server_response(self, response_data: Dict[str, Any]):
        """
        处理服务器响应
        
        Args:
            response_data: 响应数据
        """
        try:
            trace_id = response_data.get("trace_id")
            if trace_id in self.callback_handlers:
                callback = self.callback_handlers[trace_id]
                callback(response_data)
                del self.callback_handlers[trace_id]
            
            # 记录追踪信息
            if self.trace_writer:
                self.trace_writer.record_acp_message(
                    trace_id=trace_id,
                    context_id=response_data.get("context_id"),
                    message_type="client_receive",
                    payload=response_data
                )
                
        except Exception as e:
            self.logger.error(f"Failed to handle server response: {e}")
    
    def get_message_history(self, context_id: str = None) -> List[Dict[str, Any]]:
        """
        获取消息历史
        
        Args:
            context_id: 上下文ID（可选）
            
        Returns:
            List[Dict[str, Any]]: 消息历史
        """
        if context_id:
            return [msg for msg in self.message_queue 
                   if msg["payload"].get("context_id") == context_id]
        return self.message_queue
    
    def disconnect(self):
        """断开连接"""
        self.connected = False
        self.logger.info("Disconnected from ACP server")


class ACPClientManager:
    """
    ACP客户端管理器
    负责管理多个ACP客户端实例
    """
    
    def __init__(self):
        self.clients = {}
        self.default_client = None
    
    def create_client(self, 
                     name: str, 
                     server_url: str, 
                     trace_writer=None) -> ACPClient:
        """
        创建ACP客户端
        
        Args:
            name: 客户端名称
            server_url: 服务器URL
            trace_writer: 追踪写入器
            
        Returns:
            ACPClient: ACP客户端实例
        """
        client = ACPClient(server_url, trace_writer)
        self.clients[name] = client
        
        if not self.default_client:
            self.default_client = client
            
        return client
    
    def get_client(self, name: str = None) -> Optional[ACPClient]:
        """
        获取ACP客户端
        
        Args:
            name: 客户端名称（可选）
            
        Returns:
            Optional[ACPClient]: ACP客户端实例
        """
        if name:
            return self.clients.get(name)
        return self.default_client
    
    def remove_client(self, name: str):
        """移除客户端"""
        if name in self.clients:
            client = self.clients[name]
            client.disconnect()
            del self.clients[name]
            
            if self.default_client == client:
                self.default_client = list(self.clients.values())[0] if self.clients else None 