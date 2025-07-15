from adk.agent import Agent
from adk.tool import Tool
from adk.reasoner import Reasoner
from adk.agent_container import agent_container
from adk.prompt_manager import prompt_manager

# 注册工具
def echo_tool(ctx):
    return f"echo: {ctx.get('msg', '')}"
Tool.register("echo")(echo_tool)

def upper_tool(ctx):
    return ctx.get('msg', '').upper()
Tool.register("upper")(upper_tool)

# 注册推理器
def passthrough_reasoner(ctx):
    return ctx
Reasoner.register("pass")(passthrough_reasoner)

# 注册Prompt模板
prompt_manager.register_template("echo", "Echo: {{ msg }}")
prompt_manager.register_template("upper", "Upper: {{ msg }}")

# 定义两个Agent
class EchoAgent(Agent):
    def __init__(self):
        super().__init__(reasoner="pass", tools=["echo"], prompt="echo")

class UpperAgent(Agent):
    def __init__(self):
        super().__init__(reasoner="pass", tools=["upper"], prompt="upper")

# 注册到容器
agent_container.register("echo_agent", EchoAgent())
agent_container.register("upper_agent", UpperAgent())

# 测试调用
echo_result = agent_container.run("echo_agent", {"msg": "hello"})
upper_result = agent_container.run("upper_agent", {"msg": "hello"})

print("EchoAgent result:", echo_result)
print("UpperAgent result:", upper_result)
print("All agents:", agent_container.list()) 