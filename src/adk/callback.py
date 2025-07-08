class CallbackRegistry:
    def __init__(self):
        self._registry = {}

    def register(self, name, func):
        if name in self._registry:
            raise ValueError(f"Callback '{name}' already registered.")
        self._registry[name] = func

    def get(self, name):
        return self._registry.get(name)

    def list_tasks(self):
        return list(self._registry.keys()) 