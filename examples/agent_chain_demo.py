import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
import time
from src.core.tools.base_tool import BaseTool
from src.core.tools.tool_registry import LocalToolRegistry
from src.execution.tools.tool_executor import ToolExecutor
from src.execution.callbacks.callback_handler import CallbackHandler
from src.monitoring.log.trace_writer import TraceWriter

# 简单同步内存引擎适配器
class SimpleMemoryEngine:
    def __init__(self):
        self._results = []

    def store_result(self, result):
        self._results.append(result)

    def get_all(self):
        return self._results

# 1. 定义一个简单的工具（加法器）
class AddTool(BaseTool):
    def __init__(self):
        super().__init__(name="add", description="加法工具", permissions=["math:add"])

    def run(self, payload, context=None):
        a = payload.get("a", 0)
        b = payload.get("b", 0)
        return {"success": True, "result": a + b}

# 2. 初始化各核心模块
trace_writer = TraceWriter()
memory_engine = SimpleMemoryEngine()
tool_registry = LocalToolRegistry()
callback_handler = CallbackHandler(memory_engine, trace_writer)
tool_executor = ToolExecutor(tool_registry, trace_writer, callback_handler)

# 3. 注册工具
add_tool = AddTool()
tool_registry.register(add_tool)

# 4. 构造 Reasoner 输出的 action
trace_id = f"trace_{int(time.time())}"
context = {"agent_id": "demo_agent", "permissions": ["math:add"]}
action = {
    "tool": "add",
    "args": {"a": 7, "b": 5}
}

# 5. 通过 ToolExecutor 执行工具（自动走 ToolRouter/Callback/Trace/Memory）
try:
    print(f"\n[DEMO] 开始执行行为链，trace_id={trace_id}")
    result = tool_executor.execute(action, context, trace_id)
    print(f"[DEMO] 工具执行结果: {result}")
except Exception as e:
    print(f"[DEMO] 执行异常: {e}")

# 6. 检查 trace 和 memory 写入
print("\n[DEMO] TraceWriter 记录：")
for event in trace_writer.get_events(trace_id):
    print(event)

print("\n[DEMO] MemoryEngine 记录：")
for entry in memory_engine.get_all():
    print(entry) 