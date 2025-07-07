import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from datetime import datetime
from src.execution.callbacks.tool_result import ToolResult
from src.execution.callbacks.callback_policy import CallbackPolicy
from src.execution.callbacks.policy_resolver import PolicyResolver
from src.execution.callbacks.callback_context import CallbackContext
from src.execution.callbacks.callback_handler import CallbackHandler

# Mock回调实现
async def mock_memory_write(content, memory_type, context_id, trace_id, metadata):
    print(f"[memory_write] type={memory_type}, context_id={context_id}, trace_id={trace_id}, content={content}, metadata={metadata}")

async def mock_trace_write(event_type, data, context_id, trace_id):
    print(f"[trace_write] event_type={event_type}, context_id={context_id}, trace_id={trace_id}, data={data}")

async def mock_status_update(status, data, context_id):
    print(f"[status_update] status={status}, context_id={context_id}, data={data}")

async def mock_fallback_handler(result, context):
    print(f"[fallback_handler] Fallback triggered for tool={result.tool}, context_id={context.context_id}")
    return {"fallback": "default", "original_result": result.to_memory_entry()}

async def main():
    # 1. 构造ToolResult
    result = ToolResult(
        output="search result: agent企业级架构",
        success=False,  # 故意失败以测试fallback
        tool="search",
        trace_id="trace-001",
        timestamp=datetime.utcnow(),
        metadata={"confidence": 0.4, "extra": "test"}
    )
    # 2. 构造CallbackContext
    context = CallbackContext(
        trace_id="trace-001",
        context_id="ctx-001",
        source_agent="planner_agent",
        executing_agent="search_agent"
    )
    # 3. PolicyResolver生成策略
    resolver = PolicyResolver()
    policy = resolver.resolve(result, {"intent": "multi_step"})
    # 4. CallbackHandler注册mock回调
    handler = CallbackHandler(agent_id="search_agent")
    await handler.register_callback("memory_write", mock_memory_write)
    await handler.register_callback("trace_write", mock_trace_write)
    await handler.register_callback("status_update", mock_status_update)
    await handler.register_callback("fallback_handler", mock_fallback_handler)
    # 5. 执行策略驱动回调
    cb_result = await handler.handle_callback_with_policy(result, context, policy)
    print("\n[CallbackResult]", cb_result.to_dict())

if __name__ == "__main__":
    asyncio.run(main()) 