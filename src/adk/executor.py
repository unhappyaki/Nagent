class RuntimeExecutor:
    def __init__(self, agent_or_registry, memory=None):
        from .agent_base import AgentBase
        from .callback import CallbackRegistry
        from .memory import AgentMemory
        if isinstance(agent_or_registry, AgentBase):
            self.agent = agent_or_registry
            self.registry = None
            self.memory = self.agent.memory
        elif isinstance(agent_or_registry, CallbackRegistry):
            self.agent = None
            self.registry = agent_or_registry
            self.memory = memory or AgentMemory()
        else:
            raise ValueError("Must pass AgentBase or CallbackRegistry")

    def run_task(self, task_name, *args, **kwargs):
        try:
            if self.agent:
                print(f"[Executor] Running task: {task_name}")
                return self.agent.on_task(task_name, *args, **kwargs)
            elif self.registry:
                cb = self.registry.get(task_name)
                if cb:
                    print(f"[Executor] Running task: {task_name}")
                    return cb(self.memory, *args, **kwargs)
                raise ValueError(f"No callback found for task '{task_name}'")
        except Exception as e:
            print(f"[Error] Task '{task_name}' failed: {e}")
            return None 