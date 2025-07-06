# 执行域模块 (Execution Domain)

## 模块概述

执行域模块负责任务执行调度、执行状态管理、错误处理和回调控制，是企业级Agent系统的执行引擎。

## 模块组成

### 1. 执行器模块 (`executor.py`)
- **功能**: 任务执行调度、执行状态管理、错误处理和重试
- **核心类**: `Executor`
- **主要接口**:
  - `execute_task(task)`: 执行任务
  - `get_execution_status(task_id)`: 获取执行状态
  - `cancel_task(task_id)`: 取消任务

### 2. 回调控制模块 (`callbacks/`)
- **功能**: 执行过程回调、事件通知机制、回调链管理
- **核心类**: `CallbackManager`
- **主要接口**:
  - `register_callback(event, callback)`: 注册回调
  - `trigger_callback(event, data)`: 触发回调
  - `remove_callback(event, callback)`: 移除回调

### 3. 适配器模块 (`adapters/`)
- **功能**: 外部系统适配器、协议转换、接口封装
- **核心类**: `BaseAdapter`
- **主要接口**:
  - `connect()`: 连接外部系统
  - `execute(command)`: 执行命令
  - `disconnect()`: 断开连接

### 4. 工具执行模块 (`tools/`)
- **功能**: 工具执行管理、工具链编排、执行结果处理
- **核心类**: `ToolExecutor`
- **主要接口**:
  - `execute_tool(tool_name, params)`: 执行工具
  - `get_tool_result(execution_id)`: 获取执行结果
  - `cancel_tool_execution(execution_id)`: 取消工具执行

## 技术架构

### 设计原则
- **异步执行**: 支持异步任务执行
- **状态管理**: 完整的执行状态跟踪
- **错误恢复**: 自动重试和错误恢复机制
- **可扩展性**: 支持插件化扩展

### 依赖关系
```
Executor
├── CallbackManager
├── BaseAdapter
└── ToolExecutor
```

## 开发规范

### 代码规范
- 遵循PEP 8代码规范
- 使用类型注解
- 完整的文档字符串
- 单元测试覆盖率 > 80%

### 接口设计
- 统一的错误处理机制
- 异步接口支持
- 配置驱动的设计
- 插件化架构

## 使用示例

```python
from src.execution import Executor
from src.execution.callbacks import CallbackManager

# 创建执行器
executor = Executor()

# 注册回调
callback_manager = CallbackManager()
callback_manager.register_callback("task_completed", on_task_completed)

# 执行任务
task = Task(name="example_task", params={"key": "value"})
result = executor.execute_task(task)

# 获取执行状态
status = executor.get_execution_status(task.id)
```

## 测试

```bash
# 运行单元测试
pytest tests/unit/execution/

# 运行集成测试
pytest tests/integration/execution/

# 生成测试覆盖率报告
pytest --cov=src/execution tests/unit/execution/
```

## 部署

执行域模块需要配置任务队列和执行环境：

```yaml
# docker-compose.yml
services:
  execution:
    build: .
    ports:
      - "8001:8001"
    environment:
      - REDIS_URL=redis://localhost:6379
      - MAX_WORKERS=10
    volumes:
      - ./config:/app/config
```

## 监控

- **性能指标**: 任务执行时间、成功率、错误率
- **资源使用**: CPU、内存、网络
- **业务指标**: 任务队列长度、执行吞吐量

## 模块边界与扩展点

- **Executor** 负责任务调度、状态管理和错误恢复，是行为链的核心调度器。
- **ToolExecutor** 专注于工具链的编排和执行，支持多工具并发和异步调用。
- **CallbackHandler/CallbackManager** 负责回调注册、事件分发和回调链闭环，所有 memory/trace/状态更新均通过回调链出口。
- **Adapter** 用于对接外部系统或协议，支持自定义扩展。

### 扩展点
- **自定义回调**：实现并注册自定义回调函数，支持多级回调链。
- **自定义工具**：继承 ToolExecutor 或注册新工具，支持插件化扩展。
- **自定义适配器**：继承 BaseAdapter，实现 connect/execute/disconnect。

## 回调链与行为链闭环

回调链是行为链闭环的唯一出口，所有 memory/trace/状态更新均通过回调链驱动，保证推理行为的可追溯、可恢复。

### 回调链三大锚点
1. **写 memory**：结构化写入 memory_entry，带 context_id/trace_id/agent_id。
2. **写 trace**：结构化写入 trace_event，记录行为链路。
3. **更新链路/状态**：更新 session/context，保证链路状态一致。

#### 回调链伪代码示例
```python
# 回调链闭环伪代码
result = executor.execute_task(task)
callback_manager.trigger_callback("task_completed", {
    "context_id": context.id,
    "trace_id": trace.id,
    "agent_id": agent.id,
    "result": result
})
# 回调函数内部：
def on_task_completed(event):
    memory_engine.write_entry(event)
    trace_writer.write_event(event)
    session_manager.update(event)
```

## 行为链全流程用例

```python
from src.execution.executor import Executor
from src.execution.callbacks.callback_handler import CallbackHandler
from src.execution.tools.tool_executor import ToolExecutor
from src.state.memory import MemoryEngine
from src.monitoring.tracing.trace_writer import TraceWriter

# 初始化各组件
executor = Executor()
tool_executor = ToolExecutor()
callback_handler = CallbackHandler()
memory_engine = MemoryEngine()
trace_writer = TraceWriter()

def on_task_completed(event):
    memory_engine.write_entry(event)
    trace_writer.write_event(event)
    # 可扩展：更新 session/context

callback_handler.register_callback("task_completed", on_task_completed)

# 注册工具并执行
tool_executor.register_tool("search", search_tool)
task = Task(name="search", params={"query": "agent架构"})
executor.execute_task(task)

# 行为链：任务调度→工具执行→回调→memory/trace写入
```

## 与 state/monitoring 等模块的协作
- **与 state 协作**：通过回调链写入 memory、更新 session/context，保证状态持久化和链路一致性。
- **与 monitoring 协作**：通过 TraceWriter 结构化写入 trace_event，实现全链路追踪和异常溯源。

## 版本历史

- **v1.0.0**: 初始版本，基础功能实现
- **v1.1.0**: 添加异步执行支持
- **v1.2.0**: 优化错误处理机制 