# 状态域模块 (State Domain)

## 模块概述

状态域模块负责上下文管理、内存管理、会话管理和状态持久化，是企业级Agent系统的状态管理中心。

## 模块组成

### 1. 上下文管理模块 (`context/`)
- **功能**: 会话上下文管理、上下文持久化、上下文共享机制
- **核心类**: `ContextManager`, `Session`
- **主要接口**:
  - `create_session(session_id)`: 创建会话
  - `get_context(session_id)`: 获取上下文
  - `update_context(session_id, context)`: 更新上下文

### 2. 内存管理模块 (`memory/`)
- **功能**: 短期记忆管理、长期记忆存储、记忆检索和更新
- **核心类**: `MemoryManager`
- **主要接口**:
  - `store(key, value, memory_type)`: 存储记忆
  - `retrieve(key, memory_type)`: 检索记忆
  - `update(key, value, memory_type)`: 更新记忆

### 3. 会话管理模块 (`session/`)
- **功能**: 会话生命周期管理、会话状态跟踪、会话数据持久化
- **核心类**: `SessionManager`
- **主要接口**:
  - `create_session(user_id)`: 创建会话
  - `get_session(session_id)`: 获取会话
  - `update_session(session_id, data)`: 更新会话
  - `close_session(session_id)`: 关闭会话

### 4. 状态持久化模块 (`context.py`, `memory.py`)
- **功能**: 状态数据持久化、数据序列化、存储后端抽象
- **核心类**: `StatePersistence`
- **主要接口**:
  - `save_state(state_data)`: 保存状态
  - `load_state(state_id)`: 加载状态
  - `delete_state(state_id)`: 删除状态

## 技术架构

### 设计原则
- **状态一致性**: 确保状态数据的一致性
- **持久化支持**: 支持多种存储后端
- **性能优化**: 缓存和索引优化
- **可扩展性**: 支持分布式状态管理

### 依赖关系
```
ContextManager
├── SessionManager
├── MemoryManager
└── StatePersistence
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
from src.state.context import ContextManager
from src.state.memory import MemoryManager

# 创建上下文管理器
context_manager = ContextManager()

# 创建会话
session = context_manager.create_session("user123")

# 获取上下文
context = context_manager.get_context("user123")

# 创建内存管理器
memory_manager = MemoryManager()

# 存储记忆
memory_manager.store("user_preference", {"theme": "dark"}, "long_term")

# 检索记忆
preference = memory_manager.retrieve("user_preference", "long_term")
```

## 测试

```bash
# 运行单元测试
pytest tests/unit/state/

# 运行集成测试
pytest tests/integration/state/

# 生成测试覆盖率报告
pytest --cov=src/state tests/unit/state/
```

## 部署

状态域模块需要配置数据库和缓存：

```yaml
# docker-compose.yml
services:
  state:
    build: .
    ports:
      - "8002:8002"
    environment:
      - REDIS_URL=redis://localhost:6379
      - POSTGRES_URL=postgresql://user:pass@localhost:5432/nagent
    volumes:
      - ./config:/app/config
```

## 监控

- **性能指标**: 状态访问延迟、存储容量、缓存命中率
- **资源使用**: CPU、内存、磁盘
- **业务指标**: 活跃会话数、状态更新频率

## 版本历史

- **v1.0.0**: 初始版本，基础功能实现
- **v1.1.0**: 添加分布式状态支持
- **v1.2.0**: 优化缓存机制 

## 上下文持久化与回调闭环

- 所有 memory/trace/session 的写入建议通过回调链闭环驱动，保证推理行为的连续性、可追溯性、可恢复性。
- 强烈建议所有 memory_entry、trace_event、session 更新均带 context_id、trace_id、agent_id 字段。

### memory_entry/trace_event/session 结构化写入模板
```python
memory_entry = {
    "context_id": context.id,
    "trace_id": trace.id,
    "agent_id": agent.id,
    "type": "observation",
    "content": "用户输入/工具输出/推理结果等",
    "timestamp": now()
}
trace_event = {
    "trace_id": trace.id,
    "agent_id": agent.id,
    "event_type": "tool_execution",
    "payload": {...},
    "timestamp": now()
}
session_update = {
    "session_id": session.id,
    "context_id": context.id,
    "status": "active/closed",
    "last_event": trace_event,
    "updated_at": now()
}
```

## 推理行为闭环用例

```python
from src.state.context import ContextManager
from src.state.memory import MemoryManager
from src.state.session import SessionManager

# 创建会话和上下文
context_manager = ContextManager()
session_manager = SessionManager()
session = session_manager.create_session("user123")
context = context_manager.create_session(session.id)

# 推理行为发生后，结构化写入 memory/trace/session
memory_manager = MemoryManager()
memory_entry = {"context_id": context.id, "trace_id": "t1", "agent_id": "a1", "type": "observation", "content": "用户输入"}
memory_manager.store("user_input", memory_entry, "short_term")

trace_event = {"trace_id": "t1", "agent_id": "a1", "event_type": "tool_execution", "payload": {"result": "ok"}}
# 假设有 trace_writer
# trace_writer.write_event(trace_event)

session_update = {"session_id": session.id, "context_id": context.id, "status": "active", "last_event": trace_event}
session_manager.update_session(session.id, session_update)
```

## 扩展点与多后端支持
- **Memory/Session 后端**：支持 Redis、Postgres、本地文件等多种后端，扩展只需实现对应存储接口。
- **插件化**：可通过插件扩展 memory 检索、session 生命周期、context 持久化等能力。

## 与 execution/monitoring 的协作
- **与 execution 协作**：为执行域提供上下文、记忆、会话等支撑，所有行为链闭环均需写入 memory/trace。
- **与 monitoring 协作**：为监控域提供 trace_event、状态快照等数据，支持全链路追踪和异常恢复。 