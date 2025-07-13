"""
推理引擎

提供统一的推理接口，支持多种推理策略：
- LLM推理
- 规则推理
- 强化学习推理
- 混合推理
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum

import structlog
from pydantic import BaseModel

from .llm_reasoner import LLMReasoner
from .rule_reasoner import RuleReasoner
from .rl_reasoner import RLReasoner


logger = structlog.get_logger(__name__)


class ReasoningStrategy(Enum):
    """推理策略枚举"""
    LLM = "llm"
    RULE = "rule"
    RL = "rl"
    HYBRID = "hybrid"


class ReasoningResult(BaseModel):
    """推理结果模型"""
    action: str
    parameters: Dict[str, Any] = {}
    confidence: float = 0.0
    reasoning: str = ""
    strategy: str = ""
    metadata: Dict[str, Any] = {}


class ReasoningEngine:
    """
    推理引擎
    
    提供统一的推理接口，支持多种推理策略的切换和组合
    """
    
    def __init__(
        self,
        model: str = "gpt-4",
        max_tokens: int = 4000,
        temperature: float = 0.7,
        strategy: ReasoningStrategy = ReasoningStrategy.LLM,
        fallback_strategy: ReasoningStrategy = ReasoningStrategy.RULE
    ):
        """
        初始化推理引擎
        
        Args:
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度参数
            strategy: 主要推理策略
            fallback_strategy: 备用推理策略
        """
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.strategy = strategy
        self.fallback_strategy = fallback_strategy
        
        # 初始化各种推理器
        self.llm_reasoner = LLMReasoner(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        self.rule_reasoner = RuleReasoner()
        self.rl_reasoner = RLReasoner()
        
        # 统计信息
        self.stats = {
            "total_reasoning_calls": 0,
            "successful_reasoning": 0,
            "failed_reasoning": 0,
            "strategy_usage": {
                "llm": 0,
                "rule": 0,
                "rl": 0,
                "hybrid": 0
            }
        }
        
        logger.info(
            "Reasoning engine initialized",
            model=model,
            strategy=strategy.value,
            fallback_strategy=fallback_strategy.value
        )
    
    async def reason(
        self,
        task: str,
        context: List[Dict[str, Any]] = None,
        memory: List[Dict[str, Any]] = None,
        available_tools: List[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行推理
        
        Args:
            task: 任务描述
            context: 上下文信息
            memory: 内存信息
            available_tools: 可用工具列表
            **kwargs: 额外参数
            
        Returns:
            推理结果
        """
        self.stats["total_reasoning_calls"] += 1
        
        try:
            # 构建推理上下文
            reasoning_context = self._build_reasoning_context(task, context, memory, available_tools)
            
            # 根据策略选择推理器
            if self.strategy == ReasoningStrategy.LLM:
                result = await self._reason_with_llm(reasoning_context, **kwargs)
            elif self.strategy == ReasoningStrategy.RULE:
                result = await self._reason_with_rule(reasoning_context, **kwargs)
            elif self.strategy == ReasoningStrategy.RL:
                result = await self._reason_with_rl(reasoning_context, **kwargs)
            elif self.strategy == ReasoningStrategy.HYBRID:
                result = await self._reason_with_hybrid(reasoning_context, **kwargs)
            else:
                raise ValueError(f"不支持的推理策略: {self.strategy}")
            
            self.stats["successful_reasoning"] += 1
            self.stats["strategy_usage"][self.strategy.value] += 1
            
            logger.debug(
                "Reasoning completed successfully",
                strategy=self.strategy.value,
                task=task,
                action=result.get("action")
            )
            
            return result
            
        except Exception as e:
            self.stats["failed_reasoning"] += 1
            
            logger.warning(
                "Primary reasoning strategy failed, trying fallback",
                strategy=self.strategy.value,
                fallback_strategy=self.fallback_strategy.value,
                error=str(e)
            )
            
            # 尝试备用策略
            try:
                return await self._reason_with_fallback(task, context, memory, available_tools, **kwargs)
            except Exception as e2:
                logger.error("Fallback reasoning also failed", error=str(e2))
                # 始终返回 dict
                return {"action": {"type": "respond", "parameters": {"response": f"推理失败: {str(e2)}"}}}
    
    def _build_reasoning_context(
        self,
        task: str,
        context: List[Dict[str, Any]] = None,
        memory: List[Dict[str, Any]] = None,
        available_tools: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        构建推理上下文
        
        Args:
            task: 任务描述
            context: 上下文信息
            memory: 内存信息
            available_tools: 可用工具列表
            
        Returns:
            推理上下文
        """
        reasoning_context = {
            "task": task,
            "context": context or [],
            "memory": memory or [],
            "available_tools": available_tools or [],
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # 构建提示词
        prompt = self._build_prompt(task, context, memory, available_tools)
        reasoning_context["prompt"] = prompt
        
        return reasoning_context
    
    def _build_prompt(
        self,
        task: str,
        context: List[Dict[str, Any]] = None,
        memory: List[Dict[str, Any]] = None,
        available_tools: List[Dict[str, Any]] = None
    ) -> str:
        """
        构建推理提示词
        
        Args:
            task: 任务描述
            context: 上下文信息
            memory: 内存信息
            available_tools: 可用工具列表
            
        Returns:
            提示词
        """
        prompt_parts = []
        
        # 添加任务
        prompt_parts.append(f"任务: {task}")
        
        # 添加上下文
        if context:
            prompt_parts.append("\n上下文:")
            for ctx in context:
                prompt_parts.append(f"- {ctx.get('content', str(ctx))}")
        
        # 添加内存
        if memory:
            prompt_parts.append("\n相关记忆:")
            for mem in memory:
                prompt_parts.append(f"- {mem.get('content', str(mem))}")
        
        # 添加可用工具
        if available_tools:
            prompt_parts.append("\n可用工具:")
            for tool in available_tools:
                tool_name = tool.get('name', 'unknown')
                tool_desc = tool.get('description', '')
                prompt_parts.append(f"- {tool_name}: {tool_desc}")
        
        # 添加推理指令
        prompt_parts.append("\n请根据上述信息进行推理，并选择最合适的行动。")
        
        return "\n".join(prompt_parts)
    
    async def _reason_with_llm(
        self,
        reasoning_context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """使用LLM进行推理"""
        return await self.llm_reasoner.reason(
            reasoning_context["prompt"],
            reasoning_context["context"],
            reasoning_context["available_tools"],
            **kwargs
        )
    
    async def _reason_with_rule(
        self,
        reasoning_context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """使用规则进行推理"""
        return await self.rule_reasoner.reason(
            reasoning_context["prompt"],
            reasoning_context["context"],
            reasoning_context["available_tools"],
            **kwargs
        )
    
    async def _reason_with_rl(
        self,
        reasoning_context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """使用强化学习进行推理"""
        return await self.rl_reasoner.reason(
            reasoning_context["prompt"],
            reasoning_context["context"],
            reasoning_context["available_tools"],
            **kwargs
        )
    
    async def _reason_with_hybrid(
        self,
        reasoning_context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """使用混合策略进行推理"""
        try:
            # 首先尝试LLM推理
            llm_result = await self._reason_with_llm(reasoning_context, **kwargs)
            
            # 如果LLM推理成功且置信度高，直接返回
            if llm_result.get("confidence", 0) > 0.7:
                return llm_result
            
            # 否则使用规则推理进行验证
            rule_result = await self._reason_with_rule(reasoning_context, **kwargs)
            
            # 比较两种结果，选择更合适的
            if llm_result.get("confidence", 0) > rule_result.get("confidence", 0):
                return llm_result
            else:
                return rule_result
                
        except Exception as e:
            logger.warning("Hybrid reasoning failed, falling back to rule-based", error=str(e))
            return await self._reason_with_rule(reasoning_context, **kwargs)
    
    async def _reason_with_fallback(
        self,
        task: str,
        context: List[Dict[str, Any]] = None,
        memory: List[Dict[str, Any]] = None,
        available_tools: List[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """使用备用策略进行推理"""
        try:
            reasoning_context = self._build_reasoning_context(task, context, memory, available_tools)
            
            if self.fallback_strategy == ReasoningStrategy.LLM:
                result = await self._reason_with_llm(reasoning_context, **kwargs)
            elif self.fallback_strategy == ReasoningStrategy.RULE:
                result = await self._reason_with_rule(reasoning_context, **kwargs)
            elif self.fallback_strategy == ReasoningStrategy.RL:
                result = await self._reason_with_rl(reasoning_context, **kwargs)
            elif self.fallback_strategy == ReasoningStrategy.HYBRID:
                result = await self._reason_with_hybrid(reasoning_context, **kwargs)
            else:
                raise ValueError(f"不支持的备用推理策略: {self.fallback_strategy}")
            
            self.stats["strategy_usage"][self.fallback_strategy.value] += 1
            
            return result
            
        except Exception as e:
            logger.error("Fallback reasoning also failed", error=str(e))
            
            # 始终返回 dict
            return {"action": {"type": "respond", "parameters": {"response": f"推理失败: {str(e)}"}}}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_reasoning"] / self.stats["total_reasoning_calls"]
                if self.stats["total_reasoning_calls"] > 0 else 0
            )
        }
    
    def update_strategy(self, strategy: ReasoningStrategy) -> None:
        """更新推理策略"""
        self.strategy = strategy
        logger.info("Reasoning strategy updated", new_strategy=strategy.value)
    
    def update_fallback_strategy(self, fallback_strategy: ReasoningStrategy) -> None:
        """更新备用推理策略"""
        self.fallback_strategy = fallback_strategy
        logger.info("Fallback reasoning strategy updated", new_fallback_strategy=fallback_strategy.value)
    
    async def initialize(self) -> None:
        """初始化推理引擎"""
        try:
            logger.info("Initializing reasoning engine")
            
            # 初始化各种推理器
            await self.llm_reasoner.initialize()
            await self.rule_reasoner.initialize()
            await self.rl_reasoner.initialize()
            
            logger.info("Reasoning engine initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize reasoning engine", error=str(e))
            raise
    
    async def is_healthy(self) -> bool:
        """检查推理引擎健康状态"""
        try:
            # 检查各种推理器是否健康
            llm_healthy = await self.llm_reasoner.is_healthy()
            rule_healthy = await self.rule_reasoner.is_healthy()
            rl_healthy = await self.rl_reasoner.is_healthy()
            
            return all([llm_healthy, rule_healthy, rl_healthy])
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False 