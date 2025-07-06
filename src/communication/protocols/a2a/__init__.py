# A2A协议核心实现骨架
# 参考MCP协议结构，支持Agent Card、注册、能力发现、任务流转等

from .a2a_types import AgentCard, A2AAgentRegistration
from .a2a_server import A2AServer
from .a2a_client import A2AClient
from .a2a_adapter import A2AAdapter 