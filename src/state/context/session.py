"""
Session会话管理模块
实现Runtime上下文管理中的会话生命周期控制，包括初始化、延展、销毁与快照机制
"""

import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import json
import logging


class SessionStatus(Enum):
    """会话状态枚举"""
    INITIALIZING = "initializing"  # 初始化中
    ACTIVE = "active"             # 活跃状态
    PAUSED = "paused"             # 暂停状态
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败状态
    EXPIRED = "expired"           # 已过期


@dataclass
class SessionMeta:
    """会话元数据"""
    session_id: str               # 会话ID
    context_id: str               # 上下文ID
    agent_id: str                 # 智能体ID
    tenant_id: str                # 租户ID
    created_at: int               # 创建时间
    updated_at: int               # 更新时间
    status: SessionStatus         # 会话状态
    priority: int = 0             # 优先级
    timeout: Optional[int] = None # 超时时间
    tags: List[str] = field(default_factory=list)  # 标签


@dataclass
class SessionSnapshot:
    """会话快照"""
    snapshot_id: str              # 快照ID
    session_id: str               # 会话ID
    timestamp: int                # 快照时间
    state: Dict[str, Any]         # 状态数据
    memory_entries: List[Dict]    # 内存条目
    context_data: Dict[str, Any]  # 上下文数据


class Session:
    """
    会话类
    管理智能体任务的生命周期和状态
    """
    
    def __init__(self, 
                 context_id: str,
                 agent_id: str,
                 tenant_id: str = "default",
                 timeout: Optional[int] = None):
        """
        初始化会话
        
        Args:
            context_id: 上下文ID
            agent_id: 智能体ID
            tenant_id: 租户ID
            timeout: 超时时间（秒）
        """
        self.session_id = self._generate_session_id()
        self.context_id = context_id
        self.agent_id = agent_id
        self.tenant_id = tenant_id
        self.timeout = timeout
        
        # 创建元数据
        current_time = int(time.time())
        self.meta = SessionMeta(
            session_id=self.session_id,
            context_id=context_id,
            agent_id=agent_id,
            tenant_id=tenant_id,
            created_at=current_time,
            updated_at=current_time,
            status=SessionStatus.INITIALIZING,
            timeout=timeout
        )
        
        # 会话数据
        self.data = {}
        self.memory_entries = []
        self.context_data = {}
        
        # 快照历史
        self.snapshots = []
        
        # 日志记录器
        self.logger = logging.getLogger(f"Session.{self.session_id}")
        
        # 初始化完成
        self.meta.status = SessionStatus.ACTIVE
        self.logger.info(f"Session initialized: {self.session_id}")
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return f"session-{uuid.uuid4().hex[:12]}"
    
    def update_status(self, status: SessionStatus):
        """
        更新会话状态
        
        Args:
            status: 新状态
        """
        self.meta.status = status
        self.meta.updated_at = int(time.time())
        self.logger.info(f"Session status updated to: {status.value}")
    
    def set_data(self, key: str, value: Any):
        """
        设置会话数据
        
        Args:
            key: 数据键
            value: 数据值
        """
        self.data[key] = value
        self.meta.updated_at = int(time.time())
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """
        获取会话数据
        
        Args:
            key: 数据键
            default: 默认值
            
        Returns:
            Any: 数据值
        """
        return self.data.get(key, default)
    
    def add_memory_entry(self, entry: Dict[str, Any]):
        """
        添加内存条目
        
        Args:
            entry: 内存条目
        """
        entry["timestamp"] = int(time.time())
        entry["session_id"] = self.session_id
        self.memory_entries.append(entry)
        self.meta.updated_at = int(time.time())
    
    def get_memory_entries(self, 
                          entry_type: Optional[str] = None,
                          limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取内存条目
        
        Args:
            entry_type: 条目类型过滤
            limit: 限制数量
            
        Returns:
            List[Dict[str, Any]]: 内存条目列表
        """
        entries = self.memory_entries
        
        if entry_type:
            entries = [e for e in entries if e.get("type") == entry_type]
        
        if limit:
            entries = entries[-limit:]
        
        return entries
    
    def set_context_data(self, key: str, value: Any):
        """
        设置上下文数据
        
        Args:
            key: 数据键
            value: 数据值
        """
        self.context_data[key] = value
        self.meta.updated_at = int(time.time())
    
    def get_context_data(self, key: str, default: Any = None) -> Any:
        """
        获取上下文数据
        
        Args:
            key: 数据键
            default: 默认值
            
        Returns:
            Any: 上下文数据
        """
        return self.context_data.get(key, default)
    
    def create_snapshot(self) -> SessionSnapshot:
        """
        创建会话快照
        
        Returns:
            SessionSnapshot: 会话快照
        """
        snapshot_id = f"snapshot-{uuid.uuid4().hex[:8]}"
        
        snapshot = SessionSnapshot(
            snapshot_id=snapshot_id,
            session_id=self.session_id,
            timestamp=int(time.time()),
            state=self.data.copy(),
            memory_entries=self.memory_entries.copy(),
            context_data=self.context_data.copy()
        )
        
        self.snapshots.append(snapshot)
        self.logger.info(f"Snapshot created: {snapshot_id}")
        
        return snapshot
    
    def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        恢复会话快照
        
        Args:
            snapshot_id: 快照ID
            
        Returns:
            bool: 恢复是否成功
        """
        for snapshot in self.snapshots:
            if snapshot.snapshot_id == snapshot_id:
                self.data = snapshot.state.copy()
                self.memory_entries = snapshot.memory_entries.copy()
                self.context_data = snapshot.context_data.copy()
                self.meta.updated_at = int(time.time())
                
                self.logger.info(f"Session restored from snapshot: {snapshot_id}")
                return True
        
        self.logger.warning(f"Snapshot not found: {snapshot_id}")
        return False
    
    def is_expired(self) -> bool:
        """
        检查会话是否过期
        
        Returns:
            bool: 是否过期
        """
        if not self.timeout:
            return False
        
        current_time = int(time.time())
        return (current_time - self.meta.updated_at) > self.timeout
    
    def extend(self, timeout: Optional[int] = None):
        """
        延展会话
        
        Args:
            timeout: 新的超时时间
        """
        self.meta.updated_at = int(time.time())
        
        if timeout:
            self.timeout = timeout
            self.meta.timeout = timeout
        
        self.logger.info(f"Session extended: {self.session_id}")
    
    def complete(self):
        """完成会话"""
        self.update_status(SessionStatus.COMPLETED)
        self.logger.info(f"Session completed: {self.session_id}")
    
    def fail(self, error_message: str = ""):
        """
        标记会话失败
        
        Args:
            error_message: 错误信息
        """
        self.update_status(SessionStatus.FAILED)
        self.set_data("error", error_message)
        self.logger.error(f"Session failed: {self.session_id}, error: {error_message}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            Dict[str, Any]: 字典格式的会话数据
        """
        return {
            "session_id": self.session_id,
            "context_id": self.context_id,
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "meta": {
                "created_at": self.meta.created_at,
                "updated_at": self.meta.updated_at,
                "status": self.meta.status.value,
                "priority": self.meta.priority,
                "timeout": self.meta.timeout,
                "tags": self.meta.tags
            },
            "data": self.data,
            "memory_entries_count": len(self.memory_entries),
            "snapshots_count": len(self.snapshots)
        }


class SessionManager:
    """
    会话管理器
    负责管理多个会话实例
    """
    
    def __init__(self):
        self.sessions = {}
        self.logger = logging.getLogger("SessionManager")
    
    def create_session(self, 
                      context_id: str,
                      agent_id: str,
                      tenant_id: str = "default",
                      timeout: Optional[int] = None) -> Session:
        """
        创建新会话
        
        Args:
            context_id: 上下文ID
            agent_id: 智能体ID
            tenant_id: 租户ID
            timeout: 超时时间
            
        Returns:
            Session: 会话实例
        """
        session = Session(context_id, agent_id, tenant_id, timeout)
        self.sessions[session.session_id] = session
        
        self.logger.info(f"Session created: {session.session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Session]: 会话实例
        """
        return self.sessions.get(session_id)
    
    def get_sessions_by_context(self, context_id: str) -> List[Session]:
        """
        根据上下文ID获取会话列表
        
        Args:
            context_id: 上下文ID
            
        Returns:
            List[Session]: 会话列表
        """
        return [s for s in self.sessions.values() if s.context_id == context_id]
    
    def get_sessions_by_agent(self, agent_id: str) -> List[Session]:
        """
        根据智能体ID获取会话列表
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            List[Session]: 会话列表
        """
        return [s for s in self.sessions.values() if s.agent_id == agent_id]
    
    def remove_session(self, session_id: str) -> bool:
        """
        移除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 移除是否成功
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.complete()
            del self.sessions[session_id]
            
            self.logger.info(f"Session removed: {session_id}")
            return True
        
        return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        清理过期会话
        
        Returns:
            int: 清理的会话数量
        """
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.remove_session(session_id)
        
        if expired_sessions:
            self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        获取会话统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        total_sessions = len(self.sessions)
        active_sessions = len([s for s in self.sessions.values() 
                             if s.meta.status == SessionStatus.ACTIVE])
        completed_sessions = len([s for s in self.sessions.values() 
                                if s.meta.status == SessionStatus.COMPLETED])
        failed_sessions = len([s for s in self.sessions.values() 
                             if s.meta.status == SessionStatus.FAILED])
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "completed_sessions": completed_sessions,
            "failed_sessions": failed_sessions,
            "expired_sessions": len([s for s in self.sessions.values() if s.is_expired()])
        } 