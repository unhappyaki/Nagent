"""
回调控制模块

实现企业级架构的回调机制，支持：
- 状态锚点：将工具执行结果写入memory
- 审计锚点：将callback行为写入trace
- 链路锚点：决定是否继续执行后续行为
- 异常链回调与中断恢复
- 多Agent协同下的回调权限管理
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class CallbackType(Enum):
    """回调类型枚举"""
    SUCCESS = "success"
    ERROR = "error"
    FALLBACK = "fallback"
    INTERRUPT = "interrupt"
    RESUME = "resume"


class CallbackStatus(Enum):
    """回调状态枚举"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CallbackResult:
    """回调结果结构"""
    
    def __init__(
        self,
        callback_id: str,
        status: CallbackStatus,
        result: Any = None,
        error: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ):
        """
        初始化回调结果
        
        Args:
            callback_id: 回调ID
            status: 回调状态
            result: 结果
            error: 错误信息
            metadata: 元数据
        """
        self.callback_id = callback_id
        self.status = status
        self.result = result
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "callback_id": self.callback_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class CallbackHandler:
    """
    回调处理器
    
    实现企业级架构的回调控制机制
    """
    
    def __init__(self, agent_id: str):
        """
        初始化回调处理器
        
        Args:
            agent_id: Agent ID
        """
        self.agent_id = agent_id
        self.callback_id = str(uuid.uuid4())
        
        # 回调注册表
        self.callbacks: Dict[str, Callable] = {}
        self.callback_results: Dict[str, CallbackResult] = {}
        
        # 回调策略
        self.callback_policies = {
            "max_retries": 3,
            "retry_delay": 1.0,
            "timeout": 30.0,
            "enable_fallback": True,
            "enable_audit": True
        }
        
        # 回调统计
        self.callback_stats = {
            "total_callbacks": 0,
            "successful_callbacks": 0,
            "failed_callbacks": 0,
            "fallback_callbacks": 0,
            "total_execution_time": 0.0
        }
        
        logger.info("Callback handler initialized", agent_id=agent_id, callback_id=self.callback_id)
    
    async def initialize(self) -> None:
        """初始化回调处理器"""
        try:
            logger.info("Initializing callback handler", agent_id=self.agent_id)
            
            # 注册默认回调
            await self._register_default_callbacks()
            
            logger.info("Callback handler initialized successfully", agent_id=self.agent_id)
            
        except Exception as e:
            logger.error("Failed to initialize callback handler", error=str(e))
            raise
    
    async def is_healthy(self) -> bool:
        """检查回调处理器健康状态"""
        try:
            # 检查基本状态
            if not self.callbacks:
                return False
            
            # 检查是否有必要的回调
            required_callbacks = ["memory_write", "trace_write", "status_update"]
            for callback_name in required_callbacks:
                if callback_name not in self.callbacks:
                    return False
            
            return True
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False
    
    async def register_callback(self, name: str, callback_func: Callable) -> None:
        """
        注册回调函数
        
        Args:
            name: 回调名称
            callback_func: 回调函数
        """
        self.callbacks[name] = callback_func
        logger.debug("Callback registered", name=name, agent_id=self.agent_id)
    
    async def handle_callback(
        self,
        callback_type: CallbackType,
        data: Dict[str, Any],
        context_id: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> CallbackResult:
        """
        处理回调
        
        Args:
            callback_type: 回调类型
            data: 回调数据
            context_id: 上下文ID
            trace_id: 追踪ID
            **kwargs: 额外参数
            
        Returns:
            回调结果
        """
        callback_id = str(uuid.uuid4())
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.callback_stats["total_callbacks"] += 1
            
            # 创建回调结果
            result = CallbackResult(
                callback_id=callback_id,
                status=CallbackStatus.EXECUTING
            )
            self.callback_results[callback_id] = result
            
            logger.debug(
                "Callback started",
                callback_id=callback_id,
                callback_type=callback_type.value,
                context_id=context_id
            )
            
            # 根据回调类型执行相应的处理
            if callback_type == CallbackType.SUCCESS:
                await self._handle_success_callback(data, context_id, trace_id, **kwargs)
            elif callback_type == CallbackType.ERROR:
                await self._handle_error_callback(data, context_id, trace_id, **kwargs)
            elif callback_type == CallbackType.FALLBACK:
                await self._handle_fallback_callback(data, context_id, trace_id, **kwargs)
            elif callback_type == CallbackType.INTERRUPT:
                await self._handle_interrupt_callback(data, context_id, trace_id, **kwargs)
            elif callback_type == CallbackType.RESUME:
                await self._handle_resume_callback(data, context_id, trace_id, **kwargs)
            else:
                raise ValueError(f"Unsupported callback type: {callback_type}")
            
            # 更新结果
            result.status = CallbackStatus.COMPLETED
            result.result = data
            self.callback_stats["successful_callbacks"] += 1
            
            execution_time = asyncio.get_event_loop().time() - start_time
            self.callback_stats["total_execution_time"] += execution_time
            
            logger.info(
                "Callback completed successfully",
                callback_id=callback_id,
                callback_type=callback_type.value,
                execution_time=execution_time
            )
            
            return result
            
        except Exception as e:
            # 处理异常
            result.status = CallbackStatus.FAILED
            result.error = str(e)
            self.callback_stats["failed_callbacks"] += 1
            
            logger.error(
                "Callback failed",
                callback_id=callback_id,
                callback_type=callback_type.value,
                error=str(e)
            )
            
            # 尝试fallback
            if self.callback_policies["enable_fallback"]:
                return await self._handle_fallback_callback(data, context_id, trace_id, error=e, **kwargs)
            
            return result
    
    async def _handle_success_callback(
        self,
        data: Dict[str, Any],
        context_id: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """处理成功回调"""
        # 状态锚点：写入memory
        if "memory_write" in self.callbacks:
            await self.callbacks["memory_write"](
                content=str(data.get("result", "")),
                memory_type="tool_result",
                context_id=context_id,
                trace_id=trace_id,
                metadata={"callback_type": "success"}
            )
        
        # 审计锚点：写入trace
        if "trace_write" in self.callbacks and self.callback_policies["enable_audit"]:
            await self.callbacks["trace_write"](
                event_type="callback_success",
                data=data,
                context_id=context_id,
                trace_id=trace_id
            )
        
        # 链路锚点：状态更新
        if "status_update" in self.callbacks:
            await self.callbacks["status_update"](
                status="completed",
                data=data,
                context_id=context_id
            )
    
    async def _handle_error_callback(
        self,
        data: Dict[str, Any],
        context_id: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """处理错误回调"""
        error_info = data.get("error", "Unknown error")
        
        # 状态锚点：记录错误到memory
        if "memory_write" in self.callbacks:
            await self.callbacks["memory_write"](
                content=f"Error: {error_info}",
                memory_type="error",
                context_id=context_id,
                trace_id=trace_id,
                metadata={"callback_type": "error", "error": error_info}
            )
        
        # 审计锚点：记录错误trace
        if "trace_write" in self.callbacks and self.callback_policies["enable_audit"]:
            await self.callbacks["trace_write"](
                event_type="callback_error",
                data={"error": error_info, **data},
                context_id=context_id,
                trace_id=trace_id
            )
        
        # 链路锚点：错误状态更新
        if "status_update" in self.callbacks:
            await self.callbacks["status_update"](
                status="error",
                data={"error": error_info, **data},
                context_id=context_id
            )
    
    async def _handle_fallback_callback(
        self,
        data: Dict[str, Any],
        context_id: str,
        trace_id: Optional[str] = None,
        error: Optional[Exception] = None,
        **kwargs
    ) -> CallbackResult:
        """处理fallback回调"""
        self.callback_stats["fallback_callbacks"] += 1
        
        # 记录fallback到memory
        if "memory_write" in self.callbacks:
            await self.callbacks["memory_write"](
                content=f"Fallback triggered: {error}",
                memory_type="fallback",
                context_id=context_id,
                trace_id=trace_id,
                metadata={"callback_type": "fallback", "error": str(error) if error else "Unknown"}
            )
        
        # 记录fallback trace
        if "trace_write" in self.callbacks and self.callback_policies["enable_audit"]:
            await self.callbacks["trace_write"](
                event_type="callback_fallback",
                data={"error": str(error) if error else "Unknown", **data},
                context_id=context_id,
                trace_id=trace_id
            )
        
        # 尝试执行fallback策略
        fallback_result = await self._execute_fallback_strategy(data, context_id, trace_id, error, **kwargs)
        
        return CallbackResult(
            callback_id=str(uuid.uuid4()),
            status=CallbackStatus.COMPLETED if fallback_result else CallbackStatus.FAILED,
            result=fallback_result,
            error=str(error) if error else None,
            metadata={"callback_type": "fallback"}
        )
    
    async def _handle_interrupt_callback(
        self,
        data: Dict[str, Any],
        context_id: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """处理中断回调"""
        # 记录中断到memory
        if "memory_write" in self.callbacks:
            await self.callbacks["memory_write"](
                content="Task interrupted",
                memory_type="interrupt",
                context_id=context_id,
                trace_id=trace_id,
                metadata={"callback_type": "interrupt"}
            )
        
        # 记录中断trace
        if "trace_write" in self.callbacks and self.callback_policies["enable_audit"]:
            await self.callbacks["trace_write"](
                event_type="callback_interrupt",
                data=data,
                context_id=context_id,
                trace_id=trace_id
            )
        
        # 更新状态为中断
        if "status_update" in self.callbacks:
            await self.callbacks["status_update"](
                status="interrupted",
                data=data,
                context_id=context_id
            )
    
    async def _handle_resume_callback(
        self,
        data: Dict[str, Any],
        context_id: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """处理恢复回调"""
        # 记录恢复到memory
        if "memory_write" in self.callbacks:
            await self.callbacks["memory_write"](
                content="Task resumed",
                memory_type="resume",
                context_id=context_id,
                trace_id=trace_id,
                metadata={"callback_type": "resume"}
            )
        
        # 记录恢复trace
        if "trace_write" in self.callbacks and self.callback_policies["enable_audit"]:
            await self.callbacks["trace_write"](
                event_type="callback_resume",
                data=data,
                context_id=context_id,
                trace_id=trace_id
            )
        
        # 更新状态为恢复
        if "status_update" in self.callbacks:
            await self.callbacks["status_update"](
                status="resumed",
                data=data,
                context_id=context_id
            )
    
    async def _execute_fallback_strategy(
        self,
        data: Dict[str, Any],
        context_id: str,
        trace_id: Optional[str] = None,
        error: Optional[Exception] = None,
        **kwargs
    ) -> Any:
        """执行fallback策略"""
        try:
            # 简单的fallback策略：重试或使用默认值
            if "fallback_handler" in self.callbacks:
                return await self.callbacks["fallback_handler"](data, context_id, trace_id, error, **kwargs)
            
            # 默认fallback：返回错误信息
            return {
                "fallback_result": "Default fallback executed",
                "original_error": str(error) if error else "Unknown error",
                "context_id": context_id
            }
            
        except Exception as e:
            logger.error("Fallback strategy failed", error=str(e))
            return None
    
    async def _register_default_callbacks(self) -> None:
        """注册默认回调"""
        # 这些回调函数应该由外部注入
        # 这里只是占位符
        self.callbacks["memory_write"] = self._default_memory_write
        self.callbacks["trace_write"] = self._default_trace_write
        self.callbacks["status_update"] = self._default_status_update
        self.callbacks["fallback_handler"] = self._default_fallback_handler
        
        logger.info("Default callbacks registered", agent_id=self.agent_id)
    
    async def _default_memory_write(self, *args, **kwargs) -> None:
        """默认内存写入回调"""
        logger.debug("Default memory write callback", args=args, kwargs=kwargs)
    
    async def _default_trace_write(self, *args, **kwargs) -> None:
        """默认trace写入回调"""
        logger.debug("Default trace write callback", args=args, kwargs=kwargs)
    
    async def _default_status_update(self, *args, **kwargs) -> None:
        """默认状态更新回调"""
        logger.debug("Default status update callback", args=args, kwargs=kwargs)
    
    async def _default_fallback_handler(self, *args, **kwargs) -> Any:
        """默认fallback处理器"""
        logger.debug("Default fallback handler", args=args, kwargs=kwargs)
        return {"fallback": "default"}
    
    async def get_callback_result(self, callback_id: str) -> Optional[CallbackResult]:
        """
        获取回调结果
        
        Args:
            callback_id: 回调ID
            
        Returns:
            回调结果
        """
        return self.callback_results.get(callback_id)
    
    async def get_callback_stats(self) -> Dict[str, Any]:
        """
        获取回调统计信息
        
        Returns:
            统计信息
        """
        total_callbacks = self.callback_stats["total_callbacks"]
        success_rate = (
            self.callback_stats["successful_callbacks"] / total_callbacks 
            if total_callbacks > 0 else 0
        )
        
        return {
            "agent_id": self.agent_id,
            "callback_id": self.callback_id,
            "total_callbacks": total_callbacks,
            "successful_callbacks": self.callback_stats["successful_callbacks"],
            "failed_callbacks": self.callback_stats["failed_callbacks"],
            "fallback_callbacks": self.callback_stats["fallback_callbacks"],
            "success_rate": success_rate,
            "total_execution_time": self.callback_stats["total_execution_time"],
            "average_execution_time": (
                self.callback_stats["total_execution_time"] / total_callbacks 
                if total_callbacks > 0 else 0
            )
        }
    
    async def clear_results(self) -> None:
        """清理回调结果"""
        self.callback_results.clear()
        logger.info("Callback results cleared", agent_id=self.agent_id) 