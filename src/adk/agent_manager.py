class AgentManager:
    def __init__(self):
        self.containers = {}
        self.agent_status = {}  # {(container, agent): status}
    def add_container(self, name, container):
        self.containers[name] = container
    def start_agent(self, container_name, agent_name):
        # 启动逻辑（此处模拟为设置状态）
        self.agent_status[(container_name, agent_name)] = "running"
    def stop_agent(self, container_name, agent_name):
        self.agent_status[(container_name, agent_name)] = "stopped"
    def restart_agent(self, container_name, agent_name):
        self.stop_agent(container_name, agent_name)
        self.start_agent(container_name, agent_name)
    def health_check(self, container_name, agent_name):
        # 简单模拟，实际可扩展为心跳/探针
        return self.agent_status.get((container_name, agent_name), "unknown")
    def status(self, container_name, agent_name):
        return self.agent_status.get((container_name, agent_name), "unknown")

agent_manager = AgentManager() 