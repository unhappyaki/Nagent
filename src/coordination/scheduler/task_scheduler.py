"""
任务调度器

实现任务调度、状态管理和调度策略
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class SchedulingStrategy(Enum):
    """调度策略枚举"""
    FIFO = "fifo"  # 先进先出
    PRIORITY = "priority"  # 优先级
    ROUND_ROBIN = "round_robin"  # 轮询
    LEAST_LOADED = "least_loaded"  # 最少负载
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"  # 加权轮询


class TaskInfo:
    """任务信息"""
    
    def __init__(
        self,
        task_id: str,
        task_name: str,
        task_type: str,
        priority: int = 0,
        timeout: int = 300,
        resources: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ):
        self.task_id = task_id
        self.task_name = task_name
        self.task_type = task_type
        self.priority = priority
        self.timeout = timeout
        self.resources = resources or {}
        self.metadata = metadata or {}
        
        # 时间戳
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        
        # 状态
        self.status = TaskStatus.PENDING
        self.assigned_worker: Optional[str] = None
        self.error_message: Optional[str] = None
        
        # 执行信息
        self.execution_time: Optional[float] = None
        self.retry_count = 0
        self.max_retries = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "task_type": self.task_type,
            "priority": self.priority,
            "timeout": self.timeout,
            "resources": self.resources,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "assigned_worker": self.assigned_worker,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }
    
    def start(self, worker_id: str) -> None:
        """开始执行任务"""
        self.status = TaskStatus.RUNNING
        self.assigned_worker = worker_id
        self.started_at = datetime.utcnow()
    
    def complete(self, execution_time: float = None) -> None:
        """完成任务"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if execution_time is not None:
            self.execution_time = execution_time
        elif self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()
    
    def fail(self, error_message: str) -> None:
        """任务失败"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()
    
    def cancel(self) -> None:
        """取消任务"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.utcnow()
    
    def timeout(self) -> None:
        """任务超时"""
        self.status = TaskStatus.TIMEOUT
        self.completed_at = datetime.utcnow()
        self.error_message = "Task timeout"
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()
    
    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return self.retry_count < self.max_retries and self.status in [
            TaskStatus.FAILED, TaskStatus.TIMEOUT
        ]
    
    def increment_retry(self) -> None:
        """增加重试次数"""
        self.retry_count += 1
        self.status = TaskStatus.PENDING
        self.started_at = None
        self.completed_at = None
        self.assigned_worker = None
        self.error_message = None
        self.execution_time = None


class TaskScheduler:
    """
    任务调度器
    
    负责任务调度、状态管理和调度策略
    """
    
    def __init__(self):
        """初始化任务调度器"""
        self.tasks: Dict[str, TaskInfo] = {}
        self.task_queues: Dict[str, List[str]] = {}  # 任务类型 -> 任务ID队列
        self.workers: Dict[str, Dict[str, Any]] = {}  # 工作节点信息
        
        # 调度配置
        self.default_strategy = SchedulingStrategy.FIFO
        self.max_concurrent_tasks = 100
        self.task_timeout_check_interval = 30  # 秒
        
        # 统计
        self.scheduler_stats = {
            "total_tasks": 0,
            "pending_tasks": 0,
            "running_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0,
            "timeout_tasks": 0,
            "total_execution_time": 0.0,
            "avg_execution_time": 0.0
        }
        
        logger.info("Task scheduler initialized")
    
    async def initialize(self) -> None:
        """初始化任务调度器"""
        try:
            logger.info("Initializing task scheduler")
            
            # 启动超时检查任务
            asyncio.create_task(self._timeout_check_loop())
            
            logger.info("Task scheduler initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize task scheduler", error=str(e))
            raise
    
    async def submit_task(
        self,
        task_name: str,
        task_type: str,
        priority: int = 0,
        timeout: int = 300,
        resources: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        提交任务
        
        Args:
            task_name: 任务名称
            task_type: 任务类型
            priority: 优先级
            timeout: 超时时间（秒）
            resources: 资源需求
            metadata: 元数据
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        try:
            logger.info(
                "Submitting task",
                task_id=task_id,
                task_name=task_name,
                task_type=task_type,
                priority=priority
            )
            
            # 创建任务信息
            task_info = TaskInfo(
                task_id=task_id,
                task_name=task_name,
                task_type=task_type,
                priority=priority,
                timeout=timeout,
                resources=resources,
                metadata=metadata
            )
            
            # 添加任务
            self.tasks[task_id] = task_info
            
            # 添加到队列
            if task_type not in self.task_queues:
                self.task_queues[task_type] = []
            self.task_queues[task_type].append(task_id)
            
            # 更新统计
            self.scheduler_stats["total_tasks"] += 1
            self.scheduler_stats["pending_tasks"] += 1
            
            logger.info(
                "Task submitted successfully",
                task_id=task_id,
                task_name=task_name
            )
            
            return task_id
            
        except Exception as e:
            logger.error(
                "Failed to submit task",
                task_id=task_id,
                task_name=task_name,
                error=str(e)
            )
            raise
    
    async def get_next_task(
        self,
        worker_id: str,
        task_type: str = None,
        strategy: SchedulingStrategy = None
    ) -> Optional[TaskInfo]:
        """
        获取下一个任务
        
        Args:
            worker_id: 工作节点ID
            task_type: 任务类型
            strategy: 调度策略
            
        Returns:
            任务信息
        """
        try:
            # 确定要调度的任务类型
            task_types = [task_type] if task_type else list(self.task_queues.keys())
            
            for t_type in task_types:
                if t_type not in self.task_queues or not self.task_queues[t_type]:
                    continue
                
                # 应用调度策略
                task_id = await self._apply_scheduling_strategy(
                    self.task_queues[t_type], strategy or self.default_strategy
                )
                
                if task_id and task_id in self.tasks:
                    task_info = self.tasks[task_id]
                    
                    # 分配任务给工作节点
                    task_info.start(worker_id)
                    
                    # 从队列中移除
                    self.task_queues[t_type].remove(task_id)
                    
                    # 更新统计
                    self.scheduler_stats["pending_tasks"] -= 1
                    self.scheduler_stats["running_tasks"] += 1
                    
                    logger.info(
                        "Task assigned to worker",
                        task_id=task_id,
                        worker_id=worker_id,
                        strategy=strategy.value if strategy else self.default_strategy.value
                    )
                    
                    return task_info
            
            return None
            
        except Exception as e:
            logger.error(
                "Error getting next task",
                worker_id=worker_id,
                error=str(e)
            )
            return None
    
    async def complete_task(self, task_id: str, execution_time: float = None) -> bool:
        """
        完成任务
        
        Args:
            task_id: 任务ID
            execution_time: 执行时间
            
        Returns:
            是否成功
        """
        if task_id not in self.tasks:
            return False
        
        try:
            task_info = self.tasks[task_id]
            task_info.complete(execution_time)
            
            # 更新统计
            self.scheduler_stats["running_tasks"] -= 1
            self.scheduler_stats["completed_tasks"] += 1
            
            if execution_time:
                self.scheduler_stats["total_execution_time"] += execution_time
                self._update_avg_execution_time()
            
            logger.info(
                "Task completed",
                task_id=task_id,
                execution_time=execution_time
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Error completing task",
                task_id=task_id,
                error=str(e)
            )
            return False
    
    async def fail_task(self, task_id: str, error_message: str) -> bool:
        """
        任务失败
        
        Args:
            task_id: 任务ID
            error_message: 错误信息
            
        Returns:
            是否成功
        """
        if task_id not in self.tasks:
            return False
        
        try:
            task_info = self.tasks[task_id]
            
            # 检查是否可以重试
            if task_info.can_retry():
                task_info.increment_retry()
                
                # 重新加入队列
                task_type = task_info.task_type
                if task_type not in self.task_queues:
                    self.task_queues[task_type] = []
                self.task_queues[task_type].append(task_id)
                
                # 更新统计
                self.scheduler_stats["running_tasks"] -= 1
                self.scheduler_stats["pending_tasks"] += 1
                
                logger.info(
                    "Task retry scheduled",
                    task_id=task_id,
                    retry_count=task_info.retry_count
                )
            else:
                task_info.fail(error_message)
                
                # 更新统计
                self.scheduler_stats["running_tasks"] -= 1
                self.scheduler_stats["failed_tasks"] += 1
                
                logger.error(
                    "Task failed permanently",
                    task_id=task_id,
                    error_message=error_message
                )
            
            return True
            
        except Exception as e:
            logger.error(
                "Error failing task",
                task_id=task_id,
                error=str(e)
            )
            return False
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功
        """
        if task_id not in self.tasks:
            return False
        
        try:
            task_info = self.tasks[task_id]
            
            if task_info.status == TaskStatus.PENDING:
                # 从队列中移除
                task_type = task_info.task_type
                if task_type in self.task_queues and task_id in self.task_queues[task_type]:
                    self.task_queues[task_type].remove(task_id)
                    self.scheduler_stats["pending_tasks"] -= 1
            elif task_info.status == TaskStatus.RUNNING:
                self.scheduler_stats["running_tasks"] -= 1
            
            task_info.cancel()
            self.scheduler_stats["cancelled_tasks"] += 1
            
            logger.info("Task cancelled", task_id=task_id)
            return True
            
        except Exception as e:
            logger.error(
                "Error cancelling task",
                task_id=task_id,
                error=str(e)
            )
            return False
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        if task_id not in self.tasks:
            return None
        
        task_info = self.tasks[task_id]
        return task_info.to_dict()
    
    async def get_scheduler_stats(self) -> Dict[str, Any]:
        """
        获取调度器统计信息
        
        Returns:
            统计信息
        """
        return {
            **self.scheduler_stats,
            "task_queues": {
                task_type: len(queue) for task_type, queue in self.task_queues.items()
            },
            "workers": len(self.workers),
            "success_rate": (
                self.scheduler_stats["completed_tasks"] / self.scheduler_stats["total_tasks"]
                if self.scheduler_stats["total_tasks"] > 0 else 0
            )
        }
    
    async def _apply_scheduling_strategy(
        self,
        task_queue: List[str],
        strategy: SchedulingStrategy
    ) -> Optional[str]:
        """
        应用调度策略
        
        Args:
            task_queue: 任务队列
            strategy: 调度策略
            
        Returns:
            选中的任务ID
        """
        if not task_queue:
            return None
        
        if strategy == SchedulingStrategy.FIFO:
            return task_queue[0]
        
        elif strategy == SchedulingStrategy.PRIORITY:
            # 按优先级排序
            sorted_tasks = sorted(
                task_queue,
                key=lambda task_id: self.tasks[task_id].priority,
                reverse=True
            )
            return sorted_tasks[0]
        
        elif strategy == SchedulingStrategy.ROUND_ROBIN:
            # 轮询
            task_id = task_queue.pop(0)
            task_queue.append(task_id)
            return task_id
        
        elif strategy == SchedulingStrategy.LEAST_LOADED:
            # 最少负载（这里简化处理，实际应该考虑工作节点负载）
            return task_queue[0]
        
        else:
            # 默认FIFO
            return task_queue[0]
    
    async def _timeout_check_loop(self) -> None:
        """超时检查循环"""
        while True:
            try:
                await self._check_task_timeouts()
                await asyncio.sleep(self.task_timeout_check_interval)
            except Exception as e:
                logger.error("Error in timeout check loop", error=str(e))
                await asyncio.sleep(5)
    
    async def _check_task_timeouts(self) -> None:
        """检查任务超时"""
        current_time = datetime.utcnow()
        timeout_tasks = []
        
        for task_id, task_info in self.tasks.items():
            if task_info.status == TaskStatus.RUNNING and task_info.started_at:
                elapsed_time = (current_time - task_info.started_at).total_seconds()
                if elapsed_time > task_info.timeout:
                    timeout_tasks.append(task_id)
        
        # 处理超时任务
        for task_id in timeout_tasks:
            await self.fail_task(task_id, "Task timeout")
            self.tasks[task_id].timeout()
            self.scheduler_stats["timeout_tasks"] += 1
    
    def _update_avg_execution_time(self) -> None:
        """更新平均执行时间"""
        completed_tasks = self.scheduler_stats["completed_tasks"]
        total_time = self.scheduler_stats["total_execution_time"]
        
        if completed_tasks > 0:
            self.scheduler_stats["avg_execution_time"] = total_time / completed_tasks 