"""
ACP协议消息格式定义模块
标准化消息构建工具和消息类型定义
"""

import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class ACPMessageType(Enum):
    """ACP消息类型"""
    REGISTER = "register"           # Agent注册
    UNREGISTER = "unregister"      # Agent注销
    TASK = "task"                  # 任务分发
    EXECUTE = "execute"            # 执行指令
    RESULT = "result"              # 执行结果
    STATE = "state"                # 状态更新
    HEARTBEAT = "heartbeat"        # 心跳检测
    ACK = "ack"                    # 确认消息
    ERROR = "error"                # 错误消息
    QUERY = "query"                # 查询请求
    RESPONSE = "response"          # 查询响应


class ACPCommandType(Enum):
    """ACP命令类型"""
    CALL = "call"  # 兼容 demo
    CALL_TOOL = "call_tool"               # 工具调用
    CALL_API = "call_api"                 # API调用
    CALL_MODEL = "call_model"             # 模型调用
    UPDATE_MEMORY = "update_memory"       # 更新内存
    QUERY_MEMORY = "query_memory"         # 查询内存
    UPDATE_STATE = "update_state"         # 更新状态
    QUERY_STATE = "query_state"           # 查询状态
    TRANSFER_TASK = "transfer_task"       # 任务转移
    SPAWN_AGENT = "spawn_agent"           # 生成Agent
    TERMINATE_AGENT = "terminate_agent"   # 终止Agent


class ACPActionType(Enum):
    """ACP动作类型"""
    REASONING = "reasoning"        # 推理
    EXECUTION = "execution"        # 执行
    COMMUNICATION = "communication" # 通信
    MEMORY = "memory"             # 内存操作
    STATE = "state"               # 状态管理


class MessagePriority(Enum):
    """消息优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class MessageMeta:
    """消息元数据"""
    message_id: str
    message_type: str
    timestamp: str
    sender_id: str
    receiver_id: str
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    priority: int = MessagePriority.NORMAL.value
    ttl: Optional[int] = None  # 生存时间(秒)
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = str(uuid.uuid4())


@dataclass
class MessageContext:
    """消息上下文"""
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    agent_capabilities: List[str] = None
    environment: Dict[str, Any] = None
    security_context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.agent_capabilities is None:
            self.agent_capabilities = []
        if self.environment is None:
            self.environment = {}
        if self.security_context is None:
            self.security_context = {}


@dataclass
class ACPPayload:
    """ACP载荷"""
    command_type: str
    action_type: str
    data: Dict[str, Any]
    parameters: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ACPMessage:
    """ACP标准消息"""
    meta: MessageMeta
    context: MessageContext
    payload: ACPPayload
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "meta": asdict(self.meta),
            "context": asdict(self.context),
            "payload": asdict(self.payload)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ACPMessage':
        """从字典创建消息"""
        return cls(
            meta=MessageMeta(**data["meta"]),
            context=MessageContext(**data["context"]),
            payload=ACPPayload(**data["payload"])
        )


class ACPMessageBuilder:
    """ACP消息构建器"""
    
    def __init__(self, sender_id: str, trace_writer=None):
        self.sender_id = sender_id
        self.trace_writer = trace_writer
        self.default_context = MessageContext()
    
    def create_register_message(
        self,
        agent_id: str,
        capabilities: List[str],
        metadata: Dict[str, Any] = None
    ) -> ACPMessage:
        """创建Agent注册消息"""
        meta = MessageMeta(
            message_id=str(uuid.uuid4()),
            message_type=ACPMessageType.REGISTER.value,
            timestamp=datetime.utcnow().isoformat(),
            sender_id=self.sender_id,
            receiver_id="acp_server",
            priority=MessagePriority.HIGH.value
        )
        
        context = MessageContext(
            agent_capabilities=capabilities
        )
        
        payload = ACPPayload(
            command_type=ACPCommandType.SPAWN_AGENT.value,
            action_type=ACPActionType.COMMUNICATION.value,
            data={
                "agent_id": agent_id,
                "capabilities": capabilities,
                "registration_time": datetime.utcnow().isoformat()
            },
            metadata=metadata or {}
        )
        
        return ACPMessage(meta=meta, context=context, payload=payload)
    
    def create_task_message(
        self,
        receiver_id: str,
        task_type: str,
        task_data: Dict[str, Any],
        context_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> ACPMessage:
        """创建任务消息"""
        meta = MessageMeta(
            message_id=str(uuid.uuid4()),
            message_type=ACPMessageType.TASK.value,
            timestamp=datetime.utcnow().isoformat(),
            sender_id=self.sender_id,
            receiver_id=receiver_id,
            priority=priority.value
        )
        
        context = MessageContext(
            session_id=context_id
        )
        
        payload = ACPPayload(
            command_type=ACPCommandType.TRANSFER_TASK.value,
            action_type=ACPActionType.EXECUTION.value,
            data={
                "task_type": task_type,
                "task_data": task_data,
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        return ACPMessage(meta=meta, context=context, payload=payload)
    
    def create_tool_call_message(
        self,
        receiver_id: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        context_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> ACPMessage:
        """创建工具调用消息"""
        meta = MessageMeta(
            message_id=str(uuid.uuid4()),
            message_type=ACPMessageType.EXECUTE.value,
            timestamp=datetime.utcnow().isoformat(),
            sender_id=self.sender_id,
            receiver_id=receiver_id,
            trace_id=trace_id
        )
        
        context = MessageContext(
            session_id=context_id
        )
        
        payload = ACPPayload(
            command_type=ACPCommandType.CALL_TOOL.value,
            action_type=ACPActionType.EXECUTION.value,
            data={
                "tool_name": tool_name,
                "arguments": tool_args,
                "call_time": datetime.utcnow().isoformat()
            }
        )
        
        return ACPMessage(meta=meta, context=context, payload=payload)
    
    def create_result_message(
        self,
        receiver_id: str,
        result_data: Dict[str, Any],
        success: bool = True,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> ACPMessage:
        """创建结果消息"""
        meta = MessageMeta(
            message_id=str(uuid.uuid4()),
            message_type=ACPMessageType.RESULT.value,
            timestamp=datetime.utcnow().isoformat(),
            sender_id=self.sender_id,
            receiver_id=receiver_id,
            correlation_id=correlation_id
        )
        
        context = MessageContext()
        
        payload = ACPPayload(
            command_type="return_result",
            action_type=ACPActionType.COMMUNICATION.value,
            data={
                "success": success,
                "result": result_data,
                "error": error,
                "completed_at": datetime.utcnow().isoformat()
            }
        )
        
        return ACPMessage(meta=meta, context=context, payload=payload)
    
    def create_heartbeat_message(self, receiver_id: str = "acp_server") -> ACPMessage:
        """创建心跳消息"""
        meta = MessageMeta(
            message_id=str(uuid.uuid4()),
            message_type=ACPMessageType.HEARTBEAT.value,
            timestamp=datetime.utcnow().isoformat(),
            sender_id=self.sender_id,
            receiver_id=receiver_id,
            priority=MessagePriority.LOW.value
        )
        
        context = MessageContext()
        
        payload = ACPPayload(
            command_type="heartbeat",
            action_type=ACPActionType.STATE.value,
            data={
                "status": "alive",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime": time.time()
            }
        )
        
        return ACPMessage(meta=meta, context=context, payload=payload) 