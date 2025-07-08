import datetime
from src.monitoring.log.trace_writer import get_trace_writer

def log(message, trace_id="adk-log", event_type="LOG", agent_id=None, context_id=None):
    payload = {"message": message}
    if agent_id:
        payload["agent_id"] = agent_id
    if context_id:
        payload["context_id"] = context_id
    get_trace_writer().record_event(trace_id, event_type, payload) 