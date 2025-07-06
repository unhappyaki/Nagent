"""
ACP Server 实现
基于企业级架构实践的三层结构：Gateway -> Router -> Container
"""

import json
import time
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import websockets
from websockets.server import WebSocketServerProtocol

from .acp_client import ACPPayload
from .message_schema import ACPMessage


class ACPMessageType(Enum):
    """ACP消息类型"""
    REGISTER = "register"
    TASK = "task"
    ACK = "ack"
    RESULT = "result"
    STATE = "state"
    HEARTBEAT = "heartbeat"


@dataclass
class ACPMessage:
    """ACP消息结构"""
    type: str
    agent_id: str
    trace_id: str
    payload: Dict[str, Any]
    timestamp: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ACPMessage':
        """从字典创建消息"""
        return cls(
            type=data.get("type", ""),
            agent_id=data.get("agent_id", ""),
            trace_id=data.get("trace_id", ""),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", int(time.time()))
        )


class ACPGateway:
    """
    ACP网关 - 协议层消息入口
    负责接收消息、初步校验、反序列化
    """
    
    def __init__(self, router, trace_writer=None):
        self.router = router
        self.trace_writer = trace_writer
        self.logger = logging.getLogger(__name__)
    
    async def receive(self, websocket: WebSocketServerProtocol, raw_data: str):
        """
        接收并处理原始消息
        
        Args:
            websocket: WebSocket连接
            raw_data: 原始消息数据
        """
        try:
            message_data = json.loads(raw_data)
            # 优先用标准格式解析
            if 'meta' in message_data and 'context' in message_data and 'payload' in message_data:
                message = ACPMessage.from_dict(message_data)
            else:
                # 兼容老格式
                message = ACPMessage(
                    meta=None, context=None, payload=None
                )
            if self.trace_writer and getattr(message, 'meta', None) and getattr(message.meta, 'trace_id', None):
                self.trace_writer.record_acp_message(
                    trace_id=message.meta.trace_id,
                    context_id=getattr(message.context, 'session_id', None) if message.context else None,
                    message_type="gateway_received",
                    payload=message_data
                )
            await self.router.route(websocket, message)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON message: {e}")
            await self._send_error(websocket, "Invalid JSON format")
        except Exception as e:
            self.logger.error(f"Gateway error: {e}")
            await self._send_error(websocket, "Gateway processing error")
    
    async def _send_error(self, websocket: WebSocketServerProtocol, error_msg: str):
        """发送错误消息"""
        error_response = {
            "type": "error",
            "message": error_msg,
            "timestamp": int(time.time())
        }
        await websocket.send(json.dumps(error_response))


class ACPRouter:
    """
    ACP路由器 - 解析投递路径 + 执行权限判断
    负责将消息路由到正确的Agent容器
    """
    
    def __init__(self, container, trace_writer=None):
        self.container = container
        self.trace_writer = trace_writer
        self.logger = logging.getLogger(__name__)
    
    async def route(self, websocket: WebSocketServerProtocol, message: ACPMessage):
        """
        路由消息到目标Agent
        
        Args:
            websocket: WebSocket连接
            message: ACP消息
        """
        try:
            trace_id = getattr(message.meta, 'trace_id', None) if message.meta else None
            context_id = getattr(message.context, 'session_id', None) if message.context else None
            if self.trace_writer and trace_id:
                self.trace_writer.record_acp_message(
                    trace_id=trace_id,
                    context_id=context_id,
                    message_type="router_routed",
                    payload={"message_type": getattr(message.meta, 'message_type', None)}
                )
            # 根据meta.message_type路由
            msg_type = getattr(message.meta, 'message_type', None) if message.meta else None
            if msg_type == "register":
                await self._handle_register(websocket, message)
            elif msg_type == "task":
                await self._handle_task(websocket, message)
            elif msg_type == "ack":
                await self._handle_ack(websocket, message)
            elif msg_type == "result":
                await self._handle_result(websocket, message)
            elif msg_type == "state":
                await self._handle_state(websocket, message)
            else:
                self.logger.warning(f"Unknown message type: {msg_type}")
        except Exception as e:
            self.logger.error(f"Router error: {e}")
    
    async def _handle_register(self, websocket: WebSocketServerProtocol, message: ACPMessage):
        """处理Agent注册"""
        await self.container.register_agent(message.agent_id, websocket, message.payload)
        
        # 发送注册确认
        ack_message = {
            "type": "ack",
            "message": "registered",
            "agent_id": message.agent_id,
            "timestamp": int(time.time())
        }
        await websocket.send(json.dumps(ack_message))
    
    async def _handle_task(self, websocket: WebSocketServerProtocol, message: ACPMessage):
        """处理任务消息"""
        await self.container.dispatch_task(message.agent_id, message)
    
    async def _handle_ack(self, websocket: WebSocketServerProtocol, message: ACPMessage):
        """处理确认消息"""
        self.logger.info(f"Received ACK from {message.agent_id}: {message.trace_id}")
    
    async def _handle_result(self, websocket: WebSocketServerProtocol, message: ACPMessage):
        """处理结果消息"""
        self.logger.info(f"Received RESULT from {message.agent_id}: {message.payload}")
    
    async def _handle_state(self, websocket: WebSocketServerProtocol, message: ACPMessage):
        """处理状态消息（心跳）"""
        await self.container.update_agent_state(message.agent_id, message.payload)


class AgentContainer:
    """
    Agent容器 - Agent的生命周期注册中心
    负责Agent注册、任务分发、状态管理
    """
    
    def __init__(self, trace_writer=None):
        self.agents = {}  # agent_id -> {ws, metadata, last_seen}
        self.trace_writer = trace_writer
        self.logger = logging.getLogger(__name__)
        
        # 任务处理器
        self.task_handlers = {}
    
    async def register_agent(self, agent_id: str, websocket: WebSocketServerProtocol, metadata: Dict[str, Any]):
        """
        注册Agent
        
        Args:
            agent_id: Agent ID
            websocket: WebSocket连接
            metadata: Agent元数据
        """
        self.agents[agent_id] = {
            "ws": websocket,
            "metadata": metadata,
            "last_seen": time.time(),
            "status": "online"
        }
        
        self.logger.info(f"Agent registered: {agent_id}")
    
    async def dispatch_task(self, agent_id: str, message: ACPMessage):
        """
        分发任务到目标Agent
        
        Args:
            agent_id: 目标Agent ID
            message: 任务消息
        """
        if agent_id not in self.agents:
            self.logger.error(f"Agent {agent_id} not found")
            return
        
        agent_info = self.agents[agent_id]
        websocket = agent_info["ws"]
        
        try:
            trace_id = getattr(message.meta, 'trace_id', None) if message.meta else None
            if self.trace_writer and trace_id:
                self.trace_writer.record_acp_message(
                    trace_id=trace_id,
                    context_id=agent_id,
                    message_type="container_dispatched",
                    payload={"agent_id": agent_id, "task_id": trace_id}
                )
            # 发送标准消息
            await websocket.send(json.dumps(message.to_dict(), ensure_ascii=False))
            
            self.logger.info(f"Task dispatched to {agent_id}: {trace_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to dispatch task to {agent_id}: {e}")
    
    async def update_agent_state(self, agent_id: str, state_data: Dict[str, Any]):
        """
        更新Agent状态
        
        Args:
            agent_id: Agent ID
            state_data: 状态数据
        """
        if agent_id in self.agents:
            self.agents[agent_id]["last_seen"] = time.time()
            self.agents[agent_id]["status"] = state_data.get("status", "online")
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取Agent信息"""
        return self.agents.get(agent_id)
    
    def get_all_agents(self) -> List[str]:
        """获取所有Agent ID"""
        return list(self.agents.keys())
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self.task_handlers[task_type] = handler


class ACPServer:
    """
    ACP服务器主类
    整合Gateway、Router、Container三层架构
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765, trace_writer=None):
        self.host = host
        self.port = port
        self.trace_writer = trace_writer
        self.logger = logging.getLogger(__name__)
        
        # 三层架构组件
        self.container = AgentContainer(trace_writer)
        self.router = ACPRouter(self.container, trace_writer)
        self.gateway = ACPGateway(self.router, trace_writer)
        
        # 服务器状态
        self.server = None
        self.running = False
    
    async def start(self):
        """启动ACP服务器"""
        try:
            self.server = await websockets.serve(
                self._handle_connection,
                self.host,
                self.port
            )
            self.running = True
            self.logger.info(f"ACP Server started on {self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start ACP server: {e}")
            raise
    
    async def stop(self):
        """停止ACP服务器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.running = False
            self.logger.info("ACP Server stopped")
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """
        处理WebSocket连接
        
        Args:
            websocket: WebSocket连接
            path: 连接路径
        """
        self.logger.info(f"New connection from {websocket.remote_address}")
        
        try:
            async for message in websocket:
                await self.gateway.receive(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Connection closed: {websocket.remote_address}")
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取Agent信息"""
        return self.container.get_agent_info(agent_id)
    
    def get_all_agents(self) -> List[str]:
        """获取所有Agent"""
        return self.container.get_all_agents()
    
    async def send_task_to_agent(self, agent_id: str, task_data: Dict[str, Any]) -> bool:
        """
        向指定Agent发送任务
        
        Args:
            agent_id: 目标Agent ID
            task_data: 任务数据
            
        Returns:
            bool: 发送是否成功
        """
        try:
            task_message = ACPMessage(
                type=ACPMessageType.TASK.value,
                agent_id=agent_id,
                trace_id=str(uuid.uuid4()),
                payload=task_data,
                timestamp=int(time.time())
            )
            
            await self.container.dispatch_task(agent_id, task_message)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send task to {agent_id}: {e}")
            return False 