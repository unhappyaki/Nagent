class AgentContext:
    def __init__(self, session_id=None):
        self.session_id = session_id
        self.data = {}

    def set(self, key, value):
        self.data[key] = value

    def get(self, key, default=None):
        return self.data.get(key, default)

    def dump(self):
        return self.data.copy() 