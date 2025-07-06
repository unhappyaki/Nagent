import asyncio
from src.infrastructure.registry.unified_registry import UnifiedModuleRegistry
from src.communication.protocols.a2a.a2a_types import AgentCard
from src.communication.protocols.a2a.a2a_client import A2AClient
from src.communication.protocols.acp.acp_client import ACPClient
from src.communication.protocols.acp.acp_server import ACPServer
from src.coordination.container.agent_container import AgentContainer
from src.coordination.container.container_manager import ContainerConfig

async def main():
    # 1. 初始化注册中心和AgentCard
    registry = UnifiedModuleRegistry()
    agent_card = AgentCard(
        agent_id="agent-001",
        name="DemoAgent",
        description="A demo agent for A2A+ACP integration",
        capabilities=["demo_task", "echo"],
        endpoints={"acp": "http://localhost:8000/acp"}
    )
    config = ContainerConfig(
        agent_id="agent-001",
        agent_type="demo",
        agent_card=agent_card,
        acp_config={"host": "localhost", "port": 8000},
        environment={}
    )

    # 2. 启动AgentContainer（注册A2A能力并启动ACPServer）
    container = AgentContainer("container-001", config, registry)
    await container.start()
    print("[Container] Agent started and registered.")

    # 3. 用A2AClient发现并注册Agent（模拟外部发现）
    a2a_client = A2AClient(registry)
    await a2a_client.discover_and_register_agent(agent_card)
    print("[A2AClient] Agent discovered and registered.")

    # 4. 构造行为包，通过ACPClient发送到AgentContainer
    acp_client = ACPClient(server_url="http://localhost:8000")
    behavior_package = {
        "intent": "echo",
        "from_agent": "tester",
        "to_agent": "agent-001",
        "payload": {"text": "Hello, Agent!"},
        "trace_id": "trace-123",
        "context_id": "session-abc",
        "timestamp": int(asyncio.get_event_loop().time())
    }
    result = acp_client.send_behavior_package(behavior_package)
    print(f"[ACPClient] Sent behavior package, result: {result}")

    # 5. 查询Agent能力卡片
    agent_card_info = container.get_agent_card()
    print(f"[Container] AgentCard: {agent_card_info}")

    # 6. 停止容器
    await container.stop()
    print("[Container] Agent stopped.")

if __name__ == "__main__":
    asyncio.run(main()) 