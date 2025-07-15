class ToolRegistry:
    def __init__(self):
        self.tools = {}
    def register(self, name):
        def decorator(fn):
            self.tools[name] = fn
            return fn
        return decorator
    def get(self, name):
        return self.tools.get(name)
    def list(self):
        return list(self.tools.keys())

tool_registry = ToolRegistry()

class Tool:
    register = tool_registry.register
    get = tool_registry.get
    list = tool_registry.list 