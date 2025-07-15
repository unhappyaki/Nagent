class Edge:
    def __init__(self, source, target, condition=None):
        self.source = source
        self.target = target
        self.condition = condition  # condition是个函数，输入state，返回True/False

    def is_active(self, state):
        if self.condition is None:
            return True
        return self.condition(state) 