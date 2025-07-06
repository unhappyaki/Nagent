"""
MCP监控集成

与现有监控系统和执行器集成，提供MCP工具的监控和跟踪
"""

import asyncio
import time
import json
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import structlog

from .mcp_adapter import MCPAdapter
from .external_tool_registry import ExternalToolRegistry

logger = structlog.get_logger(__name__)


class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertLevel(Enum):
    """告警级别枚举"""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MCPMetric:
    """MCP指标"""
    name: str
    type: MetricType
    value: float
    labels: Dict[str, str]
    timestamp: float
    description: Optional[str] = None


@dataclass
class MCPAlert:
    """MCP告警"""
    name: str
    level: AlertLevel
    message: str
    labels: Dict[str, str]
    timestamp: float
    resolved: bool = False
    metadata: Optional[Dict[str, Any]] = None


class MCPExecutionEvent:
    """MCP执行事件"""
    
    def __init__(
        self,
        tool_name: str,
        server_name: str,
        execution_id: str,
        start_time: float,
        arguments: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ):
        self.tool_name = tool_name
        self.server_name = server_name
        self.execution_id = execution_id
        self.start_time = start_time
        self.arguments = arguments
        self.user_context = user_context or {}
        self.end_time: Optional[float] = None
        self.success: Optional[bool] = None
        self.error: Optional[str] = None
        self.result: Optional[Any] = None
        self.duration: Optional[float] = None
    
    def complete(self, success: bool, result: Any = None, error: str = None) -> None:
        """完成执行事件"""
        self.end_time = time.time()
        self.success = success
        self.result = result
        self.error = error
        self.duration = self.end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_name": self.tool_name,
            "server_name": self.server_name,
            "execution_id": self.execution_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "success": self.success,
            "error": self.error,
            "arguments_count": len(self.arguments),
            "user_context": self.user_context
        }


class MCPMonitoringIntegration:
    """MCP监控集成"""
    
    def __init__(
        self,
        mcp_adapter: MCPAdapter,
        external_registry: ExternalToolRegistry,
        metrics_collector=None,
        log_manager=None,
        alert_manager=None
    ):
        """
        初始化MCP监控集成
        
        Args:
            mcp_adapter: MCP适配器
            external_registry: 外部工具注册表
            metrics_collector: 指标收集器
            log_manager: 日志管理器
            alert_manager: 告警管理器
        """
        self.mcp_adapter = mcp_adapter
        self.external_registry = external_registry
        self.metrics_collector = metrics_collector
        self.log_manager = log_manager
        self.alert_manager = alert_manager
        
        # 执行事件追踪
        self._execution_events: Dict[str, MCPExecutionEvent] = {}
        self._execution_history: List[MCPExecutionEvent] = []
        self._max_history_size = 10000
        
        # 指标缓存
        self._metrics_cache: List[MCPMetric] = []
        self._alerts_cache: List[MCPAlert] = []
        
        # 监控配置
        self.config = {
            "collect_metrics": True,
            "collect_logs": True,
            "collect_traces": True,
            "alert_enabled": True,
            "metrics_interval": 60,  # 1分钟
            "cleanup_interval": 3600,  # 1小时
            "error_rate_threshold": 0.1,  # 10%错误率告警
            "slow_execution_threshold": 30.0,  # 30秒慢执行告警
        }
        
        # 监控任务
        self._metrics_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # 回调函数
        self._execution_callbacks: List[Callable] = []
        self._metrics_callbacks: List[Callable] = []
        self._alert_callbacks: List[Callable] = []
        
        logger.info("MCP monitoring integration initialized")
    
    async def start(self) -> None:
        """启动监控集成"""
        try:
            # 启动指标收集
            if self.config["collect_metrics"]:
                await self.start_metrics_collection()
            
            # 启动清理任务
            await self.start_cleanup_task()
            
            # 注册执行钩子
            await self._register_execution_hooks()
            
            logger.info("MCP monitoring integration started")
            
        except Exception as e:
            logger.error("Failed to start MCP monitoring integration", error=str(e))
            raise
    
    async def stop(self) -> None:
        """停止监控集成"""
        try:
            # 停止监控任务
            await self.stop_metrics_collection()
            await self.stop_cleanup_task()
            
            # 注销执行钩子
            await self._unregister_execution_hooks()
            
            logger.info("MCP monitoring integration stopped")
            
        except Exception as e:
            logger.error("Error stopping MCP monitoring integration", error=str(e))
    
    async def track_execution(
        self,
        tool_name: str,
        server_name: str,
        arguments: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        开始追踪工具执行
        
        Args:
            tool_name: 工具名称
            server_name: 服务器名称
            arguments: 执行参数
            user_context: 用户上下文
            
        Returns:
            执行ID
        """
        execution_id = f"{tool_name}_{server_name}_{time.time()}_{id(arguments)}"
        
        event = MCPExecutionEvent(
            tool_name=tool_name,
            server_name=server_name,
            execution_id=execution_id,
            start_time=time.time(),
            arguments=arguments,
            user_context=user_context
        )
        
        self._execution_events[execution_id] = event
        
        # 记录开始日志
        if self.config["collect_logs"] and self.log_manager:
            await self._log_execution_start(event)
        
        # 发送开始指标
        if self.config["collect_metrics"]:
            await self._record_execution_start_metric(event)
        
        # 触发回调
        for callback in self._execution_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback("start", event)
                else:
                    callback("start", event)
            except Exception as e:
                logger.error("Error in execution callback", error=str(e))
        
        logger.debug(
            "Execution tracking started",
            execution_id=execution_id,
            tool_name=tool_name,
            server_name=server_name
        )
        
        return execution_id
    
    async def complete_execution(
        self,
        execution_id: str,
        success: bool,
        result: Any = None,
        error: str = None
    ) -> None:
        """
        完成执行追踪
        
        Args:
            execution_id: 执行ID
            success: 是否成功
            result: 执行结果
            error: 错误信息
        """
        if execution_id not in self._execution_events:
            logger.warning("Execution event not found", execution_id=execution_id)
            return
        
        event = self._execution_events[execution_id]
        event.complete(success, result, error)
        
        # 移动到历史记录
        self._execution_history.append(event)
        del self._execution_events[execution_id]
        
        # 限制历史记录大小
        if len(self._execution_history) > self._max_history_size:
            self._execution_history = self._execution_history[-self._max_history_size:]
        
        # 记录完成日志
        if self.config["collect_logs"] and self.log_manager:
            await self._log_execution_complete(event)
        
        # 发送完成指标
        if self.config["collect_metrics"]:
            await self._record_execution_complete_metric(event)
        
        # 检查告警条件
        if self.config["alert_enabled"]:
            await self._check_execution_alerts(event)
        
        # 触发回调
        for callback in self._execution_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback("complete", event)
                else:
                    callback("complete", event)
            except Exception as e:
                logger.error("Error in execution callback", error=str(e))
        
        logger.debug(
            "Execution tracking completed",
            execution_id=execution_id,
            success=success,
            duration=event.duration
        )
    
    async def collect_metrics(self) -> List[MCPMetric]:
        """收集MCP指标"""
        metrics = []
        current_time = time.time()
        
        try:
            # 适配器统计指标
            adapter_stats = self.mcp_adapter.get_stats()
            for key, value in adapter_stats.items():
                if isinstance(value, (int, float)):
                    metrics.append(MCPMetric(
                        name=f"mcp_adapter_{key}",
                        type=MetricType.GAUGE,
                        value=float(value),
                        labels={"component": "adapter"},
                        timestamp=current_time,
                        description=f"MCP adapter {key}"
                    ))
            
            # 外部工具注册表指标
            registry_stats = self.external_registry.get_stats()
            for key, value in registry_stats.items():
                if isinstance(value, (int, float)):
                    metrics.append(MCPMetric(
                        name=f"mcp_registry_{key}",
                        type=MetricType.GAUGE,
                        value=float(value),
                        labels={"component": "registry"},
                        timestamp=current_time,
                        description=f"MCP registry {key}"
                    ))
            
            # 执行统计指标
            execution_metrics = await self._collect_execution_metrics(current_time)
            metrics.extend(execution_metrics)
            
            # 工具级别指标
            tool_metrics = await self._collect_tool_metrics(current_time)
            metrics.extend(tool_metrics)
            
            # 服务器级别指标
            server_metrics = await self._collect_server_metrics(current_time)
            metrics.extend(server_metrics)
            
            # 缓存指标
            self._metrics_cache.extend(metrics)
            
            # 限制缓存大小
            if len(self._metrics_cache) > 100000:
                self._metrics_cache = self._metrics_cache[-50000:]
            
            logger.debug("MCP metrics collected", count=len(metrics))
            
            return metrics
            
        except Exception as e:
            logger.error("Error collecting MCP metrics", error=str(e))
            return []
    
    async def get_execution_stats(
        self,
        time_window: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        获取执行统计
        
        Args:
            time_window: 时间窗口（秒），None表示全部
            
        Returns:
            执行统计
        """
        current_time = time.time()
        cutoff_time = current_time - time_window if time_window else 0
        
        # 过滤历史记录
        events = [
            event for event in self._execution_history
            if event.start_time >= cutoff_time
        ]
        
        if not events:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "average_duration": 0.0,
                "error_rate": 0.0,
                "tool_stats": {},
                "server_stats": {}
            }
        
        # 基础统计
        total_executions = len(events)
        successful_executions = sum(1 for e in events if e.success)
        failed_executions = total_executions - successful_executions
        
        success_rate = successful_executions / total_executions if total_executions > 0 else 0
        error_rate = failed_executions / total_executions if total_executions > 0 else 0
        
        # 持续时间统计
        durations = [e.duration for e in events if e.duration is not None]
        average_duration = sum(durations) / len(durations) if durations else 0
        
        # 工具级别统计
        tool_stats = {}
        server_stats = {}
        
        for event in events:
            # 工具统计
            if event.tool_name not in tool_stats:
                tool_stats[event.tool_name] = {
                    "executions": 0,
                    "successes": 0,
                    "failures": 0,
                    "total_duration": 0.0,
                    "avg_duration": 0.0
                }
            
            stats = tool_stats[event.tool_name]
            stats["executions"] += 1
            if event.success:
                stats["successes"] += 1
            else:
                stats["failures"] += 1
            
            if event.duration:
                stats["total_duration"] += event.duration
                stats["avg_duration"] = stats["total_duration"] / stats["executions"]
            
            # 服务器统计
            if event.server_name not in server_stats:
                server_stats[event.server_name] = {
                    "executions": 0,
                    "successes": 0,
                    "failures": 0,
                    "total_duration": 0.0,
                    "avg_duration": 0.0
                }
            
            stats = server_stats[event.server_name]
            stats["executions"] += 1
            if event.success:
                stats["successes"] += 1
            else:
                stats["failures"] += 1
            
            if event.duration:
                stats["total_duration"] += event.duration
                stats["avg_duration"] = stats["total_duration"] / stats["executions"]
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": success_rate,
            "error_rate": error_rate,
            "average_duration": average_duration,
            "tool_stats": tool_stats,
            "server_stats": server_stats,
            "time_window": time_window,
            "generated_at": current_time
        }
    
    def add_execution_callback(self, callback: Callable) -> None:
        """添加执行回调"""
        self._execution_callbacks.append(callback)
    
    def add_metrics_callback(self, callback: Callable) -> None:
        """添加指标回调"""
        self._metrics_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable) -> None:
        """添加告警回调"""
        self._alert_callbacks.append(callback)
    
    async def start_metrics_collection(self) -> None:
        """启动指标收集"""
        if self._metrics_task is not None:
            logger.warning("Metrics collection already running")
            return
        
        self._metrics_task = asyncio.create_task(self._metrics_collection_loop())
        logger.info("MCP metrics collection started")
    
    async def stop_metrics_collection(self) -> None:
        """停止指标收集"""
        if self._metrics_task is not None:
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass
            self._metrics_task = None
            logger.info("MCP metrics collection stopped")
    
    async def start_cleanup_task(self) -> None:
        """启动清理任务"""
        if self._cleanup_task is not None:
            logger.warning("Cleanup task already running")
            return
        
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("MCP cleanup task started")
    
    async def stop_cleanup_task(self) -> None:
        """停止清理任务"""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("MCP cleanup task stopped")
    
    async def _register_execution_hooks(self) -> None:
        """注册执行钩子"""
        # 这里可以集成到现有的执行器系统
        pass
    
    async def _unregister_execution_hooks(self) -> None:
        """注销执行钩子"""
        pass
    
    async def _log_execution_start(self, event: MCPExecutionEvent) -> None:
        """记录执行开始日志"""
        if self.log_manager:
            try:
                log_data = {
                    "event_type": "mcp_execution_start",
                    "execution_id": event.execution_id,
                    "tool_name": event.tool_name,
                    "server_name": event.server_name,
                    "start_time": event.start_time,
                    "arguments_count": len(event.arguments),
                    "user_context": event.user_context
                }
                
                # 假设log_manager有log_structured方法
                if hasattr(self.log_manager, 'log_structured'):
                    await self.log_manager.log_structured("INFO", "MCP tool execution started", log_data)
                    
            except Exception as e:
                logger.error("Error logging execution start", error=str(e))
    
    async def _log_execution_complete(self, event: MCPExecutionEvent) -> None:
        """记录执行完成日志"""
        if self.log_manager:
            try:
                log_data = {
                    "event_type": "mcp_execution_complete",
                    "execution_id": event.execution_id,
                    "tool_name": event.tool_name,
                    "server_name": event.server_name,
                    "start_time": event.start_time,
                    "end_time": event.end_time,
                    "duration": event.duration,
                    "success": event.success,
                    "error": event.error,
                    "user_context": event.user_context
                }
                
                level = "INFO" if event.success else "ERROR"
                message = "MCP tool execution completed" if event.success else "MCP tool execution failed"
                
                if hasattr(self.log_manager, 'log_structured'):
                    await self.log_manager.log_structured(level, message, log_data)
                    
            except Exception as e:
                logger.error("Error logging execution complete", error=str(e))
    
    async def _record_execution_start_metric(self, event: MCPExecutionEvent) -> None:
        """记录执行开始指标"""
        metric = MCPMetric(
            name="mcp_tool_execution_started",
            type=MetricType.COUNTER,
            value=1.0,
            labels={
                "tool_name": event.tool_name,
                "server_name": event.server_name
            },
            timestamp=event.start_time,
            description="MCP tool execution started"
        )
        
        self._metrics_cache.append(metric)
        
        # 触发指标回调
        for callback in self._metrics_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(metric)
                else:
                    callback(metric)
            except Exception as e:
                logger.error("Error in metrics callback", error=str(e))
    
    async def _record_execution_complete_metric(self, event: MCPExecutionEvent) -> None:
        """记录执行完成指标"""
        # 完成计数指标
        complete_metric = MCPMetric(
            name="mcp_tool_execution_completed",
            type=MetricType.COUNTER,
            value=1.0,
            labels={
                "tool_name": event.tool_name,
                "server_name": event.server_name,
                "success": str(event.success).lower()
            },
            timestamp=event.end_time,
            description="MCP tool execution completed"
        )
        
        # 持续时间指标
        duration_metric = MCPMetric(
            name="mcp_tool_execution_duration",
            type=MetricType.HISTOGRAM,
            value=event.duration or 0.0,
            labels={
                "tool_name": event.tool_name,
                "server_name": event.server_name
            },
            timestamp=event.end_time,
            description="MCP tool execution duration"
        )
        
        self._metrics_cache.extend([complete_metric, duration_metric])
        
        # 触发指标回调
        for metric in [complete_metric, duration_metric]:
            for callback in self._metrics_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(metric)
                    else:
                        callback(metric)
                except Exception as e:
                    logger.error("Error in metrics callback", error=str(e))
    
    async def _check_execution_alerts(self, event: MCPExecutionEvent) -> None:
        """检查执行告警条件"""
        alerts = []
        
        # 检查执行失败
        if not event.success:
            alert = MCPAlert(
                name="mcp_tool_execution_failed",
                level=AlertLevel.ERROR,
                message=f"MCP tool {event.tool_name} execution failed: {event.error}",
                labels={
                    "tool_name": event.tool_name,
                    "server_name": event.server_name,
                    "execution_id": event.execution_id
                },
                timestamp=event.end_time,
                metadata={"event": event.to_dict()}
            )
            alerts.append(alert)
        
        # 检查慢执行
        if (event.duration is not None and 
            event.duration > self.config["slow_execution_threshold"]):
            alert = MCPAlert(
                name="mcp_tool_slow_execution",
                level=AlertLevel.WARNING,
                message=f"MCP tool {event.tool_name} slow execution: {event.duration:.2f}s",
                labels={
                    "tool_name": event.tool_name,
                    "server_name": event.server_name,
                    "execution_id": event.execution_id
                },
                timestamp=event.end_time,
                metadata={"event": event.to_dict()}
            )
            alerts.append(alert)
        
        # 发送告警
        for alert in alerts:
            await self._send_alert(alert)
    
    async def _send_alert(self, alert: MCPAlert) -> None:
        """发送告警"""
        self._alerts_cache.append(alert)
        
        # 限制告警缓存大小
        if len(self._alerts_cache) > 10000:
            self._alerts_cache = self._alerts_cache[-5000:]
        
        # 发送到告警管理器
        if self.alert_manager:
            try:
                if hasattr(self.alert_manager, 'send_alert'):
                    await self.alert_manager.send_alert(alert)
            except Exception as e:
                logger.error("Error sending alert", error=str(e))
        
        # 触发告警回调
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error("Error in alert callback", error=str(e))
        
        logger.warning(
            "MCP alert generated",
            alert_name=alert.name,
            level=alert.level.value,
            message=alert.message
        )
    
    async def _collect_execution_metrics(self, timestamp: float) -> List[MCPMetric]:
        """收集执行指标"""
        metrics = []
        
        # 活跃执行数量
        active_executions = len(self._execution_events)
        metrics.append(MCPMetric(
            name="mcp_active_executions",
            type=MetricType.GAUGE,
            value=float(active_executions),
            labels={"component": "execution"},
            timestamp=timestamp,
            description="Number of active MCP executions"
        ))
        
        # 历史执行数量
        total_history = len(self._execution_history)
        metrics.append(MCPMetric(
            name="mcp_total_executions",
            type=MetricType.GAUGE,
            value=float(total_history),
            labels={"component": "execution"},
            timestamp=timestamp,
            description="Total MCP executions in history"
        ))
        
        return metrics
    
    async def _collect_tool_metrics(self, timestamp: float) -> List[MCPMetric]:
        """收集工具级别指标"""
        metrics = []
        
        # 获取所有工具的统计
        tools = self.external_registry.list_tools()
        
        for tool_info in tools:
            try:
                tool_stats = await tool_info.wrapper.get_stats()
                
                for key, value in tool_stats.items():
                    if isinstance(value, (int, float)):
                        metrics.append(MCPMetric(
                            name=f"mcp_tool_{key}",
                            type=MetricType.GAUGE,
                            value=float(value),
                            labels={
                                "tool_name": tool_info.name,
                                "server_name": tool_info.server_name,
                                "category": tool_info.category.value
                            },
                            timestamp=timestamp,
                            description=f"MCP tool {key}"
                        ))
                        
            except Exception as e:
                logger.error(
                    "Error collecting tool metrics",
                    tool_name=tool_info.name,
                    error=str(e)
                )
        
        return metrics
    
    async def _collect_server_metrics(self, timestamp: float) -> List[MCPMetric]:
        """收集服务器级别指标"""
        metrics = []
        
        # 服务器健康状态检查
        try:
            health_status = await self.mcp_adapter.health_check()
            
            # 连接管理器健康状态
            connection_health = health_status.get("connection_manager", "unknown")
            health_value = 1.0 if connection_health == "healthy" else 0.0
            
            metrics.append(MCPMetric(
                name="mcp_connection_manager_healthy",
                type=MetricType.GAUGE,
                value=health_value,
                labels={"component": "connection_manager"},
                timestamp=timestamp,
                description="MCP connection manager health status"
            ))
            
        except Exception as e:
            logger.error("Error collecting server health metrics", error=str(e))
        
        return metrics
    
    async def _metrics_collection_loop(self) -> None:
        """指标收集循环"""
        logger.debug("MCP metrics collection loop started")
        
        try:
            while True:
                await asyncio.sleep(self.config["metrics_interval"])
                
                try:
                    await self.collect_metrics()
                except Exception as e:
                    logger.error("Error in metrics collection loop", error=str(e))
                    
        except asyncio.CancelledError:
            logger.debug("MCP metrics collection loop cancelled")
            raise
        except Exception as e:
            logger.error("Error in MCP metrics collection loop", error=str(e))
    
    async def _cleanup_loop(self) -> None:
        """清理循环"""
        logger.debug("MCP cleanup loop started")
        
        try:
            while True:
                await asyncio.sleep(self.config["cleanup_interval"])
                
                try:
                    current_time = time.time()
                    
                    # 清理过期的执行事件（超过1小时未完成的）
                    expired_events = []
                    for execution_id, event in list(self._execution_events.items()):
                        if current_time - event.start_time > 3600:  # 1小时
                            expired_events.append(execution_id)
                    
                    for execution_id in expired_events:
                        event = self._execution_events[execution_id]
                        event.complete(False, error="Execution timeout")
                        self._execution_history.append(event)
                        del self._execution_events[execution_id]
                        
                        logger.warning(
                            "Expired execution event cleaned up",
                            execution_id=execution_id,
                            tool_name=event.tool_name
                        )
                    
                    # 清理旧的指标缓存（保留最近24小时）
                    cutoff_time = current_time - 86400  # 24小时
                    self._metrics_cache = [
                        m for m in self._metrics_cache 
                        if m.timestamp > cutoff_time
                    ]
                    
                    # 清理旧的告警缓存（保留最近7天）
                    cutoff_time = current_time - 604800  # 7天
                    self._alerts_cache = [
                        a for a in self._alerts_cache 
                        if a.timestamp > cutoff_time
                    ]
                    
                    logger.debug("MCP monitoring cleanup completed")
                    
                except Exception as e:
                    logger.error("Error in cleanup loop", error=str(e))
                    
        except asyncio.CancelledError:
            logger.debug("MCP cleanup loop cancelled")
            raise
        except Exception as e:
            logger.error("Error in MCP cleanup loop", error=str(e))
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        return {
            "active_executions": len(self._execution_events),
            "execution_history_size": len(self._execution_history),
            "metrics_cache_size": len(self._metrics_cache),
            "alerts_cache_size": len(self._alerts_cache),
            "callbacks": {
                "execution_callbacks": len(self._execution_callbacks),
                "metrics_callbacks": len(self._metrics_callbacks),
                "alert_callbacks": len(self._alert_callbacks)
            },
            "tasks": {
                "metrics_task_running": self._metrics_task is not None and not self._metrics_task.done(),
                "cleanup_task_running": self._cleanup_task is not None and not self._cleanup_task.done()
            },
            "config": self.config
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop() 