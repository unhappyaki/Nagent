# ACP (Agent Communication Protocol) 模块

基于企业级架构实践的智能体通信协议完整实现。

## 🎯 概述

ACP协议是Nagent框架的核心通信协议，实现了完整的智能体双栈通信架构。基于企业级架构的21模块理论，提供：

- ✅ **完整的Client-Server双栈通信**
- ✅ **三层服务器架构**(Gateway-Router-Container)
- ✅ **智能任务分发和调度**
- ✅ **Agent生命周期管理**
- ✅ **多种控制适配器**
- ✅ **全链路追踪和监控**
- ✅ **HTTP管理接口**
- ✅ **标准化消息格式**

## 🏗️ 核心组件

### 1. 通信层 (Communication Layer)

#### ACPClient - 智能体客户端
```python
from src.communication.acp import ACPClient

client = ACPClient("ws://localhost:8000", agent_id="agent_001")
await client.connect()
```

#### ACPServer - 三层服务器架构
```python
from src.communication.acp import ACPServer

server = ACPServer(host="localhost", port=8000)
await server.start()
```

### 2. 消息格式层 (Message Schema)

#### 标准化消息构建
```python
from src.communication.acp import ACPMessageBuilder, MessagePriority

builder = ACPMessageBuilder("sender_001")
message = builder.create_task_message(
    receiver_id="agent_002",
    task_type="data_analysis", 
    task_data={"data": "sample"},
    priority=MessagePriority.HIGH
)
```

#### 三段式载荷结构
- **Meta**: 消息元数据(ID、类型、时间戳、优先级)
- **Context**: 上下文信息(会话、用户、环境)  
- **Payload**: 命令载荷(命令类型、动作类型、数据)

### 3. 任务分发层 (Task Dispatcher)

#### 智能任务调度
```python
from src.communication.acp import TaskDispatcher, DispatchStrategy

dispatcher = TaskDispatcher(strategy=DispatchStrategy.CAPABILITY_MATCH)
await dispatcher.start()

task_id = await dispatcher.submit_task(
    task_type="text_processing",
    task_data={"text": "要处理的文本"},
    required_capabilities=["nlp", "text_analysis"]
)
```

#### 支持的分发策略
- `ROUND_ROBIN`: 轮询分发
- `LEAST_LOADED`: 最少负载
- `CAPABILITY_MATCH`: 能力匹配
- `PRIORITY_BASED`: 优先级分发
- `RANDOM`: 随机分发

### 4. Agent注册中心 (Agent Registry)

#### Agent生命周期管理
```python
from src.communication.acp import ACPAgentRegistry

registry = ACPAgentRegistry()
await registry.start()

# 注册Agent
await registry.register_agent(
    agent_id="agent_001",
    capabilities=["nlp", "text_analysis", "data_processing"],
    max_load=10
)

# 获取可用Agent
available = registry.get_available_agents(["nlp"])
```

### 5. 控制适配器 (Control Adapters)

#### 多种执行模式
```python
from src.communication.acp import ControlDispatcher

dispatcher = ControlDispatcher()
result = await dispatcher.dispatch(acp_payload)
```

- **APIControlAdapter**: HTTP API调用
- **ToolControlAdapter**: 工具执行
- **ModelControlAdapter**: 大模型调用

### 6. Web管理接口 (Flask App)

#### HTTP管理服务
```python
from src.communication.acp import create_app

app = create_app()
app.run(host="0.0.0.0", port=5000)
```

#### REST API端点
- `GET /health` - 健康检查
- `GET /status` - 服务状态
- `GET /agents` - Agent列表
- `POST /tasks` - 提交任务
- `GET /tasks/{id}` - 任务状态
- `GET /metrics` - 性能指标

### 7. 工具辅助 (Utilities)

#### 时间和ID管理
```python
from src.communication.acp import TimeUtils, IDGenerator

timestamp = TimeUtils.get_current_timestamp()
trace_id = IDGenerator.generate_trace_id()
```

## 🚀 快速开始

### 1. 启动完整ACP服务

```python
import asyncio
from src.communication.acp import ACPServer, TaskDispatcher, ACPAgentRegistry

async def start_acp_service():
    # 1. 启动Agent注册中心
    registry = ACPAgentRegistry()
    await registry.start()
    
    # 2. 启动任务分发器
    dispatcher = TaskDispatcher()
    await dispatcher.start()
    
    # 3. 启动ACP服务器
    server = ACPServer(host="localhost", port=8000)
    await server.start()
    
    print("ACP服务已启动: ws://localhost:8000")

asyncio.run(start_acp_service())
```

### 2. 客户端连接和任务提交

```python
import asyncio
from src.communication.acp import create_acp_client

async def submit_task():
    # 创建客户端
    client = create_acp_client("ws://localhost:8000", "client_001")
    await client.connect()
    
    # 注册为Agent
    await client.register_agent(["text_processing", "data_analysis"])
    
    # 调用工具
    result = await client.call_tool(
        "text_summarizer",
        {"text": "这是要总结的长文本..."},
        context_id="session_123"
    )
    
    print(f"工具执行结果: {result}")

asyncio.run(submit_task())
```

### 3. 启动Web管理界面

```python
from src.communication.acp import create_app

# 创建Flask应用
app = create_app({
    "server": {"host": "localhost", "port": 8000},
    "flask": {"host": "0.0.0.0", "port": 5000}
})

# 启动Web服务
app.run(debug=True)
```

访问 `http://localhost:5000/status` 查看服务状态。

## 📋 消息格式规范

### ACP标准消息结构

```json
{
  "meta": {
    "message_id": "msg-uuid-here",
    "message_type": "task",
    "timestamp": "2024-01-15T10:30:00Z",
    "sender_id": "agent_001", 
    "receiver_id": "agent_002",
    "trace_id": "trace-uuid-here",
    "priority": 2,
    "ttl": 300
  },
  "context": {
    "session_id": "sess-uuid-here",
    "tenant_id": "tenant_001",
    "user_id": "user_123",
    "agent_capabilities": ["nlp", "analysis"],
    "environment": {"lang": "zh-CN"},
    "security_context": {"role": "user"}
  },
  "payload": {
    "command_type": "call_tool",
    "action_type": "execution", 
    "data": {
      "tool_name": "text_processor",
      "arguments": {"text": "输入文本"},
      "created_at": "2024-01-15T10:30:00Z"
    },
    "parameters": {},
    "metadata": {}
  }
}
```

### 支持的消息类型

- `REGISTER/UNREGISTER` - Agent注册/注销
- `TASK` - 任务分发
- `EXECUTE` - 执行指令  
- `RESULT` - 执行结果
- `STATE` - 状态更新
- `HEARTBEAT` - 心跳检测
- `ACK` - 确认消息
- `ERROR` - 错误消息

### 支持的命令类型

- `CALL_TOOL` - 工具调用
- `CALL_API` - API调用
- `CALL_MODEL` - 模型调用
- `UPDATE_MEMORY` - 更新内存
- `QUERY_MEMORY` - 查询内存
- `UPDATE_STATE` - 更新状态
- `TRANSFER_TASK` - 任务转移
- `SPAWN_AGENT` - 生成Agent

## 🔧 配置管理

### 默认配置

```python
from src.communication.acp import ConfigUtils

config = ConfigUtils.DEFAULT_CONFIG
# {
#   "message": {
#     "default_ttl": 300,
#     "max_retry_count": 3,
#     "heartbeat_interval": 30
#   },
#   "agent": {
#     "max_concurrent_tasks": 10,
#     "heartbeat_timeout": 60
#   },
#   "dispatcher": {
#     "task_timeout": 300,
#     "max_pending_tasks": 1000
#   },
#   "server": {
#     "host": "localhost",
#     "port": 8000
#   }
# }
```

### 自定义配置

```python
custom_config = {
    "server": {"port": 9000},
    "agent": {"max_concurrent_tasks": 20}
}

app = create_app(custom_config)
```

## 📊 监控和指标

### 服务器统计信息

```python
server_stats = server.get_server_stats()
# {
#   "active_connections": 5,
#   "total_messages": 1250,
#   "registered_agents": 3,
#   "uptime": 3600,
#   "container_stats": {...}
# }
```

### 任务分发统计

```python
dispatcher_stats = dispatcher.get_dispatcher_stats()
# {
#   "total_tasks": 100,
#   "successful_tasks": 95,
#   "failed_tasks": 5,
#   "pending_tasks": 10,
#   "active_tasks": 5,
#   "average_task_time": 2.5
# }
```

### Agent注册统计

```python
registry_stats = registry.get_registry_stats()
# {
#   "total_agents": 10,
#   "active_agents": 8,
#   "healthy_agents": 7,
#   "status_distribution": {...},
#   "capability_distribution": {...}
# }
```

## 🔌 扩展开发

### 自定义控制适配器

```python
from src.communication.acp import ControlAdapter, ControlResult

class DatabaseControlAdapter(ControlAdapter):
    def match(self, action_type: str) -> bool:
        return action_type == "database_query"
    
    async def execute(self, acp_payload) -> ControlResult:
        # 实现数据库查询逻辑
        query = acp_payload.payload.data.get("query")
        result = await self.execute_query(query)
        
        return ControlResult(
            control_id=acp_payload.meta.trace_id,
            status="success",
            output={"data": result},
            trace={"duration_ms": 50}
        )

# 注册到分发器
dispatcher.register_adapter(DatabaseControlAdapter())
```

### 自定义消息处理器

```python
class CustomMessageHandler:
    async def handle_custom_message(self, message):
        # 处理自定义消息类型
        pass

# 注册到服务器
server.register_message_handler("custom_type", CustomMessageHandler())
```

## 🧪 测试和调试

### 单元测试

```bash
python -m pytest tests/unit/communication/acp/
```

### 集成测试

```bash
python examples/acp_demo.py
python examples/test_acp_client_server.py
```

### 调试模式

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 启用详细日志
server = ACPServer(host="localhost", port=8000, debug=True)
```

## 🚦 状态码和错误处理

### 常见状态码

- `SUCCESS` - 执行成功
- `FAILED` - 执行失败
- `TIMEOUT` - 执行超时
- `CANCELLED` - 任务取消
- `AGENT_NOT_FOUND` - Agent未找到
- `INSUFFICIENT_RESOURCES` - 资源不足

### 错误处理

```python
try:
    result = await client.call_tool("processor", {"data": "test"})
except ACPTimeoutError:
    print("调用超时")
except ACPAgentNotFoundError:
    print("Agent未找到")
except ACPPermissionError:
    print("权限不足")
```

## 📈 性能优化

### 连接池管理

```python
client_manager = ACPClientManager(max_connections=100)
client = await client_manager.get_client("ws://localhost:8000")
```

### 消息批处理

```python
messages = [msg1, msg2, msg3]
results = await client.send_batch(messages)
```

### 异步处理

```python
# 异步提交多个任务
tasks = []
for i in range(10):
    task = dispatcher.submit_task(f"task_{i}", {"data": i})
    tasks.append(task)

task_ids = await asyncio.gather(*tasks)
```

## 📝 最佳实践

1. **消息设计**: 保持载荷大小合理，避免传输大量数据
2. **错误处理**: 实现完整的错误处理和重试机制
3. **资源管理**: 及时清理连接和资源，避免内存泄漏
4. **监控告警**: 监控关键指标，设置合理的告警阈值
5. **安全考虑**: 验证消息来源，控制访问权限
6. **性能调优**: 根据业务需求调整超时时间和并发数

## 🤝 贡献指南

欢迎提交Issue和Pull Request！在开发新功能时，请：

1. 遵循现有的代码规范
2. 添加完整的测试用例
3. 更新相关文档
4. 确保向后兼容性

---

ACP协议是Nagent框架智能体通信的核心实现，为构建高可用、高性能的多智能体系统提供了坚实的基础。
