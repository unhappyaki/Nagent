"""
上下文管理模块

管理Agent的对话上下文，支持：
- 消息历史记录
- 上下文压缩
- 会话管理
- 上下文检索
- 上下文持久化
- trace_id绑定
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class ContextType(Enum):
    """上下文类型枚举"""
    SESSION = "session"
    TASK = "task"
    CONVERSATION = "conversation"
    WORKFLOW = "workflow"


class Context:
    """
    上下文管理器
    
    管理Agent的对话上下文和历史记录，支持企业级架构的状态管理
    """
    
    def __init__(self, agent_id: str, max_history: int = 100):
        """
        初始化上下文管理器
        
        Args:
            agent_id: Agent ID
            max_history: 最大历史记录数
        """
        self.agent_id = agent_id
        self.max_history = max_history
        self.messages = []
        
        # 企业级架构新增字段
        self.context_id = f"{agent_id}_{uuid.uuid4().hex[:8]}"
        self.session_id = None
        self.trace_id = None
        self.context_type = ContextType.SESSION
        self.metadata = {}
        self.created_at = datetime.utcnow()
        self.last_updated = datetime.utcnow()
        
        # 上下文状态
        self.is_active = True
        self.is_persistent = False
        
        logger.info("Context manager initialized", agent_id=agent_id, context_id=self.context_id)
    
    async def initialize(self) -> None:
        """初始化上下文管理器"""
        try:
            logger.info("Initializing context manager", context_id=self.context_id)
            
            # 这里可以加载持久化的上下文数据
            await self._load_persistent_context()
            
            logger.info("Context manager initialized successfully", context_id=self.context_id)
            
        except Exception as e:
            logger.error("Failed to initialize context manager", error=str(e))
            raise
    
    async def is_healthy(self) -> bool:
        """检查上下文管理器健康状态"""
        try:
            # 检查基本状态
            if not self.is_active:
                return False
            
            # 检查消息完整性
            for msg in self.messages:
                if not all(key in msg for key in ["role", "content", "timestamp"]):
                    return False
            
            return True
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False
    
    async def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """
        添加消息到上下文
        
        Args:
            role: 消息角色 (user/assistant/system)
            content: 消息内容
            metadata: 元数据
        """
        message = {
            "message_id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            "context_id": self.context_id,
            "trace_id": self.trace_id
        }
        
        self.messages.append(message)
        self.last_updated = datetime.utcnow()
        
        # 限制历史记录数量
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
        
        # 如果是持久化上下文，保存到存储
        if self.is_persistent:
            await self._save_persistent_context()
        
        logger.debug("Message added to context", role=role, content_length=len(content))
    
    async def get_context(self) -> Dict[str, Any]:
        """
        获取完整上下文
        
        Returns:
            上下文信息
        """
        return {
            "context_id": self.context_id,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "context_type": self.context_type.value,
            "agent_id": self.agent_id,
            "messages": self.messages,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "is_active": self.is_active,
            "is_persistent": self.is_persistent
        }
    
    async def get_recent_messages(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的消息
        
        Args:
            count: 消息数量
            
        Returns:
            消息列表
        """
        return self.messages[-count:] if self.messages else []
    
    async def get_messages_by_role(self, role: str) -> List[Dict[str, Any]]:
        """
        根据角色获取消息
        
        Args:
            role: 消息角色
            
        Returns:
            消息列表
        """
        return [msg for msg in self.messages if msg["role"] == role]
    
    async def get_messages_by_trace_id(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        根据trace_id获取消息
        
        Args:
            trace_id: 追踪ID
            
        Returns:
            消息列表
        """
        return [msg for msg in self.messages if msg.get("trace_id") == trace_id]
    
    async def set_session_id(self, session_id: str) -> None:
        """
        设置会话ID
        
        Args:
            session_id: 会话ID
        """
        self.session_id = session_id
        self.last_updated = datetime.utcnow()
        logger.debug("Session ID set", session_id=session_id)
    
    async def set_trace_id(self, trace_id: str) -> None:
        """
        设置追踪ID
        
        Args:
            trace_id: 追踪ID
        """
        self.trace_id = trace_id
        self.last_updated = datetime.utcnow()
        logger.debug("Trace ID set", trace_id=trace_id)
    
    async def set_context_type(self, context_type: ContextType) -> None:
        """
        设置上下文类型
        
        Args:
            context_type: 上下文类型
        """
        self.context_type = context_type
        self.last_updated = datetime.utcnow()
        logger.debug("Context type set", context_type=context_type.value)
    
    async def set_persistent(self, persistent: bool) -> None:
        """
        设置是否持久化
        
        Args:
            persistent: 是否持久化
        """
        self.is_persistent = persistent
        logger.debug("Persistent setting changed", persistent=persistent)
    
    async def add_metadata(self, key: str, value: Any) -> None:
        """
        添加元数据
        
        Args:
            key: 键
            value: 值
        """
        self.metadata[key] = value
        self.last_updated = datetime.utcnow()
        logger.debug("Metadata added", key=key)
    
    async def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        获取元数据
        
        Args:
            key: 键
            default: 默认值
            
        Returns:
            元数据值
        """
        return self.metadata.get(key, default)
    
    async def clear_context(self):
        """清空上下文"""
        self.messages.clear()
        self.metadata.clear()
        self.last_updated = datetime.utcnow()
        logger.info("Context cleared", context_id=self.context_id)
    
    async def deactivate(self) -> None:
        """停用上下文"""
        self.is_active = False
        self.last_updated = datetime.utcnow()
        logger.info("Context deactivated", context_id=self.context_id)
    
    async def activate(self) -> None:
        """激活上下文"""
        self.is_active = True
        self.last_updated = datetime.utcnow()
        logger.info("Context activated", context_id=self.context_id)
    
    async def get_size(self) -> int:
        """获取上下文大小"""
        return len(self.messages)
    
    async def get_summary(self) -> Dict[str, Any]:
        """获取上下文摘要"""
        return {
            "context_id": self.context_id,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "context_type": self.context_type.value,
            "agent_id": self.agent_id,
            "message_count": len(self.messages),
            "roles": list(set(msg["role"] for msg in self.messages)),
            "first_message": self.messages[0] if self.messages else None,
            "last_message": self.messages[-1] if self.messages else None,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "is_active": self.is_active,
            "is_persistent": self.is_persistent
        }
    
    async def _load_persistent_context(self) -> None:
        """加载持久化上下文"""
        # 这里应该从数据库或文件系统加载持久化的上下文
        # 暂时为空实现
        pass
    
    async def _save_persistent_context(self) -> None:
        """保存持久化上下文"""
        # 这里应该将上下文保存到数据库或文件系统
        # 暂时为空实现
        pass
    
    async def create_snapshot(self) -> Dict[str, Any]:
        """
        创建上下文快照
        
        Returns:
            上下文快照
        """
        snapshot = {
            "context_id": self.context_id,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "context_type": self.context_type.value,
            "agent_id": self.agent_id,
            "messages": self.messages.copy(),
            "metadata": self.metadata.copy(),
            "created_at": self.created_at.isoformat(),
            "snapshot_at": datetime.utcnow().isoformat(),
            "is_active": self.is_active,
            "is_persistent": self.is_persistent
        }
        
        logger.debug("Context snapshot created", context_id=self.context_id)
        return snapshot
    
    async def restore_from_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """
        从快照恢复上下文
        
        Args:
            snapshot: 上下文快照
        """
        self.context_id = snapshot.get("context_id", self.context_id)
        self.session_id = snapshot.get("session_id")
        self.trace_id = snapshot.get("trace_id")
        self.context_type = ContextType(snapshot.get("context_type", "session"))
        self.messages = snapshot.get("messages", [])
        self.metadata = snapshot.get("metadata", {})
        self.is_active = snapshot.get("is_active", True)
        self.is_persistent = snapshot.get("is_persistent", False)
        self.last_updated = datetime.utcnow()
        
        logger.info("Context restored from snapshot", context_id=self.context_id) 