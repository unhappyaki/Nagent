from .a2a_types import AgentCard, A2AAgentRegistration
from datetime import datetime
from typing import Dict, Any, List, Optional

class A2AServer:
    """A2A协议服务器实现骨架"""
    def __init__(self, unified_registry, agent_card: AgentCard):
        self.unified_registry = unified_registry
        self.agent_card = agent_card
        self.registration: Optional[A2AAgentRegistration] = None

    async def register_agent(self):
        """注册本地Agent到统一注册中心"""
        now = datetime.utcnow().isoformat()
        self.registration = A2AAgentRegistration(
            agent_card=self.agent_card,
            registered_at=now,
            status="online"
        )
        await self.unified_registry.register_module(
            module_type="agent",
            module_id=self.agent_card.agent_id,
            module_config=self.agent_card.to_dict(),
            metadata={"a2a": True}
        )
        return self.registration

    async def get_agent_card(self) -> AgentCard:
        return self.agent_card

    async def get_capabilities(self) -> List[str]:
        return self.agent_card.capabilities 