from adk.agent import Agent
from adk.tool import Tool
from adk.reasoner import Reasoner
from adk.agent_container import AgentContainer
from adk.agent_manager import agent_manager
from adk.prompt_manager import prompt_manager

# 定义简单工具和推理器
@Tool.register("echo")
def echo_tool(ctx):
    return f"echo: {ctx.get('msg', '')}"

@Reasoner.register("pass")
def passthrough(ctx):
    return ctx

prompt_manager.register_template("echo", "Echo: {{ msg }}")

class EchoAgent(Agent):
    def __init__(self):
        super().__init__(reasoner="pass", tools=["echo"], prompt="echo")

# 创建两个容器
container1 = AgentContainer()
container2 = AgentContainer()

container1.register("echo1", EchoAgent())
container2.register("echo2", EchoAgent())

# 注册容器到AgentManager
agent_manager.add_container("c1", container1)
agent_manager.add_container("c2", container2)

# 启动、停止、重启、健康检查
agent_manager.start_agent("c1", "echo1")
agent_manager.start_agent("c2", "echo2")
print("Status c1-echo1:", agent_manager.status("c1", "echo1"))
print("Status c2-echo2:", agent_manager.status("c2", "echo2"))

agent_manager.stop_agent("c1", "echo1")
print("After stop, c1-echo1:", agent_manager.status("c1", "echo1"))

agent_manager.restart_agent("c1", "echo1")
print("After restart, c1-echo1:", agent_manager.status("c1", "echo1"))

print("Health check c2-echo2:", agent_manager.health_check("c2", "echo2")) 