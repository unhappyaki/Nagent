from .tool_result import ToolResult
from .callback_policy import CallbackPolicy
from typing import Dict, Any

class PolicyResolver:
    """
    策略解析器，根据ToolResult和上下文生成CallbackPolicy
    """
    def resolve(self, result: ToolResult, context: Dict[str, Any]) -> CallbackPolicy:
        # 示例策略：失败时fallback，search置信度低不写memory，多步任务触发下一步
        fallback_required = not result.success
        write_memory = result.success and result.metadata.get("confidence", 1.0) >= 0.5
        record_trace = True
        trigger_next = context.get("intent") == "multi_step"
        return CallbackPolicy(
            write_memory=write_memory,
            record_trace=record_trace,
            fallback_required=fallback_required,
            trigger_next=trigger_next
        ) 