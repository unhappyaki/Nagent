from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class AgentCard:
    """A2A智能体能力卡片"""
    agent_id: str
    name: str
    description: str
    capabilities: List[str]
    version: str = "1.0.0"
    endpoints: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentCard':
        return cls(**data)

@dataclass
class A2AAgentRegistration:
    """A2A协议Agent注册信息"""
    agent_card: AgentCard
    registered_at: str
    last_heartbeat: Optional[str] = None
    status: str = "registering"
    connection_info: Optional[Dict[str, Any]] = None
    performance_stats: Optional[Dict[str, Any]] = None 