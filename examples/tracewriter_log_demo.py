import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.adk.logger import log
import time

if __name__ == "__main__":
    # 基本日志
    log("系统启动", trace_id="demo-001", event_type="SYSTEM_START", agent_id="agentA", context_id="ctx-001")
    
    # 业务事件
    log("任务分发", trace_id="task-123", event_type="TASK_DISPATCH", agent_id="agentA", context_id="ctx-002")
    
    # 错误事件
    log("发生错误：无效输入", trace_id="task-123", event_type="ERROR", agent_id="agentA", context_id="ctx-002")
    
    # 多条事件
    for i in range(3):
        log(f"循环事件 {i}", trace_id="loop-001", event_type="LOOP_EVENT", agent_id="agentB", context_id="ctx-003")
        time.sleep(0.1)
    
    # 查看 TraceWriter 事件
    from src.monitoring.log.trace_writer import get_trace_writer
    tw = get_trace_writer()
    print("\n[trace_id=task-123] 事件记录:")
    for event in tw.get_events("task-123"):
        print(event)
    print("\n[trace_id=loop-001] 事件记录:")
    for event in tw.get_events("loop-001"):
        print(event) 