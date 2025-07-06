"""
MCP执行器集成

将MCP工具集成到现有执行器系统中，提供统一的工具执行接口
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import structlog

from .mcp_adapter import MCPAdapter
from .tool_wrapper import MCPToolWrapper
from .monitoring_integration import MCPMonitoringIntegration
from ..mcp_types import MCPResult

logger = structlog.get_logger(__name__)


class MCPExecutionResult:
    """MCP执行结果"""
    
    def __init__(
        self,
        execution_id: str,
        tool_name: str,
        server_name: str,
        success: bool,
        result: Any = None,
        error: str = None,
        duration: float = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.execution_id = execution_id
        self.tool_name = tool_name
        self.server_name = server_name
        self.success = success
        self.result = result
        self.error = error
        self.duration = duration
        self.metadata = metadata or {}
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "execution_id": self.execution_id,
            "tool_name": self.tool_name,
            "server_name": self.server_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "duration": self.duration,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class MCPExecutorIntegration:
    """MCP执行器集成"""
    
    def __init__(
        self,
        mcp_adapter: MCPAdapter,
        monitoring_integration: Optional[MCPMonitoringIntegration] = None,
        executor=None
    ):
        """
        初始化MCP执行器集成
        
        Args:
            mcp_adapter: MCP适配器
            monitoring_integration: 监控集成（可选）
            executor: 现有执行器实例（可选）
        """
        self.mcp_adapter = mcp_adapter
        self.monitoring_integration = monitoring_integration
        self.executor = executor
        
        # 执行配置
        self.config = {
            "enable_monitoring": True,
            "enable_timeout": True,
            "default_timeout": 60.0,  # 默认60秒超时
            "enable_retry": True,
            "default_retry_count": 2,
            "retry_delay": 1.0,  # 重试延迟
            "enable_caching": False,  # 结果缓存（暂不启用）
            "enable_parallel_execution": True
        }
        
        # 执行状态追踪
        self._active_executions: Dict[str, Dict[str, Any]] = {}
        self._execution_history: List[MCPExecutionResult] = []
        self._max_history_size = 10000
        
        # 回调函数
        self._pre_execution_callbacks: List[Callable] = []
        self._post_execution_callbacks: List[Callable] = []
        self._error_callbacks: List[Callable] = []
        
        logger.info("MCP executor integration initialized")
    
    async def execute_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None,
        retry_count: Optional[int] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> MCPExecutionResult:
        """
        执行MCP工具
        
        Args:
            tool_name: 工具名称
            arguments: 执行参数
            timeout: 超时时间（秒）
            retry_count: 重试次数
            user_context: 用户上下文
            
        Returns:
            执行结果
        """
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        
        # 使用配置的默认值
        if timeout is None:
            timeout = self.config["default_timeout"]
        if retry_count is None:
            retry_count = self.config["default_retry_count"]
        
        # 获取工具包装器
        tool_wrapper = await self.mcp_adapter.get_mcp_tool(tool_name)
        if not tool_wrapper:
            error_msg = f"MCP tool not found: {tool_name}"
            logger.error(error_msg)
            return MCPExecutionResult(
                execution_id=execution_id,
                tool_name=tool_name,
                server_name="unknown",
                success=False,
                error=error_msg,
                duration=time.time() - start_time
            )
        
        server_name = tool_wrapper.server_name
        
        # 记录执行开始
        execution_info = {
            "execution_id": execution_id,
            "tool_name": tool_name,
            "server_name": server_name,
            "arguments": arguments,
            "start_time": start_time,
            "timeout": timeout,
            "retry_count": retry_count,
            "user_context": user_context
        }
        self._active_executions[execution_id] = execution_info
        
        # 开始监控追踪
        monitoring_execution_id = None
        if self.monitoring_integration and self.config["enable_monitoring"]:
            monitoring_execution_id = await self.monitoring_integration.track_execution(
                tool_name, server_name, arguments, user_context
            )
        
        try:
            # 执行前回调
            await self._trigger_pre_execution_callbacks(execution_info)
            
            # 执行工具（带重试机制）
            result = await self._execute_with_retry(
                tool_wrapper, arguments, timeout, retry_count
            )
            
            # 创建成功结果
            execution_result = MCPExecutionResult(
                execution_id=execution_id,
                tool_name=tool_name,
                server_name=server_name,
                success=True,
                result=result,
                duration=time.time() - start_time,
                metadata={
                    "retry_attempts": 0,  # 这里简化，实际应该记录真实重试次数
                    "timeout": timeout,
                    "user_context": user_context
                }
            )
            
            logger.info(
                "MCP tool executed successfully",
                execution_id=execution_id,
                tool_name=tool_name,
                server_name=server_name,
                duration=execution_result.duration
            )
            
        except Exception as e:
            # 创建失败结果
            execution_result = MCPExecutionResult(
                execution_id=execution_id,
                tool_name=tool_name,
                server_name=server_name,
                success=False,
                error=str(e),
                duration=time.time() - start_time,
                metadata={
                    "timeout": timeout,
                    "user_context": user_context
                }
            )
            
            logger.error(
                "MCP tool execution failed",
                execution_id=execution_id,
                tool_name=tool_name,
                server_name=server_name,
                error=str(e),
                duration=execution_result.duration
            )
            
            # 错误回调
            await self._trigger_error_callbacks(execution_info, e)
        
        finally:
            # 清理活跃执行记录
            if execution_id in self._active_executions:
                del self._active_executions[execution_id]
            
            # 添加到历史记录
            self._execution_history.append(execution_result)
            
            # 限制历史记录大小
            if len(self._execution_history) > self._max_history_size:
                self._execution_history = self._execution_history[-self._max_history_size:]
            
            # 完成监控追踪
            if monitoring_execution_id and self.monitoring_integration:
                await self.monitoring_integration.complete_execution(
                    monitoring_execution_id,
                    execution_result.success,
                    execution_result.result,
                    execution_result.error
                )
            
            # 执行后回调
            await self._trigger_post_execution_callbacks(execution_info, execution_result)
        
        return execution_result
    
    async def execute_mcp_tools_batch(
        self,
        tool_requests: List[Dict[str, Any]],
        max_concurrent: Optional[int] = None,
        timeout: Optional[float] = None
    ) -> List[MCPExecutionResult]:
        """
        批量执行MCP工具
        
        Args:
            tool_requests: 工具请求列表，每个包含tool_name, arguments等
            max_concurrent: 最大并发数
            timeout: 总超时时间
            
        Returns:
            执行结果列表
        """
        if not self.config["enable_parallel_execution"]:
            # 串行执行
            results = []
            for request in tool_requests:
                result = await self.execute_mcp_tool(
                    tool_name=request["tool_name"],
                    arguments=request.get("arguments", {}),
                    timeout=request.get("timeout", timeout),
                    retry_count=request.get("retry_count"),
                    user_context=request.get("user_context")
                )
                results.append(result)
            return results
        
        # 并行执行
        max_concurrent = max_concurrent or 5
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_single(request: Dict[str, Any]) -> MCPExecutionResult:
            async with semaphore:
                return await self.execute_mcp_tool(
                    tool_name=request["tool_name"],
                    arguments=request.get("arguments", {}),
                    timeout=request.get("timeout", timeout),
                    retry_count=request.get("retry_count"),
                    user_context=request.get("user_context")
                )
        
        # 创建并发任务
        tasks = [execute_single(request) for request in tool_requests]
        
        try:
            if timeout:
                # 带总超时的并发执行
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout
                )
            else:
                # 无总超时的并发执行
                results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # 创建错误结果
                    request = tool_requests[i]
                    error_result = MCPExecutionResult(
                        execution_id=str(uuid.uuid4()),
                        tool_name=request["tool_name"],
                        server_name="unknown",
                        success=False,
                        error=str(result),
                        duration=0.0
                    )
                    processed_results.append(error_result)
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except asyncio.TimeoutError:
            logger.error("Batch execution timed out", timeout=timeout)
            # 创建超时错误结果
            return [
                MCPExecutionResult(
                    execution_id=str(uuid.uuid4()),
                    tool_name=request["tool_name"],
                    server_name="unknown",
                    success=False,
                    error="Batch execution timeout",
                    duration=timeout or 0.0
                )
                for request in tool_requests
            ]
    
    async def _execute_with_retry(
        self,
        tool_wrapper: MCPToolWrapper,
        arguments: Dict[str, Any],
        timeout: float,
        retry_count: int
    ) -> Any:
        """
        带重试机制的执行
        
        Args:
            tool_wrapper: 工具包装器
            arguments: 执行参数
            timeout: 超时时间
            retry_count: 重试次数
            
        Returns:
            执行结果
        """
        last_error = None
        
        for attempt in range(retry_count + 1):
            try:
                if self.config["enable_timeout"]:
                    # 带超时的执行
                    result = await asyncio.wait_for(
                        tool_wrapper.execute(**arguments),
                        timeout=timeout
                    )
                else:
                    # 无超时的执行
                    result = await tool_wrapper.execute(**arguments)
                
                return result
                
            except asyncio.TimeoutError as e:
                last_error = f"Execution timeout after {timeout}s"
                logger.warning(
                    "MCP tool execution timeout",
                    tool_name=tool_wrapper.name,
                    attempt=attempt + 1,
                    timeout=timeout
                )
                
                if attempt < retry_count:
                    await asyncio.sleep(self.config["retry_delay"])
                
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "MCP tool execution error",
                    tool_name=tool_wrapper.name,
                    attempt=attempt + 1,
                    error=str(e)
                )
                
                if attempt < retry_count:
                    await asyncio.sleep(self.config["retry_delay"])
        
        # 所有重试都失败
        raise RuntimeError(f"Execution failed after {retry_count + 1} attempts: {last_error}")
    
    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取执行状态
        
        Args:
            execution_id: 执行ID
            
        Returns:
            执行状态信息
        """
        # 检查活跃执行
        if execution_id in self._active_executions:
            return {
                "status": "running",
                **self._active_executions[execution_id]
            }
        
        # 检查历史记录
        for result in reversed(self._execution_history):
            if result.execution_id == execution_id:
                return {
                    "status": "completed" if result.success else "failed",
                    **result.to_dict()
                }
        
        return None
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """
        取消执行
        
        Args:
            execution_id: 执行ID
            
        Returns:
            取消是否成功
        """
        if execution_id in self._active_executions:
            # 这里简化实现，实际需要更复杂的取消机制
            execution_info = self._active_executions[execution_id]
            
            # 创建取消结果
            cancel_result = MCPExecutionResult(
                execution_id=execution_id,
                tool_name=execution_info["tool_name"],
                server_name=execution_info["server_name"],
                success=False,
                error="Execution cancelled",
                duration=time.time() - execution_info["start_time"]
            )
            
            # 移除活跃执行
            del self._active_executions[execution_id]
            
            # 添加到历史记录
            self._execution_history.append(cancel_result)
            
            logger.info("Execution cancelled", execution_id=execution_id)
            return True
        
        return False
    
    async def list_active_executions(self) -> List[Dict[str, Any]]:
        """列出活跃执行"""
        return [
            {
                "status": "running",
                "elapsed_time": time.time() - info["start_time"],
                **info
            }
            for info in self._active_executions.values()
        ]
    
    async def get_execution_history(
        self,
        limit: Optional[int] = None,
        tool_name: Optional[str] = None,
        server_name: Optional[str] = None,
        success_only: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        获取执行历史
        
        Args:
            limit: 限制返回数量
            tool_name: 过滤工具名称
            server_name: 过滤服务器名称
            success_only: 只返回成功的执行
            
        Returns:
            执行历史列表
        """
        history = self._execution_history
        
        # 过滤
        if tool_name:
            history = [r for r in history if r.tool_name == tool_name]
        if server_name:
            history = [r for r in history if r.server_name == server_name]
        if success_only is not None:
            history = [r for r in history if r.success == success_only]
        
        # 排序（最新在前）
        history = sorted(history, key=lambda r: r.timestamp, reverse=True)
        
        # 限制数量
        if limit:
            history = history[:limit]
        
        return [result.to_dict() for result in history]
    
    def add_pre_execution_callback(self, callback: Callable) -> None:
        """添加执行前回调"""
        self._pre_execution_callbacks.append(callback)
    
    def add_post_execution_callback(self, callback: Callable) -> None:
        """添加执行后回调"""
        self._post_execution_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable) -> None:
        """添加错误回调"""
        self._error_callbacks.append(callback)
    
    async def _trigger_pre_execution_callbacks(self, execution_info: Dict[str, Any]) -> None:
        """触发执行前回调"""
        for callback in self._pre_execution_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(execution_info)
                else:
                    callback(execution_info)
            except Exception as e:
                logger.error("Error in pre-execution callback", error=str(e))
    
    async def _trigger_post_execution_callbacks(
        self,
        execution_info: Dict[str, Any],
        result: MCPExecutionResult
    ) -> None:
        """触发执行后回调"""
        for callback in self._post_execution_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(execution_info, result)
                else:
                    callback(execution_info, result)
            except Exception as e:
                logger.error("Error in post-execution callback", error=str(e))
    
    async def _trigger_error_callbacks(
        self,
        execution_info: Dict[str, Any],
        error: Exception
    ) -> None:
        """触发错误回调"""
        for callback in self._error_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(execution_info, error)
                else:
                    callback(execution_info, error)
            except Exception as e:
                logger.error("Error in error callback", error=str(e))
    
    async def get_integration_stats(self) -> Dict[str, Any]:
        """获取集成统计信息"""
        total_executions = len(self._execution_history)
        successful_executions = sum(1 for r in self._execution_history if r.success)
        failed_executions = total_executions - successful_executions
        
        # 计算平均执行时间
        durations = [r.duration for r in self._execution_history if r.duration]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "active_executions": len(self._active_executions),
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": successful_executions / max(1, total_executions),
            "average_duration": avg_duration,
            "config": self.config,
            "callbacks": {
                "pre_execution": len(self._pre_execution_callbacks),
                "post_execution": len(self._post_execution_callbacks),
                "error": len(self._error_callbacks)
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查MCP适配器健康状态
            adapter_health = await self.mcp_adapter.health_check()
            
            # 检查监控集成（如果存在）
            monitoring_health = "not_configured"
            if self.monitoring_integration:
                monitoring_stats = self.monitoring_integration.get_monitoring_stats()
                monitoring_health = "healthy" if monitoring_stats else "error"
            
            # 检查执行器（如果存在）
            executor_health = "not_configured"
            if self.executor:
                try:
                    if hasattr(self.executor, 'get_execution_stats'):
                        await self.executor.get_execution_stats()
                        executor_health = "healthy"
                except Exception:
                    executor_health = "error"
            
            return {
                "status": "healthy",
                "adapter_health": adapter_health,
                "monitoring_health": monitoring_health,
                "executor_health": executor_health,
                "active_executions": len(self._active_executions),
                "integration_stats": await self.get_integration_stats()
            }
            
        except Exception as e:
            logger.error("Error during health check", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        # 取消所有活跃执行
        for execution_id in list(self._active_executions.keys()):
            await self.cancel_execution(execution_id) 