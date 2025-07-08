class AgentMemory:
    def __init__(self):
        self._store = {}

    def remember(self, key, value):
        self._store[key] = value

    def recall(self, key):
        return self._store.get(key)

    def dump_all(self):
        return self._store.copy()

    def load_all(self, data):
        self._store.update(data) 