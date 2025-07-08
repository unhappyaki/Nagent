import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from adk import AgentBase, AgentRegistry, RuntimeExecutor, log
from concurrent.futures import ThreadPoolExecutor

# 1. ReACT Agent模式
def react_agent_demo():
    class ReACTAgent(AgentBase):
        def __init__(self, name):
            super().__init__(name)
            self.register_callback("react_cycle", self.react_cycle)
        def react_cycle(self, memory, context):
            reason = f"分析: {context['problem']}"
            action = f"行动: 针对{context['problem']}采取措施"
            observation = f"观察: 结果良好"
            memory.remember("last_cycle", {"reason": reason, "action": action, "observation": observation})
            return {"reason": reason, "action": action, "observation": observation}
    agent = ReACTAgent("reactor")
    executor = RuntimeExecutor(agent)
    result = executor.run_task("react_cycle", {"problem": "检测到异常流量"})
    print("[ReACT模式]", result)

# 2. 路由模式
def routing_demo():
    class RouterAgent(AgentBase):
        def __init__(self, name):
            super().__init__(name)
            self.register_callback("handle", self.handle)
        def handle(self, memory, task):
            return f"{self.name} 处理: {task}"
    registry = AgentRegistry()
    a = RouterAgent("A")
    b = RouterAgent("B")
    registry.register_agent("threat", a)
    registry.register_agent("vuln", b)
    def route_task(task_type, task):
        agent = registry.get_agent(task_type)
        return agent.on_task("handle", task)
    print("[路由模式]", route_task("threat", "威胁检测"), ",", route_task("vuln", "漏洞评估"))

# 3. 顺序模式
def sequential_demo():
    class StepAgent(AgentBase):
        def __init__(self, name):
            super().__init__(name)
            self.register_callback("step", self.step)
        def step(self, memory, context):
            return f"{self.name} 完成: {context}"
    registry = AgentRegistry()
    a = StepAgent("A")
    b = StepAgent("B")
    registry.register_agent("a", a)
    registry.register_agent("b", b)
    steps = [("a", "step"), ("b", "step")]
    context = "事件响应"
    results = []
    for agent_name, task in steps:
        agent = registry.get_agent(agent_name)
        results.append(agent.on_task(task, context))
    print("[顺序模式]", results)

# 4. 主从层次模式
def master_slave_demo():
    class SlaveAgent(AgentBase):
        def __init__(self, name):
            super().__init__(name)
            self.register_callback("handle", self.handle)
        def handle(self, memory, task):
            return f"{self.name} 执行: {task}"
    class MasterAgent(AgentBase):
        def __init__(self, name, slaves):
            super().__init__(name)
            self.slaves = slaves
            self.register_callback("delegate", self.delegate)
        def delegate(self, memory, task):
            results = [slave.on_task("handle", task) for slave in self.slaves]
            memory.remember("delegation", results)
            return results
    s1 = SlaveAgent("S1")
    s2 = SlaveAgent("S2")
    master = MasterAgent("M", [s1, s2])
    executor = RuntimeExecutor(master)
    print("[主从模式]", executor.run_task("delegate", "安全检查"))

# 5. 反思模式
def reflect_demo():
    class PartnerAgent(AgentBase):
        def __init__(self, name):
            super().__init__(name)
            self.register_callback("handle", self.handle)
        def handle(self, memory, input_):
            return f"{self.name} 处理: {input_}"
    class ReflectAgent(AgentBase):
        def __init__(self, name, partner):
            super().__init__(name)
            self.partner = partner
            self.register_callback("reflect", self.reflect)
        def reflect(self, memory, input_):
            partner_result = self.partner.on_task("handle", input_)
            reflection = f"反思: {partner_result}"
            memory.remember("last_reflection", reflection)
            return reflection
    p = PartnerAgent("P")
    r = ReflectAgent("R", p)
    print("[反思模式]", r.on_task("reflect", "上次检测结果"))

# 6. 辩论模式
def debate_demo():
    class Debater(AgentBase):
        def __init__(self, name):
            super().__init__(name)
            self.register_callback("debate", self.debate)
        def debate(self, memory, topic):
            return f"{self.name} 观点: {topic} 很重要"
    a = Debater("A")
    b = Debater("B")
    def debate_flow(agent_a, agent_b, topic):
        return {"A": agent_a.on_task("debate", topic), "B": agent_b.on_task("debate", topic)}
    print("[辩论模式]", debate_flow(a, b, "网络安全"))

# 7. 群聊模式
def group_chat_demo():
    class ChatAgent(AgentBase):
        def __init__(self, name):
            super().__init__(name)
            self.register_callback("chat", self.chat)
        def chat(self, memory, message):
            return f"{self.name} 回复: {message}"
    agents = [ChatAgent(f"C{i}") for i in range(3)]
    responses = [agent.on_task("chat", "大家好") for agent in agents]
    print("[群聊模式]", responses)

# 8. 异步群聊模式
def async_group_chat_demo():
    class ChatAgent(AgentBase):
        def __init__(self, name):
            super().__init__(name)
            self.register_callback("chat", self.chat)
        def chat(self, memory, message):
            return f"{self.name} 回复: {message}"
    agents = [ChatAgent(f"A{i}") for i in range(3)]
    async def async_group_chat():
        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(None, agent.on_task, "chat", "异步群聊") for agent in agents]
        return await asyncio.gather(*tasks)
    responses = asyncio.get_event_loop().run_until_complete(async_group_chat())
    print("[异步群聊模式]", responses)

# 9. 动态智能体添加模式
def dynamic_add_demo():
    class DynamicAgent(AgentBase):
        def __init__(self, name):
            super().__init__(name)
            self.register_callback("handle", self.handle)
        def handle(self, memory, task):
            return f"{self.name} 动态处理: {task}"
    registry = AgentRegistry()
    for i in range(2):
        agent = DynamicAgent(f"D{i}")
        registry.register_agent(f"d{i}", agent)
    results = [registry.get_agent(f"d{i}").on_task("handle", f"任务{i}") for i in range(2)]
    print("[动态添加模式]", results)

# 10. 并行化MOA仿神经网络模式
def parallel_moa_demo():
    class MOAAgent(AgentBase):
        def __init__(self, name):
            super().__init__(name)
            self.register_callback("process", self.process)
        def process(self, memory, input_):
            return f"{self.name} 输出: {input_}"
    agents = [MOAAgent(f"M{i}") for i in range(4)]
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(agent.on_task, "process", "输入信号") for agent in agents]
        results = [f.result() for f in futures]
    print("[并行MOA模式]", results)

if __name__ == "__main__":
    print("\n==== MAS 10种协作模式 ADK DEMO ====")
    react_agent_demo()
    routing_demo()
    sequential_demo()
    master_slave_demo()
    reflect_demo()
    debate_demo()
    group_chat_demo()
    async_group_chat_demo()
    dynamic_add_demo()
    parallel_moa_demo()
    print("==== END ====") 