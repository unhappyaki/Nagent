from .memory import AgentMemory

class AgentBase:
    def __init__(self, name, memory=None):
        self.name = name
        self.memory = memory or AgentMemory()
        self.callbacks = {}

    def register_callback(self, name, func):
        if name in self.callbacks:
            raise ValueError(f"Callback '{name}' already registered.")
        self.callbacks[name] = func

    def on_task(self, task_name, *args, **kwargs):
        cb = self.callbacks.get(task_name)
        if cb:
            return cb(self.memory, *args, **kwargs)
        raise ValueError(f"No callback for {task_name}")

    def on_start(self):
        pass
    def on_finish(self):
        pass 