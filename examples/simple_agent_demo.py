from adk.agent import Agent
from adk.tool import Tool
from adk.reasoner import Reasoner
from adk.prompt_manager import prompt_manager

# 注册工具
def greet_tool(ctx):
    name = ctx.get("name", "world")
    return f"Hello, {name}!"
Tool.register("greet")(greet_tool)

# 注册推理器
def name_reasoner(ctx):
    # 直接返回输入，实际可做更复杂推理
    return ctx
Reasoner.register("simple")(name_reasoner)

# 注册Prompt模板
prompt_manager.register_template("greet", "请用中文打招呼：{{ name }}")

# 定义Agent
class SimpleAgent(Agent):
    def __init__(self):
        super().__init__(reasoner="simple", tools=["greet"], prompt="greet")

# 实例化并调用
agent = SimpleAgent()
result = agent.run({"name": "小明"})
print("Agent result:", result)
print("Agent trace:", agent.trace) 