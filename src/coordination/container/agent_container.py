"""
智能体容器

实现单个智能体容器的生命周期管理
"""

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import structlog

from .container_manager import ContainerStatus, ContainerConfig
from src.communication.protocols.a2a.a2a_server import A2AServer
from src.communication.protocols.acp.acp_server import ACPServer
from src.infrastructure.registry.unified_registry import UnifiedModuleRegistry

logger = structlog.get_logger(__name__)


class AgentContainer:
    """
    智能体容器
    
    负责单个智能体容器的生命周期管理
    """
    
    def __init__(self, container_id: str, config: ContainerConfig, unified_registry: UnifiedModuleRegistry):
        """
        初始化容器
        
        Args:
            container_id: 容器ID
            config: 容器配置
        """
        self.container_id = container_id
        self.config = config
        self.status = ContainerStatus.CREATED
        
        # 时间戳
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        
        # 进程管理
        self.process: Optional[subprocess.Popen] = None
        self.pid: Optional[int] = None
        
        # 日志管理
        self.logs: List[str] = []
        self.max_logs = 1000
        
        # 资源使用
        self.resource_usage: Dict[str, Any] = {}
        
        # 健康检查
        self.health_check_interval = 30  # 秒
        self.last_health_check = None
        self.health_status = "unknown"
        
        # 新增：协议组件
        self.unified_registry = unified_registry
        self.a2a_server = A2AServer(self.unified_registry, self.config.agent_card)
        self.acp_server = ACPServer(self.config.acp_config)
        
        logger.info(
            "Agent container initialized",
            container_id=container_id,
            agent_id=config.agent_id,
            agent_type=config.agent_type
        )
    
    async def start(self) -> bool:
        """
        启动容器
        
        Returns:
            是否启动成功
        """
        try:
            logger.info("Starting agent container", container_id=self.container_id)
            
            # 更新状态
            self.status = ContainerStatus.STARTING
            
            # 创建容器环境
            await self._create_environment()
            
            # 新增：A2A能力注册
            await self.a2a_server.register_agent()
            # 新增：启动ACPServer监听
            await self.acp_server.start()
            
            # 启动Agent进程
            success = await self._start_process()
            
            if success:
                self.status = ContainerStatus.RUNNING
                self.started_at = datetime.utcnow()
                
                # 启动健康检查
                asyncio.create_task(self._health_check_loop())
                
                logger.info(
                    "Agent container started successfully",
                    container_id=self.container_id,
                    pid=self.pid
                )
            else:
                self.status = ContainerStatus.ERROR
                logger.error("Failed to start agent container", container_id=self.container_id)
            
            return success
            
        except Exception as e:
            self.status = ContainerStatus.ERROR
            logger.error(
                "Error starting agent container",
                container_id=self.container_id,
                error=str(e)
            )
            return False
    
    async def stop(self, force: bool = False) -> bool:
        """
        停止容器
        
        Args:
            force: 是否强制停止
            
        Returns:
            是否停止成功
        """
        try:
            logger.info("Stopping agent container", container_id=self.container_id, force=force)
            
            # 更新状态
            self.status = ContainerStatus.STOPPING
            
            # 停止进程
            success = await self._stop_process(force=force)
            
            if success:
                self.status = ContainerStatus.STOPPED
                self.stopped_at = datetime.utcnow()
                logger.info("Agent container stopped successfully", container_id=self.container_id)
            else:
                self.status = ContainerStatus.ERROR
                logger.error("Failed to stop agent container", container_id=self.container_id)
            
            return success
            
        except Exception as e:
            self.status = ContainerStatus.ERROR
            logger.error(
                "Error stopping agent container",
                container_id=self.container_id,
                error=str(e)
            )
            return False
    
    async def destroy(self) -> bool:
        """
        销毁容器
        
        Returns:
            是否销毁成功
        """
        try:
            logger.info("Destroying agent container", container_id=self.container_id)
            
            # 停止容器
            if self.status == ContainerStatus.RUNNING:
                await self.stop(force=True)
            
            # 清理环境
            await self._cleanup_environment()
            
            # 更新状态
            self.status = ContainerStatus.DESTROYED
            
            logger.info("Agent container destroyed successfully", container_id=self.container_id)
            return True
            
        except Exception as e:
            logger.error(
                "Error destroying agent container",
                container_id=self.container_id,
                error=str(e)
            )
            return False
    
    async def get_resource_usage(self) -> Dict[str, Any]:
        """
        获取资源使用情况
        
        Returns:
            资源使用信息
        """
        if not self.process or not self.pid:
            return {}
        
        try:
            # 获取进程信息
            import psutil
            
            process = psutil.Process(self.pid)
            
            # CPU使用率
            cpu_percent = process.cpu_percent()
            
            # 内存使用
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            # 网络IO
            try:
                net_io = process.io_counters()
            except:
                net_io = None
            
            self.resource_usage = {
                "cpu_percent": cpu_percent,
                "memory_rss": memory_info.rss,
                "memory_vms": memory_info.vms,
                "memory_percent": memory_percent,
                "network_io": {
                    "bytes_sent": net_io.bytes_sent if net_io else 0,
                    "bytes_recv": net_io.bytes_recv if net_io else 0
                } if net_io else None,
                "num_threads": process.num_threads(),
                "num_fds": process.num_fds() if hasattr(process, 'num_fds') else None,
                "create_time": process.create_time(),
                "status": process.status()
            }
            
        except Exception as e:
            logger.warning(
                "Failed to get resource usage",
                container_id=self.container_id,
                error=str(e)
            )
        
        return self.resource_usage
    
    async def get_logs(self, lines: int = 100) -> List[str]:
        """
        获取容器日志
        
        Args:
            lines: 返回的日志行数
            
        Returns:
            日志列表
        """
        return self.logs[-lines:] if lines > 0 else self.logs
    
    async def add_log(self, message: str) -> None:
        """
        添加日志
        
        Args:
            message: 日志消息
        """
        timestamp = datetime.utcnow().isoformat()
        log_entry = f"[{timestamp}] {message}"
        
        self.logs.append(log_entry)
        
        # 限制日志数量
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
    
    async def _create_environment(self) -> None:
        """创建容器环境"""
        try:
            # 创建容器目录
            container_dir = f"/tmp/nagent/containers/{self.container_id}"
            os.makedirs(container_dir, exist_ok=True)
            
            # 创建配置文件
            config_file = os.path.join(container_dir, "config.json")
            with open(config_file, 'w') as f:
                json.dump(self.config.to_dict(), f, indent=2)
            
            # 设置环境变量
            self.environment = {
                "CONTAINER_ID": self.container_id,
                "AGENT_ID": self.config.agent_id,
                "AGENT_TYPE": self.config.agent_type,
                "CONTAINER_DIR": container_dir,
                "CONFIG_FILE": config_file,
                **self.config.environment
            }
            
            await self.add_log("Container environment created")
            
        except Exception as e:
            logger.error(
                "Failed to create container environment",
                container_id=self.container_id,
                error=str(e)
            )
            raise
    
    async def _start_process(self) -> bool:
        """
        启动Agent进程
        
        Returns:
            是否启动成功
        """
        try:
            # 构建启动命令
            cmd = [
                "python", "-m", "src.core.agent.task_agent",
                "--agent-id", self.config.agent_id,
                "--agent-type", self.config.agent_type,
                "--config-file", self.environment["CONFIG_FILE"]
            ]
            
            # 启动进程
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=self.environment,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.pid = self.process.pid
            
            # 启动日志收集
            asyncio.create_task(self._log_collector())
            
            # 等待进程启动
            await asyncio.sleep(2)
            
            # 检查进程状态
            if self.process.poll() is None:
                await self.add_log(f"Agent process started with PID {self.pid}")
                return True
            else:
                await self.add_log("Agent process failed to start")
                return False
                
        except Exception as e:
            logger.error(
                "Failed to start agent process",
                container_id=self.container_id,
                error=str(e)
            )
            return False
    
    async def _stop_process(self, force: bool = False) -> bool:
        """
        停止Agent进程
        
        Args:
            force: 是否强制停止
            
        Returns:
            是否停止成功
        """
        if not self.process:
            return True
        
        try:
            if force:
                # 强制终止
                self.process.terminate()
                await asyncio.sleep(1)
                
                if self.process.poll() is None:
                    self.process.kill()
                    await asyncio.sleep(1)
            else:
                # 优雅停止
                self.process.terminate()
                
                # 等待进程结束
                try:
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, self.process.wait),
                        timeout=30
                    )
                except asyncio.TimeoutError:
                    # 超时后强制终止
                    self.process.kill()
                    await asyncio.sleep(1)
            
            # 检查进程是否已停止
            if self.process.poll() is not None:
                await self.add_log(f"Agent process stopped (PID: {self.pid})")
                return True
            else:
                await self.add_log("Failed to stop agent process")
                return False
                
        except Exception as e:
            logger.error(
                "Error stopping agent process",
                container_id=self.container_id,
                error=str(e)
            )
            return False
    
    async def _cleanup_environment(self) -> None:
        """清理容器环境"""
        try:
            # 清理容器目录
            container_dir = self.environment.get("CONTAINER_DIR")
            if container_dir and os.path.exists(container_dir):
                import shutil
                shutil.rmtree(container_dir)
            
            await self.add_log("Container environment cleaned up")
            
        except Exception as e:
            logger.error(
                "Failed to cleanup container environment",
                container_id=self.container_id,
                error=str(e)
            )
    
    async def _log_collector(self) -> None:
        """日志收集器"""
        if not self.process:
            return
        
        try:
            while self.process.poll() is None:
                line = self.process.stdout.readline()
                if line:
                    await self.add_log(line.strip())
                else:
                    await asyncio.sleep(0.1)
            
            # 读取剩余日志
            remaining_logs = self.process.stdout.read()
            if remaining_logs:
                for line in remaining_logs.split('\n'):
                    if line.strip():
                        await self.add_log(line.strip())
                        
        except Exception as e:
            logger.error(
                "Error in log collector",
                container_id=self.container_id,
                error=str(e)
            )
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self.status == ContainerStatus.RUNNING:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(
                    "Error in health check loop",
                    container_id=self.container_id,
                    error=str(e)
                )
                await asyncio.sleep(5)
    
    async def _perform_health_check(self) -> None:
        """执行健康检查"""
        try:
            if not self.process or self.process.poll() is not None:
                self.health_status = "unhealthy"
                await self.add_log("Health check failed: process not running")
                return
            
            # 检查进程响应
            # 这里可以实现更复杂的健康检查逻辑
            # 比如发送心跳请求、检查端口等
            
            self.health_status = "healthy"
            self.last_health_check = datetime.utcnow()
            
        except Exception as e:
            self.health_status = "unhealthy"
            logger.error(
                "Health check failed",
                container_id=self.container_id,
                error=str(e)
            ) 

    def get_agent_card(self) -> dict:
        """对外暴露本地Agent能力卡片"""
        return self.a2a_server.agent_card.to_dict() 