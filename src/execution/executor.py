"""
执行器核心模块

实现企业级架构的执行链控制机制，包括：
- 执行链调度：Executor + Runtime 实现模块级调度闭环
- 分布式状态机调度机制
- 执行链控制核心：Executor + Runtime 实现模块级调度闭环
- 执行链与数据调用路径全解析
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import structlog

from ..state.context import ContextManager
from ..state.memory import MemoryManager
from ..core.tools import LocalToolRegistry
from .callbacks import CallbackHandler, CallbackType, CallbackResult

logger = structlog.get_logger(__name__)


class ExecutionStatus(Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class ExecutionStep:
    """执行步骤"""
    
    def __init__(
        self,
        step_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        dependencies: List[str] = None
    ):
        self.step_id = step_id
        self.tool_name = tool_name
        self.parameters = parameters
        self.dependencies = dependencies or []
        self.status = ExecutionStatus.PENDING
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.execution_time = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "step_id": self.step_id,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_time": self.execution_time
        }


class ExecutionChain:
    """执行链"""
    
    def __init__(self, chain_id: str, agent_id: str):
        self.chain_id = chain_id
        self.agent_id = agent_id
        self.steps: Dict[str, ExecutionStep] = {}
        self.execution_order: List[str] = []
        self.status = ExecutionStatus.PENDING
        self.context_id = None
        self.trace_id = None
        self.created_at = datetime.utcnow()
        self.completed_at = None
    
    def add_step(self, step: ExecutionStep) -> None:
        """添加执行步骤"""
        self.steps[step.step_id] = step
        self.execution_order.append(step.step_id)
    
    def get_ready_steps(self) -> List[ExecutionStep]:
        """获取可以执行的步骤"""
        ready_steps = []
        for step_id in self.execution_order:
            step = self.steps[step_id]
            if step.status == ExecutionStatus.PENDING:
                # 检查依赖是否完成
                dependencies_met = True
                for dep_id in step.dependencies:
                    if dep_id not in self.steps:
                        dependencies_met = False
                        break
                    if self.steps[dep_id].status != ExecutionStatus.COMPLETED:
                        dependencies_met = False
                        break
                
                if dependencies_met:
                    ready_steps.append(step)
        
        return ready_steps
    
    def is_completed(self) -> bool:
        """检查执行链是否完成"""
        return all(step.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED] 
                  for step in self.steps.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "chain_id": self.chain_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "context_id": self.context_id,
            "trace_id": self.trace_id,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "steps": {step_id: step.to_dict() for step_id, step in self.steps.items()},
            "execution_order": self.execution_order
        }


class Executor:
    """
    执行器核心
    
    实现企业级架构的执行链控制机制
    """
    
    def __init__(
        self,
        agent_id: str,
        tool_registry: LocalToolRegistry,
        context_manager: ContextManager,
        memory_manager: MemoryManager,
        callback_handler: CallbackHandler
    ):
        self.agent_id = agent_id
        self.tool_registry = tool_registry
        self.context_manager = context_manager
        self.memory_manager = memory_manager
        self.callback_handler = callback_handler
        
        # 执行链管理
        self.execution_chains: Dict[str, ExecutionChain] = {}
        self.active_chains: Dict[str, ExecutionChain] = {}
        
        # 执行配置
        self.execution_config = {
            "max_concurrent_steps": 5,
            "step_timeout": 30.0,
            "retry_attempts": 3,
            "enable_parallel_execution": True,
            "enable_step_monitoring": True
        }
        
        # 执行统计
        self.execution_stats = {
            "total_chains": 0,
            "completed_chains": 0,
            "failed_chains": 0,
            "total_steps": 0,
            "completed_steps": 0,
            "failed_steps": 0,
            "total_execution_time": 0.0
        }
        
        logger.info("Executor initialized", agent_id=agent_id)
    
    async def initialize(self) -> None:
        """初始化执行器"""
        try:
            logger.info("Initializing executor", agent_id=self.agent_id)
            
            # 初始化回调处理器
            await self.callback_handler.initialize()
            
            # 检查依赖组件
            if not await self._check_dependencies():
                raise RuntimeError("Dependencies check failed")
            
            logger.info("Executor initialized successfully", agent_id=self.agent_id)
            
        except Exception as e:
            logger.error("Failed to initialize executor", error=str(e))
            raise
    
    async def _check_dependencies(self) -> bool:
        """检查依赖组件"""
        try:
            # 检查工具注册表
            if not self.tool_registry:
                logger.error("Tool registry not available")
                return False
            
            # 检查上下文管理器
            if not self.context_manager:
                logger.error("Context manager not available")
                return False
            
            # 检查内存管理器
            if not self.memory_manager:
                logger.error("Memory manager not available")
                return False
            
            # 检查回调处理器
            if not await self.callback_handler.is_healthy():
                logger.error("Callback handler not healthy")
                return False
            
            return True
            
        except Exception as e:
            logger.error("Dependencies check failed", error=str(e))
            return False
    
    async def create_execution_chain(
        self,
        steps: List[Dict[str, Any]],
        context_id: str,
        trace_id: Optional[str] = None
    ) -> str:
        """
        创建执行链
        
        Args:
            steps: 执行步骤列表
            context_id: 上下文ID
            trace_id: 追踪ID
            
        Returns:
            执行链ID
        """
        chain_id = str(uuid.uuid4())
        chain = ExecutionChain(chain_id, self.agent_id)
        chain.context_id = context_id
        chain.trace_id = trace_id
        
        # 创建执行步骤
        for step_data in steps:
            step = ExecutionStep(
                step_id=step_data.get("step_id", str(uuid.uuid4())),
                tool_name=step_data["tool_name"],
                parameters=step_data.get("parameters", {}),
                dependencies=step_data.get("dependencies", [])
            )
            chain.add_step(step)
        
        self.execution_chains[chain_id] = chain
        self.execution_stats["total_chains"] += 1
        self.execution_stats["total_steps"] += len(steps)
        
        logger.info(
            "Execution chain created",
            chain_id=chain_id,
            context_id=context_id,
            steps_count=len(steps)
        )
        
        return chain_id
    
    async def execute_chain(self, chain_id: str) -> Dict[str, Any]:
        """
        执行执行链
        
        Args:
            chain_id: 执行链ID
            
        Returns:
            执行结果
        """
        if chain_id not in self.execution_chains:
            raise ValueError(f"Execution chain not found: {chain_id}")
        
        chain = self.execution_chains[chain_id]
        chain.status = ExecutionStatus.RUNNING
        self.active_chains[chain_id] = chain
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(
                "Starting execution chain",
                chain_id=chain_id,
                context_id=chain.context_id
            )
            
            # 执行回调：开始执行
            await self.callback_handler.handle_callback(
                CallbackType.SUCCESS,
                {
                    "event": "chain_started",
                    "chain_id": chain_id,
                    "context_id": chain.context_id
                },
                chain.context_id,
                chain.trace_id
            )
            
            # 执行步骤
            while not chain.is_completed():
                ready_steps = chain.get_ready_steps()
                
                if not ready_steps:
                    # 检查是否有死锁
                    if self._has_deadlock(chain):
                        raise RuntimeError("Execution deadlock detected")
                    break
                
                # 并行执行步骤
                if self.execution_config["enable_parallel_execution"]:
                    await self._execute_steps_parallel(ready_steps, chain)
                else:
                    await self._execute_steps_sequential(ready_steps, chain)
            
            # 检查执行结果
            if self._has_failed_steps(chain):
                chain.status = ExecutionStatus.FAILED
                self.execution_stats["failed_chains"] += 1
                
                await self.callback_handler.handle_callback(
                    CallbackType.ERROR,
                    {
                        "event": "chain_failed",
                        "chain_id": chain_id,
                        "context_id": chain.context_id
                    },
                    chain.context_id,
                    chain.trace_id
                )
            else:
                chain.status = ExecutionStatus.COMPLETED
                chain.completed_at = datetime.utcnow()
                self.execution_stats["completed_chains"] += 1
                
                await self.callback_handler.handle_callback(
                    CallbackType.SUCCESS,
                    {
                        "event": "chain_completed",
                        "chain_id": chain_id,
                        "context_id": chain.context_id
                    },
                    chain.context_id,
                    chain.trace_id
                )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            self.execution_stats["total_execution_time"] += execution_time
            
            logger.info(
                "Execution chain completed",
                chain_id=chain_id,
                status=chain.status.value,
                execution_time=execution_time
            )
            
            return chain.to_dict()
            
        except Exception as e:
            chain.status = ExecutionStatus.FAILED
            self.execution_stats["failed_chains"] += 1
            
            logger.error(
                "Execution chain failed",
                chain_id=chain_id,
                error=str(e)
            )
            
            await self.callback_handler.handle_callback(
                CallbackType.ERROR,
                {
                    "event": "chain_error",
                    "chain_id": chain_id,
                    "context_id": chain.context_id,
                    "error": str(e)
                },
                chain.context_id,
                chain.trace_id
            )
            
            raise
        
        finally:
            if chain_id in self.active_chains:
                del self.active_chains[chain_id]
    
    async def _execute_steps_parallel(self, steps: List[ExecutionStep], chain: ExecutionChain) -> None:
        """并行执行步骤"""
        tasks = []
        for step in steps:
            task = asyncio.create_task(self._execute_step(step, chain))
            tasks.append(task)
        
        # 等待所有步骤完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Step execution failed",
                    step_id=steps[i].step_id,
                    error=str(result)
                )
    
    async def _execute_steps_sequential(self, steps: List[ExecutionStep], chain: ExecutionChain) -> None:
        """顺序执行步骤"""
        for step in steps:
            await self._execute_step(step, chain)
    
    async def _execute_step(self, step: ExecutionStep, chain: ExecutionChain) -> None:
        """执行单个步骤"""
        step.status = ExecutionStatus.RUNNING
        step.start_time = datetime.utcnow()
        
        try:
            logger.debug(
                "Executing step",
                step_id=step.step_id,
                tool_name=step.tool_name,
                chain_id=chain.chain_id
            )
            
            # 获取工具
            tool = self.tool_registry.get_tool(step.tool_name)
            if not tool:
                raise ValueError(f"Tool not found: {step.tool_name}")
            
            # 执行工具
            result = await tool.execute(step.parameters)
            
            # 更新步骤状态
            step.status = ExecutionStatus.COMPLETED
            step.result = result
            self.execution_stats["completed_steps"] += 1
            
            # 写入内存
            await self.memory_manager.add_memory(
                content=f"Tool {step.tool_name} executed successfully: {result}",
                memory_type="tool_execution",
                context_id=chain.context_id,
                trace_id=chain.trace_id,
                metadata={
                    "step_id": step.step_id,
                    "tool_name": step.tool_name,
                    "chain_id": chain.chain_id
                }
            )
            
            # 执行回调
            await self.callback_handler.handle_callback(
                CallbackType.SUCCESS,
                {
                    "event": "step_completed",
                    "step_id": step.step_id,
                    "tool_name": step.tool_name,
                    "result": result,
                    "chain_id": chain.chain_id
                },
                chain.context_id,
                chain.trace_id
            )
            
        except Exception as e:
            step.status = ExecutionStatus.FAILED
            step.error = str(e)
            self.execution_stats["failed_steps"] += 1
            
            logger.error(
                "Step execution failed",
                step_id=step.step_id,
                tool_name=step.tool_name,
                error=str(e)
            )
            
            # 执行错误回调
            await self.callback_handler.handle_callback(
                CallbackType.ERROR,
                {
                    "event": "step_failed",
                    "step_id": step.step_id,
                    "tool_name": step.tool_name,
                    "error": str(e),
                    "chain_id": chain.chain_id
                },
                chain.context_id,
                chain.trace_id
            )
        
        finally:
            step.end_time = datetime.utcnow()
            if step.start_time and step.end_time:
                step.execution_time = (step.end_time - step.start_time).total_seconds()
    
    def _has_deadlock(self, chain: ExecutionChain) -> bool:
        """检查是否有死锁"""
        # 简单的死锁检测：检查是否有循环依赖
        visited = set()
        rec_stack = set()
        
        def has_cycle(step_id: str) -> bool:
            if step_id in rec_stack:
                return True
            if step_id in visited:
                return False
            
            visited.add(step_id)
            rec_stack.add(step_id)
            
            step = chain.steps[step_id]
            for dep_id in step.dependencies:
                if has_cycle(dep_id):
                    return True
            
            rec_stack.remove(step_id)
            return False
        
        for step_id in chain.steps:
            if has_cycle(step_id):
                return True
        
        return False
    
    def _has_failed_steps(self, chain: ExecutionChain) -> bool:
        """检查是否有失败的步骤"""
        return any(step.status == ExecutionStatus.FAILED for step in chain.steps.values())
    
    async def get_chain_status(self, chain_id: str) -> Optional[Dict[str, Any]]:
        """获取执行链状态"""
        if chain_id not in self.execution_chains:
            return None
        
        chain = self.execution_chains[chain_id]
        return chain.to_dict()
    
    async def cancel_chain(self, chain_id: str) -> bool:
        """取消执行链"""
        if chain_id not in self.active_chains:
            return False
        
        chain = self.active_chains[chain_id]
        chain.status = ExecutionStatus.CANCELLED
        
        logger.info("Execution chain cancelled", chain_id=chain_id)
        
        await self.callback_handler.handle_callback(
            CallbackType.INTERRUPT,
            {
                "event": "chain_cancelled",
                "chain_id": chain_id,
                "context_id": chain.context_id
            },
            chain.context_id,
            chain.trace_id
        )
        
        return True
    
    async def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return {
            "agent_id": self.agent_id,
            "total_chains": self.execution_stats["total_chains"],
            "completed_chains": self.execution_stats["completed_chains"],
            "failed_chains": self.execution_stats["failed_chains"],
            "total_steps": self.execution_stats["total_steps"],
            "completed_steps": self.execution_stats["completed_steps"],
            "failed_steps": self.execution_stats["failed_steps"],
            "total_execution_time": self.execution_stats["total_execution_time"],
            "active_chains": len(self.active_chains),
            "success_rate": (
                self.execution_stats["completed_chains"] / self.execution_stats["total_chains"]
                if self.execution_stats["total_chains"] > 0 else 0
            )
        } 