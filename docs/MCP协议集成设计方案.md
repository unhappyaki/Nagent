# MCP协议集成设计方案

## 项目概述

本文档描述了在现有企业级Agent架构基础上集成MCP（Model Context Protocol）协议的完整设计方案。MCP协议是一个开放标准，旨在实现AI应用与外部工具和数据源的安全、标准化连接。

## 设计目标

### 核心目标
1. **工具生态扩展**：通过MCP协议接入丰富的外部工具生态
2. **标准化集成**：遵循MCP协议规范，实现标准化工具集成
3. **安全可控**：保持企业级安全控制和权限管理
4. **无缝融合**：与现有工具注册表和执行引擎深度集成
5. **高性能**：优化的工具调用和资源管理

### 技术目标
- **协议兼容性**：100%兼容MCP协议标准
- **工具调用延迟**：平均 < 300ms
- **并发工具调用**：支持200+并发工具执行
- **可用性**：MCP服务可用性 > 99.9%
- **工具覆盖率**：支持90%以上的主流MCP工具

## MCP协议概述

### 协议特点
- **客户端-服务器架构**：MCP Client连接MCP Server
- **JSON-RPC通信**：基于JSON-RPC 2.0消息协议
- **资源管理**：统一的资源发现和访问机制
- **工具调用**：标准化的工具调用接口
- **流式支持**：支持流式数据传输
- **安全机制**：内置认证和权限控制

### 核心组件
1. **MCP Client**：连接和管理MCP服务器
2. **MCP Server**：提供工具和资源的服务端
3. **Resource**：可访问的数据资源
4. **Tool**：可调用的功能工具
5. **Prompt**：模板化的提示词
6. **Transport**：底层传输协议（stdio/HTTP/WebSocket）

## 整体架构设计

### 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│              External MCP Ecosystem 外部MCP生态              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Database Tools  │  │ File System     │  │ API Tools       │ │
│  │ MCP Server      │  │ MCP Server      │  │ MCP Server      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Cloud Services  │  │ Analytics Tools │  │ Custom Tools    │ │
│  │ MCP Server      │  │ MCP Server      │  │ MCP Server      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │ MCP Protocol
┌─────────────────────────────────────────────────────────────┐
│                   MCP Interface Layer MCP接口层              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ MCP Client      │  │ MCP Server      │  │ Resource        │ │
│  │ Manager         │  │ (Optional)      │  │ Manager         │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Connection      │  │ Transport       │  │ Protocol        │ │
│  │ Manager         │  │ Manager         │  │ Handler         │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │ Tool Integration
┌─────────────────────────────────────────────────────────────┐
│                  Adapter Layer 适配器层                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ MCP Adapter     │  │ Tool Wrapper    │  │ External Tool   │ │
│  │                 │  │                 │  │ Registry        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │ Tool Registry Integration
┌─────────────────────────────────────────────────────────────┐
│                 Existing Core 现有核心架构                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Tool Registry   │  │ Executor        │  │ Base Tool       │ │
│  │                 │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 模块目录结构

```
src/communication/protocols/mcp/          # MCP协议实现
├── __init__.py
├── README.md
├── mcp_client.py                         # MCP客户端实现
├── mcp_server.py                         # MCP服务器实现（可选）
├── resource_manager.py                   # 资源管理器
├── connection_manager.py                 # 连接管理器
├── transport_manager.py                  # 传输管理器
├── protocol_handler.py                   # 协议处理器
├── mcp_types.py                          # MCP类型定义
├── auth_manager.py                       # 认证管理器
└── transports/                           # 传输协议实现
    ├── __init__.py
    ├── stdio_transport.py                # Stdio传输
    ├── http_transport.py                 # HTTP传输
    └── websocket_transport.py            # WebSocket传输

src/communication/adapters/               # 适配器实现
├── mcp_adapter.py                        # MCP适配器
├── tool_wrapper.py                       # 工具包装器
└── external_tool_registry.py             # 外部工具注册表

src/core/tools/external/                  # 外部工具模块
├── __init__.py
├── mcp_tool.py                           # MCP工具基类
├── mcp_tool_factory.py                   # MCP工具工厂
└── tool_discovery.py                     # 工具发现服务
```

## 核心模块详细设计

### 1. MCP客户端实现

#### 1.1 MCP客户端核心 (mcp_client.py)

```python
class MCPClient:
    """MCP协议客户端实现"""
    
    def __init__(
        self,
        server_config: MCPServerConfig,
        transport_type: str = "stdio",
        auth_manager: AuthManager = None,
        trace_writer: TraceWriter = None
    ):
        self.server_config = server_config
        self.transport_type = transport_type
        self.auth_manager = auth_manager
        self.trace_writer = trace_writer
        
    async def connect(self) -> bool:
        """连接到MCP服务器"""
        
    async def disconnect(self) -> bool:
        """断开与MCP服务器的连接"""
        
    async def list_tools(self) -> List[MCPTool]:
        """获取可用工具列表"""
        
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: int = 30
    ) -> MCPResult:
        """调用MCP工具"""
        
    async def list_resources(self) -> List[MCPResource]:
        """获取可用资源列表"""
        
    async def read_resource(
        self,
        resource_uri: str
    ) -> MCPResourceContent:
        """读取资源内容"""
```

#### 1.2 连接管理器 (connection_manager.py)

```python
class MCPConnectionManager:
    """MCP连接管理器"""
    
    def __init__(self, config: MCPConfig = None):
        self.config = config or MCPConfig()
        self.connections = {}
        
    async def create_connection(
        self,
        server_config: MCPServerConfig
    ) -> MCPClient:
        """创建MCP连接"""
        
    async def get_connection(
        self,
        server_name: str
    ) -> Optional[MCPClient]:
        """获取现有连接"""
        
    async def close_connection(self, server_name: str) -> bool:
        """关闭连接"""
        
    async def health_check(self) -> Dict[str, bool]:
        """检查所有连接健康状态"""
```

### 2. MCP适配器

#### 2.1 MCP适配器实现 (mcp_adapter.py)

```python
class MCPAdapter:
    """MCP协议适配器"""
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        connection_manager: MCPConnectionManager,
        trace_writer: TraceWriter
    ):
        self.tool_registry = tool_registry
        self.connection_manager = connection_manager
        self.trace_writer = trace_writer
        
    async def register_mcp_server(
        self,
        server_config: MCPServerConfig
    ) -> bool:
        """注册MCP服务器"""
        
    async def discover_and_register_tools(
        self,
        server_name: str
    ) -> List[str]:
        """发现并注册MCP工具"""
        
    async def wrap_mcp_tool(
        self,
        mcp_tool: MCPTool,
        server_name: str
    ) -> BaseTool:
        """包装MCP工具为内部工具"""
        
    async def execute_mcp_tool(
        self,
        tool_id: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """执行MCP工具"""
```

#### 2.2 工具包装器 (tool_wrapper.py)

```python
class MCPToolWrapper(BaseTool):
    """MCP工具包装器 - 完全兼容现有BaseTool接口"""
    
    def __init__(
        self,
        mcp_tool: MCPTool,
        mcp_client: MCPClient,
        server_name: str,
        tool_registry: 'ToolRegistry' = None
    ):
        # 继承BaseTool的标准初始化
        super().__init__(
            name=f"mcp_{server_name}_{mcp_tool.name}",
            description=mcp_tool.description or f"MCP tool from {server_name}"
        )
        
        self.mcp_tool = mcp_tool
        self.mcp_client = mcp_client
        self.server_name = server_name
        self.tool_registry = tool_registry
        
        # MCP特有属性
        self.mcp_schema = mcp_tool.inputSchema
        self.capabilities = getattr(mcp_tool, 'capabilities', [])
        
    async def execute(self, **kwargs) -> Any:
        """执行MCP工具 - 完全兼容BaseTool.execute()接口"""
        try:
            # 参数验证
            if not await self.validate_arguments(kwargs):
                raise ValueError(f"Invalid arguments for MCP tool {self.name}")
            
            # 记录工具调用开始
            start_time = time.time()
            
            # 调用MCP工具
            result = await self.mcp_client.call_tool(
                tool_name=self.mcp_tool.name,
                arguments=kwargs,
                timeout=getattr(self.mcp_tool, 'timeout', 30)
            )
            
            # 处理MCP结果格式
            processed_result = await self._process_mcp_result(result)
            
            # 更新工具统计（如果有tool_registry）
            if self.tool_registry:
                execution_time = time.time() - start_time
                await self._update_tool_stats(execution_time, True)
            
            return processed_result
            
        except Exception as e:
            # 更新失败统计
            if self.tool_registry:
                await self._update_tool_stats(0, False, str(e))
            
            # 重新抛出异常，让上层处理
            raise MCPToolExecutionError(
                f"MCP tool {self.name} execution failed: {str(e)}"
            ) from e
    
    async def validate_arguments(self, arguments: Dict[str, Any]) -> bool:
        """验证工具参数 - 基于MCP schema"""
        if not self.mcp_schema:
            return True
        
        try:
            # 使用jsonschema验证参数
            import jsonschema
            jsonschema.validate(arguments, self.mcp_schema)
            return True
        except Exception as e:
            logger.warning(
                "MCP tool argument validation failed",
                tool_name=self.name,
                error=str(e)
            )
            return False
    
    async def get_schema(self) -> Dict[str, Any]:
        """获取工具模式"""
        return {
            "name": self.name,
            "description": self.description,
            "mcp_schema": self.mcp_schema,
            "server_name": self.server_name,
            "capabilities": self.capabilities,
            "type": "mcp_tool"
        }
    
    def get_info(self) -> Dict[str, Any]:
        """获取工具信息 - 扩展BaseTool.get_info()"""
        base_info = super().get_info()
        base_info.update({
            "server_name": self.server_name,
            "mcp_tool_name": self.mcp_tool.name,
            "capabilities": self.capabilities,
            "type": "mcp_tool",
            "schema": self.mcp_schema
        })
        return base_info
    
    async def _process_mcp_result(self, mcp_result: MCPResult) -> Any:
        """处理MCP结果，转换为统一格式"""
        if mcp_result.isError:
            raise MCPToolExecutionError(mcp_result.content)
        
        # 根据内容类型处理结果
        if hasattr(mcp_result, 'content'):
            if isinstance(mcp_result.content, list):
                # 多个内容块
                return {
                    "type": "multi_content",
                    "content": mcp_result.content,
                    "server": self.server_name
                }
            else:
                # 单个内容
                return {
                    "type": "single_content", 
                    "content": mcp_result.content,
                    "server": self.server_name
                }
        
        return {"result": str(mcp_result), "server": self.server_name}
    
    async def _update_tool_stats(
        self, 
        execution_time: float, 
        success: bool, 
        error: str = None
    ):
        """更新工具统计信息"""
        if not self.tool_registry or not hasattr(self.tool_registry, 'tool_stats'):
            return
        
        stats = self.tool_registry.tool_stats.get(self.name, {
            "calls": 0,
            "success": 0,
            "errors": 0,
            "total_time": 0.0
        })
        
        stats["calls"] += 1
        if success:
            stats["success"] += 1
        else:
            stats["errors"] += 1
        stats["total_time"] += execution_time
        
        self.tool_registry.tool_stats[self.name] = stats


class MCPToolExecutionError(Exception):
    """MCP工具执行异常"""
    pass
```

## 配置管理

### MCP协议配置 (config/mcp.yaml)

```yaml
mcp:
  enabled: true
  
  # 客户端配置
  client:
    default_timeout: 30
    max_retries: 3
    retry_delay: 1
    connection_pool_size: 20
    keep_alive: true
    
  # MCP服务器配置
  servers:
    # 数据库工具服务器
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
      
    # 文件系统工具服务器
    - name: "filesystem_tools"
      description: "文件系统操作工具集"
      transport:
        type: "stdio"
        command: ["mcp-filesystem-server"]
        args: ["--root", "/data"]
      capabilities: ["filesystem", "file_io", "directory"]
      enabled: true
      
    # API工具服务器
    - name: "api_tools"
      description: "外部API调用工具集"
      transport:
        type: "http"
        url: "http://localhost:3001/mcp"
        headers:
          Authorization: "Bearer ${API_TOOLS_TOKEN}"
      capabilities: ["api", "http", "rest"]
      enabled: true
  
  # 工具发现配置
  discovery:
    auto_discovery: true
    discovery_interval: 300  # 5分钟
    cache_tools: true
    cache_ttl: 3600  # 1小时
    
  # 资源管理配置
  resources:
    cache_enabled: true
    cache_size: 100  # MB
    cache_ttl: 1800  # 30分钟
    max_resource_size: 10485760  # 10MB
    
  # 工具执行配置
  execution:
    default_timeout: 30
    max_concurrent_calls: 50
    rate_limit:
      enabled: true
      max_calls_per_minute: 100
      max_calls_per_hour: 1000
    
    # 工具类别配置
    tool_categories:
      database:
        timeout: 60
        max_concurrent: 10
        rate_limit: 50
      filesystem:
        timeout: 30
        max_concurrent: 20
        rate_limit: 200
      api:
        timeout: 45
        max_concurrent: 30
        rate_limit: 100
  
  # 安全配置
  security:
    # 工具白名单
    allowed_tools:
      - "database.*"
      - "filesystem.read*"
      - "api.get*"
    
    # 工具黑名单
    blocked_tools:
      - "filesystem.delete_all"
      - "database.drop_table"
      - "api.admin.*"
    
    # 参数验证
    validate_arguments: true
    sanitize_inputs: true
    
    # 资源访问控制
    resource_access:
      max_file_size: 10485760  # 10MB
      allowed_extensions: [".txt", ".json", ".csv", ".xml"]
      blocked_paths: ["/etc", "/proc", "/sys"]
  
  # 监控配置
  monitoring:
    enable_metrics: true
    enable_tracing: true
    log_tool_calls: true
    log_resource_access: true
    performance_tracking: true
    
    # 告警配置
    alerts:
      high_latency_threshold: 5000  # 5秒
      error_rate_threshold: 0.05   # 5%
      connection_failure_threshold: 3
  
  # 传输协议配置
  transports:
    stdio:
      buffer_size: 8192
      timeout: 30
      
    http:
      connection_timeout: 10
      read_timeout: 30
      max_connections: 10
      
    websocket:
      ping_interval: 30
      ping_timeout: 10
      max_message_size: 1048576  # 1MB
```

## 与现有架构集成

### 1. 工具注册表增强

基于现有工具调用实现，MCP集成需要完全兼容现有的权限系统、统计机制和执行流程：

```python
# 修改 src/core/tools/tool_registry.py
class ToolRegistry:
    def __init__(self, ...):
        # ... 现有代码 ...
        
        # 新增MCP支持，完全兼容现有架构
        self.mcp_adapter = None
        self.external_tool_registry = None
        self.mcp_connection_manager = None
        
        if config.get("mcp", {}).get("enabled", False):
            self.mcp_connection_manager = MCPConnectionManager(config.get("mcp", {}))
            self.mcp_adapter = MCPAdapter(
                tool_registry=self,
                connection_manager=self.mcp_connection_manager,
                trace_writer=trace_writer
            )
            self.external_tool_registry = ExternalToolRegistry(
                self.mcp_adapter, self
            )
    
    async def initialize(self):
        """初始化工具注册表"""
        # ... 现有初始化代码 ...
        
        # 注册默认工具
        self._register_default_tools()
        
        # 初始化MCP工具
        if self.external_tool_registry:
            await self._initialize_mcp_tools()
    
    async def _initialize_mcp_tools(self):
        """初始化MCP工具 - 完全集成到现有注册机制"""
        mcp_servers = config.get("mcp", {}).get("servers", [])
        
        for server_config in mcp_servers:
            if server_config.get("enabled", True):
                try:
                    # 连接MCP服务器
                    mcp_client = await self.mcp_connection_manager.create_connection(
                        MCPServerConfig.from_dict(server_config)
                    )
                    
                    # 发现工具
                    mcp_tools = await mcp_client.list_tools()
                    
                    # 将MCP工具注册到现有系统
                    for mcp_tool in mcp_tools:
                        await self._register_mcp_tool(mcp_tool, mcp_client, server_config["name"])
                    
                    logger.info(
                        "Registered MCP server",
                        server_name=server_config["name"],
                        tool_count=len(mcp_tools)
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to register MCP server",
                        server_name=server_config["name"],
                        error=str(e)
                    )
    
    async def _register_mcp_tool(
        self, 
        mcp_tool: MCPTool, 
        mcp_client: MCPClient, 
        server_name: str
    ):
        """将MCP工具注册到现有工具注册表"""
        # 创建工具包装器
        tool_wrapper = MCPToolWrapper(
            mcp_tool=mcp_tool,
            mcp_client=mcp_client,
            server_name=server_name,
            tool_registry=self
        )
        
        # 使用现有的register_tool方法
        self.register_tool(
            name=tool_wrapper.name,
            tool_func=tool_wrapper,  # 直接传入包装器实例
            description=tool_wrapper.description,
            metadata={
                "server_name": server_name,
                "mcp_tool_name": mcp_tool.name,
                "type": "mcp_tool",
                "capabilities": getattr(mcp_tool, 'capabilities', [])
            },
            permissions=self._map_mcp_permissions(mcp_tool, server_name),
            timeout=getattr(mcp_tool, 'timeout', 30)
        )
    
    def _map_mcp_permissions(self, mcp_tool: MCPTool, server_name: str) -> List[ToolPermission]:
        """将MCP工具权限映射到现有权限系统"""
        permissions = [ToolPermission.EXECUTE]  # 默认执行权限
        
        # 根据工具类型和服务器配置映射权限
        server_config = next(
            (s for s in config.get("mcp", {}).get("servers", []) 
             if s["name"] == server_name), 
            {}
        )
        
        capabilities = server_config.get("capabilities", [])
        
        if "database" in capabilities or "sql" in capabilities:
            permissions.extend([ToolPermission.READ, ToolPermission.WRITE])
        elif "filesystem" in capabilities:
            permissions.extend([ToolPermission.READ, ToolPermission.WRITE])
        elif "api" in capabilities:
            permissions.append(ToolPermission.READ)
        
        return permissions
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取工具 - 无需修改，MCP工具已集成到现有系统"""
        # 现有逻辑无需修改，MCP工具已通过register_tool注册
        return self.tools.get(name)
    
    async def execute_tool(self, name: str, params: Dict[str, Any], **kwargs) -> Any:
        """执行工具 - 无需修改，MCP工具完全兼容现有执行流程"""
        # 现有逻辑无需修改，MCP工具包装器实现了BaseTool接口
        return await super().execute_tool(name, params, **kwargs)
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表 - 自动包含MCP工具"""
        tools = []
        for name in self.tools:
            tool_info = self.get_tool_info(name)
            if tool_info:
                tools.append(tool_info)
        return tools
    
    def discover_tools(self, pattern: str = None) -> List[Dict[str, Any]]:
        """发现工具 - 支持MCP工具搜索"""
        tools = self.get_available_tools()
        
        if pattern:
            filtered_tools = []
            for tool in tools:
                if (pattern.lower() in tool["name"].lower() or 
                    pattern.lower() in tool["description"].lower() or
                    (tool.get("metadata", {}).get("type") == "mcp_tool" and 
                     pattern.lower() in tool.get("metadata", {}).get("server_name", "").lower())):
                    filtered_tools.append(tool)
            return filtered_tools
        
        return tools
```

### 2. 执行器集成

基于现有执行器实现，MCP工具可以无缝集成到现有的ExecutionChain和ExecutionStep流程中：

```python
# src/execution/executor.py - 无需修改现有代码
# MCP工具通过MCPToolWrapper完全兼容现有执行流程

class Executor:
    # 现有代码保持不变，无需任何修改
    # MCP工具已通过工具注册表集成，执行器自动支持
    
    async def _execute_step(self, step: ExecutionStep, chain: ExecutionChain) -> None:
        """执行单个步骤 - 现有逻辑，自动支持MCP工具"""
        step.status = ExecutionStatus.RUNNING
        step.start_time = datetime.utcnow()
        
        try:
            logger.debug(
                "Executing step",
                step_id=step.step_id,
                tool_name=step.tool_name,
                chain_id=chain.chain_id
            )
            
            # 获取工具（包括MCP工具）
            tool = self.tool_registry.get_tool(step.tool_name)
            if not tool:
                raise ValueError(f"Tool not found: {step.tool_name}")
            
            # 执行工具 - MCPToolWrapper实现了BaseTool.execute()
            # 无需特殊处理，统一调用
            result = await tool.execute(**step.parameters)
            
            # 更新步骤状态
            step.status = ExecutionStatus.COMPLETED
            step.result = result
            self.execution_stats["completed_steps"] += 1
            
            # 写入内存 - 支持MCP工具结果
            await self.memory_manager.add_memory(
                content=f"Tool {step.tool_name} executed successfully: {result}",
                memory_type="tool_execution",
                context_id=chain.context_id,
                trace_id=chain.trace_id,
                metadata={
                    "step_id": step.step_id,
                    "tool_name": step.tool_name,
                    "chain_id": chain.chain_id,
                    "tool_type": getattr(tool, 'get_info', lambda: {}).get("type", "internal")
                }
            )
            
            # 执行回调 - 现有回调机制自动支持MCP工具
            await self.callback_handler.handle_callback(
                CallbackType.SUCCESS,
                {
                    "event": "step_completed",
                    "step_id": step.step_id,
                    "tool_name": step.tool_name,
                    "result": result,
                    "chain_id": chain.chain_id,
                    "tool_info": tool.get_info() if hasattr(tool, 'get_info') else {}
                },
                chain.context_id,
                chain.trace_id
            )
            
        except Exception as e:
            step.status = ExecutionStatus.FAILED
            step.error = str(e)
            self.execution_stats["failed_steps"] += 1
            
            logger.error(
                "Step execution failed",
                step_id=step.step_id,
                tool_name=step.tool_name,
                error=str(e),
                tool_type=getattr(tool, 'get_info', lambda: {}).get("type", "unknown") if 'tool' in locals() else "unknown"
            )
            
            # 执行错误回调 - 支持MCP工具错误处理
            await self.callback_handler.handle_callback(
                CallbackType.ERROR,
                {
                    "event": "step_failed",
                    "step_id": step.step_id,
                    "tool_name": step.tool_name,
                    "error": str(e),
                    "chain_id": chain.chain_id,
                    "tool_info": tool.get_info() if hasattr(tool, 'get_info') else {}
                },
                chain.context_id,
                chain.trace_id
            )
        
        finally:
            step.end_time = datetime.utcnow()
            if step.start_time and step.end_time:
                step.execution_time = (step.end_time - step.start_time).total_seconds()


# 新增：MCP特有的执行统计和监控
class MCPExecutionMonitor:
    """MCP工具执行监控器"""
    
    def __init__(self, executor: Executor):
        self.executor = executor
        self.mcp_stats = {
            "total_mcp_calls": 0,
            "successful_mcp_calls": 0,
            "failed_mcp_calls": 0,
            "mcp_servers": {},
            "average_mcp_latency": 0.0
        }
    
    async def record_mcp_execution(
        self,
        tool_name: str,
        server_name: str,
        execution_time: float,
        success: bool,
        error: str = None
    ):
        """记录MCP工具执行统计"""
        self.mcp_stats["total_mcp_calls"] += 1
        
        if success:
            self.mcp_stats["successful_mcp_calls"] += 1
        else:
            self.mcp_stats["failed_mcp_calls"] += 1
        
        # 服务器级别统计
        if server_name not in self.mcp_stats["mcp_servers"]:
            self.mcp_stats["mcp_servers"][server_name] = {
                "calls": 0,
                "success": 0,
                "errors": 0,
                "total_time": 0.0,
                "tools": set()
            }
        
        server_stats = self.mcp_stats["mcp_servers"][server_name]
        server_stats["calls"] += 1
        server_stats["tools"].add(tool_name)
        server_stats["total_time"] += execution_time
        
        if success:
            server_stats["success"] += 1
        else:
            server_stats["errors"] += 1
        
        # 更新平均延迟
        total_time = sum(
            stats["total_time"] 
            for stats in self.mcp_stats["mcp_servers"].values()
        )
        total_calls = self.mcp_stats["total_mcp_calls"]
        self.mcp_stats["average_mcp_latency"] = total_time / total_calls if total_calls > 0 else 0.0
    
    def get_mcp_stats(self) -> Dict[str, Any]:
        """获取MCP执行统计"""
        stats = self.mcp_stats.copy()
        
        # 转换服务器统计中的set为list
        for server_name, server_stats in stats["mcp_servers"].items():
            server_stats = server_stats.copy()
            server_stats["tools"] = list(server_stats["tools"])
            server_stats["success_rate"] = (
                server_stats["success"] / server_stats["calls"] 
                if server_stats["calls"] > 0 else 0.0
            )
            server_stats["average_latency"] = (
                server_stats["total_time"] / server_stats["calls"]
                if server_stats["calls"] > 0 else 0.0
            )
            stats["mcp_servers"][server_name] = server_stats
        
        stats["mcp_success_rate"] = (
            stats["successful_mcp_calls"] / stats["total_mcp_calls"]
            if stats["total_mcp_calls"] > 0 else 0.0
        )
        
        return stats
```

## 开发计划集成

### 里程碑2.1：MCP协议基础（第5-6周）

#### 第5周：协议核心实现
- [ ] 实现MCP协议类型定义 (mcp_types.py)
- [ ] 实现MCP客户端核心 (mcp_client.py)
- [ ] 实现连接管理器 (connection_manager.py)
- [ ] 实现传输协议 (transports/)
- [ ] 实现协议处理器 (protocol_handler.py)
- [ ] 基础连接和通信测试

#### 第6周：资源和工具管理
- [ ] 实现资源管理器 (resource_manager.py)
- [ ] 实现工具包装器 (tool_wrapper.py)
- [ ] 实现认证管理器 (auth_manager.py)
- [ ] MCP服务器连接测试
- [ ] 工具发现和调用测试

### 里程碑2.2：适配器层（第7-8周）

#### 第7周：适配器实现
- [ ] 实现MCP适配器 (mcp_adapter.py)
- [ ] 实现外部工具注册表 (external_tool_registry.py)
- [ ] 工具注册表MCP增强
- [ ] 执行器MCP集成
- [ ] 适配器功能测试

#### 第8周：集成和优化
- [ ] 与现有架构深度集成
- [ ] 性能优化和调优
- [ ] 安全控制和权限管理
- [ ] 监控和追踪集成
- [ ] 端到端MCP工具执行测试

## 监控和追踪

### MCP操作追踪

```python
class MCPTraceWriter:
    """MCP操作追踪写入器"""
    
    async def record_mcp_connection(
        self,
        server_name: str,
        connection_type: str,
        status: str,
        trace_id: str
    ):
        """记录MCP连接"""
        
    async def record_tool_discovery(
        self,
        server_name: str,
        discovered_tools: List[str],
        duration: float,
        trace_id: str
    ):
        """记录工具发现"""
        
    async def record_tool_execution(
        self,
        tool_name: str,
        server_name: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
        duration: float,
        status: str,
        trace_id: str
    ):
        """记录工具执行"""
```

### 性能指标

#### 关键指标
- **工具调用延迟**：平均 < 300ms，P99 < 1000ms
- **连接建立时间**：平均 < 100ms
- **工具发现时间**：平均 < 500ms
- **并发工具调用**：支持 200+ 并发
- **成功率**：MCP工具调用成功率 > 99%

#### 监控指标
- MCP服务器连接状态
- 工具调用频率和延迟
- 资源访问统计
- 错误率和失败原因
- 缓存命中率

## 安全考虑

### 1. 工具执行安全
- 工具白名单和黑名单控制
- 参数验证和输入清理
- 执行超时和资源限制
- 权限检查和访问控制

### 2. 连接安全
- 传输加密（TLS/SSL）
- 认证和授权机制
- 连接限制和速率控制
- 恶意服务器检测

### 3. 数据安全
- 敏感数据脱敏
- 资源访问控制
- 数据传输加密
- 审计日志记录

## 关键调整说明

基于工具调用实现分析，本MCP集成方案进行了以下重要调整：

### 1. 架构集成方式调整
**原方案**：独立的MCP适配器层，需要修改现有执行流程
**调整后**：完全集成到现有ToolRegistry，无需修改Executor代码

### 2. 工具注册机制调整
**原方案**：外部工具注册表独立管理MCP工具
**调整后**：直接使用现有`register_tool()`方法，MCP工具享受完整的权限控制、统计监控、健康检查

### 3. 执行流程调整
**原方案**：需要在Executor中特殊处理MCP工具
**调整后**：MCPToolWrapper完全实现BaseTool接口，现有ExecutionChain和ExecutionStep无需任何修改

### 4. 权限系统调整
**原方案**：MCP工具使用独立的权限系统
**调整后**：完全映射到现有ToolPermission枚举，享受统一的权限检查机制

### 5. 监控追踪调整
**原方案**：独立的MCP追踪机制
**调整后**：完全集成到现有TraceWriter和CallbackHandler，统一的三大锚点机制

## 总结

调整后的MCP协议集成方案在保持现有企业级架构优势的基础上，实现了真正的无缝集成。方案具有以下特点：

### 技术优势
1. **完全兼容**：100%兼容现有工具调用架构，零代码修改
2. **统一管理**：MCP工具享受与内部工具相同的权限、监控、统计机制
3. **企业级特性**：完整保持现有的安全控制、全链路追踪、异常处理
4. **高性能**：复用现有的执行链调度、并发控制、缓存机制
5. **标准兼容**：严格遵循MCP协议规范

### 实施优势
1. **零风险集成**：不影响现有功能，渐进式启用MCP工具
2. **统一体验**：用户无需区分内部工具和MCP工具，统一的调用方式
3. **完整监控**：MCP工具调用自动纳入现有监控体系
4. **权限一致**：统一的权限控制，符合企业安全要求
5. **可扩展性**：为后续A2A协议集成提供了最佳实践模板

### 实施价值
1. **能力爆炸**：通过MCP生态大幅扩展系统工具能力
2. **开发效率**：复用丰富的MCP工具生态，减少重复开发
3. **标准化**：遵循行业标准，降低集成和维护成本
4. **生态融合**：无缝融入MCP工具生态系统
5. **架构演进**：为企业级Agent系统提供了工具生态扩展的完美范例

该调整后的方案真正体现了企业级架构的设计理念：**通过统一的接口和标准化的流程，实现复杂系统的简单集成**。MCP工具不再是"外部工具"，而是"扩展工具"，完全融入现有的企业级工具调用体系。 