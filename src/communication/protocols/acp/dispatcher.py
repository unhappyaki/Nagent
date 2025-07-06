"""
ACP协议任务分发器
独立的任务分发模块，负责将任务分发给合适的Agent
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import structlog

from .message_schema import (
    ACPMessage, ACPMessageBuilder, 
    ACPMessageType, MessagePriority
)

logger = structlog.get_logger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class DispatchStrategy(Enum):
    """分发策略"""
    ROUND_ROBIN = "round_robin"          # 轮询
    LEAST_LOADED = "least_loaded"        # 最少负载
    CAPABILITY_MATCH = "capability_match" # 能力匹配
    PRIORITY_BASED = "priority_based"    # 基于优先级
    RANDOM = "random"                    # 随机


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    task_type: str
    task_data: Dict[str, Any]
    priority: int
    timeout: int  # 超时时间(秒)
    required_capabilities: List[str]
    assigned_agent: Optional[str] = None
    status: str = TaskStatus.PENDING.value
    created_at: str = None
    assigned_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class AgentInfo:
    """Agent信息"""
    agent_id: str
    capabilities: List[str]
    current_load: int
    max_load: int
    status: str
    last_heartbeat: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TaskDispatcher:
    """
    ACP任务分发器
    
    负责：
    - 任务接收和队列管理
    - Agent注册和状态管理
    - 任务分发和调度
    - 任务执行监控
    - 超时和重试处理
    """
    
    def __init__(
        self,
        strategy: DispatchStrategy = DispatchStrategy.CAPABILITY_MATCH,
        acp_client=None,
        trace_writer=None
    ):
        self.strategy = strategy
        self.acp_client = acp_client
        self.trace_writer = trace_writer
        
        # 消息构建器
        self.message_builder = ACPMessageBuilder("task_dispatcher", trace_writer)
        
        # 任务管理
        self.pending_tasks: List[TaskInfo] = []
        self.active_tasks: Dict[str, TaskInfo] = {}
        self.completed_tasks: Dict[str, TaskInfo] = {}
        
        # Agent管理
        self.registered_agents: Dict[str, AgentInfo] = {}
        
        # 分发统计
        self.dispatch_stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "timeout_tasks": 0,
            "retry_tasks": 0,
            "agent_count": 0,
            "average_task_time": 0.0
        }
        
        # 轮询索引
        self._round_robin_index = 0
        
        # 启动后台任务
        self._running = False
        self._monitor_task = None
        
        logger.info("TaskDispatcher initialized", strategy=strategy.value)
    
    async def start(self):
        """启动分发器"""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_tasks())
        logger.info("TaskDispatcher started")
    
    async def stop(self):
        """停止分发器"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("TaskDispatcher stopped")
    
    async def register_agent(
        self,
        agent_id: str,
        capabilities: List[str],
        max_load: int = 10,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        注册Agent
        
        Args:
            agent_id: Agent ID
            capabilities: Agent能力列表
            max_load: 最大负载
            metadata: 元数据
            
        Returns:
            bool: 注册是否成功
        """
        try:
            agent_info = AgentInfo(
                agent_id=agent_id,
                capabilities=capabilities,
                current_load=0,
                max_load=max_load,
                status="online",
                last_heartbeat=datetime.utcnow().isoformat(),
                metadata=metadata or {}
            )
            
            self.registered_agents[agent_id] = agent_info
            self.dispatch_stats["agent_count"] = len(self.registered_agents)
            
            # 记录追踪
            if self.trace_writer:
                await self._record_agent_event("register", agent_id, {
                    "capabilities": capabilities,
                    "max_load": max_load,
                    "metadata": metadata
                })
            
            logger.info("Agent registered", agent_id=agent_id, capabilities=capabilities)
            return True
            
        except Exception as e:
            logger.error("Failed to register agent", agent_id=agent_id, error=str(e))
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """
        注销Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 注销是否成功
        """
        try:
            if agent_id not in self.registered_agents:
                return False
            
            # 取消该Agent的所有任务
            await self._cancel_agent_tasks(agent_id)
            
            # 移除Agent
            del self.registered_agents[agent_id]
            self.dispatch_stats["agent_count"] = len(self.registered_agents)
            
            # 记录追踪
            if self.trace_writer:
                await self._record_agent_event("unregister", agent_id, {})
            
            logger.info("Agent unregistered", agent_id=agent_id)
            return True
            
        except Exception as e:
            logger.error("Failed to unregister agent", agent_id=agent_id, error=str(e))
            return False
    
    async def update_agent_heartbeat(self, agent_id: str, status: str = "online") -> bool:
        """
        更新Agent心跳
        
        Args:
            agent_id: Agent ID
            status: Agent状态
            
        Returns:
            bool: 更新是否成功
        """
        if agent_id not in self.registered_agents:
            return False
        
        try:
            self.registered_agents[agent_id].last_heartbeat = datetime.utcnow().isoformat()
            self.registered_agents[agent_id].status = status
            return True
        except Exception as e:
            logger.error("Failed to update agent heartbeat", agent_id=agent_id, error=str(e))
            return False
    
    async def submit_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        required_capabilities: List[str] = None,
        priority: int = MessagePriority.NORMAL.value,
        timeout: int = 300,
        max_retries: int = 3
    ) -> str:
        """提交任务"""
        task_id = str(uuid.uuid4())
        
        try:
            task_info = TaskInfo(
                task_id=task_id,
                task_type=task_type,
                task_data=task_data,
                priority=priority,
                timeout=timeout,
                required_capabilities=required_capabilities or [],
                max_retries=max_retries
            )
            
            # 添加到待处理队列
            self.pending_tasks.append(task_info)
            
            # 按优先级排序
            self.pending_tasks.sort(key=lambda t: t.priority, reverse=True)
            
            self.dispatch_stats["total_tasks"] += 1
            
            # 尝试立即分发
            await self._dispatch_pending_tasks()
            
            logger.info("Task submitted", task_id=task_id, task_type=task_type)
            return task_id
            
        except Exception as e:
            logger.error("Failed to submit task", task_id=task_id, error=str(e))
            raise
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Dict[str, Any]]: 任务状态信息
        """
        # 检查活跃任务
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            return {
                "task_id": task.task_id,
                "status": task.status,
                "assigned_agent": task.assigned_agent,
                "created_at": task.created_at,
                "assigned_at": task.assigned_at,
                "started_at": task.started_at,
                "retry_count": task.retry_count
            }
        
        # 检查已完成任务
        if task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
            return {
                "task_id": task.task_id,
                "status": task.status,
                "assigned_agent": task.assigned_agent,
                "created_at": task.created_at,
                "completed_at": task.completed_at,
                "result": task.result,
                "error": task.error,
                "retry_count": task.retry_count
            }
        
        # 检查待处理任务
        for task in self.pending_tasks:
            if task.task_id == task_id:
                return {
                    "task_id": task.task_id,
                    "status": task.status,
                    "created_at": task.created_at,
                    "position_in_queue": self.pending_tasks.index(task)
                }
        
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 取消是否成功
        """
        try:
            # 从待处理队列中移除
            for i, task in enumerate(self.pending_tasks):
                if task.task_id == task_id:
                    task.status = TaskStatus.CANCELLED.value
                    self.pending_tasks.pop(i)
                    self.completed_tasks[task_id] = task
                    
                    if self.trace_writer:
                        await self._record_task_event("cancel", task_id, {"reason": "user_cancelled"})
                    
                    logger.info("Task cancelled from pending queue", task_id=task_id)
                    return True
            
            # 从活跃任务中取消
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                task.status = TaskStatus.CANCELLED.value
                task.completed_at = datetime.utcnow().isoformat()
                
                # 通知Agent取消任务
                if task.assigned_agent and self.acp_client:
                    cancel_message = self.message_builder.create_error_message(
                        task.assigned_agent,
                        "TASK_CANCELLED",
                        "Task has been cancelled",
                        {"task_id": task_id}
                    )
                    await self.acp_client.send_message(cancel_message)
                
                # 移动到已完成任务
                del self.active_tasks[task_id]
                self.completed_tasks[task_id] = task
                
                # 减少Agent负载
                if task.assigned_agent in self.registered_agents:
                    self.registered_agents[task.assigned_agent].current_load -= 1
                
                if self.trace_writer:
                    await self._record_task_event("cancel", task_id, {"reason": "user_cancelled"})
                
                logger.info("Task cancelled from active tasks", task_id=task_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to cancel task", task_id=task_id, error=str(e))
            return False
    
    async def handle_task_result(
        self,
        task_id: str,
        result: Dict[str, Any],
        success: bool = True,
        error: Optional[str] = None
    ) -> bool:
        """
        处理任务结果
        
        Args:
            task_id: 任务ID
            result: 任务结果
            success: 是否成功
            error: 错误信息
            
        Returns:
            bool: 处理是否成功
        """
        if task_id not in self.active_tasks:
            logger.warning("Task not found in active tasks", task_id=task_id)
            return False
        
        try:
            task = self.active_tasks[task_id]
            task.completed_at = datetime.utcnow().isoformat()
            task.result = result
            task.error = error
            
            if success:
                task.status = TaskStatus.COMPLETED.value
                self.dispatch_stats["successful_tasks"] += 1
            else:
                task.status = TaskStatus.FAILED.value
                self.dispatch_stats["failed_tasks"] += 1
                
                # 检查是否需要重试
                if task.retry_count < task.max_retries:
                    return await self._retry_task(task)
            
            # 移动到已完成任务
            del self.active_tasks[task_id]
            self.completed_tasks[task_id] = task
            
            # 减少Agent负载
            if task.assigned_agent in self.registered_agents:
                self.registered_agents[task.assigned_agent].current_load -= 1
            
            # 更新平均任务时间
            if task.started_at and task.completed_at:
                start_time = datetime.fromisoformat(task.started_at)
                end_time = datetime.fromisoformat(task.completed_at)
                task_duration = (end_time - start_time).total_seconds()
                
                # 简单移动平均
                current_avg = self.dispatch_stats["average_task_time"]
                completed_count = self.dispatch_stats["successful_tasks"] + self.dispatch_stats["failed_tasks"]
                self.dispatch_stats["average_task_time"] = (current_avg * (completed_count - 1) + task_duration) / completed_count
            
            # 记录追踪
            if self.trace_writer:
                await self._record_task_event("complete", task_id, {
                    "success": success,
                    "error": error,
                    "duration": task_duration if 'task_duration' in locals() else None
                })
            
            logger.info("Task completed", task_id=task_id, success=success)
            return True
            
        except Exception as e:
            logger.error("Failed to handle task result", task_id=task_id, error=str(e))
            return False
    
    async def _dispatch_pending_tasks(self):
        """分发待处理任务"""
        if not self.pending_tasks:
            return
        
        available_agents = self._get_available_agents()
        if not available_agents:
            return
        
        dispatched_tasks = []
        
        for task in self.pending_tasks:
            # 选择合适的Agent
            selected_agent = await self._select_agent_for_task(task, available_agents)
            if not selected_agent:
                continue
            
            # 分发任务
            if await self._assign_task_to_agent(task, selected_agent):
                dispatched_tasks.append(task)
                available_agents = self._get_available_agents()  # 更新可用Agent列表
                
                if not available_agents:
                    break
        
        # 移除已分发的任务
        for task in dispatched_tasks:
            self.pending_tasks.remove(task)
    
    async def _select_agent_for_task(self, task: TaskInfo, available_agents: List[str]) -> Optional[str]:
        """为任务选择Agent"""
        # 过滤具备所需能力的Agent
        capable_agents = []
        for agent_id in available_agents:
            agent = self.registered_agents[agent_id]
            if self._has_required_capabilities(agent.capabilities, task.required_capabilities):
                capable_agents.append(agent_id)
        
        if not capable_agents:
            return None
        
        # 根据策略选择Agent
        if self.strategy == DispatchStrategy.ROUND_ROBIN:
            return self._select_round_robin(capable_agents)
        elif self.strategy == DispatchStrategy.LEAST_LOADED:
            return self._select_least_loaded(capable_agents)
        elif self.strategy == DispatchStrategy.CAPABILITY_MATCH:
            return self._select_best_capability_match(task, capable_agents)
        elif self.strategy == DispatchStrategy.RANDOM:
            import random
            return random.choice(capable_agents)
        else:
            return capable_agents[0]  # 默认选择第一个
    
    async def _assign_task_to_agent(self, task: TaskInfo, agent_id: str) -> bool:
        """将任务分配给Agent"""
        try:
            # 更新任务状态
            task.assigned_agent = agent_id
            task.assigned_at = datetime.utcnow().isoformat()
            task.status = TaskStatus.ASSIGNED.value
            
            # 增加Agent负载
            self.registered_agents[agent_id].current_load += 1
            
            # 添加到活跃任务
            self.active_tasks[task.task_id] = task
            
            # 发送任务消息给Agent
            if self.acp_client:
                task_message = self.message_builder.create_task_message(
                    agent_id,
                    task.task_type,
                    task.task_data,
                    priority=MessagePriority(task.priority)
                )
                await self.acp_client.send_message(task_message)
            
            # 记录追踪
            if self.trace_writer:
                await self._record_task_event("assign", task.task_id, {
                    "assigned_agent": agent_id,
                    "assigned_at": task.assigned_at
                })
            
            logger.info("Task assigned to agent", task_id=task.task_id, agent_id=agent_id)
            return True
            
        except Exception as e:
            logger.error("Failed to assign task to agent", task_id=task.task_id, agent_id=agent_id, error=str(e))
            return False
    
    async def _monitor_tasks(self):
        """监控任务执行"""
        while self._running:
            try:
                await self._check_task_timeouts()
                await self._check_agent_health()
                await self._dispatch_pending_tasks()
                await asyncio.sleep(1)  # 每秒检查一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in task monitor", error=str(e))
    
    async def _check_task_timeouts(self):
        """检查任务超时"""
        current_time = datetime.utcnow()
        timeout_tasks = []
        
        for task_id, task in self.active_tasks.items():
            if task.assigned_at:
                assigned_time = datetime.fromisoformat(task.assigned_at)
                if (current_time - assigned_time).total_seconds() > task.timeout:
                    timeout_tasks.append(task)
        
        for task in timeout_tasks:
            await self._handle_task_timeout(task)
    
    async def _handle_task_timeout(self, task: TaskInfo):
        """处理任务超时"""
        task.status = TaskStatus.TIMEOUT.value
        task.completed_at = datetime.utcnow().isoformat()
        task.error = f"Task timeout after {task.timeout} seconds"
        
        self.dispatch_stats["timeout_tasks"] += 1
        
        # 检查是否需要重试
        if task.retry_count < task.max_retries:
            await self._retry_task(task)
        else:
            # 移动到已完成任务
            del self.active_tasks[task.task_id]
            self.completed_tasks[task.task_id] = task
            
            # 减少Agent负载
            if task.assigned_agent in self.registered_agents:
                self.registered_agents[task.assigned_agent].current_load -= 1
        
        # 记录追踪
        if self.trace_writer:
            await self._record_task_event("timeout", task.task_id, {
                "timeout_seconds": task.timeout,
                "retry_count": task.retry_count
            })
        
        logger.warning("Task timeout", task_id=task.task_id, timeout=task.timeout)
    
    async def _retry_task(self, task: TaskInfo) -> bool:
        """重试任务"""
        try:
            task.retry_count += 1
            task.status = TaskStatus.PENDING.value
            task.assigned_agent = None
            task.assigned_at = None
            task.started_at = None
            task.error = None
            
            # 减少原Agent负载
            if task.assigned_agent in self.registered_agents:
                self.registered_agents[task.assigned_agent].current_load -= 1
            
            # 移回待处理队列
            del self.active_tasks[task.task_id]
            self.pending_tasks.append(task)
            
            # 按优先级重新排序
            self.pending_tasks.sort(key=lambda t: t.priority, reverse=True)
            
            self.dispatch_stats["retry_tasks"] += 1
            
            # 记录追踪
            if self.trace_writer:
                await self._record_task_event("retry", task.task_id, {
                    "retry_count": task.retry_count,
                    "max_retries": task.max_retries
                })
            
            logger.info("Task queued for retry", task_id=task.task_id, retry_count=task.retry_count)
            return True
            
        except Exception as e:
            logger.error("Failed to retry task", task_id=task.task_id, error=str(e))
            return False
    
    async def _check_agent_health(self):
        """检查Agent健康状态"""
        current_time = datetime.utcnow()
        offline_agents = []
        
        for agent_id, agent in self.registered_agents.items():
            if agent.last_heartbeat:
                last_heartbeat = datetime.fromisoformat(agent.last_heartbeat)
                if (current_time - last_heartbeat).total_seconds() > 60:  # 60秒无心跳认为离线
                    offline_agents.append(agent_id)
        
        for agent_id in offline_agents:
            await self._handle_agent_offline(agent_id)
    
    async def _handle_agent_offline(self, agent_id: str):
        """处理Agent离线"""
        self.registered_agents[agent_id].status = "offline"
        
        # 取消该Agent的所有任务
        await self._cancel_agent_tasks(agent_id, reason="agent_offline")
        
        # 记录追踪
        if self.trace_writer:
            await self._record_agent_event("offline", agent_id, {
                "reason": "heartbeat_timeout"
            })
        
        logger.warning("Agent marked as offline", agent_id=agent_id)
    
    async def _cancel_agent_tasks(self, agent_id: str, reason: str = "agent_unregistered"):
        """取消Agent的所有任务"""
        cancelled_tasks = []
        
        for task_id, task in self.active_tasks.items():
            if task.assigned_agent == agent_id:
                cancelled_tasks.append(task)
        
        for task in cancelled_tasks:
            if task.retry_count < task.max_retries:
                await self._retry_task(task)
            else:
                task.status = TaskStatus.FAILED.value
                task.completed_at = datetime.utcnow().isoformat()
                task.error = f"Agent offline: {reason}"
                
                del self.active_tasks[task.task_id]
                self.completed_tasks[task.task_id] = task
                
                self.dispatch_stats["failed_tasks"] += 1
    
    def _get_available_agents(self) -> List[str]:
        """获取可用的Agent列表"""
        available = []
        for agent_id, agent in self.registered_agents.items():
            if (agent.status == "online" and 
                agent.current_load < agent.max_load):
                available.append(agent_id)
        return available
    
    def _has_required_capabilities(self, agent_capabilities: List[str], required_capabilities: List[str]) -> bool:
        """检查Agent是否具备所需能力"""
        if not required_capabilities:
            return True
        return all(cap in agent_capabilities for cap in required_capabilities)
    
    def _select_round_robin(self, agents: List[str]) -> str:
        """轮询选择Agent"""
        if not agents:
            return None
        
        selected = agents[self._round_robin_index % len(agents)]
        self._round_robin_index = (self._round_robin_index + 1) % len(agents)
        return selected
    
    def _select_least_loaded(self, agents: List[str]) -> str:
        """选择负载最少的Agent"""
        if not agents:
            return None
        
        min_load = float('inf')
        selected_agent = None
        
        for agent_id in agents:
            agent = self.registered_agents[agent_id]
            if agent.current_load < min_load:
                min_load = agent.current_load
                selected_agent = agent_id
        
        return selected_agent
    
    def _select_best_capability_match(self, task: TaskInfo, agents: List[str]) -> str:
        """选择能力最匹配的Agent"""
        if not agents:
            return None
        
        if not task.required_capabilities:
            return self._select_least_loaded(agents)
        
        # 计算能力匹配度
        best_score = -1
        selected_agent = None
        
        for agent_id in agents:
            agent = self.registered_agents[agent_id]
            
            # 计算匹配分数：匹配的能力数量 / 总能力数量
            matched_capabilities = sum(1 for cap in task.required_capabilities if cap in agent.capabilities)
            score = matched_capabilities / len(agent.capabilities) if agent.capabilities else 0
            
            # 考虑负载因子
            load_factor = 1 - (agent.current_load / agent.max_load)
            final_score = score * 0.7 + load_factor * 0.3
            
            if final_score > best_score:
                best_score = final_score
                selected_agent = agent_id
        
        return selected_agent
    
    async def _record_task_event(self, event: str, task_id: str, data: Dict[str, Any]):
        """记录任务事件"""
        try:
            trace_data = {
                "trace_id": task_id,
                "component": "task_dispatcher",
                "operation": f"task_{event}",
                "timestamp": datetime.utcnow().isoformat(),
                "task_id": task_id,
                "event": event,
                "data": data
            }
            await self.trace_writer.write_trace(trace_data)
        except Exception as e:
            logger.error("Failed to record task event", error=str(e))
    
    async def _record_agent_event(self, event: str, agent_id: str, data: Dict[str, Any]):
        """记录Agent事件"""
        try:
            trace_data = {
                "trace_id": str(uuid.uuid4()),
                "component": "task_dispatcher",
                "operation": f"agent_{event}",
                "timestamp": datetime.utcnow().isoformat(),
                "agent_id": agent_id,
                "event": event,
                "data": data
            }
            await self.trace_writer.write_trace(trace_data)
        except Exception as e:
            logger.error("Failed to record agent event", error=str(e))
    
    def get_dispatcher_stats(self) -> Dict[str, Any]:
        """获取分发器统计信息"""
        return {
            **self.dispatch_stats,
            "pending_tasks": len(self.pending_tasks),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "registered_agents": len(self.registered_agents),
            "online_agents": len([a for a in self.registered_agents.values() if a.status == "online"]),
            "total_agent_load": sum(a.current_load for a in self.registered_agents.values()),
            "strategy": self.strategy.value
        } 