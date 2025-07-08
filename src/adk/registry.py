class AgentRegistry:
    def __init__(self):
        self._agents = {}

    def register_agent(self, name, agent):
        if name in self._agents:
            raise ValueError(f"Agent '{name}' already registered.")
        self._agents[name] = agent

    def get_agent(self, name):
        return self._agents.get(name)

    def list_agents(self):
        return list(self._agents.keys()) 