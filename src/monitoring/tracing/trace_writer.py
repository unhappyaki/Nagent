"""
追踪写入器模块
实现行为链的完整追踪和审计功能，包括trace记录、链路追踪、行为审计等
"""

import time
import json
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime


class TraceLevel(Enum):
    """追踪级别枚举"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TraceType(Enum):
    """追踪类型枚举"""
    BEHAVIOR = "behavior"           # 行为追踪
    REASONING = "reasoning"         # 推理追踪
    TOOL_CALL = "tool_call"         # 工具调用追踪
    ACP_MESSAGE = "acp_message"     # ACP消息追踪
    SESSION = "session"             # 会话追踪
    MEMORY = "memory"               # 内存追踪
    CALLBACK = "callback"           # 回调追踪


@dataclass
class TraceEntry:
    """追踪条目"""
    trace_id: str                   # 追踪ID
    context_id: str                 # 上下文ID
    session_id: Optional[str]       # 会话ID
    agent_id: Optional[str]         # 智能体ID
    trace_type: TraceType           # 追踪类型
    level: TraceLevel               # 追踪级别
    timestamp: int                  # 时间戳
    message: str                    # 消息
    data: Dict[str, Any]           # 数据
    parent_trace_id: Optional[str] = None  # 父追踪ID
    duration: Optional[float] = None  # 持续时间


class TraceWriter:
    """
    追踪写入器
    负责记录和管理系统的所有追踪信息
    """
    
    def __init__(self, storage_backend=None):
        """
        初始化追踪写入器
        
        Args:
            storage_backend: 存储后端（可选）
        """
        self.storage_backend = storage_backend
        self.logger = logging.getLogger(__name__)
        
        # 内存存储（临时）
        self.trace_entries = []
        self.trace_chains = {}  # trace_id -> 追踪链
        
        # 配置
        self.enable_tracing = True
        self.max_entries = 10000
        self.auto_cleanup = True
    
    async def initialize(self):
        """兼容框架的初始化流程，实际可为空实现"""
        pass
    
    def record_trace(self,
                    trace_id: str,
                    context_id: str,
                    trace_type: TraceType,
                    message: str,
                    data: Dict[str, Any] = None,
                    level: TraceLevel = TraceLevel.INFO,
                    session_id: str = None,
                    agent_id: str = None,
                    parent_trace_id: str = None,
                    duration: float = None) -> str:
        """
        记录追踪信息
        
        Args:
            trace_id: 追踪ID
            context_id: 上下文ID
            trace_type: 追踪类型
            message: 消息
            data: 数据
            level: 追踪级别
            session_id: 会话ID
            agent_id: 智能体ID
            parent_trace_id: 父追踪ID
            duration: 持续时间
            
        Returns:
            str: 追踪条目ID
        """
        if not self.enable_tracing:
            return ""
        
        try:
            entry = TraceEntry(
                trace_id=trace_id,
                context_id=context_id,
                session_id=session_id,
                agent_id=agent_id,
                trace_type=trace_type,
                level=level,
                timestamp=int(time.time()),
                message=message,
                data=data or {},
                parent_trace_id=parent_trace_id,
                duration=duration
            )
            
            # 添加到内存存储
            self.trace_entries.append(entry)
            
            # 构建追踪链
            if trace_id not in self.trace_chains:
                self.trace_chains[trace_id] = []
            self.trace_chains[trace_id].append(entry)
            
            # 写入存储后端
            if self.storage_backend:
                self._write_to_backend(entry)
            
            # 自动清理
            if self.auto_cleanup and len(self.trace_entries) > self.max_entries:
                self._cleanup_old_entries()
            
            self.logger.debug(f"Trace recorded: {trace_id} - {message}")
            return trace_id
            
        except Exception as e:
            self.logger.error(f"Failed to record trace: {e}")
            return ""
    
    def record_behavior_trace(self,
                            trace_id: str,
                            context_id: str,
                            intent: str,
                            from_agent: str,
                            to_agent: str,
                            intent_type: str,
                            data: Dict[str, Any] = None) -> str:
        """
        记录行为追踪
        
        Args:
            trace_id: 追踪ID
            context_id: 上下文ID
            intent: 行为意图
            from_agent: 发起方智能体
            to_agent: 目标智能体
            intent_type: 意图类型
            data: 额外数据
            
        Returns:
            str: 追踪条目ID
        """
        return self.record_trace(
            trace_id=trace_id,
            context_id=context_id,
            trace_type=TraceType.BEHAVIOR,
            message=f"Behavior: {intent} from {from_agent} to {to_agent}",
            data={
                "intent": intent,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "intent_type": intent_type,
                **(data or {})
            }
        )
    
    def record_reasoning_trace(self,
                             trace_id: str,
                             context_id: str,
                             reasoning_input: Dict[str, Any],
                             reasoning_output: Dict[str, Any],
                             session_id: str = None,
                             agent_id: str = None) -> str:
        """
        记录推理追踪
        
        Args:
            trace_id: 追踪ID
            context_id: 上下文ID
            reasoning_input: 推理输入
            reasoning_output: 推理输出
            session_id: 会话ID
            agent_id: 智能体ID
            
        Returns:
            str: 追踪条目ID
        """
        return self.record_trace(
            trace_id=trace_id,
            context_id=context_id,
            session_id=session_id,
            agent_id=agent_id,
            trace_type=TraceType.REASONING,
            message="Reasoning execution",
            data={
                "input": reasoning_input,
                "output": reasoning_output
            }
        )
    
    def record_tool_call_trace(self,
                              trace_id: str,
                              context_id: str,
                              tool_name: str,
                              parameters: Dict[str, Any],
                              result: Dict[str, Any],
                              session_id: str = None,
                              agent_id: str = None) -> str:
        """
        记录工具调用追踪
        
        Args:
            trace_id: 追踪ID
            context_id: 上下文ID
            tool_name: 工具名称
            parameters: 工具参数
            result: 执行结果
            session_id: 会话ID
            agent_id: 智能体ID
            
        Returns:
            str: 追踪条目ID
        """
        return self.record_trace(
            trace_id=trace_id,
            context_id=context_id,
            session_id=session_id,
            agent_id=agent_id,
            trace_type=TraceType.TOOL_CALL,
            message=f"Tool call: {tool_name}",
            data={
                "tool_name": tool_name,
                "parameters": parameters,
                "result": result
            }
        )
    
    def record_acp_message(self,
                          trace_id: str,
                          context_id: str,
                          message_type: str,
                          payload: Dict[str, Any]) -> str:
        """
        记录ACP消息追踪
        
        Args:
            trace_id: 追踪ID
            context_id: 上下文ID
            message_type: 消息类型
            payload: 消息载荷
            
        Returns:
            str: 追踪条目ID
        """
        return self.record_trace(
            trace_id=trace_id,
            context_id=context_id,
            trace_type=TraceType.ACP_MESSAGE,
            message=f"ACP {message_type}",
            data={
                "message_type": message_type,
                "payload": payload
            }
        )
    
    def record_session_trace(self,
                           trace_id: str,
                           context_id: str,
                           session_id: str,
                           action: str,
                           data: Dict[str, Any] = None) -> str:
        """
        记录会话追踪
        
        Args:
            trace_id: 追踪ID
            context_id: 上下文ID
            session_id: 会话ID
            action: 会话动作
            data: 额外数据
            
        Returns:
            str: 追踪条目ID
        """
        return self.record_trace(
            trace_id=trace_id,
            context_id=context_id,
            session_id=session_id,
            trace_type=TraceType.SESSION,
            message=f"Session {action}",
            data={
                "action": action,
                **(data or {})
            }
        )
    
    def get_trace_chain(self, trace_id: str) -> List[TraceEntry]:
        """
        获取追踪链
        
        Args:
            trace_id: 追踪ID
            
        Returns:
            List[TraceEntry]: 追踪链
        """
        return self.trace_chains.get(trace_id, [])
    
    def get_traces_by_context(self, context_id: str) -> List[TraceEntry]:
        """
        根据上下文ID获取追踪条目
        
        Args:
            context_id: 上下文ID
            
        Returns:
            List[TraceEntry]: 追踪条目列表
        """
        return [entry for entry in self.trace_entries if entry.context_id == context_id]
    
    def get_traces_by_session(self, session_id: str) -> List[TraceEntry]:
        """
        根据会话ID获取追踪条目
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[TraceEntry]: 追踪条目列表
        """
        return [entry for entry in self.trace_entries if entry.session_id == session_id]
    
    def get_traces_by_type(self, trace_type: TraceType) -> List[TraceEntry]:
        """
        根据追踪类型获取追踪条目
        
        Args:
            trace_type: 追踪类型
            
        Returns:
            List[TraceEntry]: 追踪条目列表
        """
        return [entry for entry in self.trace_entries if entry.trace_type == trace_type]
    
    def get_traces_by_level(self, level: TraceLevel) -> List[TraceEntry]:
        """
        根据追踪级别获取追踪条目
        
        Args:
            level: 追踪级别
            
        Returns:
            List[TraceEntry]: 追踪条目列表
        """
        return [entry for entry in self.trace_entries if entry.level == level]
    
    def search_traces(self, 
                     context_id: str = None,
                     session_id: str = None,
                     agent_id: str = None,
                     trace_type: TraceType = None,
                     level: TraceLevel = None,
                     start_time: int = None,
                     end_time: int = None) -> List[TraceEntry]:
        """
        搜索追踪条目
        
        Args:
            context_id: 上下文ID
            session_id: 会话ID
            agent_id: 智能体ID
            trace_type: 追踪类型
            level: 追踪级别
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            List[TraceEntry]: 追踪条目列表
        """
        results = self.trace_entries
        
        if context_id:
            results = [entry for entry in results if entry.context_id == context_id]
        if session_id:
            results = [entry for entry in results if entry.session_id == session_id]
        if agent_id:
            results = [entry for entry in results if entry.agent_id == agent_id]
        if trace_type:
            results = [entry for entry in results if entry.trace_type == trace_type]
        if level:
            results = [entry for entry in results if entry.level == level]
        if start_time:
            results = [entry for entry in results if entry.timestamp >= start_time]
        if end_time:
            results = [entry for entry in results if entry.timestamp <= end_time]
        
        return results
    
    def export_traces(self, 
                     trace_ids: List[str] = None,
                     format: str = "json") -> str:
        """
        导出追踪数据
        
        Args:
            trace_ids: 追踪ID列表
            format: 导出格式
            
        Returns:
            str: 导出的数据
        """
        if trace_ids:
            entries = []
            for trace_id in trace_ids:
                entries.extend(self.get_trace_chain(trace_id))
        else:
            entries = self.trace_entries
        
        if format.lower() == "json":
            return json.dumps([asdict(entry) for entry in entries], 
                            ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _write_to_backend(self, entry: TraceEntry):
        """写入存储后端"""
        if self.storage_backend and hasattr(self.storage_backend, 'write_trace'):
            try:
                self.storage_backend.write_trace(entry)
            except Exception as e:
                self.logger.error(f"Failed to write to backend: {e}")
    
    def _cleanup_old_entries(self):
        """清理旧的追踪条目"""
        if len(self.trace_entries) > self.max_entries:
            # 保留最新的条目
            self.trace_entries = self.trace_entries[-self.max_entries:]
            
            # 重新构建追踪链
            self.trace_chains = {}
            for entry in self.trace_entries:
                if entry.trace_id not in self.trace_chains:
                    self.trace_chains[entry.trace_id] = []
                self.trace_chains[entry.trace_id].append(entry)
            
            self.logger.info(f"Cleaned up trace entries, kept {len(self.trace_entries)} entries")
    
    def get_trace_stats(self) -> Dict[str, Any]:
        """
        获取追踪统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        total_entries = len(self.trace_entries)
        total_chains = len(self.trace_chains)
        
        type_stats = {}
        level_stats = {}
        
        for entry in self.trace_entries:
            # 按类型统计
            type_name = entry.trace_type.value
            type_stats[type_name] = type_stats.get(type_name, 0) + 1
            
            # 按级别统计
            level_name = entry.level.value
            level_stats[level_name] = level_stats.get(level_name, 0) + 1
        
        return {
            "total_entries": total_entries,
            "total_chains": total_chains,
            "type_stats": type_stats,
            "level_stats": level_stats,
            "oldest_entry": min([entry.timestamp for entry in self.trace_entries]) if self.trace_entries else 0,
            "newest_entry": max([entry.timestamp for entry in self.trace_entries]) if self.trace_entries else 0
        } 

    async def start_trace(self, trace_id, task):
        """兼容追踪调用，空实现"""
        pass
    async def end_trace(self, trace_id, execution_result):
        """兼容追踪调用，空实现"""
        pass 