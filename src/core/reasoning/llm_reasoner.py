"""
LLM推理器

基于大语言模型实现智能推理功能，支持：
- OpenAI GPT系列
- 本地模型
- 自定义模型
"""

import json
import re
from typing import Any, Dict, List, Optional
import openai
import structlog
from src.infrastructure.config.unified_config import UnifiedConfigManager
import asyncio

logger = structlog.get_logger(__name__)


class LLMReasoner:
    """
    LLM推理器
    
    使用大语言模型进行智能推理和决策
    """
    
    def __init__(
        self,
        model: str = "gpt-4",
        max_tokens: int = 4000,
        temperature: float = 0.4,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        初始化LLM推理器
        
        Args:
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度参数
            api_key: API密钥
            base_url: API基础URL
        """
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # 优先使用传入api_key，否则自动从统一配置读取
        if not api_key:
            try:
                config = UnifiedConfigManager().get_llm_gateway_config().get("oneapi", {})
                api_key = config.get("api_key", None)
            except Exception as e:
                api_key = None
                logger.warning("自动获取oneapi.api_key失败", error=str(e))
        if api_key:
            openai.api_key = api_key
        if base_url:
            openai.base_url = base_url
        
        # 统计信息
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_tokens_used": 0
        }
        
        logger.info(
            "LLM reasoner initialized",
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    async def reason(
        self,
        task: str,
        context: List[Dict[str, Any]] = None,
        available_tools: List[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        使用LLM进行推理
        
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
            # 构建提示词
            prompt = self._build_prompt(task, context, available_tools)
            
            # 调用LLM
            response = await self._call_llm(prompt, **kwargs)
            
            # 解析响应
            result = self._parse_response(response)
            
            self.stats["successful_calls"] += 1
            
            logger.debug(
                "LLM reasoning completed",
                task=task,
                action=result.get("action"),
                confidence=result.get("confidence")
            )
            
            return result
            
        except Exception as e:
            self.stats["failed_calls"] += 1
            
            logger.error(
                "LLM reasoning failed",
                task=task,
                error=str(e)
            )
            
            # 返回默认响应
            return {
                "action": "respond",
                "parameters": {
                    "response": f"我理解您的任务：{task}。我正在处理中。"
                },
                "confidence": 0.5,
                "reasoning": f"LLM推理失败，使用默认响应: {str(e)}",
                "strategy": "llm"
            }
    
    def _build_prompt(
        self,
        task: str,
        context: List[Dict[str, Any]] = None,
        available_tools: List[Dict[str, Any]] = None
    ) -> str:
        """
        构建提示词
        
        Args:
            task: 任务描述
            context: 上下文信息
            available_tools: 可用工具列表
            
        Returns:
            构建的提示词
        """
        prompt_parts = []
        
        # 系统提示
        system_prompt = """你是一个智能Agent，负责分析任务并决定下一步行动。

你的主要职责是：
1. 理解用户的任务需求
2. 分析当前上下文
3. 选择合适的行动方案
4. 提供清晰的推理过程

可用的行动类型：
- tool_call: 调用工具执行特定功能
- delegate: 将任务委托给其他Agent
- respond: 直接响应用户
- skip: 跳过当前任务

请以JSON格式返回你的决策，包含以下字段：
{
    "action": "行动类型",
    "parameters": {
        // 行动的具体参数
    },
    "confidence": 0.0-1.0的置信度,
    "reasoning": "推理过程说明"
}"""
        
        prompt_parts.append(system_prompt)
        
        # 添加上下文
        if context:
            context_text = "上下文信息：\n"
            for i, ctx in enumerate(context[-5:], 1):  # 只取最近5条
                context_text += f"{i}. {ctx.get('role', 'unknown')}: {ctx.get('content', '')}\n"
            prompt_parts.append(context_text)
        
        # 添加可用工具
        if available_tools:
            tools_text = "可用工具：\n"
            for tool in available_tools:
                tools_text += f"- {tool.get('name', 'unknown')}: {tool.get('description', '')}\n"
            prompt_parts.append(tools_text)
        
        # 添加任务
        task_text = f"当前任务：{task}\n\n请分析任务并决定下一步行动："
        prompt_parts.append(task_text)
        
        return "\n".join(prompt_parts)
    
    async def _call_llm(self, prompt: str, **kwargs) -> str:
        """
        调用LLM
        """
        try:
            # 优先用异步acreate，若无则降级为同步create
            chat_completions = getattr(getattr(openai, "chat", None), "completions", None)
            if hasattr(chat_completions, "acreate"):
                response = await chat_completions.acreate(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个智能推理助手。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    **kwargs
                )
            else:
                # 用同步create并用asyncio.to_thread包裹
                response = await asyncio.to_thread(
                    chat_completions.create,
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个智能推理助手。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    **kwargs
                )
            # 更新统计信息
            if hasattr(response, 'usage') and response.usage:
                self.stats["total_tokens_used"] += response.usage.total_tokens
            return response.choices[0].message.content
        except Exception as e:
            logger.error("LLM API call failed", error=str(e))
            raise
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析LLM响应
        
        Args:
            response: LLM响应文本
            
        Returns:
            解析后的结果
        """
        try:
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                # 验证必要字段
                if "action" not in result:
                    raise ValueError("响应中缺少action字段")
                
                return {
                    "action": result.get("action", "respond"),
                    "parameters": result.get("parameters", {}),
                    "confidence": result.get("confidence", 0.5),
                    "reasoning": result.get("reasoning", ""),
                    "strategy": "llm"
                }
            else:
                # 如果没有找到JSON，尝试解析文本
                return self._parse_text_response(response)
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse JSON response, using text parser", error=str(e))
            return self._parse_text_response(response)
    
    def _parse_text_response(self, response: str) -> Dict[str, Any]:
        """
        解析文本响应
        
        Args:
            response: 文本响应
            
        Returns:
            解析后的结果
        """
        # 简单的文本解析逻辑
        response_lower = response.lower()
        
        # 检测行动类型
        if any(word in response_lower for word in ["工具", "调用", "tool", "call"]):
            action = "tool_call"
        elif any(word in response_lower for word in ["委托", "delegate", "转交"]):
            action = "delegate"
        elif any(word in response_lower for word in ["跳过", "skip", "忽略"]):
            action = "skip"
        else:
            action = "respond"
        
        return {
            "action": action,
            "parameters": {
                "response": response.strip()
            },
            "confidence": 0.6,
            "reasoning": "基于文本内容分析得出的决策",
            "strategy": "llm"
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_calls"] / self.stats["total_calls"]
                if self.stats["total_calls"] > 0 else 0
            )
        }
    
    def update_model(self, model: str) -> None:
        """更新模型"""
        self.model = model
        logger.info("LLM model updated", new_model=model)
    
    def update_parameters(self, max_tokens: int = None, temperature: float = None) -> None:
        """更新参数"""
        if max_tokens is not None:
            self.max_tokens = max_tokens
        if temperature is not None:
            self.temperature = temperature
        
        logger.info(
            "LLM parameters updated",
            max_tokens=self.max_tokens,
            temperature=self.temperature
        ) 