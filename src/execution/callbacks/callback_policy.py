class CallbackPolicy:
    """
    回调行为后处理策略的统一抽象结构
    """
    def __init__(self, write_memory: bool, record_trace: bool, fallback_required: bool, trigger_next: bool):
        self.write_memory = write_memory
        self.record_trace = record_trace
        self.fallback_required = fallback_required
        self.trigger_next = trigger_next 