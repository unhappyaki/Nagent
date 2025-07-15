# Graph Engine 模块说明

## 1. 作用
- 支持用“节点-边-状态-图”方式定义和运行智能体推理流
- 支持分支、回环、终止等复杂流程
- 可扩展支持并发、RL策略等

## 2. 快速上手

```python
from src.graph_engine.node import ReasonerNode, ToolNode, CallbackNode, EndNode
from src.graph_engine.edge import Edge
from src.graph_engine.state import State
from src.graph_engine.graph import Graph

# 假设你有reasoner/tool/callback对象
reasoner = ...  # 你的Reasoner实现
tool = ...      # 你的Tool实现
callback = ...  # 你的Callback实现

g = Graph()
g.add_node(ReasonerNode('reasoner', reasoner))
g.add_node(ToolNode('tool', tool))
g.add_node(CallbackNode('callback', callback))
g.add_node(EndNode('end'))

g.add_edge(Edge('reasoner', 'tool'))
g.add_edge(Edge('tool', 'callback'))
g.add_edge(Edge('callback', 'end'))

state = State(intent='generate_report', context_id='session-001')
result = g.run('reasoner', state)
print(result)
```

## 3. 高级用法
- 支持条件分支：Edge('callback', 'reasoner', condition=lambda s: s['result']['success'] is False)
- 支持回环、并发、RL Controller等（可扩展）

## 4. 目录结构
- node.py：节点定义
- edge.py：边定义
- state.py：状态对象
- graph.py：图结构和运行主逻辑 