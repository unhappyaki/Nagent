"""
容器管理器

实现智能体容器管理、资源分配和隔离、容器生命周期管理
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class ContainerStatus(Enum):
    """容器状态枚举"""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    DESTROYED = "destroyed"


class ContainerConfig:
    """容器配置"""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        image: str = "nagent/agent:latest",
        resources: Dict[str, Any] = None,
        environment: Dict[str, str] = None,
        volumes: List[Dict[str, str]] = None,
        network: str = "default",
        timeout: int = 300
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.image = image
        self.resources = resources or {
            "cpu": "1",
            "memory": "1Gi",
            "gpu": "0"
        }
        self.environment = environment or {}
        self.volumes = volumes or []
        self.network = network
        self.timeout = timeout
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "image": self.image,
            "resources": self.resources,
            "environment": self.environment,
            "volumes": self.volumes,
            "network": self.network,
            "timeout": self.timeout,
            "created_at": self.created_at.isoformat()
        }


class ContainerManager:
    """
    容器管理器
    
    负责智能体容器的创建、启动、停止、销毁等生命周期管理
    """
    
    def __init__(self):
        """初始化容器管理器"""
        self.containers: Dict[str, 'AgentContainer'] = {}
        self.container_configs: Dict[str, ContainerConfig] = {}
        self.resource_manager = None  # 将在后续实现
        
        # 容器统计
        self.container_stats = {
            "total_containers": 0,
            "running_containers": 0,
            "stopped_containers": 0,
            "error_containers": 0,
            "total_created": 0,
            "total_destroyed": 0
        }
        
        logger.info("Container manager initialized")
    
    async def initialize(self) -> None:
        """初始化容器管理器"""
        try:
            logger.info("Initializing container manager")
            
            # 初始化资源管理器
            # self.resource_manager = ResourceManager()
            # await self.resource_manager.initialize()
            
            # 清理已存在的容器
            await self._cleanup_existing_containers()
            
            logger.info("Container manager initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize container manager", error=str(e))
            raise
    
    async def create_container(self, config: ContainerConfig) -> str:
        """
        创建容器
        
        Args:
            config: 容器配置
            
        Returns:
            容器ID
        """
        container_id = str(uuid.uuid4())
        
        try:
            logger.info(
                "Creating container",
                container_id=container_id,
                agent_id=config.agent_id,
                agent_type=config.agent_type
            )
            
            # 检查资源可用性
            if not await self._check_resources(config):
                raise RuntimeError(f"Insufficient resources for container {container_id}")
            
            # 创建容器实例
            container = AgentContainer(container_id, config)
            self.containers[container_id] = container
            self.container_configs[container_id] = config
            
            # 更新统计
            self.container_stats["total_containers"] += 1
            self.container_stats["total_created"] += 1
            
            logger.info(
                "Container created successfully",
                container_id=container_id,
                agent_id=config.agent_id
            )
            
            return container_id
            
        except Exception as e:
            logger.error(
                "Failed to create container",
                container_id=container_id,
                agent_id=config.agent_id,
                error=str(e)
            )
            raise
    
    async def start_container(self, container_id: str) -> bool:
        """
        启动容器
        
        Args:
            container_id: 容器ID
            
        Returns:
            是否启动成功
        """
        if container_id not in self.containers:
            raise ValueError(f"Container not found: {container_id}")
        
        container = self.containers[container_id]
        
        try:
            logger.info("Starting container", container_id=container_id)
            
            # 启动容器
            success = await container.start()
            
            if success:
                self.container_stats["running_containers"] += 1
                logger.info("Container started successfully", container_id=container_id)
            else:
                self.container_stats["error_containers"] += 1
                logger.error("Failed to start container", container_id=container_id)
            
            return success
            
        except Exception as e:
            self.container_stats["error_containers"] += 1
            logger.error(
                "Error starting container",
                container_id=container_id,
                error=str(e)
            )
            return False
    
    async def stop_container(self, container_id: str, force: bool = False) -> bool:
        """
        停止容器
        
        Args:
            container_id: 容器ID
            force: 是否强制停止
            
        Returns:
            是否停止成功
        """
        if container_id not in self.containers:
            raise ValueError(f"Container not found: {container_id}")
        
        container = self.containers[container_id]
        
        try:
            logger.info("Stopping container", container_id=container_id, force=force)
            
            # 停止容器
            success = await container.stop(force=force)
            
            if success:
                if container.status == ContainerStatus.RUNNING:
                    self.container_stats["running_containers"] -= 1
                self.container_stats["stopped_containers"] += 1
                logger.info("Container stopped successfully", container_id=container_id)
            else:
                logger.error("Failed to stop container", container_id=container_id)
            
            return success
            
        except Exception as e:
            logger.error(
                "Error stopping container",
                container_id=container_id,
                error=str(e)
            )
            return False
    
    async def destroy_container(self, container_id: str) -> bool:
        """
        销毁容器
        
        Args:
            container_id: 容器ID
            
        Returns:
            是否销毁成功
        """
        if container_id not in self.containers:
            raise ValueError(f"Container not found: {container_id}")
        
        container = self.containers[container_id]
        
        try:
            logger.info("Destroying container", container_id=container_id)
            
            # 先停止容器
            if container.status == ContainerStatus.RUNNING:
                await container.stop(force=True)
            
            # 销毁容器
            success = await container.destroy()
            
            if success:
                # 更新统计
                if container.status == ContainerStatus.RUNNING:
                    self.container_stats["running_containers"] -= 1
                elif container.status == ContainerStatus.STOPPED:
                    self.container_stats["stopped_containers"] -= 1
                elif container.status == ContainerStatus.ERROR:
                    self.container_stats["error_containers"] -= 1
                
                self.container_stats["total_containers"] -= 1
                self.container_stats["total_destroyed"] += 1
                
                # 移除容器记录
                del self.containers[container_id]
                if container_id in self.container_configs:
                    del self.container_configs[container_id]
                
                logger.info("Container destroyed successfully", container_id=container_id)
            else:
                logger.error("Failed to destroy container", container_id=container_id)
            
            return success
            
        except Exception as e:
            logger.error(
                "Error destroying container",
                container_id=container_id,
                error=str(e)
            )
            return False
    
    async def get_container_status(self, container_id: str) -> Optional[Dict[str, Any]]:
        """
        获取容器状态
        
        Args:
            container_id: 容器ID
            
        Returns:
            容器状态信息
        """
        if container_id not in self.containers:
            return None
        
        container = self.containers[container_id]
        config = self.container_configs.get(container_id)
        
        return {
            "container_id": container_id,
            "status": container.status.value,
            "agent_id": container.config.agent_id,
            "agent_type": container.config.agent_type,
            "created_at": container.created_at.isoformat(),
            "started_at": container.started_at.isoformat() if container.started_at else None,
            "stopped_at": container.stopped_at.isoformat() if container.stopped_at else None,
            "config": config.to_dict() if config else None,
            "resources": await container.get_resource_usage(),
            "logs": await container.get_logs()
        }
    
    async def list_containers(self, status: Optional[ContainerStatus] = None) -> List[Dict[str, Any]]:
        """
        列出容器
        
        Args:
            status: 状态过滤
            
        Returns:
            容器列表
        """
        containers = []
        
        for container_id, container in self.containers.items():
            if status and container.status != status:
                continue
            
            container_info = {
                "container_id": container_id,
                "status": container.status.value,
                "agent_id": container.config.agent_id,
                "agent_type": container.config.agent_type,
                "created_at": container.created_at.isoformat()
            }
            containers.append(container_info)
        
        return containers
    
    async def get_container_stats(self) -> Dict[str, Any]:
        """
        获取容器统计信息
        
        Returns:
            统计信息
        """
        return {
            "total_containers": self.container_stats["total_containers"],
            "running_containers": self.container_stats["running_containers"],
            "stopped_containers": self.container_stats["stopped_containers"],
            "error_containers": self.container_stats["error_containers"],
            "total_created": self.container_stats["total_created"],
            "total_destroyed": self.container_stats["total_destroyed"],
            "success_rate": (
                (self.container_stats["total_created"] - self.container_stats["error_containers"]) 
                / self.container_stats["total_created"]
                if self.container_stats["total_created"] > 0 else 0
            )
        }
    
    async def _check_resources(self, config: ContainerConfig) -> bool:
        """
        检查资源可用性
        
        Args:
            config: 容器配置
            
        Returns:
            资源是否足够
        """
        # 这里应该实现实际的资源检查逻辑
        # 暂时返回True
        return True
    
    async def _cleanup_existing_containers(self) -> None:
        """清理已存在的容器"""
        # 这里应该实现清理逻辑
        # 暂时为空
        pass 