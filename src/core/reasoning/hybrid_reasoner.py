"""
混合推理器

组合多种推理策略，支持：
- 策略融合
- 权重调整
- 动态选择
- 结果聚合
"""

import asyncio
from typing import Any, Dict, List, Optional
from enum import Enum
import structlog

from .llm_reasoner import LLMReasoner
from .rule_reasoner import RuleReasoner
from .rl_reasoner import RLReasoner


logger = structlog.get_logger(__name__)


class FusionStrategy(Enum):
    """融合策略枚举"""
    WEIGHTED_AVERAGE = "weighted_average"
    VOTING = "voting"
    CONFIDENCE_BASED = "confidence_based"
    ENSEMBLE = "ensemble"


class HybridReasoner:
    """
    混合推理器
    
    组合多种推理策略，提供更可靠的推理结果
    """
    
    def __init__(
        self,
        fusion_strategy: FusionStrategy = FusionStrategy.CONFIDENCE_BASED,
        weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化混合推理器
        
        Args:
            fusion_strategy: 融合策略
            weights: 各推理器的权重
        """
        self.fusion_strategy = fusion_strategy
        
        # 默认权重
        self.weights = weights or {
            "llm": 0.5,
            "rule": 0.3,
            "rl": 0.2
        }
        
        # 初始化各种推理器
        self.llm_reasoner = LLMReasoner()
        self.rule_reasoner = RuleReasoner()
        self.rl_reasoner = RLReasoner()
        
        # 统计信息
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "strategy_usage": {
                "llm": 0,
                "rule": 0,
                "rl": 0,
                "hybrid": 0
            }
        }
        
        logger.info(
            "Hybrid reasoner initialized",
            fusion_strategy=fusion_strategy.value,
            weights=self.weights
        )
    
    async def reason(
        self,
        task: str,
        context: List[Dict[str, Any]] = None,
        available_tools: List[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        使用混合策略进行推理
        
        Args:
            task: 任务描述
            context: 上下文信息
            available_tools: 可用工具列表
            **kwargs: 额外参数
            
        Returns:
            推理结果
        """
        self.stats["total_calls"] += 1
        
        try:
            # 并行执行多种推理策略
            results = await self._execute_all_reasoners(task, context, available_tools, **kwargs)
            
            # 融合结果
            final_result = self._fuse_results(results)
            
            self.stats["successful_calls"] += 1
            self.stats["strategy_usage"]["hybrid"] += 1
            
            logger.debug(
                "Hybrid reasoning completed",
                task=task,
                action=final_result.get("action"),
                confidence=final_result.get("confidence")
            )
            
            return final_result
            
        except Exception as e:
            self.stats["failed_calls"] += 1
            
            logger.error(
                "Hybrid reasoning failed",
                task=task,
                error=str(e)
            )
            
            # 返回默认响应
            return {
                "action": "respond",
                "parameters": {
                    "response": f"我理解您的任务：{task}。我正在处理中。"
                },
                "confidence": 0.4,
                "reasoning": f"混合推理失败，使用默认响应: {str(e)}",
                "strategy": "hybrid"
            }
    
    async def _execute_all_reasoners(
        self,
        task: str,
        context: List[Dict[str, Any]] = None,
        available_tools: List[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Dict[str, Any]]:
        """
        执行所有推理器
        
        Args:
            task: 任务描述
            context: 上下文信息
            available_tools: 可用工具列表
            **kwargs: 额外参数
            
        Returns:
            各推理器的结果
        """
        # 并行执行
        tasks = [
            self.llm_reasoner.reason(task, context, available_tools, **kwargs),
            self.rule_reasoner.reason(task, context, available_tools, **kwargs),
            self.rl_reasoner.reason(task, context, available_tools, **kwargs)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        reasoner_results = {}
        
        for i, (reasoner_name, result) in enumerate([
            ("llm", results[0]),
            ("rule", results[1]),
            ("rl", results[2])
        ]):
            if isinstance(result, Exception):
                logger.warning(
                    f"{reasoner_name} reasoner failed",
                    error=str(result)
                )
                # 使用默认结果
                reasoner_results[reasoner_name] = {
                    "action": "respond",
                    "parameters": {"response": "推理失败"},
                    "confidence": 0.0,
                    "reasoning": f"{reasoner_name}推理器失败",
                    "strategy": reasoner_name
                }
            else:
                reasoner_results[reasoner_name] = result
                self.stats["strategy_usage"][reasoner_name] += 1
        
        return reasoner_results
    
    def _fuse_results(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        融合结果
        
        Args:
            results: 各推理器的结果
            
        Returns:
            融合后的结果
        """
        if self.fusion_strategy == FusionStrategy.WEIGHTED_AVERAGE:
            return self._weighted_average_fusion(results)
        elif self.fusion_strategy == FusionStrategy.VOTING:
            return self._voting_fusion(results)
        elif self.fusion_strategy == FusionStrategy.CONFIDENCE_BASED:
            return self._confidence_based_fusion(results)
        elif self.fusion_strategy == FusionStrategy.ENSEMBLE:
            return self._ensemble_fusion(results)
        else:
            raise ValueError(f"不支持的融合策略: {self.fusion_strategy}")
    
    def _weighted_average_fusion(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """加权平均融合"""
        # 按动作分组
        action_groups = {}
        
        for reasoner_name, result in results.items():
            action = result.get("action", "respond")
            confidence = result.get("confidence", 0.0)
            weight = self.weights.get(reasoner_name, 0.0)
            
            if action not in action_groups:
                action_groups[action] = {
                    "total_weight": 0.0,
                    "weighted_confidence": 0.0,
                    "reasoners": []
                }
            
            action_groups[action]["total_weight"] += weight
            action_groups[action]["weighted_confidence"] += confidence * weight
            action_groups[action]["reasoners"].append(reasoner_name)
        
        # 选择加权置信度最高的动作
        best_action = max(
            action_groups.items(),
            key=lambda x: x[1]["weighted_confidence"]
        )
        
        action_name, action_data = best_action
        
        # 计算平均置信度
        avg_confidence = (
            action_data["weighted_confidence"] / action_data["total_weight"]
            if action_data["total_weight"] > 0 else 0.0
        )
        
        # 合并参数
        merged_parameters = self._merge_parameters(
            [results[r] for r in action_data["reasoners"]]
        )
        
        return {
            "action": action_name,
            "parameters": merged_parameters,
            "confidence": avg_confidence,
            "reasoning": f"加权平均融合: {', '.join(action_data['reasoners'])}",
            "strategy": "hybrid"
        }
    
    def _voting_fusion(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """投票融合"""
        # 统计各动作的投票数
        action_votes = {}
        
        for reasoner_name, result in results.items():
            action = result.get("action", "respond")
            weight = self.weights.get(reasoner_name, 0.0)
            
            if action not in action_votes:
                action_votes[action] = {
                    "votes": 0.0,
                    "reasoners": [],
                    "results": []
                }
            
            action_votes[action]["votes"] += weight
            action_votes[action]["reasoners"].append(reasoner_name)
            action_votes[action]["results"].append(result)
        
        # 选择得票最多的动作
        best_action = max(
            action_votes.items(),
            key=lambda x: x[1]["votes"]
        )
        
        action_name, action_data = best_action
        
        # 计算平均置信度
        avg_confidence = sum(
            r.get("confidence", 0.0) for r in action_data["results"]
        ) / len(action_data["results"])
        
        # 合并参数
        merged_parameters = self._merge_parameters(action_data["results"])
        
        return {
            "action": action_name,
            "parameters": merged_parameters,
            "confidence": avg_confidence,
            "reasoning": f"投票融合: {', '.join(action_data['reasoners'])}",
            "strategy": "hybrid"
        }
    
    def _confidence_based_fusion(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """基于置信度的融合"""
        # 选择置信度最高的结果
        best_result = max(
            results.items(),
            key=lambda x: x[1].get("confidence", 0.0)
        )
        
        reasoner_name, result = best_result
        
        return {
            **result,
            "reasoning": f"置信度融合: 选择{reasoner_name}推理器结果",
            "strategy": "hybrid"
        }
    
    def _ensemble_fusion(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """集成融合"""
        # 统计各动作的出现次数
        action_counts = {}
        
        for result in results.values():
            action = result.get("action", "respond")
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # 选择出现次数最多的动作
        most_common_action = max(
            action_counts.items(),
            key=lambda x: x[1]
        )[0]
        
        # 收集该动作的所有结果
        action_results = [
            result for result in results.values()
            if result.get("action") == most_common_action
        ]
        
        # 计算平均置信度
        avg_confidence = sum(
            r.get("confidence", 0.0) for r in action_results
        ) / len(action_results)
        
        # 合并参数
        merged_parameters = self._merge_parameters(action_results)
        
        return {
            "action": most_common_action,
            "parameters": merged_parameters,
            "confidence": avg_confidence,
            "reasoning": f"集成融合: {most_common_action}获得最多支持",
            "strategy": "hybrid"
        }
    
    def _merge_parameters(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并参数
        
        Args:
            results: 结果列表
            
        Returns:
            合并后的参数
        """
        if not results:
            return {}
        
        # 简单合并策略：使用第一个非空参数
        for result in results:
            parameters = result.get("parameters", {})
            if parameters:
                return parameters
        
        return {}
    
    def update_weights(self, weights: Dict[str, float]) -> None:
        """
        更新权重
        
        Args:
            weights: 新的权重
        """
        self.weights.update(weights)
        logger.info("Hybrid reasoner weights updated", weights=self.weights)
    
    def update_fusion_strategy(self, strategy: FusionStrategy) -> None:
        """
        更新融合策略
        
        Args:
            strategy: 新的融合策略
        """
        self.fusion_strategy = strategy
        logger.info("Fusion strategy updated", strategy=strategy.value)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_calls"] / self.stats["total_calls"]
                if self.stats["total_calls"] > 0 else 0
            ),
            "fusion_strategy": self.fusion_strategy.value,
            "weights": self.weights
        } 