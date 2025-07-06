"""
健康检查模块

实现服务健康检查和监控
"""

import asyncio
import aiohttp
import socket
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import structlog

from .service_registry import ServiceRegistry, ServiceInfo, ServiceStatus

logger = structlog.get_logger(__name__)


class HealthCheckType(Enum):
    """健康检查类型"""
    HTTP = "http"
    TCP = "tcp"
    CUSTOM = "custom"


class HealthCheckResult:
    """健康检查结果"""
    
    def __init__(self, service_id: str, is_healthy: bool, response_time: float = 0.0, error: str = None):
        self.service_id = service_id
        self.is_healthy = is_healthy
        self.response_time = response_time
        self.error = error
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "service_id": self.service_id,
            "is_healthy": self.is_healthy,
            "response_time": self.response_time,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


class HealthChecker:
    """
    健康检查器
    
    实现服务健康检查和监控
    """
    
    def __init__(self, service_registry: ServiceRegistry):
        """
        初始化健康检查器
        
        Args:
            service_registry: 服务注册中心
        """
        self.service_registry = service_registry
        
        # 健康检查配置
        self.check_interval = 30  # 秒
        self.timeout = 10  # 秒
        self.max_retries = 3
        
        # 自定义健康检查回调
        self.custom_health_checks: Dict[str, Callable] = {}
        
        # 健康检查历史
        self.health_history: Dict[str, List[HealthCheckResult]] = {}
        self.max_history_size = 100
        
        # 统计
        self.health_stats = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "avg_response_time": 0.0
        }
        
        logger.info("Health checker initialized")
    
    async def initialize(self) -> None:
        """初始化健康检查器"""
        try:
            logger.info("Initializing health checker")
            
            # 启动健康检查循环
            asyncio.create_task(self._health_check_loop())
            
            logger.info("Health checker initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize health checker", error=str(e))
            raise
    
    async def register_custom_health_check(
        self,
        service_name: str,
        check_function: Callable[[ServiceInfo], bool]
    ) -> None:
        """
        注册自定义健康检查
        
        Args:
            service_name: 服务名称
            check_function: 健康检查函数
        """
        self.custom_health_checks[service_name] = check_function
        logger.info(
            "Custom health check registered",
            service_name=service_name
        )
    
    async def check_service_health(self, service_info: ServiceInfo) -> HealthCheckResult:
        """
        检查服务健康状态
        
        Args:
            service_info: 服务信息
            
        Returns:
            健康检查结果
        """
        start_time = datetime.utcnow()
        
        try:
            logger.debug(
                "Checking service health",
                service_id=service_info.service_id,
                service_name=service_info.service_name
            )
            
            # 确定健康检查类型
            check_type = await self._determine_check_type(service_info)
            
            # 执行健康检查
            if check_type == HealthCheckType.HTTP:
                result = await self._http_health_check(service_info)
            elif check_type == HealthCheckType.TCP:
                result = await self._tcp_health_check(service_info)
            elif check_type == HealthCheckType.CUSTOM:
                result = await self._custom_health_check(service_info)
            else:
                result = HealthCheckResult(
                    service_info.service_id,
                    False,
                    error="Unknown health check type"
                )
            
            # 计算响应时间
            response_time = (datetime.utcnow() - start_time).total_seconds()
            result.response_time = response_time
            
            # 更新统计
            self._update_stats(result)
            
            # 保存历史
            await self._save_health_history(result)
            
            # 更新服务状态
            status = ServiceStatus.HEALTHY if result.is_healthy else ServiceStatus.UNHEALTHY
            await self.service_registry.update_service_health(service_info.service_id, status)
            
            logger.debug(
                "Health check completed",
                service_id=service_info.service_id,
                is_healthy=result.is_healthy,
                response_time=response_time
            )
            
            return result
            
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds()
            result = HealthCheckResult(
                service_info.service_id,
                False,
                response_time,
                str(e)
            )
            
            # 更新统计
            self._update_stats(result)
            
            # 保存历史
            await self._save_health_history(result)
            
            # 更新服务状态
            await self.service_registry.update_service_health(
                service_info.service_id, ServiceStatus.UNHEALTHY
            )
            
            logger.error(
                "Health check failed",
                service_id=service_info.service_id,
                error=str(e)
            )
            
            return result
    
    async def get_health_history(self, service_id: str, limit: int = 50) -> List[HealthCheckResult]:
        """
        获取健康检查历史
        
        Args:
            service_id: 服务ID
            limit: 返回结果数量限制
            
        Returns:
            健康检查历史
        """
        history = self.health_history.get(service_id, [])
        return history[-limit:] if limit > 0 else history
    
    async def get_health_stats(self) -> Dict[str, Any]:
        """
        获取健康检查统计信息
        
        Returns:
            统计信息
        """
        return {
            **self.health_stats,
            "success_rate": (
                self.health_stats["successful_checks"] / self.health_stats["total_checks"]
                if self.health_stats["total_checks"] > 0 else 0
            ),
            "services_monitored": len(self.health_history)
        }
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while True:
            try:
                # 获取所有服务
                services = await self.service_registry.find_services()
                
                # 并发执行健康检查
                tasks = [
                    self.check_service_health(service_info)
                    for service_info in services
                ]
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error("Error in health check loop", error=str(e))
                await asyncio.sleep(5)
    
    async def _determine_check_type(self, service_info: ServiceInfo) -> HealthCheckType:
        """
        确定健康检查类型
        
        Args:
            service_info: 服务信息
            
        Returns:
            健康检查类型
        """
        # 如果有自定义健康检查
        if service_info.service_name in self.custom_health_checks:
            return HealthCheckType.CUSTOM
        
        # 如果有健康检查URL
        if service_info.health_check_url:
            return HealthCheckType.HTTP
        
        # 默认使用TCP检查
        return HealthCheckType.TCP
    
    async def _http_health_check(self, service_info: ServiceInfo) -> HealthCheckResult:
        """
        HTTP健康检查
        
        Args:
            service_info: 服务信息
            
        Returns:
            健康检查结果
        """
        if not service_info.health_check_url:
            return HealthCheckResult(
                service_info.service_id,
                False,
                error="No health check URL provided"
            )
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(service_info.health_check_url) as response:
                    if response.status == 200:
                        return HealthCheckResult(service_info.service_id, True)
                    else:
                        return HealthCheckResult(
                            service_info.service_id,
                            False,
                            error=f"HTTP {response.status}"
                        )
                        
        except asyncio.TimeoutError:
            return HealthCheckResult(
                service_info.service_id,
                False,
                error="Timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                service_info.service_id,
                False,
                error=str(e)
            )
    
    async def _tcp_health_check(self, service_info: ServiceInfo) -> HealthCheckResult:
        """
        TCP健康检查
        
        Args:
            service_info: 服务信息
            
        Returns:
            健康检查结果
        """
        try:
            # 创建socket连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            
            result = sock.connect_ex((service_info.host, service_info.port))
            sock.close()
            
            if result == 0:
                return HealthCheckResult(service_info.service_id, True)
            else:
                return HealthCheckResult(
                    service_info.service_id,
                    False,
                    error=f"TCP connection failed: {result}"
                )
                
        except Exception as e:
            return HealthCheckResult(
                service_info.service_id,
                False,
                error=str(e)
            )
    
    async def _custom_health_check(self, service_info: ServiceInfo) -> HealthCheckResult:
        """
        自定义健康检查
        
        Args:
            service_info: 服务信息
            
        Returns:
            健康检查结果
        """
        try:
            check_function = self.custom_health_checks.get(service_info.service_name)
            if not check_function:
                return HealthCheckResult(
                    service_info.service_id,
                    False,
                    error="Custom health check function not found"
                )
            
            # 执行自定义检查
            is_healthy = check_function(service_info)
            
            return HealthCheckResult(service_info.service_id, is_healthy)
            
        except Exception as e:
            return HealthCheckResult(
                service_info.service_id,
                False,
                error=str(e)
            )
    
    def _update_stats(self, result: HealthCheckResult) -> None:
        """
        更新统计信息
        
        Args:
            result: 健康检查结果
        """
        self.health_stats["total_checks"] += 1
        
        if result.is_healthy:
            self.health_stats["successful_checks"] += 1
        else:
            self.health_stats["failed_checks"] += 1
        
        # 更新平均响应时间
        total_checks = self.health_stats["total_checks"]
        current_avg = self.health_stats["avg_response_time"]
        
        if total_checks == 1:
            self.health_stats["avg_response_time"] = result.response_time
        else:
            self.health_stats["avg_response_time"] = (
                (current_avg * (total_checks - 1) + result.response_time) / total_checks
            )
    
    async def _save_health_history(self, result: HealthCheckResult) -> None:
        """
        保存健康检查历史
        
        Args:
            result: 健康检查结果
        """
        service_id = result.service_id
        
        if service_id not in self.health_history:
            self.health_history[service_id] = []
        
        self.health_history[service_id].append(result)
        
        # 限制历史记录数量
        if len(self.health_history[service_id]) > self.max_history_size:
            self.health_history[service_id] = self.health_history[service_id][-self.max_history_size:] 