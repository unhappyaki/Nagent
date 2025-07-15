from .node import BaseNode
from .edge import Edge
from .state import State

class Graph:
    def __init__(self):
        self.nodes = {}
        self.edges = []

    def add_node(self, node: BaseNode):
        self.nodes[node.name] = node

    def add_edge(self, edge: Edge):
        self.edges.append(edge)

    def get_next_node(self, current_node, state):
        for edge in self.edges:
            if edge.source == current_node and edge.is_active(state):
                return edge.target
        return None

    def run(self, start_node_name, state: State):
        current_node = self.nodes[start_node_name]
        while True:
            state = current_node.execute(state)
            if state.get('finished'):
                break
            next_node_name = state.get('next_node') or self.get_next_node(current_node.name, state)
            if not next_node_name:
                break
            current_node = self.nodes[next_node_name]
        return state 