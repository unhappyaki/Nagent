"""
控制桥接器 (Control Adapter) 实现
基于企业级架构实践的ACP协议到执行器的适配层
"""

import json
import logging
from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass

from .acp_client import ACPPayload
from .message_schema import ACPPayload


class ActionType(Enum):
    """动作类型枚举"""
    API_CALL = "api_call"
    SHELL_EXEC = "shell_exec"
    WEB_ACTION = "web_action"
    MODEL_CALL = "model_call"
    TOOL_EXEC = "tool_exec"
    CUSTOM = "custom"


@dataclass
class ControlResult:
    """控制执行结果"""
    control_id: str
    status: str  # success, failed, error
    output: Dict[str, Any]
    trace: Dict[str, Any]
    error_message: Optional[str] = None


class ControlAdapter(ABC):
    """
    控制适配器基类
    定义从ACP协议到具体执行器的标准接口
    """
    
    @abstractmethod
    def match(self, action_type: str) -> bool:
        """
        判断是否支持当前控制类型
        
        Args:
            action_type: 动作类型
            
        Returns:
            bool: 是否支持
        """
        pass
    
    @abstractmethod
    async def execute(self, acp_payload: ACPPayload) -> ControlResult:
        """
        执行ACP载荷
        
        Args:
            acp_payload: ACP载荷
            
        Returns:
            ControlResult: 执行结果
        """
        pass


class APIControlAdapter(ControlAdapter):
    """
    API控制适配器
    处理HTTP API调用
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def match(self, action_type: str) -> bool:
        """判断是否支持API调用"""
        return action_type == ActionType.API_CALL.value
    
    async def execute(self, acp_payload: ACPPayload) -> ControlResult:
        """
        执行API调用
        
        Args:
            acp_payload: ACP载荷
            
        Returns:
            ControlResult: 执行结果
        """
        try:
            # 从载荷中提取API调用信息
            data = acp_payload.data
            endpoint = data.get("endpoint", "")
            method = data.get("method", "POST")
            params = data.get("params", {})
            headers = data.get("headers", {})
            
            # 这里应该实现实际的HTTP请求
            # 为了简化，我们返回模拟结果
            result = {
                "endpoint": endpoint,
                "method": method,
                "params": params,
                "response": {"status": "success", "data": "API调用成功"}
            }
            
            return ControlResult(
                control_id=getattr(acp_payload, 'trace_id', None),
                status="success",
                output=result,
                trace={"duration_ms": 100, "timestamp": getattr(acp_payload, 'timestamp', None)}
            )
            
        except Exception as e:
            self.logger.error(f"API调用失败: {e}")
            return ControlResult(
                control_id=getattr(acp_payload, 'trace_id', None),
                status="error",
                output={},
                trace={"timestamp": getattr(acp_payload, 'timestamp', None)},
                error_message=str(e)
            )


class ToolControlAdapter(ControlAdapter):
    """
    工具控制适配器
    处理工具执行
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tools = {}  # 工具注册表
    
    def match(self, action_type: str) -> bool:
        """判断是否支持工具执行"""
        return action_type == ActionType.TOOL_EXEC.value
    
    async def execute(self, acp_payload: ACPPayload) -> ControlResult:
        """
        执行工具调用
        
        Args:
            acp_payload: ACP载荷
            
        Returns:
            ControlResult: 执行结果
        """
        try:
            # 从载荷中提取工具信息
            data = acp_payload.data
            tool_name = data.get("tool_name", "")
            tool_params = data.get("tool_params", {})
            
            # 查找工具
            if tool_name not in self.tools:
                raise ValueError(f"工具 {tool_name} 未注册")
            
            tool_func = self.tools[tool_name]
            
            # 执行工具
            tool_result = await tool_func(tool_params)
            
            return ControlResult(
                control_id=getattr(acp_payload, 'trace_id', None),
                status="success",
                output={"tool_name": tool_name, "result": tool_result},
                trace={"duration_ms": 50, "timestamp": getattr(acp_payload, 'timestamp', None)}
            )
            
        except Exception as e:
            self.logger.error(f"工具执行失败: {e}")
            return ControlResult(
                control_id=getattr(acp_payload, 'trace_id', None),
                status="error",
                output={},
                trace={"timestamp": getattr(acp_payload, 'timestamp', None)},
                error_message=str(e)
            )
    
    def register_tool(self, tool_name: str, tool_func: Callable):
        """注册工具"""
        self.tools[tool_name] = tool_func


class ModelControlAdapter(ControlAdapter):
    """
    模型控制适配器
    处理大模型调用
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def match(self, action_type: str) -> bool:
        """判断是否支持模型调用"""
        return action_type == ActionType.MODEL_CALL.value
    
    async def execute(self, acp_payload: ACPPayload) -> ControlResult:
        """
        执行模型调用
        
        Args:
            acp_payload: ACP载荷
            
        Returns:
            ControlResult: 执行结果
        """
        try:
            # 从载荷中提取模型调用信息
            data = acp_payload.data
            model_id = data.get("model_id", "gpt-4")
            prompt = data.get("prompt", "")
            parameters = data.get("parameters", {})
            
            # 这里应该实现实际的模型调用
            # 为了简化，我们返回模拟结果
            result = {
                "model_id": model_id,
                "prompt": prompt,
                "response": f"模型 {model_id} 的响应: {prompt[:50]}..."
            }
            
            return ControlResult(
                control_id=getattr(acp_payload, 'trace_id', None),
                status="success",
                output=result,
                trace={"duration_ms": 1500, "timestamp": getattr(acp_payload, 'timestamp', None)}
            )
            
        except Exception as e:
            self.logger.error(f"模型调用失败: {e}")
            return ControlResult(
                control_id=getattr(acp_payload, 'trace_id', None),
                status="error",
                output={},
                trace={"timestamp": getattr(acp_payload, 'timestamp', None)},
                error_message=str(e)
            )


class ControlDispatcher:
    """
    控制分发器
    负责将ACP载荷分发给合适的控制适配器
    """
    
    def __init__(self, trace_writer=None):
        self.adapters: List[ControlAdapter] = []
        self.trace_writer = trace_writer
        self.logger = logging.getLogger(__name__)
        
        # 注册默认适配器
        self._register_default_adapters()
    
    def _register_default_adapters(self):
        """注册默认适配器"""
        self.adapters.append(APIControlAdapter())
        self.adapters.append(ToolControlAdapter())
        self.adapters.append(ModelControlAdapter())
    
    def register_adapter(self, adapter: ControlAdapter):
        """注册控制适配器"""
        self.adapters.append(adapter)
    
    async def dispatch(self, acp_payload: ACPPayload) -> ControlResult:
        """
        分发ACP载荷到合适的适配器
        
        Args:
            acp_payload: ACP载荷
            
        Returns:
            ControlResult: 执行结果
        """
        try:
            # 从载荷中提取动作类型
            action_type = acp_payload.data.get("action_type", "")
            # 兼容新版 trace_id、context_id、timestamp
            meta = getattr(acp_payload, 'metadata', {}) or {}
            trace_id = meta.get('trace_id')
            context_id = meta.get('context_id')
            timestamp = meta.get('timestamp')
            # 查找匹配的适配器
            for adapter in self.adapters:
                if adapter.match(action_type):
                    # 记录trace
                    if self.trace_writer:
                        self.trace_writer.record_acp_message(
                            trace_id=trace_id,
                            context_id=context_id,
                            message_type="control_dispatch",
                            payload={"action_type": action_type, "adapter": adapter.__class__.__name__}
                        )
                    # 执行控制
                    result = await adapter.execute(acp_payload)
                    # 记录结果trace
                    if self.trace_writer:
                        self.trace_writer.record_acp_message(
                            trace_id=trace_id,
                            context_id=context_id,
                            message_type="control_result",
                            payload={"status": result.status, "output": result.output}
                        )
                    return result
            # 没有找到匹配的适配器
            error_msg = f"没有找到支持动作类型 {action_type} 的适配器"
            self.logger.error(error_msg)
            return ControlResult(
                control_id=trace_id,
                status="error",
                output={},
                trace={"timestamp": timestamp},
                error_message=error_msg
            )
            
        except Exception as e:
            self.logger.error(f"控制分发失败: {e}")
            return ControlResult(
                control_id=acp_payload.trace_id,
                status="error",
                output={},
                trace={"timestamp": acp_payload.timestamp},
                error_message=str(e)
            )
    
    def get_supported_actions(self) -> List[str]:
        """获取支持的动作类型"""
        supported = []
        for action_type in ActionType:
            for adapter in self.adapters:
                if adapter.match(action_type.value):
                    supported.append(action_type.value)
                    break
        return supported
