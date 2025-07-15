class AgentContainer:
    def __init__(self):
        self.agents = {}
    def register(self, name, agent):
        self.agents[name] = agent
    def get(self, name):
        return self.agents.get(name)
    def list(self):
        return list(self.agents.keys())
    def run(self, name, input_data):
        agent = self.get(name)
        return agent.run(input_data) if agent else None

agent_container = AgentContainer() 