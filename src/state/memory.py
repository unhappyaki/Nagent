"""
内存管理模块

管理Agent的持久化内存，支持：
- 数据存储和检索
- 内存压缩
- 过期清理
- 备份恢复
- MemoryEntry结构
- 状态更新路径
- 隔离机制
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class MemoryType(Enum):
    """内存类型枚举"""
    PROMPT = "prompt"
    ACTION = "action"
    CONTEXT = "context"
    TOOL_RESULT = "tool_result"
    USER_FEEDBACK = "user_feedback"
    AGENT_OUTPUT = "agent_output"


class MemoryEntry:
    """内存条目结构"""
    
    def __init__(
        self,
        content: str,
        memory_type: MemoryType,
        context_id: str,
        trace_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ):
        """
        初始化内存条目
        
        Args:
            content: 内容
            memory_type: 内存类型
            context_id: 上下文ID
            trace_id: 追踪ID
            metadata: 元数据
        """
        self.entry_id = str(uuid.uuid4())
        self.content = content
        self.memory_type = memory_type
        self.context_id = context_id
        self.trace_id = trace_id
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.access_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entry_id": self.entry_id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "context_id": self.context_id,
            "trace_id": self.trace_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """从字典创建"""
        entry = cls(
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            context_id=data["context_id"],
            trace_id=data.get("trace_id"),
            metadata=data.get("metadata", {})
        )
        entry.entry_id = data["entry_id"]
        entry.created_at = datetime.fromisoformat(data["created_at"])
        entry.last_accessed = datetime.fromisoformat(data["last_accessed"])
        entry.access_count = data["access_count"]
        return entry


class Memory:
    """
    内存管理器
    
    管理Agent的持久化内存和状态，支持企业级架构的内存管理
    """
    
    def __init__(self, agent_id: str, ttl: int = 3600):
        """
        初始化内存管理器
        
        Args:
            agent_id: Agent ID
            ttl: 数据生存时间（秒）
        """
        self.agent_id = agent_id
        self.ttl = ttl
        self.data = {}
        self.timestamps = {}
        
        # 企业级架构新增字段
        self.memory_entries: List[MemoryEntry] = []
        self.context_partitions: Dict[str, List[str]] = {}  # context_id -> entry_ids
        self.trace_partitions: Dict[str, List[str]] = {}    # trace_id -> entry_ids
        self.memory_stats = {
            "total_entries": 0,
            "entries_by_type": {},
            "total_size": 0,
            "last_cleanup": None
        }
        
        logger.info("Memory manager initialized", agent_id=agent_id, ttl=ttl)
    
    async def initialize(self) -> None:
        """初始化内存管理器"""
        try:
            logger.info("Initializing memory manager", agent_id=self.agent_id)
            
            # 加载持久化内存数据
            await self._load_persistent_memory()
            
            # 初始化统计信息
            self._update_stats()
            
            logger.info("Memory manager initialized successfully", agent_id=self.agent_id)
            
        except Exception as e:
            logger.error("Failed to initialize memory manager", error=str(e))
            raise
    
    async def is_healthy(self) -> bool:
        """检查内存管理器健康状态"""
        try:
            # 检查基本状态
            if not self.memory_entries:
                return True  # 空内存也是健康的
            
            # 检查内存条目完整性
            for entry in self.memory_entries:
                if not entry.content or not entry.context_id:
                    return False
            
            return True
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False
    
    async def add_memory(
        self,
        content: str,
        memory_type: MemoryType,
        context_id: str,
        trace_id: Optional[str] = None,
        metadata: Dict[str, Any] = None,
        ttl: Optional[int] = None
    ) -> str:
        """
        添加内存条目
        
        Args:
            content: 内容
            memory_type: 内存类型
            context_id: 上下文ID
            trace_id: 追踪ID
            metadata: 元数据
            ttl: 生存时间
            
        Returns:
            条目ID
        """
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            context_id=context_id,
            trace_id=trace_id,
            metadata=metadata or {}
        )
        
        self.memory_entries.append(entry)
        
        # 更新分区索引
        if context_id not in self.context_partitions:
            self.context_partitions[context_id] = []
        self.context_partitions[context_id].append(entry.entry_id)
        
        if trace_id:
            if trace_id not in self.trace_partitions:
                self.trace_partitions[trace_id] = []
            self.trace_partitions[trace_id].append(entry.entry_id)
        
        # 更新统计
        self._update_stats()
        
        # 设置过期清理
        if ttl is None:
            ttl = self.ttl
        asyncio.create_task(self._schedule_cleanup(entry.entry_id, ttl))
        
        logger.debug("Memory entry added", entry_id=entry.entry_id, memory_type=memory_type.value)
        return entry.entry_id
    
    async def get_memory(self, entry_id: str) -> Optional[MemoryEntry]:
        """
        获取内存条目
        
        Args:
            entry_id: 条目ID
            
        Returns:
            内存条目
        """
        for entry in self.memory_entries:
            if entry.entry_id == entry_id:
                entry.access_count += 1
                entry.last_accessed = datetime.utcnow()
                return entry
        return None
    
    async def get_memories_by_context(self, context_id: str, limit: int = 10) -> List[MemoryEntry]:
        """
        根据上下文ID获取内存条目
        
        Args:
            context_id: 上下文ID
            limit: 限制数量
            
        Returns:
            内存条目列表
        """
        entries = []
        for entry in self.memory_entries:
            if entry.context_id == context_id:
                entries.append(entry)
                if len(entries) >= limit:
                    break
        return entries
    
    async def get_memories_by_trace(self, trace_id: str) -> List[MemoryEntry]:
        """
        根据追踪ID获取内存条目
        
        Args:
            trace_id: 追踪ID
            
        Returns:
            内存条目列表
        """
        return [entry for entry in self.memory_entries if entry.trace_id == trace_id]
    
    async def get_memories_by_type(self, memory_type: MemoryType, limit: int = 10) -> List[MemoryEntry]:
        """
        根据类型获取内存条目
        
        Args:
            memory_type: 内存类型
            limit: 限制数量
            
        Returns:
            内存条目列表
        """
        entries = []
        for entry in self.memory_entries:
            if entry.memory_type == memory_type:
                entries.append(entry)
                if len(entries) >= limit:
                    break
        return entries
    
    async def get_relevant_memories(self, query: str, context_id: str, limit: int = 5) -> List[MemoryEntry]:
        """
        获取相关内存条目（简单实现）
        
        Args:
            query: 查询内容
            context_id: 上下文ID
            limit: 限制数量
            
        Returns:
            相关内存条目列表
        """
        # 简单的相关性计算：基于上下文ID和时间
        relevant_entries = []
        for entry in self.memory_entries:
            if entry.context_id == context_id:
                relevant_entries.append(entry)
        
        # 按访问时间排序，返回最近的
        relevant_entries.sort(key=lambda x: x.last_accessed, reverse=True)
        return relevant_entries[:limit]
    
    async def delete_memory(self, entry_id: str) -> bool:
        """
        删除内存条目
        
        Args:
            entry_id: 条目ID
            
        Returns:
            是否删除成功
        """
        for i, entry in enumerate(self.memory_entries):
            if entry.entry_id == entry_id:
                # 从分区索引中移除
                if entry.context_id in self.context_partitions:
                    self.context_partitions[entry.context_id] = [
                        eid for eid in self.context_partitions[entry.context_id] 
                        if eid != entry_id
                    ]
                
                if entry.trace_id and entry.trace_id in self.trace_partitions:
                    self.trace_partitions[entry.trace_id] = [
                        eid for eid in self.trace_partitions[entry.trace_id] 
                        if eid != entry_id
                    ]
                
                # 从内存条目中移除
                del self.memory_entries[i]
                
                # 更新统计
                self._update_stats()
                
                logger.debug("Memory entry deleted", entry_id=entry_id)
                return True
        
        return False
    
    async def clear_context_memories(self, context_id: str) -> int:
        """
        清除指定上下文的所有内存条目
        
        Args:
            context_id: 上下文ID
            
        Returns:
            删除的条目数量
        """
        deleted_count = 0
        entries_to_delete = []
        
        for entry in self.memory_entries:
            if entry.context_id == context_id:
                entries_to_delete.append(entry.entry_id)
        
        for entry_id in entries_to_delete:
            if await self.delete_memory(entry_id):
                deleted_count += 1
        
        logger.info("Context memories cleared", context_id=context_id, deleted_count=deleted_count)
        return deleted_count
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """
        获取内存统计信息
        
        Returns:
            统计信息
        """
        self._update_stats()
        return {
            "agent_id": self.agent_id,
            "total_entries": self.memory_stats["total_entries"],
            "entries_by_type": self.memory_stats["entries_by_type"],
            "total_size": self.memory_stats["total_size"],
            "context_partitions": len(self.context_partitions),
            "trace_partitions": len(self.trace_partitions),
            "last_cleanup": self.memory_stats["last_cleanup"]
        }
    
    def _update_stats(self) -> None:
        """更新统计信息"""
        self.memory_stats["total_entries"] = len(self.memory_entries)
        
        # 按类型统计
        type_counts = {}
        total_size = 0
        for entry in self.memory_entries:
            memory_type = entry.memory_type.value
            type_counts[memory_type] = type_counts.get(memory_type, 0) + 1
            total_size += len(entry.content)
        
        self.memory_stats["entries_by_type"] = type_counts
        self.memory_stats["total_size"] = total_size
    
    async def _load_persistent_memory(self) -> None:
        """加载持久化内存"""
        # 这里应该从数据库或文件系统加载持久化的内存数据
        # 暂时为空实现
        pass
    
    async def _save_persistent_memory(self) -> None:
        """保存持久化内存"""
        # 这里应该将内存保存到数据库或文件系统
        # 暂时为空实现
        pass
    
    # 保留原有的简单存储方法以保持兼容性
    async def store(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        存储数据（兼容性方法）
        
        Args:
            key: 数据键
            value: 数据值
            ttl: 生存时间（秒）
        """
        self.data[key] = value
        self.timestamps[key] = datetime.utcnow()
        
        # 设置过期时间
        if ttl is None:
            ttl = self.ttl
        
        # 异步清理过期数据
        asyncio.create_task(self._schedule_cleanup(key, ttl))
        
        logger.debug("Data stored", key=key, ttl=ttl)
    
    async def retrieve(self, key: str, default: Any = None) -> Any:
        """
        检索数据（兼容性方法）
        
        Args:
            key: 数据键
            default: 默认值
            
        Returns:
            数据值
        """
        # 检查是否过期
        if key in self.timestamps:
            timestamp = self.timestamps[key]
            if datetime.utcnow() - timestamp > timedelta(seconds=self.ttl):
                # 数据已过期，删除
                await self.delete(key)
                return default
        
        return self.data.get(key, default)
    
    async def delete(self, key: str):
        """
        删除数据（兼容性方法）
        
        Args:
            key: 数据键
        """
        if key in self.data:
            del self.data[key]
        if key in self.timestamps:
            del self.timestamps[key]
        
        logger.debug("Data deleted", key=key)
    
    async def exists(self, key: str) -> bool:
        """
        检查数据是否存在（兼容性方法）
        
        Args:
            key: 数据键
            
        Returns:
            是否存在
        """
        if key not in self.data:
            return False
        
        # 检查是否过期
        if key in self.timestamps:
            timestamp = self.timestamps[key]
            if datetime.utcnow() - timestamp > timedelta(seconds=self.ttl):
                await self.delete(key)
                return False
        
        return True
    
    async def get_all_keys(self) -> List[str]:
        """
        获取所有键（兼容性方法）
        
        Returns:
            键列表
        """
        # 清理过期数据
        await self._cleanup_expired()
        return list(self.data.keys())
    
    async def get_size(self) -> int:
        """获取内存大小（兼容性方法）"""
        await self._cleanup_expired()
        return len(self.data)
    
    async def clear(self):
        """清空内存（兼容性方法）"""
        self.data.clear()
        self.timestamps.clear()
        self.memory_entries.clear()
        self.context_partitions.clear()
        self.trace_partitions.clear()
        self._update_stats()
        logger.info("Memory cleared", agent_id=self.agent_id)
    
    async def _schedule_cleanup(self, key: str, ttl: int):
        """调度清理任务"""
        await asyncio.sleep(ttl)
        if key in self.timestamps:
            timestamp = self.timestamps[key]
            if datetime.utcnow() - timestamp > timedelta(seconds=ttl):
                await self.delete(key)
    
    async def _cleanup_expired(self):
        """清理过期数据"""
        current_time = datetime.utcnow()
        expired_keys = []
        
        for key, timestamp in self.timestamps.items():
            if current_time - timestamp > timedelta(seconds=self.ttl):
                expired_keys.append(key)
        
        for key in expired_keys:
            await self.delete(key)
        
        if expired_keys:
            logger.debug("Expired data cleaned", count=len(expired_keys))
    
    async def get_summary(self) -> Dict[str, Any]:
        """获取内存摘要（兼容性方法）"""
        await self._cleanup_expired()
        
        return {
            "agent_id": self.agent_id,
            "total_keys": len(self.data),
            "ttl": self.ttl,
            "keys": list(self.data.keys()),
            "memory_entries": await self.get_memory_stats()
        } 