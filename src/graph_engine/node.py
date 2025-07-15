class BaseNode:
    def __init__(self, name):
        self.name = name

    def execute(self, state):
        """执行节点逻辑，返回更新后的state"""
        raise NotImplementedError

class ReasonerNode(BaseNode):
    def __init__(self, name, reasoner):
        super().__init__(name)
        self.reasoner = reasoner

    def execute(self, state):
        # 伪代码：调用reasoner，生成action
        action = self.reasoner.decide(state)
        state['action'] = action
        state['next_node'] = action.get('next_node')
        return state

class ToolNode(BaseNode):
    def __init__(self, name, tool):
        super().__init__(name)
        self.tool = tool

    def execute(self, state):
        result = self.tool.run(state['action'])
        state['result'] = result
        return state

class CallbackNode(BaseNode):
    def __init__(self, name, callback):
        super().__init__(name)
        self.callback = callback

    def execute(self, state):
        self.callback.handle(state)
        return state

class EndNode(BaseNode):
    def execute(self, state):
        state['finished'] = True
        return state 