"""
服务注册中心

实现服务注册、注销、查询、状态管理等功能
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class ServiceStatus(Enum):
    """服务状态枚举"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    OFFLINE = "offline"


class ServiceInfo:
    """服务信息"""
    
    def __init__(
        self,
        service_id: str,
        service_name: str,
        service_type: str,
        host: str,
        port: int,
        version: str = "1.0.0",
        metadata: Dict[str, Any] = None,
        health_check_url: str = None
    ):
        self.service_id = service_id
        self.service_name = service_name
        self.service_type = service_type
        self.host = host
        self.port = port
        self.version = version
        self.metadata = metadata or {}
        self.health_check_url = health_check_url
        
        # 时间戳
        self.registered_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.last_health_check = None
        
        # 状态
        self.status = ServiceStatus.UNKNOWN
        self.heartbeat_interval = 30  # 秒
        self.timeout = 90  # 秒
        
        # 统计
        self.request_count = 0
        self.error_count = 0
        self.response_time_avg = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "service_type": self.service_type,
            "host": self.host,
            "port": self.port,
            "version": self.version,
            "metadata": self.metadata,
            "health_check_url": self.health_check_url,
            "registered_at": self.registered_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "status": self.status.value,
            "heartbeat_interval": self.heartbeat_interval,
            "timeout": self.timeout,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "response_time_avg": self.response_time_avg
        }
    
    def update_heartbeat(self) -> None:
        """更新心跳时间"""
        self.last_heartbeat = datetime.utcnow()
    
    def is_alive(self) -> bool:
        """检查服务是否存活"""
        if self.status == ServiceStatus.OFFLINE:
            return False
        
        timeout_threshold = datetime.utcnow() - timedelta(seconds=self.timeout)
        return self.last_heartbeat > timeout_threshold
    
    def update_health_check(self, status: ServiceStatus) -> None:
        """更新健康检查状态"""
        self.status = status
        self.last_health_check = datetime.utcnow()
    
    def update_stats(self, response_time: float, is_error: bool = False) -> None:
        """更新统计信息"""
        self.request_count += 1
        if is_error:
            self.error_count += 1
        
        # 更新平均响应时间
        if self.response_time_avg == 0:
            self.response_time_avg = response_time
        else:
            self.response_time_avg = (self.response_time_avg + response_time) / 2


class ServiceRegistry:
    """
    服务注册中心
    
    负责服务的注册、注销、查询和状态管理
    """
    
    def __init__(self):
        """初始化服务注册中心"""
        self.services: Dict[str, ServiceInfo] = {}
        self.service_groups: Dict[str, Set[str]] = {}  # 服务组 -> 服务ID集合
        
        # 配置
        self.cleanup_interval = 60  # 秒
        self.health_check_interval = 30  # 秒
        
        # 统计
        self.registry_stats = {
            "total_services": 0,
            "healthy_services": 0,
            "unhealthy_services": 0,
            "offline_services": 0,
            "total_registrations": 0,
            "total_deregistrations": 0
        }
        
        logger.info("Service registry initialized")
    
    async def initialize(self) -> None:
        """初始化服务注册中心"""
        try:
            logger.info("Initializing service registry")
            
            # 启动清理任务
            asyncio.create_task(self._cleanup_loop())
            
            # 启动健康检查任务
            asyncio.create_task(self._health_check_loop())
            
            logger.info("Service registry initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize service registry", error=str(e))
            raise
    
    async def register_service(
        self,
        service_name: str,
        service_type: str,
        host: str,
        port: int,
        version: str = "1.0.0",
        metadata: Dict[str, Any] = None,
        health_check_url: str = None,
        service_group: str = None
    ) -> str:
        """
        注册服务
        
        Args:
            service_name: 服务名称
            service_type: 服务类型
            host: 主机地址
            port: 端口
            version: 版本
            metadata: 元数据
            health_check_url: 健康检查URL
            service_group: 服务组
            
        Returns:
            服务ID
        """
        service_id = str(uuid.uuid4())
        
        try:
            logger.info(
                "Registering service",
                service_id=service_id,
                service_name=service_name,
                service_type=service_type,
                host=host,
                port=port
            )
            
            # 创建服务信息
            service_info = ServiceInfo(
                service_id=service_id,
                service_name=service_name,
                service_type=service_type,
                host=host,
                port=port,
                version=version,
                metadata=metadata,
                health_check_url=health_check_url
            )
            
            # 注册服务
            self.services[service_id] = service_info
            
            # 添加到服务组
            if service_group:
                if service_group not in self.service_groups:
                    self.service_groups[service_group] = set()
                self.service_groups[service_group].add(service_id)
            
            # 更新统计
            self.registry_stats["total_services"] += 1
            self.registry_stats["total_registrations"] += 1
            
            logger.info(
                "Service registered successfully",
                service_id=service_id,
                service_name=service_name
            )
            
            return service_id
            
        except Exception as e:
            logger.error(
                "Failed to register service",
                service_id=service_id,
                service_name=service_name,
                error=str(e)
            )
            raise
    
    async def deregister_service(self, service_id: str) -> bool:
        """
        注销服务
        
        Args:
            service_id: 服务ID
            
        Returns:
            是否注销成功
        """
        if service_id not in self.services:
            return False
        
        try:
            logger.info("Deregistering service", service_id=service_id)
            
            service_info = self.services[service_id]
            
            # 从服务组中移除
            for group, services in self.service_groups.items():
                if service_id in services:
                    services.remove(service_id)
                    if not services:  # 如果组为空，删除组
                        del self.service_groups[group]
                    break
            
            # 移除服务
            del self.services[service_id]
            
            # 更新统计
            self.registry_stats["total_services"] -= 1
            self.registry_stats["total_deregistrations"] += 1
            
            logger.info("Service deregistered successfully", service_id=service_id)
            return True
            
        except Exception as e:
            logger.error(
                "Failed to deregister service",
                service_id=service_id,
                error=str(e)
            )
            return False
    
    async def get_service(self, service_id: str) -> Optional[ServiceInfo]:
        """
        获取服务信息
        
        Args:
            service_id: 服务ID
            
        Returns:
            服务信息
        """
        return self.services.get(service_id)
    
    async def find_services(
        self,
        service_name: str = None,
        service_type: str = None,
        status: ServiceStatus = None,
        service_group: str = None
    ) -> List[ServiceInfo]:
        """
        查找服务
        
        Args:
            service_name: 服务名称
            service_type: 服务类型
            status: 服务状态
            service_group: 服务组
            
        Returns:
            服务列表
        """
        services = []
        
        # 确定要搜索的服务ID集合
        if service_group and service_group in self.service_groups:
            service_ids = self.service_groups[service_group]
        else:
            service_ids = set(self.services.keys())
        
        for service_id in service_ids:
            if service_id not in self.services:
                continue
            
            service_info = self.services[service_id]
            
            # 应用过滤条件
            if service_name and service_info.service_name != service_name:
                continue
            
            if service_type and service_info.service_type != service_type:
                continue
            
            if status and service_info.status != status:
                continue
            
            services.append(service_info)
        
        return services
    
    async def update_heartbeat(self, service_id: str) -> bool:
        """
        更新服务心跳
        
        Args:
            service_id: 服务ID
            
        Returns:
            是否更新成功
        """
        if service_id not in self.services:
            return False
        
        try:
            service_info = self.services[service_id]
            service_info.update_heartbeat()
            
            # 如果服务之前是离线状态，现在恢复为未知状态
            if service_info.status == ServiceStatus.OFFLINE:
                service_info.status = ServiceStatus.UNKNOWN
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to update heartbeat",
                service_id=service_id,
                error=str(e)
            )
            return False
    
    async def update_service_health(self, service_id: str, status: ServiceStatus) -> bool:
        """
        更新服务健康状态
        
        Args:
            service_id: 服务ID
            status: 健康状态
            
        Returns:
            是否更新成功
        """
        if service_id not in self.services:
            return False
        
        try:
            service_info = self.services[service_id]
            service_info.update_health_check(status)
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to update service health",
                service_id=service_id,
                error=str(e)
            )
            return False
    
    async def get_service_stats(self, service_id: str) -> Optional[Dict[str, Any]]:
        """
        获取服务统计信息
        
        Args:
            service_id: 服务ID
            
        Returns:
            统计信息
        """
        if service_id not in self.services:
            return None
        
        service_info = self.services[service_id]
        
        return {
            "service_id": service_id,
            "service_name": service_info.service_name,
            "request_count": service_info.request_count,
            "error_count": service_info.error_count,
            "response_time_avg": service_info.response_time_avg,
            "error_rate": (
                service_info.error_count / service_info.request_count
                if service_info.request_count > 0 else 0
            ),
            "uptime": (datetime.utcnow() - service_info.registered_at).total_seconds(),
            "last_heartbeat": (datetime.utcnow() - service_info.last_heartbeat).total_seconds()
        }
    
    async def get_registry_stats(self) -> Dict[str, Any]:
        """
        获取注册中心统计信息
        
        Returns:
            统计信息
        """
        # 计算当前状态统计
        healthy_count = 0
        unhealthy_count = 0
        offline_count = 0
        
        for service_info in self.services.values():
            if service_info.status == ServiceStatus.HEALTHY:
                healthy_count += 1
            elif service_info.status == ServiceStatus.UNHEALTHY:
                unhealthy_count += 1
            elif service_info.status == ServiceStatus.OFFLINE:
                offline_count += 1
        
        return {
            **self.registry_stats,
            "healthy_services": healthy_count,
            "unhealthy_services": unhealthy_count,
            "offline_services": offline_count,
            "service_groups": len(self.service_groups),
            "total_services_by_type": self._count_services_by_type(),
            "total_services_by_group": self._count_services_by_group()
        }
    
    async def _cleanup_loop(self) -> None:
        """清理循环"""
        while True:
            try:
                await self._cleanup_offline_services()
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error("Error in cleanup loop", error=str(e))
                await asyncio.sleep(5)
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while True:
            try:
                await self._check_services_health()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error("Error in health check loop", error=str(e))
                await asyncio.sleep(5)
    
    async def _cleanup_offline_services(self) -> None:
        """清理离线服务"""
        offline_services = []
        
        for service_id, service_info in self.services.items():
            if not service_info.is_alive():
                service_info.status = ServiceStatus.OFFLINE
                offline_services.append(service_id)
        
        # 记录离线服务
        if offline_services:
            logger.warning(
                "Found offline services",
                offline_count=len(offline_services),
                service_ids=offline_services
            )
    
    async def _check_services_health(self) -> None:
        """检查服务健康状态"""
        # 这里应该实现实际的健康检查逻辑
        # 暂时只更新心跳状态
        for service_info in self.services.values():
            if not service_info.is_alive():
                service_info.status = ServiceStatus.OFFLINE
    
    def _count_services_by_type(self) -> Dict[str, int]:
        """按类型统计服务数量"""
        type_count = {}
        for service_info in self.services.values():
            service_type = service_info.service_type
            type_count[service_type] = type_count.get(service_type, 0) + 1
        return type_count
    
    def _count_services_by_group(self) -> Dict[str, int]:
        """按组统计服务数量"""
        group_count = {}
        for group, services in self.service_groups.items():
            group_count[group] = len(services)
        return group_count 