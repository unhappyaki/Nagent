"""
资源管理器

实现容器资源分配、监控和限制
"""

import asyncio
import psutil
from datetime import datetime
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)


class ResourceLimits:
    """资源限制配置"""
    
    def __init__(
        self,
        cpu_limit: float = 1.0,
        memory_limit: int = 1024 * 1024 * 1024,  # 1GB
        gpu_limit: int = 0,
        network_limit: int = 1024 * 1024 * 1024,  # 1GB
        disk_limit: int = 10 * 1024 * 1024 * 1024  # 10GB
    ):
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
        self.gpu_limit = gpu_limit
        self.network_limit = network_limit
        self.disk_limit = disk_limit


class ResourceUsage:
    """资源使用情况"""
    
    def __init__(self):
        self.cpu_percent = 0.0
        self.memory_used = 0
        self.memory_percent = 0.0
        self.gpu_used = 0
        self.network_bytes_sent = 0
        self.network_bytes_recv = 0
        self.disk_used = 0
        self.timestamp = datetime.utcnow()


class ResourceManager:
    """
    资源管理器
    
    负责系统资源监控、分配和限制
    """
    
    def __init__(self):
        """初始化资源管理器"""
        self.system_resources = {}
        self.container_resources: Dict[str, ResourceUsage] = {}
        self.resource_limits: Dict[str, ResourceLimits] = {}
        
        # 监控间隔
        self.monitor_interval = 5  # 秒
        
        # 资源统计
        self.resource_stats = {
            "total_containers": 0,
            "active_containers": 0,
            "total_cpu_usage": 0.0,
            "total_memory_usage": 0,
            "total_gpu_usage": 0,
            "system_cpu_percent": 0.0,
            "system_memory_percent": 0.0
        }
        
        logger.info("Resource manager initialized")
    
    async def initialize(self) -> None:
        """初始化资源管理器"""
        try:
            logger.info("Initializing resource manager")
            
            # 获取系统资源信息
            await self._update_system_resources()
            
            # 启动资源监控
            asyncio.create_task(self._resource_monitor_loop())
            
            logger.info("Resource manager initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize resource manager", error=str(e))
            raise
    
    async def allocate_resources(self, container_id: str, limits: ResourceLimits) -> bool:
        """
        分配资源
        
        Args:
            container_id: 容器ID
            limits: 资源限制
            
        Returns:
            是否分配成功
        """
        try:
            logger.info(
                "Allocating resources",
                container_id=container_id,
                cpu_limit=limits.cpu_limit,
                memory_limit=limits.memory_limit
            )
            
            # 检查资源可用性
            if not await self._check_resource_availability(limits):
                logger.warning(
                    "Insufficient resources for allocation",
                    container_id=container_id
                )
                return False
            
            # 分配资源
            self.resource_limits[container_id] = limits
            self.container_resources[container_id] = ResourceUsage()
            
            # 更新统计
            self.resource_stats["total_containers"] += 1
            self.resource_stats["active_containers"] += 1
            
            logger.info(
                "Resources allocated successfully",
                container_id=container_id
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to allocate resources",
                container_id=container_id,
                error=str(e)
            )
            return False
    
    async def release_resources(self, container_id: str) -> None:
        """
        释放资源
        
        Args:
            container_id: 容器ID
        """
        try:
            logger.info("Releasing resources", container_id=container_id)
            
            # 移除资源记录
            if container_id in self.resource_limits:
                del self.resource_limits[container_id]
            
            if container_id in self.container_resources:
                del self.container_resources[container_id]
            
            # 更新统计
            self.resource_stats["active_containers"] -= 1
            
            logger.info("Resources released successfully", container_id=container_id)
            
        except Exception as e:
            logger.error(
                "Failed to release resources",
                container_id=container_id,
                error=str(e)
            )
    
    async def get_container_resources(self, container_id: str) -> Optional[Dict[str, Any]]:
        """
        获取容器资源使用情况
        
        Args:
            container_id: 容器ID
            
        Returns:
            资源使用信息
        """
        if container_id not in self.container_resources:
            return None
        
        usage = self.container_resources[container_id]
        limits = self.resource_limits.get(container_id)
        
        return {
            "container_id": container_id,
            "usage": {
                "cpu_percent": usage.cpu_percent,
                "memory_used": usage.memory_used,
                "memory_percent": usage.memory_percent,
                "gpu_used": usage.gpu_used,
                "network_bytes_sent": usage.network_bytes_sent,
                "network_bytes_recv": usage.network_bytes_recv,
                "disk_used": usage.disk_used,
                "timestamp": usage.timestamp.isoformat()
            },
            "limits": {
                "cpu_limit": limits.cpu_limit if limits else None,
                "memory_limit": limits.memory_limit if limits else None,
                "gpu_limit": limits.gpu_limit if limits else None,
                "network_limit": limits.network_limit if limits else None,
                "disk_limit": limits.disk_limit if limits else None
            } if limits else None
        }
    
    async def get_system_resources(self) -> Dict[str, Any]:
        """
        获取系统资源信息
        
        Returns:
            系统资源信息
        """
        return {
            "cpu": {
                "count": psutil.cpu_count(),
                "percent": psutil.cpu_percent(interval=1),
                "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
                "used": psutil.virtual_memory().used
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            },
            "network": {
                "bytes_sent": psutil.net_io_counters().bytes_sent,
                "bytes_recv": psutil.net_io_counters().bytes_recv,
                "packets_sent": psutil.net_io_counters().packets_sent,
                "packets_recv": psutil.net_io_counters().packets_recv
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_resource_stats(self) -> Dict[str, Any]:
        """
        获取资源统计信息
        
        Returns:
            统计信息
        """
        return {
            **self.resource_stats,
            "system_resources": await self.get_system_resources(),
            "container_count": len(self.container_resources),
            "resource_utilization": await self._calculate_resource_utilization()
        }
    
    async def check_resource_limits(self, container_id: str) -> Dict[str, bool]:
        """
        检查资源限制
        
        Args:
            container_id: 容器ID
            
        Returns:
            各资源是否超限
        """
        if container_id not in self.container_resources or container_id not in self.resource_limits:
            return {}
        
        usage = self.container_resources[container_id]
        limits = self.resource_limits[container_id]
        
        return {
            "cpu_exceeded": usage.cpu_percent > limits.cpu_limit * 100,
            "memory_exceeded": usage.memory_used > limits.memory_limit,
            "gpu_exceeded": usage.gpu_used > limits.gpu_limit,
            "network_exceeded": (
                usage.network_bytes_sent + usage.network_bytes_recv > limits.network_limit
            ),
            "disk_exceeded": usage.disk_used > limits.disk_limit
        }
    
    async def _update_system_resources(self) -> None:
        """更新系统资源信息"""
        try:
            self.system_resources = await self.get_system_resources()
            
            # 更新统计
            self.resource_stats["system_cpu_percent"] = self.system_resources["cpu"]["percent"]
            self.resource_stats["system_memory_percent"] = self.system_resources["memory"]["percent"]
            
        except Exception as e:
            logger.error("Failed to update system resources", error=str(e))
    
    async def _update_container_resources(self) -> None:
        """更新容器资源使用情况"""
        try:
            total_cpu = 0.0
            total_memory = 0
            total_gpu = 0
            
            for container_id, usage in self.container_resources.items():
                # 这里应该从实际的容器进程获取资源使用情况
                # 暂时使用模拟数据
                usage.cpu_percent = 10.0  # 模拟CPU使用率
                usage.memory_used = 100 * 1024 * 1024  # 模拟内存使用
                usage.memory_percent = 5.0  # 模拟内存使用率
                usage.timestamp = datetime.utcnow()
                
                total_cpu += usage.cpu_percent
                total_memory += usage.memory_used
                total_gpu += usage.gpu_used
            
            # 更新统计
            self.resource_stats["total_cpu_usage"] = total_cpu
            self.resource_stats["total_memory_usage"] = total_memory
            self.resource_stats["total_gpu_usage"] = total_gpu
            
        except Exception as e:
            logger.error("Failed to update container resources", error=str(e))
    
    async def _resource_monitor_loop(self) -> None:
        """资源监控循环"""
        while True:
            try:
                await self._update_system_resources()
                await self._update_container_resources()
                await asyncio.sleep(self.monitor_interval)
            except Exception as e:
                logger.error("Error in resource monitor loop", error=str(e))
                await asyncio.sleep(5)
    
    async def _check_resource_availability(self, limits: ResourceLimits) -> bool:
        """
        检查资源可用性
        
        Args:
            limits: 资源限制
            
        Returns:
            资源是否足够
        """
        try:
            # 获取当前系统资源
            system_resources = await self.get_system_resources()
            
            # 计算已分配资源
            allocated_cpu = sum(
                limit.cpu_limit for limit in self.resource_limits.values()
            )
            allocated_memory = sum(
                limit.memory_limit for limit in self.resource_limits.values()
            )
            
            # 检查CPU
            available_cpu = psutil.cpu_count() - allocated_cpu
            if limits.cpu_limit > available_cpu:
                return False
            
            # 检查内存
            available_memory = system_resources["memory"]["available"] - allocated_memory
            if limits.memory_limit > available_memory:
                return False
            
            return True
            
        except Exception as e:
            logger.error("Error checking resource availability", error=str(e))
            return False
    
    async def _calculate_resource_utilization(self) -> Dict[str, float]:
        """
        计算资源利用率
        
        Returns:
            各资源利用率
        """
        try:
            system_resources = await self.get_system_resources()
            
            # 计算已分配资源
            allocated_cpu = sum(
                limit.cpu_limit for limit in self.resource_limits.values()
            )
            allocated_memory = sum(
                limit.memory_limit for limit in self.resource_limits.values()
            )
            
            total_cpu = psutil.cpu_count()
            total_memory = system_resources["memory"]["total"]
            
            return {
                "cpu_utilization": (allocated_cpu / total_cpu) * 100 if total_cpu > 0 else 0,
                "memory_utilization": (allocated_memory / total_memory) * 100 if total_memory > 0 else 0,
                "disk_utilization": system_resources["disk"]["percent"]
            }
            
        except Exception as e:
            logger.error("Error calculating resource utilization", error=str(e))
            return {} 