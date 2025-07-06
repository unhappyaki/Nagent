# Nagent - 企业级智能体框架

## 项目概述

Nagent是一个基于企业级架构设计理念构建的智能体框架，实现了完整的Agentic AI系统。框架采用五大控制域架构，包含21个核心模块，支持多智能体协作、分布式执行、状态管理、行为追踪等企业级特性。

## 🎯 最新更新

### ACP协议完整实现 ✅ (第8周)
已完成ACP协议的完整双栈实现，基于企业级架构实践的21模块理论：

#### 🚀 ACP服务器端三层架构
- **ACPServer**: 完整的WebSocket服务器端实现
- **ACPGateway**: 协议层消息入口，负责消息校验和路由
- **ACPRouter**: 权限判断和路由决策
- **AgentContainer**: Agent生命周期管理和任务分发

#### 📱 ACP客户端完整实现
- **ACPClient**: 基于WebSocket的异步客户端
- **ACPPayload**: 三段式载荷结构（Meta、Context、Command）
- **ACPClientManager**: 多客户端连接管理

#### 🎛️ 控制桥接器系统
- **ControlDispatcher**: 控制分发器，支持多种适配器
- **APIControlAdapter**: HTTP API调用适配器
- **ToolControlAdapter**: 工具执行适配器
- **ModelControlAdapter**: 大模型调用适配器

#### 📋 新增核心模块
- **MessageSchema**: 标准化消息格式定义和构建工具
- **TaskDispatcher**: 智能任务分发器，支持多种分发策略
- **AgentRegistry**: Agent注册中心，完整的生命周期管理
- **Flask App**: HTTP管理接口，提供REST API
- **Utils**: 工具辅助模块，时间、ID、验证等功能

#### 📚 完整的演示和文档
- **演示代码**: `examples/acp_demo.py` - 完整的ACP协议演示
- **详细文档**: `src/communication/acp/README.md` - 使用指南和架构说明

### 🏗️ 基础设施层完成
已完成基础设施层的完整架构设计，将Tool、Agent、Memory、Reasoner策略注册功能提升为平台级基础设施能力：

#### 📋 统一注册中心
- **UnifiedModuleRegistry**: 统一模块注册中心 ✅
- **ToolRegistry**: 工具注册器，支持动态权限绑定 ✅
- **AgentRegistry**: 智能体注册器，支持metadata注入 ✅
- **MemoryRegistry**: 记忆注册器，支持四种模式配置 ✅

#### 🌐 基础设施组件
- **UnifiedAPIGateway**: 统一API网关（接口定义完成）
- **UnifiedAuthManager**: 统一认证管理器（接口定义完成）
- **UnifiedConfigManager**: 统一配置管理器（接口定义完成）
- **ServiceDiscovery**: 服务发现（接口定义完成）

## 系统架构

### 五大控制域

1. **行为域 (Behavior Domain)**
   - BIR消息调度机制
   - 行为分发与路由
   - 意图识别与解析

2. **通信域 (Communication Domain)**
   - ACP协议实现
   - 客户端-服务器通信
   - 消息封装与传输

3. **执行域 (Execution Domain)**
   - 执行器调度引擎
   - 工具链调用管理
   - 行为链控制闭环

4. **状态域 (State Domain)**
   - 上下文管理 (Context)
   - 会话生命周期 (Session)
   - 内存管理 (Memory)

5. **协同域 (Coordination Domain)**
   - 多智能体协作
   - 任务分发与调度
   - 资源管理与分配

### 协议集成架构

框架支持多种标准协议的集成，实现与外部系统的无缝互操作：

1. **A2A协议集成**
   - 跨平台智能体协作
   - 标准化智能体通信
   - 外部智能体生态接入

2. **MCP协议集成**
   - 工具生态扩展
   - 标准化工具调用
   - 外部数据源连接

3. **混合架构设计**
   - 内部BIR+ACP协议保持企业级特性
   - 外部标准协议实现互操作性
   - 协议桥接和适配器模式

## 核心模块

### 1. BIR消息调度路由器 (`src/communication/dispatcher/bir_router.py`)

实现行为分发的起点，负责将用户输入意图解析成标准化的行为指令包。

**主要功能：**
- 意图类型识别与分类
- 行为指令包构建
- 追踪ID生成与管理
- 行为路由与分发

**使用示例：**
```python
from src.communication.dispatcher.bir_router import BIRRouter

# 创建BIR路由器
router = BIRRouter(acp_client=acp_client, trace_writer=trace_writer)

# 分发行为指令
behavior_package = router.dispatch(
    intent="生成报告",
    from_agent="user",
    to_agent="report_agent",
    context_id="context-123",
    payload={"topic": "AI发展趋势"}
)
```

### 2. ACP通信协议 (`src/communication/acp/acp_client.py`)

实现行为数据的封装与追踪核心，负责Client与Server之间的协议交互。

**主要功能：**
- ACP载荷构建与发送
- 消息队列管理
- 回调处理机制
- 连接状态管理

**使用示例：**
```python
from src.communication.acp.acp_client import ACPClient

# 创建ACP客户端
client = ACPClient(server_url="http://localhost:8000", trace_writer=trace_writer)

# 发送行为包
client.send_behavior_package(behavior_package)

# 调用工具
result = await client.call_tool("search_tool", {"query": "AI"}, context_id, trace_id)
```

### 3. 会话管理 (`src/state/context/session.py`)

实现Runtime上下文管理中的会话生命周期控制。

**主要功能：**
- 会话创建与销毁
- 状态快照管理
- 内存条目管理
- 会话延展与过期处理

**使用示例：**
```python
from src.state.context.session import Session, SessionManager

# 创建会话管理器
session_manager = SessionManager()

# 创建会话
session = session_manager.create_session(
    context_id="context-123",
    agent_id="agent-001",
    tenant_id="tenant-001",
    timeout=3600
)

# 添加内存条目
session.add_memory_entry({
    "type": "user_input",
    "data": {"message": "生成报告"},
    "timestamp": int(time.time())
})
```

### 4. 执行器 (`src/execution/executor.py`)

实现执行链控制核心，包括模块级调度闭环。

**主要功能：**
- 推理阶段执行
- 工具调用调度
- 回调处理管理
- 状态更新与内存写入

**使用示例：**
```python
from src.execution.executor import Executor

# 创建执行器
executor = Executor(
    reasoning_engine=reasoning_engine,
    tool_registry=tool_registry,
    memory_engine=memory_engine
)

# 执行任务
result = await executor.run(session, input_data)
```

### 5. 追踪写入器 (`src/monitoring/tracing/trace_writer.py`)

实现行为链的完整追踪和审计功能。

**主要功能：**
- 多类型追踪记录
- 追踪链构建
- 搜索与过滤
- 数据导出

**使用示例：**
```python
from src.monitoring.tracing.trace_writer import TraceWriter

# 创建追踪写入器
trace_writer = TraceWriter()

# 记录行为追踪
trace_writer.record_behavior_trace(
    trace_id="trace-123",
    context_id="context-123",
    intent="生成报告",
    from_agent="user",
    to_agent="agent",
    intent_type="task_execution"
)

# 获取追踪链
trace_chain = trace_writer.get_trace_chain("trace-123")
```

### 6. 协议集成使用

#### A2A协议集成示例

```python
from src.communication.protocols.a2a.a2a_client import A2AClient
from src.communication.protocols.a2a.a2a_server import A2AServer

# 创建A2A客户端，连接外部智能体
a2a_client = A2AClient(trace_writer=trace_writer)

# 发现外部智能体
agent_card = await a2a_client.discover_agent("https://external-agent.com/a2a")

# 发送任务到外部智能体
task = A2ATask(
    task_type="analysis",
    parameters={"data": "market_report.pdf"},
    requirements=["pdf_processing", "data_analysis"]
)
result = await a2a_client.send_task("https://external-agent.com/a2a", task)

# 创建A2A服务器，对外提供服务
agent_card = AgentCard(
    name="Enterprise Agent",
    description="企业级智能体系统",
    capabilities=["task_execution", "data_analysis", "document_processing"]
)
a2a_server = A2AServer(agent_card, bir_router, trace_writer)
await a2a_server.start_server(host="0.0.0.0", port=8080)
```

#### MCP协议集成示例

```python
from src.communication.protocols.mcp.mcp_client import MCPClient
from src.communication.adapters.mcp_adapter import MCPAdapter

# 创建MCP客户端连接管理器
connection_manager = MCPConnectionManager()

# 连接数据库工具服务器
db_client = await connection_manager.create_connection(
    MCPServerConfig(
        name="database_tools",
        transport_type="stdio",
        command=["python", "-m", "mcp_database_server"],
        capabilities=["database", "sql", "query"]
    )
)

# 发现可用工具
tools = await db_client.list_tools()
print(f"可用数据库工具: {[tool.name for tool in tools]}")

# 调用MCP工具
result = await db_client.call_tool(
    "execute_query",
    {"query": "SELECT * FROM users LIMIT 10"},
    timeout=30
)

# 通过适配器集成到现有工具注册表
mcp_adapter = MCPAdapter(tool_registry, connection_manager, trace_writer)
await mcp_adapter.register_mcp_server(server_config)
await mcp_adapter.discover_and_register_tools("database_tools")

# 现在可以像使用内部工具一样使用MCP工具
result = await executor.execute_tool("execute_query", {"query": "SELECT COUNT(*) FROM orders"})
```

## 目录结构

```
Nagent/
├── agent企业级架构实践/          # 架构设计文档
├── config/                      # 配置管理
│   ├── config_manager.py
│   └── system.yaml
├── docs/                        # 文档
│   ├── A2A协议集成设计方案.md   # A2A协议集成设计
│   ├── MCP协议集成设计方案.md   # MCP协议集成设计
│   ├── 知识库管理与RAG增强检索设计方案.md  # RAG增强设计
│   ├── 意图识别准确率提升方案.md # 意图识别技术升级
│   ├── 架构开发演进计划.md       # 架构演进计划
│   └── 开发进度更新.md          # 开发进度跟踪
├── examples/                    # 示例代码
│   ├── basic_usage.py
│   └── enterprise_agent_demo.py
├── main.py                      # 主程序入口
├── requirements.txt             # 依赖包
├── README.md                    # 项目说明
└── src/                         # 源代码
    ├── communication/           # 通信模块
    │   ├── dispatcher/          # 调度器
    │   │   └── bir_router.py    # BIR路由器
    │   ├── acp/                 # ACP协议
    │   │   └── acp_client.py    # ACP客户端
    │   ├── protocols/           # 协议集成
    │   │   ├── a2a/             # A2A协议
    │   │   │   ├── a2a_client.py
    │   │   │   ├── a2a_server.py
    │   │   │   └── agent_card.py
    │   │   └── mcp/             # MCP协议
    │   │       ├── mcp_client.py
    │   │       ├── connection_manager.py
    │   │       └── transports/
    │   ├── adapters/            # 协议适配器
    │   │   ├── a2a_adapter.py
    │   │   ├── mcp_adapter.py
    │   │   └── external_tool_registry.py
    │   └── router/              # 路由器
    ├── coordination/            # 协同模块
    │   ├── container/           # 容器
    │   ├── registry/            # 注册表
    │   └── scheduler/           # 调度器
    ├── core/                    # 核心模块
    │   ├── agent/               # 智能体
    │   │   ├── __init__.py
    │   │   └── base_agent.py    # 基础智能体
    │   ├── memory/              # 内存
    │   ├── reasoning/           # 推理
    │   │   ├── __init__.py
    │   │   ├── hybrid_reasoner.py
    │   │   ├── llm_reasoner.py
    │   │   ├── reasoning_engine.py
    │   │   ├── rl_reasoner.py
    │   │   └── rule_reasoner.py
    │   └── tools/               # 工具
    │       ├── __init__.py
    │       ├── base_tool.py     # 基础工具
    │       └── tool_registry.py # 工具注册表
    ├── execution/               # 执行模块
    │   ├── adapters/            # 适配器
    │   ├── callbacks/           # 回调
    │   ├── executor.py          # 执行器
    │   └── tools/               # 工具
    ├── monitoring/              # 监控模块
    │   ├── logging/             # 日志
    │   ├── metrics/             # 指标
    │   └── tracing/             # 追踪
    │       └── trace_writer.py  # 追踪写入器
    └── state/                   # 状态模块
        ├── context/             # 上下文
        │   ├── context.py
        │   └── session.py       # 会话管理
        ├── memory/              # 内存
        │   └── memory.py
        └── session/             # 会话
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行基础示例

```bash
python examples/basic_usage.py
```

### 3. 运行企业级演示

```bash
python examples/enterprise_agent_demo.py
```

## 配置说明

### 系统配置 (`config/system.yaml`)

```yaml
# 系统基础配置
system:
  name: "Nagent"
  version: "1.0.0"
  debug: true

# 智能体配置
agents:
  default_timeout: 300
  max_retries: 3
  parallel_execution: false

# 推理引擎配置
reasoning:
  default_reasoner: "llm"
  max_tokens: 2048
  temperature: 0.7

# 工具配置
tools:
  auto_discovery: true
  validation: true

# 监控配置
monitoring:
  tracing:
    enabled: true
    max_entries: 10000
    auto_cleanup: true
  logging:
    level: "INFO"
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## 监控与追踪

### 追踪功能

框架提供完整的追踪功能，包括：

- **行为追踪**: 记录智能体的行为意图和执行过程
- **推理追踪**: 记录推理引擎的输入输出
- **工具调用追踪**: 记录工具调用的参数和结果
- **会话追踪**: 记录会话的生命周期变化
- **ACP消息追踪**: 记录通信协议的消息交换

### 统计信息

```python
# 获取追踪统计
trace_stats = trace_writer.get_trace_stats()
print(f"总追踪条目: {trace_stats['total_entries']}")
print(f"追踪类型: {trace_stats['type_stats']}")

# 获取会话统计
session_stats = session_manager.get_session_stats()
print(f"活跃会话: {session_stats['active_sessions']}")
print(f"完成会话: {session_stats['completed_sessions']}")
```

## 安全特性

- **权限控制**: 基于角色的访问控制
- **数据隔离**: 多租户数据隔离
- **审计日志**: 完整的操作审计记录
- **输入验证**: 严格的输入参数验证

## 测试

### 单元测试

```bash
python -m pytest tests/unit/
```

### 集成测试

```bash
python -m pytest tests/integration/
```

### 性能测试

```bash
python -m pytest tests/performance/
```

## 性能优化

### 1. 异步执行

框架支持异步执行，提高并发性能：

```python
# 异步执行任务
result = await executor.run(session, input_data)
```

### 2. 内存管理

- 自动清理过期会话
- 追踪条目数量限制
- 内存使用监控

### 3. 缓存机制

- 推理结果缓存
- 工具调用结果缓存
- 会话状态缓存

## 扩展开发

### 自定义工具

```python
from src.core.tools.base_tool import BaseTool

class CustomTool(BaseTool):
    def __init__(self):
        super().__init__("custom_tool", "自定义工具描述")
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        # 实现工具逻辑
        return {"success": True, "result": "工具执行结果"}
```

### 自定义推理器

```python
from src.core.reasoning.reasoning_engine import BaseReasoner

class CustomReasoner(BaseReasoner):
    def reason(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # 实现推理逻辑
        return {"actions": [{"tool": "custom_tool", "parameters": {}}]}
```

## 部署指南

### 1. 单机部署

```bash
# 启动主程序
python main.py
```

### 2. 容器化部署

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
```

### 3. 分布式部署

- 使用消息队列进行任务分发
- 多实例负载均衡
- 数据库集群支持

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目主页: [GitHub Repository]
- 问题反馈: [Issues]
- 文档: [Documentation]

## 文档索引

### 架构设计文档
- [架构开发演进计划](docs/架构开发演进计划.md) - 完整的架构演进规划和开发路线图
- [开发进度更新](docs/开发进度更新.md) - 实时跟踪各模块开发进度

### 协议集成文档
- [A2A协议集成设计方案](docs/A2A协议集成设计方案.md) - A2A协议集成的完整架构设计
- [MCP协议集成设计方案](docs/MCP协议集成设计方案.md) - MCP协议集成的工具生态扩展方案

### 增强功能文档
- [知识库管理与RAG增强检索设计方案](docs/知识库管理与RAG增强检索设计方案.md) - RAG增强检索的完整设计方案
- [意图识别准确率提升方案](docs/意图识别准确率提升方案.md) - 全面的意图识别技术升级方案

### 模块文档
- [核心域模块文档](src/core/README.md) - 智能体、推理引擎、工具注册表
- [通信域模块文档](src/communication/README.md) - BIR路由、ACP协议、适配器
- [执行域模块文档](src/execution/README.md) - 执行器、回调控制、优化器
- [状态域模块文档](src/state/README.md) - 上下文、内存、会话管理
- [协同域模块文档](src/coordination/README.md) - 容器、注册表、调度器
- [监控域模块文档](src/monitoring/README.md) - 日志、指标、追踪

## 更新日志

### v1.0.0 (2024-01-XX)
- 初始版本发布
- 实现五大控制域架构
- 支持21个核心模块
- 完整的追踪和监控功能
- 企业级演示示例 

### v1.1.0 (计划中)
- A2A协议集成支持
- MCP协议集成支持
- 知识库管理与RAG增强
- 混合架构协议桥接 