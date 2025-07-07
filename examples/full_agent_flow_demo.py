import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from datetime import datetime

from src.execution.callbacks.callback_handler import CallbackHandler
from src.execution.callbacks.callback_hub import CallbackHub
from src.execution.callbacks.policy_resolver import PolicyResolver
from src.execution.callbacks.callback_context import CallbackContext
from src.execution.callbacks.tool_result import ToolResult
from src.core.reasoning.llm_reasoner import LLMReasoner

# Mock Agent注册中心
class MockAgentRegistry:
    def __init__(self):
        self.agents = {}
    def register(self, agent_id, agent_obj):
        self.agents[agent_id] = agent_obj
        print(f"[AgentRegistry] Registered agent: {agent_id}")

# Mock ACPClient
class MockACPClient:
    async def send_behavior_package(self, behavior_package):
        print(f"[ACPClient] Sent behavior package: {behavior_package}")
        return True

# Mock BIRRouter
class MockBIRRouter:
    def __init__(self, agent_registry):
        self.agent_registry = agent_registry
    async def dispatch(self, behavior_package):
        agent_id = behavior_package['to_agent']
        agent = self.agent_registry.agents.get(agent_id)
        if agent:
            return await agent.handle_task(behavior_package)
        else:
            print(f"[BIRRouter] Agent {agent_id} not found")
            return None

# DemoAgent，收到任务后LLM推理并回调
class DemoAgent:
    def __init__(self, agent_id, callback_hub):
        self.agent_id = agent_id
        self.callback_hub = callback_hub
        self.llm = LLMReasoner(model="qwen-turbo")
    async def handle_task(self, behavior_package):
        print(f"[Agent] {self.agent_id} received task: {behavior_package['payload']}")
        # LLM推理
        try:
            result_text = await self.llm.reason(task=behavior_package['payload']['instruction'], context=[])
            success = True
        except Exception as e:
            result_text = f"LLM推理失败: {e}"
            success = False
        # 回调链
        tool_result = ToolResult(
            output=result_text, success=success, tool="llm", trace_id=behavior_package['trace_id'], metadata={}
        )
        context = CallbackContext(
            trace_id=behavior_package['trace_id'],
            context_id=behavior_package['context_id'],
            source_agent=behavior_package['from_agent'],
            executing_agent=self.agent_id
        )
        policy = PolicyResolver().resolve(tool_result, {"intent": "multi_step"})
        cb_result = await self.callback_hub.handler.handle_callback_with_policy(tool_result, context, policy)
        print("[Agent] Callback result:", cb_result.to_dict())
        return cb_result

# Mock trace_writer和runtime
class MockTraceWriter:
    def record(self, *a, **k):
        print("[trace]", a, k)
class MockRuntime:
    class Executor:
        def run_next_step(self, *a, **k):
            print("[run_next_step]", a, k)
    executor = Executor()

async def main():
    # 1. 注册Agent
    agent_registry = MockAgentRegistry()
    handler = CallbackHandler(agent_id="demo_agent")
    await handler.register_callback("memory_write", lambda *a, **k: print("[memory_write]", a, k))
    await handler.register_callback("trace_write", lambda *a, **k: print("[trace_write]", a, k))
    await handler.register_callback("status_update", lambda *a, **k: print("[status_update]", a, k))
    await handler.register_callback("fallback_handler", lambda *a, **k: print("[fallback_handler]", a, k))
    callback_hub = CallbackHub(
        handler,
        fallback=None,
        trace_writer=MockTraceWriter(),
        runtime=MockRuntime(),
        policy_resolver=PolicyResolver()
    )
    agent = DemoAgent("demo_agent", callback_hub)
    agent_registry.register("demo_agent", agent)

    # 2. ACP通信/任务分发
    acp_client = MockACPClient()
    bir_router = MockBIRRouter(agent_registry)
    behavior_package = {
        "from_agent": "user_001",
        "to_agent": "demo_agent",
        "context_id": "ctx-001",
        "trace_id": "trace-001",
        "payload": {"instruction": "请写一个Python打印九九乘法表的代码。"}
    }
    await acp_client.send_behavior_package(behavior_package)
    await bir_router.dispatch(behavior_package)

if __name__ == "__main__":
    asyncio.run(main()) 