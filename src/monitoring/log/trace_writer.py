class TraceWriter:
    """
    简单的 TraceWriter 实现，支持事件记录和按 trace_id 查询。
    """
    def __init__(self):
        self._events = {}

    def record_event(self, trace_id, event_type, payload):
        event = {
            "trace_id": trace_id,
            "event_type": event_type,
            "payload": payload
        }
        self._events.setdefault(trace_id, []).append(event)

    def get_events(self, trace_id):
        return self._events.get(trace_id, [])

    async def initialize(self):
        """兼容框架的初始化流程，实际可为空实现"""
        pass

    async def start_trace(self, trace_id, task):
        """兼容追踪调用，空实现"""
        pass
    async def end_trace(self, trace_id, execution_result):
        """兼容追踪调用，空实现"""
        pass

_trace_writer_instance = None

def get_trace_writer():
    """
    获取全局唯一的 TraceWriter 实例。
    Returns:
        TraceWriter: 单例 TraceWriter 对象
    """
    global _trace_writer_instance
    if _trace_writer_instance is None:
        _trace_writer_instance = TraceWriter()
    return _trace_writer_instance 