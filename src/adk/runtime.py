class ADKRuntime:
    def __init__(self, agent_registry):
        self.agent_registry = agent_registry

    def run(self, agent_name, task, *args, **kwargs):
        agent = self.agent_registry.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not registered.")
        from .executor import RuntimeExecutor
        executor = RuntimeExecutor(agent)
        return executor.run_task(task, *args, **kwargs) 