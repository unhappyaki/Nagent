"""
服务发现模块

实现服务发现、负载均衡、故障转移等功能
"""

import asyncio
import random
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import structlog

from .service_registry import ServiceRegistry, ServiceInfo, ServiceStatus

logger = structlog.get_logger(__name__)


class LoadBalancingStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    IP_HASH = "ip_hash"


class ServiceDiscovery:
    """
    服务发现
    
    实现服务发现、负载均衡、故障转移等功能
    """
    
    def __init__(self, service_registry: ServiceRegistry):
        """
        初始化服务发现
        
        Args:
            service_registry: 服务注册中心
        """
        self.service_registry = service_registry
        
        # 负载均衡状态
        self.round_robin_index = {}  # 服务名 -> 当前索引
        self.connection_counts = {}  # 服务ID -> 连接数
        
        # 缓存
        self.service_cache = {}  # 服务名 -> 服务列表
        self.cache_ttl = 30  # 秒
        
        # 故障转移配置
        self.max_retries = 3
        self.retry_delay = 1  # 秒
        
        # 健康检查回调
        self.health_check_callbacks: Dict[str, Callable] = {}
        
        logger.info("Service discovery initialized")
    
    async def discover_service(
        self,
        service_name: str,
        service_type: str = None,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
        client_ip: str = None,
        **kwargs
    ) -> Optional[ServiceInfo]:
        """
        发现服务
        
        Args:
            service_name: 服务名称
            service_type: 服务类型
            strategy: 负载均衡策略
            client_ip: 客户端IP（用于IP哈希策略）
            **kwargs: 其他参数
            
        Returns:
            选中的服务信息
        """
        try:
            logger.info(
                "Discovering service",
                service_name=service_name,
                service_type=service_type,
                strategy=strategy.value
            )
            
            # 获取服务列表
            services = await self._get_services(service_name, service_type)
            
            if not services:
                logger.warning(
                    "No services found",
                    service_name=service_name,
                    service_type=service_type
                )
                return None
            
            # 过滤健康服务
            healthy_services = [
                service for service in services
                if service.status == ServiceStatus.HEALTHY
            ]
            
            if not healthy_services:
                logger.warning(
                    "No healthy services found",
                    service_name=service_name,
                    service_type=service_type
                )
                return None
            
            # 应用负载均衡策略
            selected_service = await self._apply_load_balancing(
                healthy_services, strategy, client_ip
            )
            
            if selected_service:
                logger.info(
                    "Service discovered",
                    service_name=service_name,
                    selected_service_id=selected_service.service_id,
                    strategy=strategy.value
                )
            
            return selected_service
            
        except Exception as e:
            logger.error(
                "Error discovering service",
                service_name=service_name,
                error=str(e)
            )
            return None
    
    async def discover_service_with_failover(
        self,
        service_name: str,
        service_type: str = None,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
        client_ip: str = None,
        **kwargs
    ) -> Optional[ServiceInfo]:
        """
        带故障转移的服务发现
        
        Args:
            service_name: 服务名称
            service_type: 服务类型
            strategy: 负载均衡策略
            client_ip: 客户端IP
            **kwargs: 其他参数
            
        Returns:
            选中的服务信息
        """
        for attempt in range(self.max_retries):
            try:
                service = await self.discover_service(
                    service_name, service_type, strategy, client_ip, **kwargs
                )
                
                if service:
                    return service
                
                # 等待后重试
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    
            except Exception as e:
                logger.error(
                    "Error in service discovery with failover",
                    service_name=service_name,
                    attempt=attempt + 1,
                    error=str(e)
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        logger.error(
            "Service discovery failed after all retries",
            service_name=service_name,
            max_retries=self.max_retries
        )
        return None
    
    async def get_all_services(
        self,
        service_name: str = None,
        service_type: str = None,
        status: ServiceStatus = None
    ) -> List[ServiceInfo]:
        """
        获取所有服务
        
        Args:
            service_name: 服务名称
            service_type: 服务类型
            status: 服务状态
            
        Returns:
            服务列表
        """
        return await self.service_registry.find_services(
            service_name, service_type, status
        )
    
    async def register_health_check_callback(
        self,
        service_name: str,
        callback: Callable[[ServiceInfo], bool]
    ) -> None:
        """
        注册健康检查回调
        
        Args:
            service_name: 服务名称
            callback: 健康检查回调函数
        """
        self.health_check_callbacks[service_name] = callback
        logger.info(
            "Health check callback registered",
            service_name=service_name
        )
    
    async def update_connection_count(self, service_id: str, increment: bool = True) -> None:
        """
        更新连接数
        
        Args:
            service_id: 服务ID
            increment: 是否增加连接数
        """
        if increment:
            self.connection_counts[service_id] = self.connection_counts.get(service_id, 0) + 1
        else:
            current_count = self.connection_counts.get(service_id, 0)
            if current_count > 0:
                self.connection_counts[service_id] = current_count - 1
    
    async def get_service_stats(self, service_name: str) -> Dict[str, Any]:
        """
        获取服务统计信息
        
        Args:
            service_name: 服务名称
            
        Returns:
            统计信息
        """
        services = await self.get_all_services(service_name)
        
        total_services = len(services)
        healthy_services = len([s for s in services if s.status == ServiceStatus.HEALTHY])
        unhealthy_services = len([s for s in services if s.status == ServiceStatus.UNHEALTHY])
        offline_services = len([s for s in services if s.status == ServiceStatus.OFFLINE])
        
        total_connections = sum(
            self.connection_counts.get(s.service_id, 0) for s in services
        )
        
        avg_response_time = sum(s.response_time_avg for s in services) / total_services if total_services > 0 else 0
        
        return {
            "service_name": service_name,
            "total_services": total_services,
            "healthy_services": healthy_services,
            "unhealthy_services": unhealthy_services,
            "offline_services": offline_services,
            "total_connections": total_connections,
            "avg_response_time": avg_response_time,
            "health_rate": healthy_services / total_services if total_services > 0 else 0
        }
    
    async def _get_services(self, service_name: str, service_type: str = None) -> List[ServiceInfo]:
        """
        获取服务列表（带缓存）
        
        Args:
            service_name: 服务名称
            service_type: 服务类型
            
        Returns:
            服务列表
        """
        cache_key = f"{service_name}:{service_type or 'all'}"
        
        # 检查缓存
        if cache_key in self.service_cache:
            cache_entry = self.service_cache[cache_key]
            if cache_entry["expires_at"] > asyncio.get_event_loop().time():
                return cache_entry["services"]
        
        # 从注册中心获取服务
        services = await self.service_registry.find_services(service_name, service_type)
        
        # 更新缓存
        self.service_cache[cache_key] = {
            "services": services,
            "expires_at": asyncio.get_event_loop().time() + self.cache_ttl
        }
        
        return services
    
    async def _apply_load_balancing(
        self,
        services: List[ServiceInfo],
        strategy: LoadBalancingStrategy,
        client_ip: str = None
    ) -> Optional[ServiceInfo]:
        """
        应用负载均衡策略
        
        Args:
            services: 服务列表
            strategy: 负载均衡策略
            client_ip: 客户端IP
            
        Returns:
            选中的服务
        """
        if not services:
            return None
        
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return await self._round_robin_select(services)
        
        elif strategy == LoadBalancingStrategy.RANDOM:
            return random.choice(services)
        
        elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return await self._least_connections_select(services)
        
        elif strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return await self._weighted_round_robin_select(services)
        
        elif strategy == LoadBalancingStrategy.IP_HASH:
            return await self._ip_hash_select(services, client_ip)
        
        else:
            # 默认使用轮询
            return await self._round_robin_select(services)
    
    async def _round_robin_select(self, services: List[ServiceInfo]) -> ServiceInfo:
        """轮询选择"""
        service_names = [s.service_name for s in services]
        service_name = service_names[0]  # 假设所有服务名称相同
        
        if service_name not in self.round_robin_index:
            self.round_robin_index[service_name] = 0
        
        index = self.round_robin_index[service_name] % len(services)
        self.round_robin_index[service_name] += 1
        
        return services[index]
    
    async def _least_connections_select(self, services: List[ServiceInfo]) -> ServiceInfo:
        """最少连接数选择"""
        min_connections = float('inf')
        selected_service = services[0]
        
        for service in services:
            connections = self.connection_counts.get(service.service_id, 0)
            if connections < min_connections:
                min_connections = connections
                selected_service = service
        
        return selected_service
    
    async def _weighted_round_robin_select(self, services: List[ServiceInfo]) -> ServiceInfo:
        """加权轮询选择"""
        # 这里可以根据服务的权重进行选择
        # 暂时使用简单的轮询
        return await self._round_robin_select(services)
    
    async def _ip_hash_select(self, services: List[ServiceInfo], client_ip: str) -> ServiceInfo:
        """IP哈希选择"""
        if not client_ip:
            return random.choice(services)
        
        # 简单的IP哈希算法
        hash_value = hash(client_ip)
        index = hash_value % len(services)
        
        return services[index]
    
    async def _clear_cache(self) -> None:
        """清理缓存"""
        current_time = asyncio.get_event_loop().time()
        expired_keys = []
        
        for key, entry in self.service_cache.items():
            if entry["expires_at"] <= current_time:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.service_cache[key]
        
        if expired_keys:
            logger.debug(f"Cleared {len(expired_keys)} expired cache entries") 