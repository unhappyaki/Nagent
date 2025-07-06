"""
MCP适配器模块

提供MCP协议与现有Nagent架构的集成适配：
- MCP适配器：与工具注册表集成
- 工具包装器：MCPTool包装为BaseTool
- 外部工具注册表：MCP工具统一管理
- 监控集成：与监控系统集成
- 执行器集成：与执行器系统集成
"""

from .mcp_adapter import MCPAdapter
from .tool_wrapper import MCPToolWrapper
from .external_tool_registry import ExternalToolRegistry
from .monitoring_integration import MCPMonitoringIntegration
from .executor_integration import MCPExecutorIntegration

__all__ = [
    "MCPAdapter",
    "MCPToolWrapper", 
    "ExternalToolRegistry",
    "MCPMonitoringIntegration",
    "MCPExecutorIntegration"
] 