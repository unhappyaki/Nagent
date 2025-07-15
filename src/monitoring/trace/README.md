# Trace/快照/diff/replay 模块说明

## 1. TraceWriter
- 结构化记录全链路trace事件，支持过滤、采样、导出（json/mermaid）、快照/恢复。
- 典型用法：
```python
from src.monitoring.trace.trace_writer import TraceWriter
trace = TraceWriter()
trace.record_event(trace_id, "TOOL_EXEC", payload={...}, agent_id="agent1")
trace.query(trace_id=trace_id, event_type="TOOL_EXEC")
trace.export(trace_id, fmt="mermaid")
trace.snapshot()
```

## 2. SnapshotManager
- 任意时刻保存/恢复Session/Context/Memory/Trace的完整快照，支持命名、版本、持久化。
- 典型用法：
```python
from src.monitoring.trace.snapshot_manager import SnapshotManager
snap = SnapshotManager()
snap.save_snapshot("run1", session.snapshot())
all_files = snap.list_snapshots()
data = snap.load_snapshot(all_files[0])
```

## 3. DiffTool
- 对比任意两个快照/trace/memory，输出结构化差异，支持可视化diff。
- 典型用法：
```python
from src.monitoring.trace.diff_tool import DiffTool
diff = DiffTool.diff_snapshots(snap_a, snap_b)
print("\n".join(diff))
```

## 4. ReplayEngine
- 基于快照和trace，重现历史行为链，支持单步/全链回放。
- 典型用法：
```python
from src.monitoring.trace.replay_engine import ReplayEngine
replay = ReplayEngine()
replay.replay(snapshot, trace_events, step_by_step=True)
replay.replay_prompt(snapshot)
```

## 5. 典型场景
- 行为链异常调试、回放、对比分析
- prompt重建、行为链可视化、行为链diff
- 生产环境行为链审计、异常复现 