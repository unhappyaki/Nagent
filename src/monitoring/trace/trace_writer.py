import json
from datetime import datetime

class TraceWriter:
    def __init__(self):
        self.events = []

    def record_event(self, trace_id, event_type, payload=None, agent_id=None, session_id=None, context_id=None, timestamp=None):
        event = {
            "trace_id": trace_id,
            "event_type": event_type,
            "timestamp": timestamp or datetime.utcnow().isoformat(),
            "agent_id": agent_id,
            "session_id": session_id,
            "context_id": context_id,
            "payload": payload or {}
        }
        self.events.append(event)

    def query(self, trace_id=None, event_type=None, agent_id=None, time_range=None):
        results = self.events
        if trace_id:
            results = [e for e in results if e["trace_id"] == trace_id]
        if event_type:
            results = [e for e in results if e["event_type"] == event_type]
        if agent_id:
            results = [e for e in results if e["agent_id"] == agent_id]
        if time_range:
            start, end = time_range
            results = [e for e in results if start <= e["timestamp"] <= end]
        return results

    def export(self, trace_id, fmt="json"):
        events = self.query(trace_id=trace_id)
        if fmt == "json":
            return json.dumps(events, ensure_ascii=False, indent=2)
        elif fmt == "mermaid":
            return self.export_mermaid(trace_id)
        elif fmt == "graphviz":
            return self.export_graphviz(trace_id)
        else:
            raise ValueError(f"Unknown format: {fmt}")

    def export_mermaid(self, trace_id):
        events = self.query(trace_id=trace_id)
        lines = ["graph TD"]
        prev = None
        for i, e in enumerate(events):
            node = f"N{i}[{e['event_type']}]"
            if prev:
                lines.append(f"{prev} --> {node}")
            prev = node
        return "\n".join(lines)

    def export_graphviz(self, trace_id):
        events = self.query(trace_id=trace_id)
        lines = ["digraph G {"]
        prev = None
        for i, e in enumerate(events):
            node = f"N{i} [label=\"{e['event_type']}\"]"
            lines.append(node)
            if prev is not None:
                lines.append(f"N{prev} -> N{i}")
            prev = i
        lines.append("}")
        return "\n".join(lines)

    def aggregate_traces(self, trace_ids):
        # 聚合多条trace，返回事件列表
        agg = []
        for tid in trace_ids:
            agg.extend(self.query(trace_id=tid))
        return agg

    def replay_trace(self, trace_id, verbose=True):
        events = self.query(trace_id=trace_id)
        for i, e in enumerate(events):
            print(f"Step {i+1}: [{e['event_type']}] @ {e['timestamp']}")
            if verbose:
                print(f"  Payload: {json.dumps(e['payload'], ensure_ascii=False)}")
        print("[Replay End]")

    def sample(self, strategy="head", n=10):
        if strategy == "head":
            return self.events[:n]
        elif strategy == "tail":
            return self.events[-n:]
        else:
            raise ValueError("Unsupported sampling strategy")

    def snapshot(self):
        return list(self.events)

    def restore(self, events):
        self.events = list(events) 