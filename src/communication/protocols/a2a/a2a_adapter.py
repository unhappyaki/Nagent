from .a2a_types import AgentCard
from .a2a_server import A2AServer
from .a2a_client import A2AClient

class A2AAdapter:
    """A2A协议注册适配器，桥接A2A协议与统一注册中心"""
    def __init__(self, unified_registry):
        self.unified_registry = unified_registry
        self.server = None
        self.client = None

    def setup_server(self, agent_card: AgentCard):
        self.server = A2AServer(self.unified_registry, agent_card)
        return self.server

    def setup_client(self):
        self.client = A2AClient(self.unified_registry)
        return self.client 