from datetime import datetime
from typing import Any, Dict

class ToolResult:
    """
    工具调用结果的结构化抽象模型
    """
    def __init__(self, output: Any, success: bool, tool: str, trace_id: str, timestamp: datetime = None, metadata: Dict[str, Any] = None):
        self.output = output
        self.success = success
        self.tool = tool
        self.trace_id = trace_id
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}

    def to_memory_entry(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "output": self.output,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    def to_trace_event(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "output": self.output,
        } 