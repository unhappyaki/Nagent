# MCP协议集成实现

## 概述

本模块实现了MCP (Model Context Protocol) 协议的完整客户端支持，使Nagent框架能够与MCP生态系统中的工具和服务进行无缝集成。

## 当前实现状态

### ✅ 已完成（第5-6周核心实现）

#### 1. 核心类型定义 (`mcp_types.py`)
- **MCPMessage**: JSON-RPC 2.0消息封装
- **MCPTool**: MCP工具定义
- **MCPResource**: MCP资源定义
- **MCPResult**: 执行结果封装
- **MCPServerConfig**: 服务器配置
- **MCPClientConfig**: 客户端配置
- **Transport系列**: 传输协议配置（Stdio/HTTP/WebSocket）

#### 2. 传输协议层 (`transports/`)
- **BaseTransport**: 传输协议基类
- **StdioTransport**: 标准输入输出传输（已完成）
- **HttpTransport**: HTTP传输（TODO）
- **WebSocketTransport**: WebSocket传输（TODO）

#### 3. 协议处理器 (`protocol_handler.py`)
- JSON-RPC消息路由和处理
- 请求/响应配对管理
- 错误处理和超时控制
- 异步消息处理

#### 4. MCP客户端核心 (`mcp_client.py`)
- 完整的MCP客户端实现
- 工具列表获取和调用
- 资源访问和读取
- 连接状态管理
- 缓存机制
- 统计信息收集

#### 5. 连接管理器 (`connection_manager.py`)
- 多MCP服务器连接管理
- 健康检查和自动重连
- 配置热重载
- 连接池管理

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│              External MCP Ecosystem 外部MCP生态              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Database Tools  │  │ File System     │  │ API Tools       │ │
│  │ MCP Server      │  │ MCP Server      │  │ MCP Server      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │ MCP Protocol
┌─────────────────────────────────────────────────────────────┐
│                   MCP Interface Layer MCP接口层              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ MCPClient       │  │ Connection      │  │ Protocol        │ │
│  │                 │  │ Manager         │  │ Handler         │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │ 接下来实现
┌─────────────────────────────────────────────────────────────┐
│                  Adapter Layer 适配器层 (TODO)               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ MCP Adapter     │  │ Tool Wrapper    │  │ External Tool   │ │
│  │                 │  │                 │  │ Registry        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 核心特性

### 1. 协议兼容性
- 100%兼容MCP协议标准（2024-11-05版本）
- 支持JSON-RPC 2.0消息格式
- 完整的错误处理机制

### 2. 传输协议支持
- **Stdio**: 通过标准输入输出与MCP服务器通信 ✅
- **HTTP**: HTTP协议支持（计划中）
- **WebSocket**: WebSocket协议支持（计划中）

### 3. 连接管理
- 多服务器连接池管理
- 自动健康检查和重连
- 连接状态监控
- 配置热重载

### 4. 性能优化
- 工具和资源缓存机制
- 异步并发处理
- 连接复用
- 请求超时控制

### 5. 企业级特性
- 完整的统计信息收集
- 结构化日志记录
- 错误追踪和监控
- 资源清理和内存管理

## 使用示例

### 基础使用

```python
from src.communication.protocols.mcp import (
    MCPClient, MCPServerConfig, StdioTransportConfig
)

# 创建服务器配置
transport_config = StdioTransportConfig(
    command=["python", "-m", "mcp_server"],
    args=["--config", "config.json"]
)

server_config = MCPServerConfig(
    name="example_server",
    description="示例MCP服务器",
    transport=transport_config,
    enabled=True
)

# 创建客户端并连接
async with MCPClient(server_config) as client:
    # 获取工具列表
    tools = await client.list_tools()
    print(f"Available tools: {[tool.name for tool in tools]}")
    
    # 调用工具
    result = await client.call_tool(
        "example_tool",
        {"param1": "value1", "param2": "value2"}
    )
    
    if not result.isError:
        print(f"Tool result: {result.content}")
    else:
        print(f"Tool error: {result.error}")
```

### 连接管理器使用

```python
from src.communication.protocols.mcp import MCPConnectionManager

# 创建连接管理器
async with MCPConnectionManager() as manager:
    # 添加多个服务器
    await manager.add_server(server_config1)
    await manager.add_server(server_config2)
    
    # 获取连接
    client = await manager.get_connection("example_server")
    if client:
        tools = await client.list_tools()
        # ... 使用客户端
    
    # 健康检查
    health = await manager.health_check()
    print(f"Connection health: {health}")
```

## 配置格式

### 服务器配置示例

```yaml
mcp:
  enabled: true
  servers:
    - name: "database_tools"
      description: "数据库操作工具集"
      transport:
        type: "stdio"
        command: ["python", "-m", "mcp_database_server"]
        args: ["--config", "/etc/mcp/database.json"]
        env:
          DATABASE_URL: "${DATABASE_URL}"
      capabilities: ["database", "sql", "query"]
      enabled: true
      
    - name: "filesystem_tools"
      description: "文件系统操作工具集"
      transport:
        type: "stdio"
        command: ["mcp-filesystem-server"]
        args: ["--root", "/data"]
      capabilities: ["filesystem", "file_io"]
      enabled: true
```

## 下一步实现计划

### 第7-8周：适配器层实现

1. **MCP适配器 (`mcp_adapter.py`)**
   - 与现有工具注册表集成
   - 工具发现和注册
   - 权限映射

2. **工具包装器 (`tool_wrapper.py`)**
   - MCPToolWrapper实现BaseTool接口
   - 参数验证和转换
   - 执行结果处理

3. **外部工具注册表 (`external_tool_registry.py`)**
   - MCP工具统一管理
   - 工具分类和标签
   - 热插拔支持

4. **与现有架构集成**
   - 工具注册表MCP增强
   - 执行器集成
   - 监控追踪集成

### 传输协议扩展

1. **HTTP传输实现**
   - RESTful API支持
   - 认证和授权
   - 连接池管理

2. **WebSocket传输实现**
   - 实时双向通信
   - 心跳检测
   - 消息压缩

### 高级特性

1. **资源管理器**
   - 资源缓存和索引
   - 大文件分块处理
   - 访问权限控制

2. **认证管理器**
   - 多种认证方式支持
   - Token管理和刷新
   - 安全传输

## 测试和调试

### 测试覆盖

- 单元测试：核心类型和消息处理
- 集成测试：与真实MCP服务器通信
- 性能测试：并发连接和工具调用
- 错误处理测试：网络异常和协议错误

### 调试工具

- 详细的结构化日志
- 消息追踪和分析
- 性能指标监控
- 连接状态诊断

## 贡献指南

1. 遵循现有代码风格和架构模式
2. 添加完整的类型注解和文档字符串
3. 使用结构化日志记录关键操作
4. 编写相应的单元测试
5. 更新相关文档

## 参考资料

- [MCP协议规范](https://spec.modelcontextprotocol.io/)
- [JSON-RPC 2.0规范](https://www.jsonrpc.org/specification)
- [Nagent架构文档](../../../README.md) 