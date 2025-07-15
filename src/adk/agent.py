from adk.tool import tool_registry
from adk.reasoner import reasoner_registry
from adk.prompt_manager import prompt_manager
from adk.memory import AgentMemory
from monitoring.trace.trace_writer import TraceWriter

class Agent:
    def __init__(self, reasoner=None, tools=None, prompt=None, memory=None, trace_writer=None):
        self.reasoner = reasoner_registry.get(reasoner) if isinstance(reasoner, str) else reasoner
        self.tools = [tool_registry.get(t) if isinstance(t, str) else t for t in (tools or [])]
        self.prompt = prompt
        self.memory = memory or AgentMemory()
        self.trace_writer = trace_writer or TraceWriter()
        self.trace_id = None

    def run(self, input_data, context=None):
        self.trace_id = input_data.get("trace_id", "agent-trace")
        # 1. 构造prompt
        prompt_str = None
        if self.prompt:
            prompt_str = prompt_manager.render_template(self.prompt, input_data)
        # 2. 推理决策
        ctx = context or {}
        ctx.update(input_data)
        if prompt_str:
            ctx["prompt"] = prompt_str
        decision = self.reasoner(ctx) if self.reasoner else ctx
        # 3. 工具调用
        result = None
        for tool in self.tools:
            result = tool(decision)
        # 4. 记忆与trace
        self.memory.remember("last_result", result)
        self.trace_writer.record_event(self.trace_id, "AGENT_RUN", {"input": input_data, "decision": decision, "result": result})
        return result

    @property
    def memory_store(self):
        return self.memory

    @property
    def trace(self):
        return self.trace_writer.query(trace_id=self.trace_id) 