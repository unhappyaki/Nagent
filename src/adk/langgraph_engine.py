from langgraph.graph import StateGraph
import time

class LangGraphEngine:
    def __init__(self):
        self.graph = StateGraph()
        self.entry_node = None
        self._trace_writer = None
        self._node_funcs = {}

    def add_node(self, name, func):
        self._node_funcs[name] = func
        if self._trace_writer:
            # 包裹trace逻辑
            def traced_func(state, _name=name, _func=func):
                start = time.time()
                try:
                    result = _func(state)
                    self._trace_writer.record_event(
                        state.get("trace_id", "unknown"),
                        "NODE_EXEC",
                        {
                            "node": _name,
                            "input": state,
                            "output": result,
                            "duration": round(time.time()-start, 4),
                            "success": True
                        }
                    )
                    return result
                except Exception as e:
                    self._trace_writer.record_event(
                        state.get("trace_id", "unknown"),
                        "NODE_ERROR",
                        {
                            "node": _name,
                            "input": state,
                            "error": str(e),
                            "duration": round(time.time()-start, 4),
                            "success": False
                        }
                    )
                    raise
            self.graph.add_node(name, traced_func)
        else:
            self.graph.add_node(name, func)

    def add_edge(self, source, target, condition=None):
        self.graph.add_edge(source, target, condition=condition)

    def add_parallel(self, nodes, next_node):
        # 并发节点，LangGraph支持add_parallel
        self.graph.add_parallel(nodes, next_node=next_node)

    def set_entry(self, name):
        self.entry_node = name
        self.graph.set_entry(name)

    def with_trace(self, trace_writer):
        self._trace_writer = trace_writer
        # 重新注册所有已添加节点，包裹trace
        for name, func in self._node_funcs.items():
            self.graph.add_node(name, func)  # 会被traced_func包裹
        return self

    def run(self, state):
        if not self.entry_node:
            raise ValueError("Entry node not set")
        return self.graph.run(state)

StateGraph = LangGraphEngine 