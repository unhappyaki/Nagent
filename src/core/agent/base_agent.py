"""
Agent基类

定义所有Agent的基础接口和通用功能，包括：
- 生命周期管理
- 状态管理
- 推理决策
- 工具调用
- 错误处理
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from pydantic import BaseModel, Field
import structlog

from src.state.context import Context
from src.state.memory import Memory
from src.core.reasoning.reasoning_engine import ReasoningEngine
from src.core.tools.tool_registry import LocalToolRegistry
from src.monitoring.tracing.trace_writer import TraceWriter


logger = structlog.get_logger(__name__)


class AgentStatus(Enum):
    """Agent状态枚举"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    TERMINATED = "terminated"
    INITIALIZING = "initializing"
    STARTING = "starting"
    STOPPING = "stopping"


class AgentType(Enum):
    """Agent类型枚举"""
    TASK = "task_agent"
    REVIEW = "review_agent"
    WRITER = "writer_agent"
    PLANNER = "planner_agent"
    EXECUTOR = "executor_agent"
    WORKFLOW = "workflow_agent"


@dataclass
class AgentConfig:
    """Agent配置类"""
    agent_id: str
    agent_type: AgentType
    name: str
    description: str = ""
    model: str = "gpt-4"
    max_tokens: int = 4000
    temperature: float = 0.7
    timeout: int = 300
    retry_count: int = 3
    enabled_tools: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # 新增配置项
    max_concurrent_tasks: int = 5
    enable_auto_recovery: bool = True
    enable_performance_monitoring: bool = True
    session_timeout: int = 3600  # 会话超时时间（秒）


class AgentMessage(BaseModel):
    """Agent消息模型"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str
    receiver_id: str
    content: str
    message_type: str = "text"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # 新增字段
    priority: int = 0  # 消息优先级
    trace_id: Optional[str] = None  # 追踪ID
    context_id: Optional[str] = None  # 上下文ID


class AgentTask(BaseModel):
    """Agent任务模型"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    task_type: str
    task_data: Dict[str, Any]
    priority: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    timeout: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """
    Agent基类
    
    提供所有Agent的基础功能，包括：
    - 生命周期管理
    - 状态管理
    - 推理决策
    - 工具调用
    - 错误处理
    """
    
    def __init__(self, config: AgentConfig):
        """
        初始化Agent
        
        Args:
            config: Agent配置
        """
        self.config = config
        self.agent_id = config.agent_id
        self.agent_type = config.agent_type
        self.name = config.name
        self.description = config.description
        
        # 状态管理
        self.status = AgentStatus.INITIALIZING
        self.created_at = datetime.utcnow()
        self.last_active = datetime.utcnow()
        self.session_id = str(uuid.uuid4())
        
        # 任务管理
        self.active_tasks: Dict[str, AgentTask] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.max_concurrent_tasks = config.max_concurrent_tasks
        
        # 核心组件
        self.context = Context(agent_id=self.agent_id)
        self.memory = Memory(agent_id=self.agent_id)
        self.reasoning_engine = ReasoningEngine(
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )
        self.tool_registry = LocalToolRegistry()
        self.trace_manager = TraceWriter()
        
        # 统计信息
        self.stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_execution_time": 0,
            "average_response_time": 0,
            "messages_processed": 0,
            "errors_count": 0
        }
        
        # 性能监控
        self.performance_metrics = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "response_times": [],
            "throughput": 0.0
        }
        
        # 错误处理
        self.error_history: List[Dict[str, Any]] = []
        self.auto_recovery_enabled = config.enable_auto_recovery
        
        logger.info(
            "Agent initialized",
            agent_id=self.agent_id,
            agent_type=self.agent_type.value,
            name=self.name
        )
    
    async def start(self) -> None:
        """启动Agent"""
        try:
            self.status = AgentStatus.STARTING
            logger.info("Starting agent", agent_id=self.agent_id)
            
            # 初始化核心组件
            await self._initialize_components()
            
            # 启动任务处理器
            await self._start_task_processor()
            
            # 启动性能监控
            if self.config.enable_performance_monitoring:
                await self._start_performance_monitoring()
            
            # 调用子类启动逻辑
            await self._on_start()
            
            self.status = AgentStatus.IDLE
            logger.info("Agent started successfully", agent_id=self.agent_id)
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            await self._handle_error("start", e)
            logger.error("Failed to start agent", agent_id=self.agent_id, error=str(e))
            raise
    
    async def stop(self) -> None:
        """停止Agent"""
        try:
            self.status = AgentStatus.STOPPING
            logger.info("Stopping agent", agent_id=self.agent_id)
            
            # 停止任务处理器
            await self._stop_task_processor()
            
            # 停止性能监控
            if self.config.enable_performance_monitoring:
                await self._stop_performance_monitoring()
            
            # 清理资源
            await self._cleanup_resources()
            
            # 调用子类停止逻辑
            await self._on_stop()
            
            self.status = AgentStatus.TERMINATED
            logger.info("Agent stopped successfully", agent_id=self.agent_id)
            
        except Exception as e:
            await self._handle_error("stop", e)
            logger.error("Failed to stop agent", agent_id=self.agent_id, error=str(e))
            raise
    
    async def execute_task(self, task: str, **kwargs) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            task: 任务描述
            **kwargs: 额外参数
            
        Returns:
            执行结果
        """
        task_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        
        # 创建任务对象
        agent_task = AgentTask(
            task_id=task_id,
            agent_id=self.agent_id,
            task_type="execute",
            task_data={"task": task, **kwargs}
        )
        
        try:
            # 检查并发限制
            if len(self.active_tasks) >= self.max_concurrent_tasks:
                raise RuntimeError(f"Agent {self.agent_id} has reached maximum concurrent tasks limit")
            
            self.status = AgentStatus.BUSY
            self.last_active = datetime.utcnow()
            
            # 添加到活动任务
            self.active_tasks[task_id] = agent_task
            
            # 开始追踪
            await self.trace_manager.start_trace(trace_id, task)
            
            # 更新上下文
            await self.context.add_message("user", task)
            
            # 推理决策
            reasoning_result = await self._reason(task, **kwargs)
            
            # 执行动作
            execution_result = await self._execute(reasoning_result, **kwargs)
            
            # 更新状态
            await self._update_state(execution_result)
            
            # 记录统计
            self._update_stats(execution_result)
            
            # 结束追踪
            await self.trace_manager.end_trace(trace_id, execution_result)
            
            # 从活动任务中移除
            del self.active_tasks[task_id]
            
            self.status = AgentStatus.IDLE
            
            logger.info(
                "Task executed successfully",
                agent_id=self.agent_id,
                task_id=task_id,
                trace_id=trace_id,
                task=task
            )
            
            return {
                "task_id": task_id,
                "trace_id": trace_id,
                "status": "success",
                "result": execution_result,
                "reasoning": reasoning_result
            }
            
        except Exception as e:
            # 从活动任务中移除
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            
            await self._handle_error("execute_task", e, task_id=task_id)
            self.status = AgentStatus.ERROR
            
            return {
                "task_id": task_id,
                "trace_id": trace_id,
                "status": "error",
                "error": str(e)
            }
    
    async def submit_task(self, task: str, priority: int = 0, **kwargs) -> str:
        """
        提交任务到队列
        
        Args:
            task: 任务描述
            priority: 任务优先级
            **kwargs: 额外参数
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        agent_task = AgentTask(
            task_id=task_id,
            agent_id=self.agent_id,
            task_type="submit",
            task_data={"task": task, **kwargs},
            priority=priority
        )
        
        await self.task_queue.put((priority, agent_task))
        logger.info("Task submitted to queue", agent_id=self.agent_id, task_id=task_id)
        
        return task_id
    
    async def send_message(self, message: AgentMessage) -> None:
        """
        发送消息
        
        Args:
            message: 消息对象
        """
        try:
            # 验证消息
            if message.receiver_id != self.agent_id:
                raise ValueError(f"Message receiver_id {message.receiver_id} does not match agent_id {self.agent_id}")
            
            # 记录消息
            await self.context.add_message(message.sender_id, message.content)
            
            # 处理消息
            await self._on_message_received(message)
            
            # 更新统计
            self.stats["messages_processed"] += 1
            
            logger.info(
                "Message processed",
                agent_id=self.agent_id,
                message_id=message.message_id,
                sender_id=message.sender_id
            )
            
        except Exception as e:
            await self._handle_error("send_message", e, message_id=message.message_id)
            raise
    
    async def get_status(self) -> Dict[str, Any]:
        """
        获取Agent状态
        
        Returns:
            状态信息
        """
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "session_id": self.session_id,
            "active_tasks_count": len(self.active_tasks),
            "queue_size": self.task_queue.qsize(),
            "stats": self.stats,
            "performance_metrics": self.performance_metrics,
            "error_count": len(self.error_history)
        }
    
    async def get_health(self) -> Dict[str, Any]:
        """
        获取Agent健康状态
        
        Returns:
            健康状态信息
        """
        try:
            # 检查核心组件状态
            context_healthy = await self.context.is_healthy()
            memory_healthy = await self.memory.is_healthy()
            reasoning_healthy = await self.reasoning_engine.is_healthy()
            
            # 计算整体健康状态
            overall_health = all([context_healthy, memory_healthy, reasoning_healthy])
            
            return {
                "overall_health": overall_health,
                "components": {
                    "context": context_healthy,
                    "memory": memory_healthy,
                    "reasoning_engine": reasoning_healthy
                },
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Health check failed", agent_id=self.agent_id, error=str(e))
            return {
                "overall_health": False,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def _reason(self, task: str, **kwargs) -> Dict[str, Any]:
        """
        推理决策
        """
        try:
            # 构建推理上下文
            context_data = await self.context.get_context()
            # 获取 context_id，若无则用 'default'
            context_id = None
            if context_data and isinstance(context_data, list) and len(context_data) > 0:
                context_id = context_data[-1].get("context_id")
            if not context_id:
                context_id = "default"
            memory_data = await self.memory.get_relevant_memories(task, context_id)
            # 执行推理
            result = await self.reasoning_engine.reason(
                task=task,
                context=context_data,
                memory=memory_data,
                **kwargs
            )
            return result
        except Exception as e:
            logger.error("Reasoning failed", agent_id=self.agent_id, task=task, error=str(e))
            # 返回兼容结构，防止后续 KeyError
            return {"action": {"type": "respond", "parameters": {"response": f"推理失败: {str(e)}"}}}
    
    async def _execute(self, reasoning_result: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        执行动作
        """
        try:
            action = reasoning_result.get("action")
            if not action or not (isinstance(action, dict) and "type" in action):
                # 兜底，保证 action 一定有 type 字段
                action = {"type": "respond", "parameters": {"response": "没有可执行的动作。"}}
            # --- 兼容 action 为字符串的情况 ---
            if isinstance(action, str):
                action = {"type": action}
            # 检查是否需要工具调用
            if action.get("type") == "tool_call":
                tool_name = action.get("tool_name")
                tool_params = action.get("parameters", {})
                tool = self.tool_registry.get_tool(tool_name)
                if not tool:
                    raise ValueError(f"Tool {tool_name} not found")
                result = await tool.execute(tool_params)
            elif action.get("type") == "delegate":
                target_agent = action.get("target_agent")
                delegated_task = action.get("task")
                result = await self._delegate_task(target_agent, delegated_task, **kwargs)
            else:
                result = {"message": action.get("message", "Action completed")}
            return {
                "action": action,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error("Execution failed", agent_id=self.agent_id, error=str(e))
            raise
    
    async def _update_state(self, execution_result: Dict[str, Any]) -> None:
        """
        更新状态
        """
        try:
            # 获取 context_id，优先从 execution_result、否则 default
            context_id = None
            if execution_result and isinstance(execution_result, dict):
                context_id = execution_result.get("context_id")
            if not context_id:
                context_id = "default"
            # 更新内存
            await self.memory.add_memory(
                content=str(execution_result),
                memory_type="execution_result",
                context_id=context_id,
                metadata={"timestamp": datetime.utcnow().isoformat()}
            )
            # 更新上下文
            await self.context.add_message("agent", str(execution_result))
        except Exception as e:
            logger.error("State update failed", agent_id=self.agent_id, error=str(e))
            raise
    
    def _update_stats(self, execution_result: Dict[str, Any]) -> None:
        """
        更新统计信息
        
        Args:
            execution_result: 执行结果
        """
        self.stats["tasks_completed"] += 1
        
        # 计算执行时间（这里简化处理）
        execution_time = 1.0  # 实际应该从开始时间计算
        self.stats["total_execution_time"] += execution_time
        
        # 更新平均响应时间
        total_tasks = self.stats["tasks_completed"] + self.stats["tasks_failed"]
        if total_tasks > 0:
            self.stats["average_response_time"] = self.stats["total_execution_time"] / total_tasks
    
    async def _delegate_task(self, target_agent: str, task: str, **kwargs) -> Dict[str, Any]:
        """
        委托任务给其他Agent
        
        Args:
            target_agent: 目标Agent ID
            task: 任务描述
            **kwargs: 额外参数
            
        Returns:
            委托结果
        """
        # 这里应该通过消息系统发送给目标Agent
        # 暂时返回模拟结果
        return {
            "delegated_to": target_agent,
            "task": task,
            "status": "delegated",
            "result": f"Task delegated to {target_agent}"
        }
    
    async def _initialize_components(self) -> None:
        """初始化核心组件"""
        try:
            # 初始化上下文
            await self.context.initialize()
            
            # 初始化内存
            await self.memory.initialize()
            
            # 初始化推理引擎
            await self.reasoning_engine.initialize()
            
            # 初始化工具注册表
            await self.tool_registry.initialize()
            
            # 初始化追踪管理器
            await self.trace_manager.initialize()
            
            logger.info("Components initialized", agent_id=self.agent_id)
            
        except Exception as e:
            logger.error("Component initialization failed", agent_id=self.agent_id, error=str(e))
            raise
    
    async def _start_task_processor(self) -> None:
        """启动任务处理器"""
        # 创建任务处理任务
        asyncio.create_task(self._task_processor_loop())
        logger.info("Task processor started", agent_id=self.agent_id)
    
    async def _stop_task_processor(self) -> None:
        """停止任务处理器"""
        # 这里应该实现优雅停止逻辑
        logger.info("Task processor stopped", agent_id=self.agent_id)
    
    async def _task_processor_loop(self) -> None:
        """任务处理循环"""
        while self.status != AgentStatus.TERMINATED:
            try:
                # 从队列获取任务
                priority, task = await asyncio.wait_for(
                    self.task_queue.get(), 
                    timeout=1.0
                )
                
                # 执行任务
                await self.execute_task(task.task_data["task"], **task.task_data)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("Task processing error", agent_id=self.agent_id, error=str(e))
                await self._handle_error("task_processor", e)
    
    async def _start_performance_monitoring(self) -> None:
        """启动性能监控"""
        # 创建性能监控任务
        asyncio.create_task(self._performance_monitoring_loop())
        logger.info("Performance monitoring started", agent_id=self.agent_id)
    
    async def _stop_performance_monitoring(self) -> None:
        """停止性能监控"""
        logger.info("Performance monitoring stopped", agent_id=self.agent_id)
    
    async def _performance_monitoring_loop(self) -> None:
        """性能监控循环"""
        while self.status != AgentStatus.TERMINATED:
            try:
                # 更新性能指标
                self.performance_metrics["throughput"] = len(self.active_tasks)
                
                # 每30秒更新一次
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error("Performance monitoring error", agent_id=self.agent_id, error=str(e))
    
    async def _cleanup_resources(self) -> None:
        """清理资源"""
        try:
            # 清理活动任务
            self.active_tasks.clear()
            
            # 清理队列
            while not self.task_queue.empty():
                try:
                    self.task_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            logger.info("Resources cleaned up", agent_id=self.agent_id)
            
        except Exception as e:
            logger.error("Resource cleanup failed", agent_id=self.agent_id, error=str(e))
    
    async def _handle_error(self, operation: str, error: Exception, **kwargs) -> None:
        """
        处理错误
        
        Args:
            operation: 操作名称
            error: 错误对象
            **kwargs: 额外参数
        """
        error_info = {
            "operation": operation,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        self.error_history.append(error_info)
        self.stats["errors_count"] += 1
        
        logger.error(
            "Agent error",
            agent_id=self.agent_id,
            operation=operation,
            error=str(error),
            **kwargs
        )
        
        # 自动恢复逻辑
        if self.auto_recovery_enabled and self.status == AgentStatus.ERROR:
            await self._attempt_recovery()
    
    async def _attempt_recovery(self) -> None:
        """尝试自动恢复"""
        try:
            logger.info("Attempting auto recovery", agent_id=self.agent_id)
            
            # 重新初始化组件
            await self._initialize_components()
            
            self.status = AgentStatus.IDLE
            logger.info("Auto recovery successful", agent_id=self.agent_id)
            
        except Exception as e:
            logger.error("Auto recovery failed", agent_id=self.agent_id, error=str(e))
    
    @abstractmethod
    async def _on_start(self) -> None:
        """Agent启动时的自定义逻辑"""
        pass
    
    @abstractmethod
    async def _on_stop(self) -> None:
        """Agent停止时的自定义逻辑"""
        pass
    
    @abstractmethod
    async def _on_message_received(self, message: AgentMessage) -> None:
        """收到消息时的处理逻辑"""
        pass 