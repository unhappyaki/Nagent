"""
智能工具选择演示

演示如何从简单关键词匹配升级到智能工具选择，
支持语义理解、上下文感知和多策略融合。
"""

import asyncio
import json
import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re


@dataclass
class ToolCandidate:
    """工具候选者"""
    name: str
    description: str
    category: str
    score: float
    match_type: str
    metadata: Dict[str, Any] = None


class MatchType(Enum):
    """匹配类型"""
    EXACT_KEYWORD = "exact_keyword"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    CATEGORY_MATCH = "category_match"
    CONTEXT_AWARE = "context_aware"
    USAGE_PATTERN = "usage_pattern"


class ToolCategory(Enum):
    """工具分类"""
    DATA_PROCESSING = "数据处理"
    FILE_OPERATIONS = "文件操作"
    NETWORK_COMMUNICATION = "网络通信"
    SYSTEM_OPERATIONS = "系统操作"
    AI_ML = "AI与机器学习"
    DEVELOPMENT = "开发工具"
    MONITORING = "监控工具"


class SimpleToolSelector:
    """简单工具选择器 - 当前系统的实现方式"""
    
    def __init__(self):
        self.tool_mapping = {
            "搜索": "web_search",
            "查找": "web_search",
            "计算": "calculator",
            "时间": "get_time",
            "天气": "get_weather",
            "文件": "file_operations",
            "网络": "http_request"
        }
    
    def select_tool(self, intent: str, available_tools: List[Dict[str, Any]]) -> str:
        """简单的关键词匹配工具选择"""
        intent_lower = intent.lower()
        
        for keyword, tool_name in self.tool_mapping.items():
            if keyword in intent_lower:
                # 检查工具是否可用
                if any(tool.get("name") == tool_name for tool in available_tools):
                    return tool_name
        
        # 返回第一个可用工具
        return available_tools[0].get("name", "default_tool") if available_tools else "default_tool"


class IntelligentToolSelector:
    """智能工具选择器 - 改进版实现"""
    
    def __init__(self):
        self.tool_database = self._init_tool_database()
        self.semantic_patterns = self._init_semantic_patterns()
        self.context_memory = []
        self.usage_stats = {}
        
    def _init_tool_database(self) -> List[Dict[str, Any]]:
        """初始化工具数据库"""
        return [
            {
                "name": "web_search",
                "description": "执行网络搜索，查找互联网上的信息",
                "category": ToolCategory.DATA_PROCESSING.value,
                "keywords": ["搜索", "查找", "寻找", "检索", "查询", "找"],
                "semantic_tags": ["信息获取", "网络查询", "内容搜索"],
                "usage_count": 150,
                "success_rate": 0.85
            },
            {
                "name": "calculator",
                "description": "执行数学计算和表达式求值",
                "category": ToolCategory.DATA_PROCESSING.value,
                "keywords": ["计算", "算", "数学", "求解", "运算"],
                "semantic_tags": ["数值计算", "数学运算", "表达式求值"],
                "usage_count": 120,
                "success_rate": 0.95
            },
            {
                "name": "get_time",
                "description": "获取当前时间和日期信息",
                "category": ToolCategory.SYSTEM_OPERATIONS.value,
                "keywords": ["时间", "日期", "现在", "当前时间"],
                "semantic_tags": ["时间查询", "日期获取", "时间信息"],
                "usage_count": 80,
                "success_rate": 0.98
            },
            {
                "name": "get_weather",
                "description": "获取指定地区的天气信息",
                "category": ToolCategory.DATA_PROCESSING.value,
                "keywords": ["天气", "气温", "降雨", "晴天", "阴天"],
                "semantic_tags": ["天气查询", "气象信息", "环境数据"],
                "usage_count": 90,
                "success_rate": 0.80
            },
            {
                "name": "file_operations",
                "description": "执行文件读写、创建、删除等操作",
                "category": ToolCategory.FILE_OPERATIONS.value,
                "keywords": ["文件", "读取", "写入", "保存", "删除"],
                "semantic_tags": ["文件管理", "数据存储", "文件处理"],
                "usage_count": 100,
                "success_rate": 0.88
            },
            {
                "name": "http_request",
                "description": "发送HTTP请求，与外部API交互",
                "category": ToolCategory.NETWORK_COMMUNICATION.value,
                "keywords": ["网络", "请求", "API", "接口", "调用"],
                "semantic_tags": ["网络通信", "API调用", "数据交换"],
                "usage_count": 70,
                "success_rate": 0.75
            },
            {
                "name": "data_analyzer",
                "description": "分析数据集，生成统计报告",
                "category": ToolCategory.DATA_PROCESSING.value,
                "keywords": ["分析", "统计", "报告", "数据", "图表"],
                "semantic_tags": ["数据分析", "统计处理", "报告生成"],
                "usage_count": 60,
                "success_rate": 0.82
            },
            {
                "name": "email_sender",
                "description": "发送电子邮件通知",
                "category": ToolCategory.NETWORK_COMMUNICATION.value,
                "keywords": ["邮件", "发送", "通知", "email"],
                "semantic_tags": ["邮件发送", "消息通知", "通信工具"],
                "usage_count": 45,
                "success_rate": 0.90
            },
            {
                "name": "image_processor",
                "description": "处理和编辑图像文件",
                "category": ToolCategory.AI_ML.value,
                "keywords": ["图像", "图片", "处理", "编辑", "照片"],
                "semantic_tags": ["图像处理", "视觉处理", "媒体编辑"],
                "usage_count": 35,
                "success_rate": 0.78
            },
            {
                "name": "text_translator",
                "description": "翻译文本内容到不同语言",
                "category": ToolCategory.AI_ML.value,
                "keywords": ["翻译", "语言", "转换", "中英文"],
                "semantic_tags": ["语言翻译", "文本转换", "多语言处理"],
                "usage_count": 55,
                "success_rate": 0.85
            }
        ]
    
    def _init_semantic_patterns(self) -> Dict[str, List[str]]:
        """初始化语义模式"""
        return {
            "search_intent": [
                r".*?(搜索|查找|寻找|检索|找|查).*?",
                r".*?(帮我找|帮忙找|能找到|找一下).*?",
                r".*?(有没有|是否有|存在).*?信息.*?"
            ],
            "calculation_intent": [
                r".*?(计算|算|求|运算).*?",
                r".*?\d+.*?[+\-*/].*?\d+.*?",
                r".*?(多少|几|数量).*?"
            ],
            "time_intent": [
                r".*?(时间|日期|现在|当前).*?",
                r".*?(几点|什么时候|今天).*?"
            ],
            "weather_intent": [
                r".*?(天气|气温|温度|下雨|晴天).*?",
                r".*?(今天.*?天气|明天.*?天气).*?"
            ],
            "file_intent": [
                r".*?(文件|保存|读取|写入|删除).*?",
                r".*?(创建.*?文件|打开.*?文件).*?"
            ],
            "communication_intent": [
                r".*?(发送|邮件|通知|消息).*?",
                r".*?(联系|通知|告诉).*?"
            ]
        }
    
    async def select_tool(
        self, 
        intent: str, 
        context: Dict[str, Any] = None
    ) -> Tuple[str, float, Dict[str, Any]]:
        """智能工具选择"""
        print(f"\n🔍 智能工具选择开始...")
        print(f"意图: {intent}")
        
        # 1. 多策略候选工具发现
        candidates = await self._discover_candidates(intent, context)
        
        # 2. 上下文感知评分
        context_scored_candidates = await self._context_aware_scoring(
            candidates, intent, context
        )
        
        # 3. 多策略融合选择
        final_selection = await self._multi_strategy_selection(
            context_scored_candidates, intent, context
        )
        
        # 4. 更新使用统计
        self._update_usage_stats(final_selection["name"], intent)
        
        print(f"✅ 选择结果: {final_selection['name']} (置信度: {final_selection['confidence']:.2f})")
        
        return final_selection["name"], final_selection["confidence"], final_selection["metadata"]
    
    async def _discover_candidates(
        self, 
        intent: str, 
        context: Dict[str, Any] = None
    ) -> List[ToolCandidate]:
        """发现候选工具"""
        candidates = []
        
        # 1. 关键词匹配
        keyword_matches = self._keyword_matching(intent)
        candidates.extend(keyword_matches)
        
        # 2. 语义模式匹配
        semantic_matches = self._semantic_pattern_matching(intent)
        candidates.extend(semantic_matches)
        
        # 3. 分类匹配
        category_matches = self._category_matching(intent)
        candidates.extend(category_matches)
        
        # 4. 上下文匹配
        if context:
            context_matches = self._context_matching(intent, context)
            candidates.extend(context_matches)
        
        # 去重并返回
        unique_candidates = self._deduplicate_candidates(candidates)
        
        print(f"📋 发现 {len(unique_candidates)} 个候选工具")
        for candidate in unique_candidates[:3]:  # 显示前3个
            print(f"  - {candidate.name}: {candidate.score:.2f} ({candidate.match_type})")
        
        return unique_candidates
    
    def _keyword_matching(self, intent: str) -> List[ToolCandidate]:
        """关键词匹配"""
        candidates = []
        intent_lower = intent.lower()
        
        for tool in self.tool_database:
            max_score = 0
            for keyword in tool["keywords"]:
                if keyword in intent_lower:
                    # 计算匹配分数
                    score = len(keyword) / len(intent_lower)
                    max_score = max(max_score, score)
            
            if max_score > 0:
                candidates.append(ToolCandidate(
                    name=tool["name"],
                    description=tool["description"],
                    category=tool["category"],
                    score=max_score * 0.8,  # 关键词匹配基础权重
                    match_type=MatchType.EXACT_KEYWORD.value,
                    metadata=tool
                ))
        
        return candidates
    
    def _semantic_pattern_matching(self, intent: str) -> List[ToolCandidate]:
        """语义模式匹配"""
        candidates = []
        
        # 意图分类映射
        intent_tool_mapping = {
            "search_intent": ["web_search", "data_analyzer"],
            "calculation_intent": ["calculator"],
            "time_intent": ["get_time"],
            "weather_intent": ["get_weather"],
            "file_intent": ["file_operations"],
            "communication_intent": ["email_sender", "http_request"]
        }
        
        for intent_type, patterns in self.semantic_patterns.items():
            for pattern in patterns:
                if re.search(pattern, intent, re.IGNORECASE):
                    tool_names = intent_tool_mapping.get(intent_type, [])
                    for tool_name in tool_names:
                        tool_info = next((t for t in self.tool_database if t["name"] == tool_name), None)
                        if tool_info:
                            candidates.append(ToolCandidate(
                                name=tool_info["name"],
                                description=tool_info["description"],
                                category=tool_info["category"],
                                score=0.7,  # 语义匹配分数
                                match_type=MatchType.SEMANTIC_SIMILARITY.value,
                                metadata=tool_info
                            ))
                    break
        
        return candidates
    
    def _category_matching(self, intent: str) -> List[ToolCandidate]:
        """分类匹配"""
        candidates = []
        
        # 基于意图内容推断可能的工具分类
        category_keywords = {
            ToolCategory.DATA_PROCESSING.value: ["数据", "信息", "查询", "搜索", "分析"],
            ToolCategory.FILE_OPERATIONS.value: ["文件", "保存", "读取", "写入"],
            ToolCategory.NETWORK_COMMUNICATION.value: ["网络", "发送", "通信", "邮件"],
            ToolCategory.SYSTEM_OPERATIONS.value: ["系统", "时间", "状态"],
            ToolCategory.AI_ML.value: ["翻译", "图像", "识别", "处理"]
        }
        
        intent_lower = intent.lower()
        for category, keywords in category_keywords.items():
            category_score = sum(1 for keyword in keywords if keyword in intent_lower)
            if category_score > 0:
                # 找到该分类下的所有工具
                category_tools = [t for t in self.tool_database if t["category"] == category]
                for tool in category_tools:
                    candidates.append(ToolCandidate(
                        name=tool["name"],
                        description=tool["description"],
                        category=tool["category"],
                        score=min(category_score * 0.2, 0.6),  # 分类匹配分数
                        match_type=MatchType.CATEGORY_MATCH.value,
                        metadata=tool
                    ))
        
        return candidates
    
    def _context_matching(self, intent: str, context: Dict[str, Any]) -> List[ToolCandidate]:
        """上下文匹配"""
        candidates = []
        
        # 分析对话历史
        if "conversation_history" in context:
            history = context["conversation_history"]
            if history:
                last_intent = history[-1].get("intent", "")
                # 如果上一次使用了某个工具，可能会继续使用相关工具
                for tool in self.tool_database:
                    if any(keyword in last_intent.lower() for keyword in tool["keywords"]):
                        candidates.append(ToolCandidate(
                            name=tool["name"],
                            description=tool["description"],
                            category=tool["category"],
                            score=0.4,  # 上下文匹配分数
                            match_type=MatchType.CONTEXT_AWARE.value,
                            metadata=tool
                        ))
        
        return candidates
    
    def _deduplicate_candidates(self, candidates: List[ToolCandidate]) -> List[ToolCandidate]:
        """去重候选工具，保留最高分数"""
        tool_scores = {}
        for candidate in candidates:
            if candidate.name not in tool_scores or candidate.score > tool_scores[candidate.name].score:
                tool_scores[candidate.name] = candidate
        
        return list(tool_scores.values())
    
    async def _context_aware_scoring(
        self, 
        candidates: List[ToolCandidate], 
        intent: str, 
        context: Dict[str, Any] = None
    ) -> List[ToolCandidate]:
        """上下文感知评分"""
        for candidate in candidates:
            # 基础分数
            base_score = candidate.score
            
            # 使用频率加权
            usage_count = candidate.metadata.get("usage_count", 0)
            usage_bonus = min(usage_count / 200, 0.2)  # 最多20%加成
            
            # 成功率加权
            success_rate = candidate.metadata.get("success_rate", 0.5)
            success_bonus = (success_rate - 0.5) * 0.3  # 成功率影响
            
            # 时间衰减（最近使用的工具得分更高）
            time_bonus = 0
            if context and "recent_tools" in context:
                if candidate.name in context["recent_tools"]:
                    time_bonus = 0.1
            
            # 综合评分
            candidate.score = min(base_score + usage_bonus + success_bonus + time_bonus, 1.0)
        
        return sorted(candidates, key=lambda x: x.score, reverse=True)
    
    async def _multi_strategy_selection(
        self, 
        candidates: List[ToolCandidate], 
        intent: str, 
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """多策略融合选择"""
        if not candidates:
            return {
                "name": "default_tool",
                "confidence": 0.1,
                "metadata": {"reason": "no_candidates_found"}
            }
        
        # 策略权重
        strategy_weights = {
            MatchType.EXACT_KEYWORD.value: 0.4,
            MatchType.SEMANTIC_SIMILARITY.value: 0.3,
            MatchType.CATEGORY_MATCH.value: 0.2,
            MatchType.CONTEXT_AWARE.value: 0.1
        }
        
        # 计算加权分数
        for candidate in candidates:
            weight = strategy_weights.get(candidate.match_type, 0.1)
            candidate.score *= weight
        
        # 选择最高分工具
        best_candidate = max(candidates, key=lambda x: x.score)
        
        # 计算置信度
        confidence = min(best_candidate.score * 2, 1.0)  # 归一化到[0,1]
        
        return {
            "name": best_candidate.name,
            "confidence": confidence,
            "metadata": {
                "description": best_candidate.description,
                "category": best_candidate.category,
                "match_type": best_candidate.match_type,
                "candidates_count": len(candidates),
                "selection_reason": f"最佳匹配 ({best_candidate.match_type})"
            }
        }
    
    def _update_usage_stats(self, tool_name: str, intent: str):
        """更新使用统计"""
        if tool_name not in self.usage_stats:
            self.usage_stats[tool_name] = {
                "count": 0,
                "intents": [],
                "success_count": 0
            }
        
        self.usage_stats[tool_name]["count"] += 1
        self.usage_stats[tool_name]["intents"].append(intent)
        
        # 更新工具数据库中的使用计数
        for tool in self.tool_database:
            if tool["name"] == tool_name:
                tool["usage_count"] += 1
                break


class ToolSelectionComparator:
    """工具选择对比器"""
    
    def __init__(self):
        self.simple_selector = SimpleToolSelector()
        self.intelligent_selector = IntelligentToolSelector()
        
    async def compare_selections(self, test_cases: List[Dict[str, Any]]):
        """对比两种选择方法"""
        print("=" * 60)
        print("🔬 工具选择方法对比测试")
        print("=" * 60)
        
        results = {
            "simple": {"correct": 0, "total": 0, "details": []},
            "intelligent": {"correct": 0, "total": 0, "details": []}
        }
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 测试用例 {i}: {test_case['intent']}")
            print(f"期望工具: {test_case['expected_tool']}")
            
            # 简单选择器测试
            simple_result = self.simple_selector.select_tool(
                test_case["intent"], 
                test_case["available_tools"]
            )
            simple_correct = simple_result == test_case["expected_tool"]
            results["simple"]["correct"] += simple_correct
            results["simple"]["total"] += 1
            results["simple"]["details"].append({
                "intent": test_case["intent"],
                "selected": simple_result,
                "expected": test_case["expected_tool"],
                "correct": simple_correct
            })
            
            print(f"  🔹 简单选择器: {simple_result} {'✅' if simple_correct else '❌'}")
            
            # 智能选择器测试
            intelligent_result, confidence, metadata = await self.intelligent_selector.select_tool(
                test_case["intent"],
                test_case.get("context", {})
            )
            intelligent_correct = intelligent_result == test_case["expected_tool"]
            results["intelligent"]["correct"] += intelligent_correct
            results["intelligent"]["total"] += 1
            results["intelligent"]["details"].append({
                "intent": test_case["intent"],
                "selected": intelligent_result,
                "expected": test_case["expected_tool"],
                "correct": intelligent_correct,
                "confidence": confidence,
                "metadata": metadata
            })
            
            print(f"  🔹 智能选择器: {intelligent_result} (置信度: {confidence:.2f}) {'✅' if intelligent_correct else '❌'}")
            if metadata:
                print(f"    理由: {metadata.get('selection_reason', 'N/A')}")
        
        # 打印总结
        print("\n" + "=" * 60)
        print("📊 测试结果总结")
        print("=" * 60)
        
        simple_accuracy = results["simple"]["correct"] / results["simple"]["total"]
        intelligent_accuracy = results["intelligent"]["correct"] / results["intelligent"]["total"]
        
        print(f"简单选择器准确率: {simple_accuracy:.2%} ({results['simple']['correct']}/{results['simple']['total']})")
        print(f"智能选择器准确率: {intelligent_accuracy:.2%} ({results['intelligent']['correct']}/{results['intelligent']['total']})")
        print(f"准确率提升: {intelligent_accuracy - simple_accuracy:.2%}")
        
        return results


async def main():
    """主演示函数"""
    print("🚀 智能工具选择演示开始")
    
    # 准备测试用例
    test_cases = [
        {
            "intent": "帮我搜索一下Python教程",
            "expected_tool": "web_search",
            "available_tools": [
                {"name": "web_search"}, {"name": "calculator"}, 
                {"name": "get_time"}, {"name": "file_operations"}
            ],
            "context": {"user_id": "user1", "conversation_history": []}
        },
        {
            "intent": "我想知道现在几点了",
            "expected_tool": "get_time",
            "available_tools": [
                {"name": "web_search"}, {"name": "calculator"}, 
                {"name": "get_time"}, {"name": "get_weather"}
            ],
            "context": {"user_id": "user1"}
        },
        {
            "intent": "帮我算一下 123 + 456 等于多少",
            "expected_tool": "calculator",
            "available_tools": [
                {"name": "web_search"}, {"name": "calculator"}, 
                {"name": "get_time"}, {"name": "file_operations"}
            ]
        },
        {
            "intent": "查看今天的天气情况",
            "expected_tool": "get_weather",
            "available_tools": [
                {"name": "web_search"}, {"name": "get_weather"}, 
                {"name": "get_time"}, {"name": "file_operations"}
            ]
        },
        {
            "intent": "能帮我找到相关的资料吗",
            "expected_tool": "web_search",
            "available_tools": [
                {"name": "web_search"}, {"name": "data_analyzer"}, 
                {"name": "file_operations"}, {"name": "calculator"}
            ]
        },
        {
            "intent": "我需要保存这个文档",
            "expected_tool": "file_operations",
            "available_tools": [
                {"name": "web_search"}, {"name": "file_operations"}, 
                {"name": "email_sender"}, {"name": "calculator"}
            ]
        },
        {
            "intent": "请翻译这段英文",
            "expected_tool": "text_translator",
            "available_tools": [
                {"name": "text_translator"}, {"name": "web_search"}, 
                {"name": "file_operations"}, {"name": "image_processor"}
            ]
        },
        {
            "intent": "发送邮件通知给团队",
            "expected_tool": "email_sender",
            "available_tools": [
                {"name": "email_sender"}, {"name": "http_request"}, 
                {"name": "file_operations"}, {"name": "web_search"}
            ]
        },
        {
            "intent": "处理这张图片",
            "expected_tool": "image_processor",
            "available_tools": [
                {"name": "image_processor"}, {"name": "file_operations"}, 
                {"name": "data_analyzer"}, {"name": "web_search"}
            ]
        },
        {
            "intent": "分析这些数据并生成报告",
            "expected_tool": "data_analyzer",
            "available_tools": [
                {"name": "data_analyzer"}, {"name": "web_search"}, 
                {"name": "file_operations"}, {"name": "calculator"}
            ]
        }
    ]
    
    # 运行对比测试
    comparator = ToolSelectionComparator()
    results = await comparator.compare_selections(test_cases)
    
    # 展示智能选择器的额外能力
    print("\n" + "=" * 60)
    print("🎯 智能选择器特殊能力演示")
    print("=" * 60)
    
    intelligent_selector = IntelligentToolSelector()
    
    # 1. 语义理解能力
    print("\n1️⃣ 语义理解能力测试:")
    semantic_tests = [
        "能不能帮我找一下相关信息",  # 应该选择web_search
        "麻烦算一下这个表达式",        # 应该选择calculator
        "现在是什么时间",            # 应该选择get_time
    ]
    
    for test_intent in semantic_tests:
        result, confidence, metadata = await intelligent_selector.select_tool(test_intent)
        print(f"  '{test_intent}' -> {result} (置信度: {confidence:.2f})")
    
    # 2. 上下文感知能力
    print("\n2️⃣ 上下文感知能力测试:")
    context_with_history = {
        "conversation_history": [
            {"intent": "搜索Python教程", "selected_tool": "web_search"},
            {"intent": "查看搜索结果", "selected_tool": "web_search"}
        ],
        "recent_tools": ["web_search"],
        "user_id": "user1"
    }
    
    result, confidence, metadata = await intelligent_selector.select_tool(
        "继续查找相关资料", context_with_history
    )
    print(f"  上下文感知选择: {result} (置信度: {confidence:.2f})")
    print(f"  选择理由: {metadata.get('selection_reason', 'N/A')}")
    
    # 3. 使用统计展示
    print("\n3️⃣ 工具使用统计:")
    usage_stats = intelligent_selector.usage_stats
    if usage_stats:
        for tool_name, stats in usage_stats.items():
            print(f"  {tool_name}: 使用 {stats['count']} 次")
    else:
        print("  暂无使用统计数据")
    
    print("\n✨ 演示完成！")
    print("\n💡 智能工具选择的优势:")
    print("  1. 语义理解：能理解同义词和相似表达")
    print("  2. 上下文感知：考虑对话历史和用户偏好")
    print("  3. 多策略融合：结合关键词、语义、分类等多种匹配方式")
    print("  4. 自适应学习：根据使用情况持续优化选择策略")
    print("  5. 置信度评估：提供选择结果的可信度评分")


if __name__ == "__main__":
    asyncio.run(main()) 