# TraceWriter 使用说明

## 简介
TraceWriter 是一个简单的事件追踪（trace）记录工具，支持事件的记录与按 trace_id 查询。为实现日志与 trace 的统一管理，推荐所有模块通过 TraceWriter 进行事件追踪。

## 单例工厂
为保证全局唯一实例，建议通过 `get_trace_writer()` 获取 TraceWriter 对象。

```python
from src.monitoring.log.trace_writer import get_trace_writer

trace_writer = get_trace_writer()
```

## 记录事件
```python
trace_id = "task-001"
event_type = "TASK_STARTED"
payload = {"agent": "agentA", "info": "任务已启动"}

trace_writer.record_event(trace_id, event_type, payload)
```

## 查询事件
```python
events = trace_writer.get_events(trace_id)
for event in events:
    print(event)
```

## 推荐用法
- 统一通过 `get_trace_writer()` 获取实例。
- 在各业务模块中用 `record_event` 记录关键事件。
- 后续可扩展为持久化、异步、分布式 trace。

## 示例
```python
from src.monitoring.log.trace_writer import get_trace_writer

tw = get_trace_writer()
tw.record_event("trace-123", "AGENT_REGISTERED", {"agent": "A"})
print(tw.get_events("trace-123"))
``` 