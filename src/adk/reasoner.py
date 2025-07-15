class ReasonerRegistry:
    def __init__(self):
        self.reasoners = {}
    def register(self, name):
        def decorator(fn):
            self.reasoners[name] = fn
            return fn
        return decorator
    def get(self, name):
        return self.reasoners.get(name)
    def list(self):
        return list(self.reasoners.keys())

reasoner_registry = ReasonerRegistry()

class Reasoner:
    register = reasoner_registry.register
    get = reasoner_registry.get
    list = reasoner_registry.list 