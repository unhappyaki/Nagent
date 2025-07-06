"""
调度策略模块

实现不同的调度策略和优化算法
"""

from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class PolicyType(Enum):
    """策略类型"""
    FIFO = "fifo"
    PRIORITY = "priority"
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    FAIR_SHARE = "fair_share"
    DEADLINE_AWARE = "deadline_aware"
    COST_AWARE = "cost_aware"


class SchedulingPolicy:
    """
    调度策略
    
    实现不同的调度策略和优化算法
    """
    
    def __init__(self, policy_type: PolicyType = PolicyType.FIFO):
        """
        初始化调度策略
        
        Args:
            policy_type: 策略类型
        """
        self.policy_type = policy_type
        self.policy_config = {}
        
        # 策略特定的状态
        self.round_robin_index = 0
        self.worker_loads = {}
        self.task_priorities = {}
        
        logger.info(f"Scheduling policy initialized: {policy_type.value}")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        配置策略参数
        
        Args:
            config: 配置参数
        """
        self.policy_config.update(config)
        logger.info(f"Policy configured: {config}")
    
    def select_task(
        self,
        available_tasks: List[Dict[str, Any]],
        available_workers: List[Dict[str, Any]],
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        选择任务
        
        Args:
            available_tasks: 可用任务列表
            available_workers: 可用工作节点列表
            **kwargs: 其他参数
            
        Returns:
            选中的任务
        """
        if not available_tasks:
            return None
        
        if self.policy_type == PolicyType.FIFO:
            return self._fifo_select(available_tasks)
        
        elif self.policy_type == PolicyType.PRIORITY:
            return self._priority_select(available_tasks)
        
        elif self.policy_type == PolicyType.ROUND_ROBIN:
            return self._round_robin_select(available_tasks)
        
        elif self.policy_type == PolicyType.LEAST_LOADED:
            return self._least_loaded_select(available_tasks, available_workers)
        
        elif self.policy_type == PolicyType.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_select(available_tasks)
        
        elif self.policy_type == PolicyType.FAIR_SHARE:
            return self._fair_share_select(available_tasks, available_workers)
        
        elif self.policy_type == PolicyType.DEADLINE_AWARE:
            return self._deadline_aware_select(available_tasks)
        
        elif self.policy_type == PolicyType.COST_AWARE:
            return self._cost_aware_select(available_tasks, available_workers)
        
        else:
            # 默认FIFO
            return self._fifo_select(available_tasks)
    
    def select_worker(
        self,
        task: Dict[str, Any],
        available_workers: List[Dict[str, Any]],
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        选择工作节点
        
        Args:
            task: 任务信息
            available_workers: 可用工作节点列表
            **kwargs: 其他参数
            
        Returns:
            选中的工作节点
        """
        if not available_workers:
            return None
        
        if self.policy_type == PolicyType.LEAST_LOADED:
            return self._select_least_loaded_worker(available_workers)
        
        elif self.policy_type == PolicyType.ROUND_ROBIN:
            return self._select_round_robin_worker(available_workers)
        
        elif self.policy_type == PolicyType.FAIR_SHARE:
            return self._select_fair_share_worker(available_workers)
        
        elif self.policy_type == PolicyType.COST_AWARE:
            return self._select_cost_aware_worker(task, available_workers)
        
        else:
            # 默认选择第一个可用节点
            return available_workers[0]
    
    def _fifo_select(self, available_tasks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """FIFO选择"""
        if not available_tasks:
            return None
        
        # 按创建时间排序
        sorted_tasks = sorted(
            available_tasks,
            key=lambda task: task.get("created_at", 0)
        )
        
        return sorted_tasks[0]
    
    def _priority_select(self, available_tasks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """优先级选择"""
        if not available_tasks:
            return None
        
        # 按优先级排序
        sorted_tasks = sorted(
            available_tasks,
            key=lambda task: task.get("priority", 0),
            reverse=True
        )
        
        return sorted_tasks[0]
    
    def _round_robin_select(self, available_tasks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """轮询选择"""
        if not available_tasks:
            return None
        
        # 轮询选择
        selected_task = available_tasks[self.round_robin_index % len(available_tasks)]
        self.round_robin_index += 1
        
        return selected_task
    
    def _least_loaded_select(
        self,
        available_tasks: List[Dict[str, Any]],
        available_workers: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """最少负载选择"""
        if not available_tasks or not available_workers:
            return None
        
        # 计算每个工作节点的负载
        worker_loads = {}
        for worker in available_workers:
            worker_id = worker.get("worker_id")
            load = worker.get("current_load", 0)
            worker_loads[worker_id] = load
        
        # 选择负载最少的工作节点上的任务
        min_load = float('inf')
        selected_task = None
        
        for task in available_tasks:
            assigned_worker = task.get("assigned_worker")
            if assigned_worker in worker_loads:
                load = worker_loads[assigned_worker]
                if load < min_load:
                    min_load = load
                    selected_task = task
        
        return selected_task or available_tasks[0]
    
    def _weighted_round_robin_select(self, available_tasks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """加权轮询选择"""
        if not available_tasks:
            return None
        
        # 计算权重
        total_weight = sum(task.get("weight", 1) for task in available_tasks)
        
        # 加权轮询
        current_weight = 0
        for task in available_tasks:
            weight = task.get("weight", 1)
            current_weight += weight
            if current_weight >= (self.round_robin_index % total_weight + 1):
                self.round_robin_index += 1
                return task
        
        # 默认选择第一个
        return available_tasks[0]
    
    def _fair_share_select(
        self,
        available_tasks: List[Dict[str, Any]],
        available_workers: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """公平分享选择"""
        if not available_tasks or not available_workers:
            return None
        
        # 计算每个用户/组的资源使用情况
        user_shares = {}
        for task in available_tasks:
            user_id = task.get("user_id", "default")
            if user_id not in user_shares:
                user_shares[user_id] = 0
            user_shares[user_id] += task.get("resource_usage", 1)
        
        # 选择资源使用最少的用户的任务
        min_share = float('inf')
        selected_task = None
        
        for task in available_tasks:
            user_id = task.get("user_id", "default")
            share = user_shares[user_id]
            if share < min_share:
                min_share = share
                selected_task = task
        
        return selected_task or available_tasks[0]
    
    def _deadline_aware_select(self, available_tasks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """截止时间感知选择"""
        if not available_tasks:
            return None
        
        current_time = self.policy_config.get("current_time", 0)
        
        # 按截止时间排序
        sorted_tasks = sorted(
            available_tasks,
            key=lambda task: task.get("deadline", float('inf'))
        )
        
        # 选择最紧急的任务
        for task in sorted_tasks:
            deadline = task.get("deadline", float('inf'))
            if deadline > current_time:
                return task
        
        # 如果没有未超期的任务，选择最早截止的
        return sorted_tasks[0] if sorted_tasks else None
    
    def _cost_aware_select(
        self,
        available_tasks: List[Dict[str, Any]],
        available_workers: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """成本感知选择"""
        if not available_tasks or not available_workers:
            return None
        
        # 计算每个工作节点的成本
        worker_costs = {}
        for worker in available_workers:
            worker_id = worker.get("worker_id")
            cost_per_hour = worker.get("cost_per_hour", 1.0)
            worker_costs[worker_id] = cost_per_hour
        
        # 选择成本最低的工作节点上的任务
        min_cost = float('inf')
        selected_task = None
        
        for task in available_tasks:
            assigned_worker = task.get("assigned_worker")
            if assigned_worker in worker_costs:
                cost = worker_costs[assigned_worker]
                if cost < min_cost:
                    min_cost = cost
                    selected_task = task
        
        return selected_task or available_tasks[0]
    
    def _select_least_loaded_worker(self, available_workers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """选择负载最少的工作节点"""
        if not available_workers:
            return None
        
        min_load = float('inf')
        selected_worker = None
        
        for worker in available_workers:
            load = worker.get("current_load", 0)
            if load < min_load:
                min_load = load
                selected_worker = worker
        
        return selected_worker
    
    def _select_round_robin_worker(self, available_workers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """轮询选择工作节点"""
        if not available_workers:
            return None
        
        selected_worker = available_workers[self.round_robin_index % len(available_workers)]
        self.round_robin_index += 1
        
        return selected_worker
    
    def _select_fair_share_worker(self, available_workers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """公平分享选择工作节点"""
        if not available_workers:
            return None
        
        # 计算每个工作节点的使用情况
        worker_usage = {}
        for worker in available_workers:
            worker_id = worker.get("worker_id")
            usage = worker.get("total_usage", 0)
            worker_usage[worker_id] = usage
        
        # 选择使用最少的工作节点
        min_usage = float('inf')
        selected_worker = None
        
        for worker in available_workers:
            worker_id = worker.get("worker_id")
            usage = worker_usage.get(worker_id, 0)
            if usage < min_usage:
                min_usage = usage
                selected_worker = worker
        
        return selected_worker
    
    def _select_cost_aware_worker(
        self,
        task: Dict[str, Any],
        available_workers: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """成本感知选择工作节点"""
        if not available_workers:
            return None
        
        # 计算每个工作节点的成本效益
        min_cost_benefit = float('inf')
        selected_worker = None
        
        for worker in available_workers:
            cost_per_hour = worker.get("cost_per_hour", 1.0)
            performance = worker.get("performance", 1.0)
            cost_benefit = cost_per_hour / performance
            
            if cost_benefit < min_cost_benefit:
                min_cost_benefit = cost_benefit
                selected_worker = worker
        
        return selected_worker
    
    def update_worker_load(self, worker_id: str, load: float) -> None:
        """
        更新工作节点负载
        
        Args:
            worker_id: 工作节点ID
            load: 负载值
        """
        self.worker_loads[worker_id] = load
    
    def update_task_priority(self, task_id: str, priority: int) -> None:
        """
        更新任务优先级
        
        Args:
            task_id: 任务ID
            priority: 优先级
        """
        self.task_priorities[task_id] = priority
    
    def get_policy_stats(self) -> Dict[str, Any]:
        """
        获取策略统计信息
        
        Returns:
            统计信息
        """
        return {
            "policy_type": self.policy_type.value,
            "policy_config": self.policy_config,
            "round_robin_index": self.round_robin_index,
            "worker_loads": self.worker_loads,
            "task_priorities": self.task_priorities
        } 