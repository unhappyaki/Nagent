class CallbackContext:
    """
    回调上下文绑定结构，支持多Agent权限归属
    """
    def __init__(self, trace_id: str, context_id: str, source_agent: str, executing_agent: str):
        self.trace_id = trace_id
        self.context_id = context_id
        self.source_agent = source_agent
        self.executing_agent = executing_agent 