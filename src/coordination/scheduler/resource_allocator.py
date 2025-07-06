"""
资源分配器

实现资源分配、优化和监控
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class ResourceAllocator:
    """
    资源分配器
    
    实现资源分配、优化和监控
    """
    
    def __init__(self):
        """初始化资源分配器"""
        self.available_resources = {
            "cpu": 0,
            "memory": 0,
            "gpu": 0,
            "disk": 0,
            "network": 0
        }
        
        self.allocated_resources = {
            "cpu": 0,
            "memory": 0,
            "gpu": 0,
            "disk": 0,
            "network": 0
        }
        
        self.resource_requests: Dict[str, Dict[str, Any]] = {}
        self.allocation_history: List[Dict[str, Any]] = []
        
        # 配置
        self.max_allocation_history = 1000
        self.optimization_interval = 60  # 秒
        
        logger.info("Resource allocator initialized")
    
    async def initialize(self, total_resources: Dict[str, Any]) -> None:
        """
        初始化资源分配器
        
        Args:
            total_resources: 总资源
        """
        try:
            logger.info("Initializing resource allocator")
            
            # 设置总资源
            self.available_resources.update(total_resources)
            
            # 启动优化任务
            asyncio.create_task(self._optimization_loop())
            
            logger.info("Resource allocator initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize resource allocator", error=str(e))
            raise
    
    async def request_resources(
        self,
        request_id: str,
        resources: Dict[str, Any],
        priority: int = 0,
        timeout: int = 300
    ) -> bool:
        """
        请求资源
        
        Args:
            request_id: 请求ID
            resources: 资源需求
            priority: 优先级
            timeout: 超时时间
            
        Returns:
            是否分配成功
        """
        try:
            logger.info(
                "Requesting resources",
                request_id=request_id,
                resources=resources,
                priority=priority
            )
            
            # 检查资源可用性
            if not await self._check_resource_availability(resources):
                logger.warning(
                    "Insufficient resources for request",
                    request_id=request_id,
                    resources=resources
                )
                return False
            
            # 分配资源
            success = await self._allocate_resources(request_id, resources)
            
            if success:
                # 记录请求
                self.resource_requests[request_id] = {
                    "resources": resources,
                    "priority": priority,
                    "timeout": timeout,
                    "allocated_at": datetime.utcnow(),
                    "status": "allocated"
                }
                
                logger.info(
                    "Resources allocated successfully",
                    request_id=request_id
                )
            else:
                logger.error(
                    "Failed to allocate resources",
                    request_id=request_id
                )
            
            return success
            
        except Exception as e:
            logger.error(
                "Error requesting resources",
                request_id=request_id,
                error=str(e)
            )
            return False
    
    async def release_resources(self, request_id: str) -> bool:
        """
        释放资源
        
        Args:
            request_id: 请求ID
            
        Returns:
            是否释放成功
        """
        try:
            logger.info("Releasing resources", request_id=request_id)
            
            if request_id not in self.resource_requests:
                logger.warning("Resource request not found", request_id=request_id)
                return False
            
            request_info = self.resource_requests[request_id]
            resources = request_info["resources"]
            
            # 释放资源
            for resource_type, amount in resources.items():
                if resource_type in self.allocated_resources:
                    self.allocated_resources[resource_type] -= amount
                    self.available_resources[resource_type] += amount
            
            # 更新请求状态
            request_info["status"] = "released"
            request_info["released_at"] = datetime.utcnow()
            
            # 记录历史
            await self._record_allocation_history(request_id, "released", resources)
            
            logger.info("Resources released successfully", request_id=request_id)
            return True
            
        except Exception as e:
            logger.error(
                "Error releasing resources",
                request_id=request_id,
                error=str(e)
            )
            return False
    
    async def get_resource_status(self) -> Dict[str, Any]:
        """
        获取资源状态
        
        Returns:
            资源状态信息
        """
        total_resources = {}
        utilization = {}
        
        for resource_type in self.available_resources:
            total = self.available_resources[resource_type] + self.allocated_resources[resource_type]
            allocated = self.allocated_resources[resource_type]
            
            total_resources[resource_type] = total
            utilization[resource_type] = (allocated / total * 100) if total > 0 else 0
        
        return {
            "available_resources": self.available_resources,
            "allocated_resources": self.allocated_resources,
            "total_resources": total_resources,
            "utilization": utilization,
            "active_requests": len([r for r in self.resource_requests.values() if r["status"] == "allocated"])
        }
    
    async def optimize_allocations(self) -> Dict[str, Any]:
        """
        优化资源分配
        
        Returns:
            优化结果
        """
        try:
            logger.info("Starting resource allocation optimization")
            
            optimization_results = {
                "optimizations_applied": 0,
                "resources_freed": {},
                "requests_reorganized": 0
            }
            
            # 按优先级重新组织请求
            sorted_requests = sorted(
                self.resource_requests.items(),
                key=lambda x: x[1]["priority"],
                reverse=True
            )
            
            # 释放所有资源
            for request_id, request_info in sorted_requests:
                if request_info["status"] == "allocated":
                    resources = request_info["resources"]
                    for resource_type, amount in resources.items():
                        if resource_type in self.allocated_resources:
                            self.allocated_resources[resource_type] -= amount
                            self.available_resources[resource_type] += amount
            
            # 重新分配资源
            for request_id, request_info in sorted_requests:
                if request_info["status"] == "allocated":
                    resources = request_info["resources"]
                    
                    if await self._check_resource_availability(resources):
                        # 重新分配
                        for resource_type, amount in resources.items():
                            if resource_type in self.available_resources:
                                self.available_resources[resource_type] -= amount
                                self.allocated_resources[resource_type] += amount
                        optimization_results["requests_reorganized"] += 1
                    else:
                        # 无法重新分配，标记为等待
                        request_info["status"] = "waiting"
                        optimization_results["optimizations_applied"] += 1
            
            logger.info(
                "Resource allocation optimization completed",
                optimizations_applied=optimization_results["optimizations_applied"],
                requests_reorganized=optimization_results["requests_reorganized"]
            )
            
            return optimization_results
            
        except Exception as e:
            logger.error("Error optimizing allocations", error=str(e))
            return {"error": str(e)}
    
    async def _check_resource_availability(self, resources: Dict[str, Any]) -> bool:
        """
        检查资源可用性
        
        Args:
            resources: 资源需求
            
        Returns:
            资源是否足够
        """
        for resource_type, amount in resources.items():
            if resource_type not in self.available_resources:
                return False
            
            if self.available_resources[resource_type] < amount:
                return False
        
        return True
    
    async def _allocate_resources(self, request_id: str, resources: Dict[str, Any]) -> bool:
        """
        分配资源
        
        Args:
            request_id: 请求ID
            resources: 资源需求
            
        Returns:
            是否分配成功
        """
        try:
            # 检查资源可用性
            if not await self._check_resource_availability(resources):
                return False
            
            # 分配资源
            for resource_type, amount in resources.items():
                self.available_resources[resource_type] -= amount
                self.allocated_resources[resource_type] += amount
            
            # 记录历史
            await self._record_allocation_history(request_id, "allocated", resources)
            
            return True
            
        except Exception as e:
            logger.error(
                "Error allocating resources",
                request_id=request_id,
                error=str(e)
            )
            return False
    
    async def _record_allocation_history(
        self,
        request_id: str,
        action: str,
        resources: Dict[str, Any]
    ) -> None:
        """
        记录分配历史
        
        Args:
            request_id: 请求ID
            action: 操作类型
            resources: 资源信息
        """
        history_entry = {
            "request_id": request_id,
            "action": action,
            "resources": resources,
            "timestamp": datetime.utcnow().isoformat(),
            "available_resources": self.available_resources.copy(),
            "allocated_resources": self.allocated_resources.copy()
        }
        
        self.allocation_history.append(history_entry)
        
        # 限制历史记录数量
        if len(self.allocation_history) > self.max_allocation_history:
            self.allocation_history = self.allocation_history[-self.max_allocation_history:]
    
    async def _optimization_loop(self) -> None:
        """优化循环"""
        while True:
            try:
                await self.optimize_allocations()
                await asyncio.sleep(self.optimization_interval)
            except Exception as e:
                logger.error("Error in optimization loop", error=str(e))
                await asyncio.sleep(5) 