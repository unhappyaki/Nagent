"""
增强意图识别演示

演示如何在现有BIR路由器基础上集成多种意图识别技术：
1. 基于BERT的深度学习分类
2. 基于LLM的语义理解
3. 上下文感知意图识别
4. 集成多种分类器的统一引擎
"""

import asyncio
import sys
from pathlib import Path
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.communication.dispatcher.bir_router import BIRRouter, IntentType
from src.monitoring.tracing.trace_writer import TraceWriter


class EnhancedIntentType(Enum):
    """增强的意图类型枚举"""
    # 原有意图类型
    TASK_EXECUTION = "task_execution"
    DATA_QUERY = "data_query"
    TOOL_CALL = "tool_call"
    STATUS_UPDATE = "status_update"
    COLLABORATION = "collaboration"
    
    # 新增意图类型
    DOCUMENT_GENERATION = "document_generation"
    DATA_ANALYSIS = "data_analysis"
    REPORT_CREATION = "report_creation"
    INFORMATION_REQUEST = "information_request"
    WORKFLOW_MANAGEMENT = "workflow_management"
    SYSTEM_CONTROL = "system_control"
    API_INVOCATION = "api_invocation"
    CONTENT_CREATION = "content_creation"
    AUTOMATION_SETUP = "automation_setup"
    TROUBLESHOOTING = "troubleshooting"


@dataclass
class IntentResult:
    """意图识别结果"""
    intent_type: str
    confidence: float
    method: str
    reasoning: str = ""
    keywords: List[str] = None
    entities: Dict[str, str] = None
    uncertainty: float = 0.0
    needs_feedback: bool = False
    context_boost: bool = False


class SimpleMLIntentClassifier:
    """简化的机器学习意图分类器"""
    
    def __init__(self):
        self.intent_patterns = {
            "document_generation": {
                "keywords": ["生成", "创建", "制作", "编写", "文档", "报告"],
                "weight": 1.0
            },
            "data_analysis": {
                "keywords": ["分析", "统计", "计算", "数据", "趋势"],
                "weight": 1.0
            },
            "data_query": {
                "keywords": ["查询", "搜索", "获取", "查找", "检索"],
                "weight": 0.9
            },
            "information_request": {
                "keywords": ["什么", "如何", "为什么", "解释", "说明"],
                "weight": 0.8
            }
        }
        self.confidence_threshold = 0.7
        
    async def predict_intent(self, text: str, context: Dict[str, Any] = None) -> IntentResult:
        """预测意图"""
        text_lower = text.lower()
        scores = {}
        
        for intent_type, pattern in self.intent_patterns.items():
            keyword_matches = sum(1 for word in pattern["keywords"] if word in text_lower)
            score = (keyword_matches / len(pattern["keywords"])) * pattern["weight"]
            scores[intent_type] = score
        
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        confidence = min(best_score, 1.0)
        
        keywords = [word for word in self.intent_patterns[best_intent]["keywords"] 
                   if word in text_lower]
        
        return IntentResult(
            intent_type=best_intent,
            confidence=confidence,
            method="ml_classification",
            reasoning=f"关键词匹配得分: {best_score:.3f}",
            keywords=keywords,
            uncertainty=1.0 - confidence,
            needs_feedback=confidence < self.confidence_threshold
        )


class ContextAwareIntentClassifier:
    """上下文感知意图分类器"""
    
    def __init__(self, base_classifier):
        self.base_classifier = base_classifier
        self.conversation_history = {}
        self.context_weight = 0.3
        
    async def predict_intent(self, text: str, context: Dict[str, Any] = None) -> IntentResult:
        """上下文感知的意图预测"""
        # 获取会话历史
        session_id = context.get("session_id", "default") if context else "default"
        history = self.conversation_history.get(session_id, [])
        
        # 基础预测
        base_result = await self.base_classifier.predict_intent(text, context)
        
        # 上下文调整
        if history:
            adjusted_result = self._adjust_with_context(base_result, history)
        else:
            adjusted_result = base_result
        
        # 更新历史
        self._update_history(session_id, text, adjusted_result.intent_type)
        
        adjusted_result.method = "context_aware_classification"
        return adjusted_result
    
    def _adjust_with_context(self, result: IntentResult, history: List[Dict]) -> IntentResult:
        """基于上下文调整结果"""
        if len(history) < 2:
            return result
        
        # 分析最近的意图模式
        recent_intents = [item["intent"] for item in history[-3:]]
        
        # 意图连续性检查
        if len(set(recent_intents)) == 1 and recent_intents[0] == result.intent_type:
            # 意图连续，提升置信度
            result.confidence = min(result.confidence * 1.1, 1.0)
            result.context_boost = True
            result.reasoning += " | 上下文连续性提升"
        
        # 任务切换检测
        if self._detect_task_switch(result.intent_type, recent_intents):
            result.reasoning += " | 检测到任务切换"
        
        return result
    
    def _detect_task_switch(self, current_intent: str, recent_intents: List[str]) -> bool:
        """检测任务切换"""
        if not recent_intents:
            return False
        
        last_intent = recent_intents[-1]
        
        # 定义任务切换模式
        switch_patterns = {
            ("data_query", "document_generation"),
            ("data_analysis", "report_creation"),
            ("information_request", "task_execution")
        }
        
        return (last_intent, current_intent) in switch_patterns
    
    def _update_history(self, session_id: str, text: str, intent: str):
        """更新对话历史"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].append({
            "text": text,
            "intent": intent,
            "timestamp": time.time()
        })
        
        # 保持历史长度限制
        if len(self.conversation_history[session_id]) > 10:
            self.conversation_history[session_id] = self.conversation_history[session_id][-10:]


class LLMIntentClassifier:
    """LLM意图分类器（模拟）"""
    
    def __init__(self):
        self.confidence_threshold = 0.8
        
    async def predict_intent(self, text: str, context: Dict[str, Any] = None) -> IntentResult:
        """模拟LLM意图预测"""
        # 模拟LLM分析过程
        await asyncio.sleep(0.1)  # 模拟API调用延迟
        
        # 简化的LLM逻辑（实际应该调用真实的LLM API）
        intent_analysis = self._simulate_llm_analysis(text)
        
        return IntentResult(
            intent_type=intent_analysis["intent_type"],
            confidence=intent_analysis["confidence"],
            method="llm_classification",
            reasoning=intent_analysis["reasoning"],
            keywords=intent_analysis["keywords"],
            entities=intent_analysis.get("entities", {})
        )
    
    def _simulate_llm_analysis(self, text: str) -> Dict[str, Any]:
        """模拟LLM分析结果"""
        text_lower = text.lower()
        
        # 模拟复杂的语义理解
        if "生成" in text_lower and ("报告" in text_lower or "文档" in text_lower):
            return {
                "intent_type": "document_generation",
                "confidence": 0.92,
                "reasoning": "用户明确要求生成文档类内容",
                "keywords": ["生成", "报告", "文档"],
                "entities": {"document_type": "报告"}
            }
        elif "分析" in text_lower and "数据" in text_lower:
            return {
                "intent_type": "data_analysis",
                "confidence": 0.89,
                "reasoning": "用户需要进行数据分析任务",
                "keywords": ["分析", "数据"],
                "entities": {"analysis_type": "数据分析"}
            }
        elif any(word in text_lower for word in ["什么", "如何", "为什么", "解释"]):
            return {
                "intent_type": "information_request",
                "confidence": 0.85,
                "reasoning": "用户询问信息或寻求解释",
                "keywords": ["什么", "如何", "解释"],
                "entities": {}
            }
        else:
            return {
                "intent_type": "task_execution",
                "confidence": 0.75,
                "reasoning": "通用任务执行意图",
                "keywords": [],
                "entities": {}
            }


class UnifiedIntentEngine:
    """统一意图识别引擎"""
    
    def __init__(self):
        self.ml_classifier = SimpleMLIntentClassifier()
        self.llm_classifier = LLMIntentClassifier()
        self.context_classifier = ContextAwareIntentClassifier(self.ml_classifier)
        self.ensemble_strategy = "cascade"  # cascade, voting, weighted
        
    async def predict_intent(self, text: str, context: Dict[str, Any] = None) -> IntentResult:
        """统一意图预测"""
        if self.ensemble_strategy == "cascade":
            return await self._cascade_prediction(text, context)
        elif self.ensemble_strategy == "voting":
            return await self._voting_prediction(text, context)
        else:
            return await self._cascade_prediction(text, context)
    
    async def _cascade_prediction(self, text: str, context: Dict[str, Any]) -> IntentResult:
        """级联预测策略"""
        # 首先尝试上下文感知分类器
        context_result = await self.context_classifier.predict_intent(text, context)
        if context_result.confidence >= 0.8:
            return context_result
        
        # 然后尝试LLM分类器
        llm_result = await self.llm_classifier.predict_intent(text, context)
        if llm_result.confidence >= 0.8:
            return llm_result
        
        # 最后使用ML分类器
        ml_result = await self.ml_classifier.predict_intent(text, context)
        
        # 返回置信度最高的结果
        results = [context_result, llm_result, ml_result]
        best_result = max(results, key=lambda r: r.confidence)
        best_result.method = "cascade_ensemble"
        
        return best_result
    
    async def _voting_prediction(self, text: str, context: Dict[str, Any]) -> IntentResult:
        """投票预测策略"""
        # 获取所有分类器的预测
        results = []
        results.append(await self.context_classifier.predict_intent(text, context))
        results.append(await self.llm_classifier.predict_intent(text, context))
        results.append(await self.ml_classifier.predict_intent(text, context))
        
        # 投票决策
        intent_votes = {}
        for result in results:
            intent_type = result.intent_type
            if intent_type not in intent_votes:
                intent_votes[intent_type] = []
            intent_votes[intent_type].append(result.confidence)
        
        # 计算加权投票得分
        intent_scores = {}
        for intent_type, confidences in intent_votes.items():
            # 投票数 * 平均置信度
            score = len(confidences) * (sum(confidences) / len(confidences))
            intent_scores[intent_type] = score
        
        # 选择得分最高的意图
        best_intent = max(intent_scores, key=intent_scores.get)
        best_confidence = min(intent_scores[best_intent] / len(results), 1.0)
        
        return IntentResult(
            intent_type=best_intent,
            confidence=best_confidence,
            method="voting_ensemble",
            reasoning=f"投票决策，得分: {intent_scores}",
            keywords=[],
            uncertainty=1.0 - best_confidence
        )


class EnhancedBIRRouter(BIRRouter):
    """增强的BIR路由器"""
    
    def __init__(self, acp_client=None, trace_writer=None):
        super().__init__(acp_client, trace_writer)
        self.intent_engine = UnifiedIntentEngine()
        
    async def enhanced_dispatch(self, 
                               intent: str, 
                               from_agent: str, 
                               to_agent: str, 
                               context_id: str, 
                               payload: Dict[str, Any],
                               priority: int = 0,
                               context: Dict[str, Any] = None) -> Dict[str, Any]:
        """增强的行为分发"""
        # 使用增强意图识别
        intent_result = await self.intent_engine.predict_intent(intent, context)
        
        # 生成追踪ID
        trace_id = self._generate_trace_id(intent, context_id)
        
        # 构建增强的行为包
        enhanced_payload = {
            **payload,
            "intent_analysis": {
                "original_intent": intent,
                "predicted_intent": intent_result.intent_type,
                "confidence": intent_result.confidence,
                "method": intent_result.method,
                "reasoning": intent_result.reasoning,
                "keywords": intent_result.keywords,
                "entities": intent_result.entities,
                "uncertainty": intent_result.uncertainty,
                "needs_feedback": intent_result.needs_feedback
            }
        }
        
        # 调用原始dispatch方法
        behavior_package = self.dispatch(
            intent=intent,
            from_agent=from_agent,
            to_agent=to_agent,
            context_id=context_id,
            payload=enhanced_payload,
            priority=priority
        )
        
        return {
            "behavior_package": behavior_package,
            "intent_analysis": intent_result,
            "enhanced": True
        }


class EnhancedIntentRecognitionDemo:
    """增强意图识别演示"""
    
    def __init__(self):
        self.trace_writer = TraceWriter()
        self.enhanced_router = EnhancedBIRRouter(trace_writer=self.trace_writer)
        
    async def run_demo(self):
        """运行演示"""
        print("🚀 增强意图识别演示")
        print("=" * 60)
        
        # 测试用例
        test_cases = [
            {
                "text": "帮我生成一份月度销售报告",
                "context": {"session_id": "session_1", "user_role": "manager"},
                "expected": "document_generation"
            },
            {
                "text": "分析最近一周的用户行为数据",
                "context": {"session_id": "session_1"},
                "expected": "data_analysis"
            },
            {
                "text": "查询订单号12345的详细信息",
                "context": {"session_id": "session_2"},
                "expected": "data_query"
            },
            {
                "text": "什么是机器学习？",
                "context": {"session_id": "session_3"},
                "expected": "information_request"
            },
            {
                "text": "调用天气API获取明天的天气",
                "context": {"session_id": "session_4"},
                "expected": "api_invocation"
            },
            {
                "text": "设置系统的访问权限",
                "context": {"session_id": "session_5"},
                "expected": "system_control"
            }
        ]
        
        # 运行测试
        correct_predictions = 0
        total_predictions = len(test_cases)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 测试案例 {i}")
            print(f"输入: {test_case['text']}")
            print(f"期望意图: {test_case['expected']}")
            
            # 执行增强意图识别
            result = await self.enhanced_router.enhanced_dispatch(
                intent=test_case['text'],
                from_agent="user",
                to_agent="system",
                context_id=f"test_context_{i}",
                payload={"test": True},
                context=test_case['context']
            )
            
            intent_analysis = result["intent_analysis"]
            
            print(f"预测意图: {intent_analysis.intent_type}")
            print(f"置信度: {intent_analysis.confidence:.3f}")
            print(f"方法: {intent_analysis.method}")
            print(f"推理: {intent_analysis.reasoning}")
            print(f"关键词: {intent_analysis.keywords}")
            
            if intent_analysis.entities:
                print(f"实体: {intent_analysis.entities}")
            
            # 检查预测准确性
            is_correct = intent_analysis.intent_type == test_case['expected']
            if is_correct:
                correct_predictions += 1
                print("✅ 预测正确")
            else:
                print("❌ 预测错误")
            
            if intent_analysis.needs_feedback:
                print("⚠️ 需要人工反馈")
            
            if intent_analysis.context_boost:
                print("🔄 上下文增强")
            
            print("-" * 40)
        
        # 显示总体统计
        accuracy = correct_predictions / total_predictions
        print(f"\n📊 总体统计:")
        print(f"总测试案例: {total_predictions}")
        print(f"正确预测: {correct_predictions}")
        print(f"准确率: {accuracy:.1%}")
        
        # 演示不同的集成策略
        await self._demo_ensemble_strategies(test_cases[0])
    
    async def _demo_ensemble_strategies(self, test_case: Dict[str, Any]):
        """演示不同的集成策略"""
        print(f"\n🔬 集成策略对比演示")
        print(f"测试文本: {test_case['text']}")
        print("-" * 40)
        
        strategies = ["cascade", "voting", "weighted"]
        
        for strategy in strategies:
            self.enhanced_router.intent_engine.ensemble_strategy = strategy
            
            result = await self.enhanced_router.intent_engine.predict_intent(
                test_case['text'], 
                test_case['context']
            )
            
            print(f"策略: {strategy}")
            print(f"  意图: {result.intent_type}")
            print(f"  置信度: {result.confidence:.3f}")
            print(f"  方法: {result.method}")
            print()


async def main():
    """主函数"""
    demo = EnhancedIntentRecognitionDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main()) 