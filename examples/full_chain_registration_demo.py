"""
全链路注册与能力发现测试
演示：本地Agent注册、A2A协议注册、统一注册中心能力发现
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import asyncio
from src.infrastructure.registry.unified_registry import UnifiedModuleRegistry
from src.communication.protocols.a2a.a2a_types import AgentCard
from src.communication.protocols.a2a.a2a_adapter import A2AAdapter

async def main():
    # 1. 初始化统一注册中心
    unified_registry = UnifiedModuleRegistry()

    # 2. 构建本地Agent能力卡片
    local_agent_card = AgentCard(
        agent_id="agent_local_001",
        name="本地数据分析Agent",
        description="企业内数据分析与处理",
        capabilities=["data_analysis", "file_ops"],
        endpoints={"task": "/agent_local_001/task"}
    )

    # 3. 通过A2A协议Server注册本地Agent
    a2a_adapter = A2AAdapter(unified_registry)
    server = a2a_adapter.setup_server(local_agent_card)
    reg_result = await server.register_agent()
    print(f"本地Agent注册结果: {reg_result}")

    # 4. 构造外部Agent能力卡片，模拟A2A协议发现
    external_agent_card = AgentCard(
        agent_id="agent_external_001",
        name="外部智能体",
        description="外部A2A生态智能体",
        capabilities=["nlp", "search"],
        endpoints={"task": "/agent_external_001/task"}
    )
    client = a2a_adapter.setup_client()
    await client.discover_and_register_agent(external_agent_card)
    print("外部Agent注册完成")

    # 5. 能力发现与健康监控
    print("注册中心能力列表：")
    agents = await unified_registry.agent_registry.list()
    for agent_id in agents:
        config = await unified_registry.agent_registry.get_agent_config(agent_id)
        print(f"Agent: {agent_id}, 能力: {config['capabilities']}, 状态: {config['metadata']['status']}")

    # 6. 输出注册历史
    print("注册历史：")
    print(unified_registry.get_registration_history(module_type="agent"))

if __name__ == '__main__':
    asyncio.run(main()) 