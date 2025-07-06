"""
规则推理器

基于预定义规则进行推理决策，支持：
- 关键词匹配
- 模式识别
- 条件判断
- 规则链
"""

import re
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)


class RuleReasoner:
    """
    规则推理器
    
    基于预定义规则进行推理决策
    """
    
    def __init__(self):
        """初始化规则推理器"""
        # 预定义规则
        self.rules = self._load_default_rules()
        
        # 统计信息
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "rules_matched": 0
        }
        
        logger.info("Rule reasoner initialized")
    
    async def reason(
        self,
        task: str,
        context: List[Dict[str, Any]] = None,
        available_tools: List[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        使用规则进行推理
        
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
            # 应用规则
            result = self._apply_rules(task, context, available_tools)
            
            self.stats["successful_calls"] += 1
            
            logger.debug(
                "Rule reasoning completed",
                task=task,
                action=result.get("action"),
                confidence=result.get("confidence")
            )
            
            return result
            
        except Exception as e:
            self.stats["failed_calls"] += 1
            
            logger.error(
                "Rule reasoning failed",
                task=task,
                error=str(e)
            )
            
            # 返回默认响应
            return {
                "action": "respond",
                "parameters": {
                    "response": f"我理解您的任务：{task}。我正在处理中。"
                },
                "confidence": 0.3,
                "reasoning": f"规则推理失败，使用默认响应: {str(e)}",
                "strategy": "rule"
            }
    
    def _load_default_rules(self) -> List[Dict[str, Any]]:
        """加载默认规则"""
        return [
            # 搜索相关规则
            {
                "name": "search_rule",
                "pattern": r"(搜索|查找|查询|search|find|lookup)",
                "action": "tool_call",
                "parameters": {
                    "tool_name": "web_search",
                    "tool_params": {"query": "{task}"}
                },
                "confidence": 0.8,
                "priority": 1
            },
            
            # 计算相关规则
            {
                "name": "calculation_rule",
                "pattern": r"(计算|算|calculate|compute|math)",
                "action": "tool_call",
                "parameters": {
                    "tool_name": "calculator",
                    "tool_params": {"expression": "{task}"}
                },
                "confidence": 0.9,
                "priority": 1
            },
            
            # 时间相关规则
            {
                "name": "time_rule",
                "pattern": r"(时间|几点|when|time|date)",
                "action": "tool_call",
                "parameters": {
                    "tool_name": "get_time",
                    "tool_params": {}
                },
                "confidence": 0.9,
                "priority": 1
            },
            
            # 天气相关规则
            {
                "name": "weather_rule",
                "pattern": r"(天气|weather|温度|temperature)",
                "action": "tool_call",
                "parameters": {
                    "tool_name": "get_weather",
                    "tool_params": {"location": "auto"}
                },
                "confidence": 0.8,
                "priority": 1
            },
            
            # 文件操作规则
            {
                "name": "file_rule",
                "pattern": r"(文件|file|文档|document|保存|save|读取|read)",
                "action": "tool_call",
                "parameters": {
                    "tool_name": "file_operations",
                    "tool_params": {"operation": "auto", "path": "{task}"}
                },
                "confidence": 0.7,
                "priority": 2
            },
            
            # 网络请求规则
            {
                "name": "http_rule",
                "pattern": r"(http|https|api|接口|请求|request)",
                "action": "tool_call",
                "parameters": {
                    "tool_name": "http_request",
                    "tool_params": {"url": "{task}"}
                },
                "confidence": 0.6,
                "priority": 2
            },
            
            # 委托规则
            {
                "name": "delegate_rule",
                "pattern": r"(委托|转交|delegate|交给|让.*处理)",
                "action": "delegate",
                "parameters": {
                    "target_agent": "task_agent",
                    "task": "{task}"
                },
                "confidence": 0.7,
                "priority": 3
            },
            
            # 默认响应规则
            {
                "name": "default_rule",
                "pattern": r".*",
                "action": "respond",
                "parameters": {
                    "response": "我理解您的需求，让我为您处理。"
                },
                "confidence": 0.5,
                "priority": 10
            }
        ]
    
    def _apply_rules(
        self,
        task: str,
        context: List[Dict[str, Any]] = None,
        available_tools: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        应用规则
        
        Args:
            task: 任务描述
            context: 上下文信息
            available_tools: 可用工具列表
            
        Returns:
            规则匹配结果
        """
        matched_rules = []
        
        # 匹配规则
        for rule in self.rules:
            pattern = rule["pattern"]
            if re.search(pattern, task, re.IGNORECASE):
                matched_rules.append(rule)
        
        if not matched_rules:
            # 如果没有匹配的规则，使用默认规则
            matched_rules = [self.rules[-1]]  # 默认规则
        
        # 按优先级排序，选择最高优先级的规则
        matched_rules.sort(key=lambda x: x["priority"])
        best_rule = matched_rules[0]
        
        # 更新统计
        self.stats["rules_matched"] += 1
        
        # 处理参数模板
        parameters = self._process_parameters(best_rule["parameters"], task)
        
        # 检查工具可用性
        if best_rule["action"] == "tool_call":
            tool_name = parameters.get("tool_name")
            if available_tools and not self._is_tool_available(tool_name, available_tools):
                # 如果工具不可用，降级到响应
                return {
                    "action": "respond",
                    "parameters": {
                        "response": f"抱歉，当前无法使用{tool_name}工具。"
                    },
                    "confidence": 0.3,
                    "reasoning": f"工具{tool_name}不可用，降级到响应",
                    "strategy": "rule"
                }
        
        return {
            "action": best_rule["action"],
            "parameters": parameters,
            "confidence": best_rule["confidence"],
            "reasoning": f"匹配规则: {best_rule['name']}",
            "strategy": "rule"
        }
    
    def _process_parameters(self, parameters: Dict[str, Any], task: str) -> Dict[str, Any]:
        """
        处理参数模板
        
        Args:
            parameters: 原始参数
            task: 任务描述
            
        Returns:
            处理后的参数
        """
        processed = {}
        
        for key, value in parameters.items():
            if isinstance(value, str):
                # 替换模板变量
                processed[key] = value.replace("{task}", task)
            elif isinstance(value, dict):
                # 递归处理嵌套字典
                processed[key] = self._process_parameters(value, task)
            else:
                processed[key] = value
        
        return processed
    
    def _is_tool_available(self, tool_name: str, available_tools: List[Dict[str, Any]]) -> bool:
        """
        检查工具是否可用
        
        Args:
            tool_name: 工具名称
            available_tools: 可用工具列表
            
        Returns:
            是否可用
        """
        if not available_tools:
            return True  # 如果没有工具列表，假设所有工具都可用
        
        return any(tool.get("name") == tool_name for tool in available_tools)
    
    def add_rule(self, rule: Dict[str, Any]) -> None:
        """
        添加新规则
        
        Args:
            rule: 规则定义
        """
        required_fields = ["name", "pattern", "action", "parameters", "confidence", "priority"]
        
        for field in required_fields:
            if field not in rule:
                raise ValueError(f"规则缺少必要字段: {field}")
        
        self.rules.append(rule)
        
        # 按优先级排序
        self.rules.sort(key=lambda x: x["priority"])
        
        logger.info("Rule added", rule_name=rule["name"])
    
    def remove_rule(self, rule_name: str) -> None:
        """
        移除规则
        
        Args:
            rule_name: 规则名称
        """
        self.rules = [rule for rule in self.rules if rule["name"] != rule_name]
        logger.info("Rule removed", rule_name=rule_name)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_calls"] / self.stats["total_calls"]
                if self.stats["total_calls"] > 0 else 0
            ),
            "total_rules": len(self.rules)
        } 