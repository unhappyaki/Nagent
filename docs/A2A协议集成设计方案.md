# A2A协议集成设计方案

## 项目概述

本文档描述了在现有企业级Agent架构基础上集成A2A（Agent-to-Agent）协议的完整设计方案。A2A协议是一个开放的行业标准，旨在实现不同厂商、不同框架的AI智能体之间的互操作性。

## 设计目标

### 核心目标
1. **跨平台互操作**：实现与外部A2A兼容智能体的无缝协作
2. **标准协议支持**：严格遵循A2A协议规范
3. **企业级集成**：保持现有BIR+ACP架构的企业级特性
4. **双向通信**：既能调用外部智能体，也能对外提供服务
5. **监控追踪**：完整的A2A操作监控和审计追踪

### 技术目标
- **协议兼容性**：100%兼容A2A协议标准
- **响应时间**：A2A调用响应时间 < 500ms
- **并发处理**：支持100+并发A2A连接
- **可用性**：A2A服务可用性 > 99.9%
- **安全性**：支持OAuth 2.0和API密钥认证

## A2A协议概述

### 协议特点
- **基于HTTP**：使用HTTP/HTTPS作为传输协议
- **JSON-RPC 2.0**：采用JSON-RPC 2.0消息格式
- **Agent Card**：通过Agent Card进行能力发现
- **任务生命周期**：完整的任务创建、执行、监控流程
- **多模态支持**：支持文本、音频、视频、文件等多种内容类型

### 核心组件
1. **Agent Card**：智能体能力描述和发现机制
2. **Task对象**：任务定义和参数传递
3. **Artifact对象**：任务执行结果和输出
4. **HTTP端点**：RESTful API和WebSocket支持
5. **认证机制**：OAuth 2.0和API密钥支持

## 整体架构设计

### 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│                External A2A Ecosystem 外部A2A生态            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ External Agent  │  │ External Agent  │  │ External Agent  │ │
│  │ (Claude/GPT)    │  │ (Custom)        │  │ (Third-party)   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │ A2A Protocol
┌─────────────────────────────────────────────────────────────┐
│                    A2A Interface Layer A2A接口层             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ A2A Server      │  │ A2A Client      │  │ Agent Card      │ │
│  │ (Inbound)       │  │ (Outbound)      │  │ Manager         │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │ Protocol Bridge
┌─────────────────────────────────────────────────────────────┐
│                  Adapter Layer 适配器层                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ A2A Adapter     │  │ Protocol        │  │ External Agent  │ │
│  │                 │  │ Bridge          │  │ Registry        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │ BIR/ACP Integration
┌─────────────────────────────────────────────────────────────┐
│                 Existing Core 现有核心架构                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ BIR Router      │  │ ACP Protocol    │  │ Reasoning       │ │
│  │                 │  │                 │  │ Engine          │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 模块目录结构

```
src/communication/protocols/a2a/          # A2A协议实现
├── __init__.py
├── README.md
├── a2a_server.py                         # A2A服务器实现
├── a2a_client.py                         # A2A客户端实现
├── agent_card.py                         # Agent Card管理
├── task_manager.py                       # 任务管理器
├── artifact_handler.py                   # 结果处理器
├── auth_manager.py                       # 认证管理器
├── a2a_types.py                          # A2A类型定义
├── protocol_validator.py                 # 协议验证器
└── endpoints/                            # HTTP端点实现
    ├── __init__.py
    ├── discovery.py                      # 发现端点
    ├── tasks.py                          # 任务端点
    ├── artifacts.py                      # 结果端点
    └── websocket.py                      # WebSocket支持

src/communication/adapters/               # 适配器实现
├── a2a_adapter.py                        # A2A适配器
└── external_agent_registry.py            # 外部智能体注册表

src/coordination/external/                # 外部协调模块
└── a2a_coordinator.py                    # A2A协调器
```

## 核心模块详细设计

### 1. A2A服务器实现

#### 1.1 A2A服务器核心 (a2a_server.py)

```python
class A2AServer:
    """A2A协议服务器实现"""
    
    def __init__(
        self,
        agent_card: AgentCard,
        bir_router: BIRRouter,
        trace_writer: TraceWriter,
        config: A2AServerConfig = None
    ):
        """
        初始化A2A服务器
        
        Args:
            agent_card: 智能体卡片
            bir_router: BIR路由器
            trace_writer: 追踪写入器
            config: 服务器配置
        """
        
    async def start_server(self, host: str = "0.0.0.0", port: int = 8080):
        """启动A2A服务器"""
        
    async def stop_server(self):
        """停止A2A服务器"""
        
    async def handle_task_request(self, request: A2ATaskRequest) -> A2AArtifact:
        """
        处理A2A任务请求
        
        Args:
            request: A2A任务请求
            
        Returns:
            A2A任务结果
        """
        
    async def publish_agent_card(self) -> AgentCard:
        """发布智能体卡片"""
        
    async def get_agent_capabilities(self) -> List[str]:
        """获取智能体能力列表"""
```

#### 1.2 Agent Card管理 (agent_card.py)

```python
class AgentCard:
    """A2A智能体卡片管理"""
    
    def __init__(
        self,
        name: str,
        description: str,
        capabilities: List[str],
        version: str = "1.0.0",
        endpoints: Dict[str, str] = None
    ):
        """
        初始化Agent Card
        
        Args:
            name: 智能体名称
            description: 智能体描述
            capabilities: 能力列表
            version: 版本号
            endpoints: 端点配置
        """
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentCard':
        """从字典创建Agent Card"""
        
    async def validate(self) -> bool:
        """验证Agent Card有效性"""
        
    async def update_capabilities(self, capabilities: List[str]):
        """更新能力列表"""
```

### 2. A2A客户端实现

#### 2.1 A2A客户端核心 (a2a_client.py)

```python
class A2AClient:
    """A2A协议客户端实现"""
    
    def __init__(
        self,
        trace_writer: TraceWriter,
        auth_manager: AuthManager,
        config: A2AClientConfig = None
    ):
        """
        初始化A2A客户端
        
        Args:
            trace_writer: 追踪写入器
            auth_manager: 认证管理器
            config: 客户端配置
        """
        
    async def discover_agent(self, agent_url: str) -> AgentCard:
        """
        发现外部智能体
        
        Args:
            agent_url: 智能体URL
            
        Returns:
            智能体卡片
        """
        
    async def send_task(
        self,
        agent_endpoint: str,
        task: A2ATask,
        timeout: int = 30
    ) -> A2AArtifact:
        """
        发送任务到外部智能体
        
        Args:
            agent_endpoint: 智能体端点
            task: A2A任务
            timeout: 超时时间
            
        Returns:
            任务结果
        """
        
    async def get_task_status(
        self,
        agent_endpoint: str,
        task_id: str
    ) -> A2ATaskStatus:
        """获取任务状态"""
        
    async def cancel_task(
        self,
        agent_endpoint: str,
        task_id: str
    ) -> bool:
        """取消任务"""
```

### 3. 任务管理器

#### 3.1 任务管理器实现 (task_manager.py)

```python
class A2ATaskManager:
    """A2A任务管理器"""
    
    def __init__(
        self,
        bir_router: BIRRouter,
        executor: Executor,
        trace_writer: TraceWriter
    ):
        """
        初始化任务管理器
        
        Args:
            bir_router: BIR路由器
            executor: 执行器
            trace_writer: 追踪写入器
        """
        
    async def create_task(
        self,
        task_request: A2ATaskRequest
    ) -> A2ATask:
        """
        创建A2A任务
        
        Args:
            task_request: 任务请求
            
        Returns:
            A2A任务对象
        """
        
    async def execute_task(self, task: A2ATask) -> A2AArtifact:
        """
        执行A2A任务
        
        Args:
            task: A2A任务
            
        Returns:
            任务结果
        """
        
    async def get_task_status(self, task_id: str) -> A2ATaskStatus:
        """获取任务状态"""
        
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        
    async def get_task_history(
        self,
        limit: int = 10,
        status_filter: str = None
    ) -> List[A2ATask]:
        """获取任务历史"""
```

## A2A协议适配器设计

### 协议桥接器 (protocol_bridge.py)

```python
class A2AProtocolBridge:
    """A2A协议桥接器"""
    
    def __init__(
        self,
        bir_router: BIRRouter,
        trace_writer: TraceWriter
    ):
        """
        初始化协议桥接器
        
        Args:
            bir_router: BIR路由器
            trace_writer: 追踪写入器
        """
        
    async def convert_a2a_to_bir(
        self,
        a2a_task: A2ATask
    ) -> BehaviorPackage:
        """
        将A2A任务转换为BIR行为包
        
        Args:
            a2a_task: A2A任务
            
        Returns:
            BIR行为包
        """
        
    async def convert_bir_to_a2a(
        self,
        result: Any,
        original_task: A2ATask
    ) -> A2AArtifact:
        """
        将BIR结果转换为A2A结果
        
        Args:
            result: BIR执行结果
            original_task: 原始A2A任务
            
        Returns:
            A2A结果对象
        """
        
    async def validate_conversion(
        self,
        original: A2ATask,
        converted: BehaviorPackage
    ) -> bool:
        """验证转换正确性"""
```

## 配置管理

### A2A协议配置 (config/a2a.yaml)

```yaml
a2a:
  enabled: true
  
  # 服务器配置
  server:
    host: "0.0.0.0"
    port: 8080
    max_connections: 100
    request_timeout: 30
    enable_websocket: true
    
    # Agent Card配置
    agent_card:
      name: "Enterprise Agent"
      description: "企业级智能体系统"
      version: "1.0.0"
      capabilities:
        - "task_execution"
        - "data_analysis"
        - "document_processing"
        - "workflow_automation"
      
      # 端点配置
      endpoints:
        discovery: "/.well-known/agent.json"
        tasks: "/a2a/tasks"
        artifacts: "/a2a/artifacts"
        websocket: "/a2a/ws"
  
  # 客户端配置
  client:
    default_timeout: 30
    max_retries: 3
    retry_delay: 1
    connection_pool_size: 10
    
    # 外部智能体配置
    external_agents:
      - name: "claude_agent"
        endpoint: "https://claude-agent.anthropic.com/a2a"
        auth_type: "api_key"
        api_key: "${CLAUDE_API_KEY}"
        capabilities: ["reasoning", "analysis"]
        
      - name: "gpt_agent"
        endpoint: "https://gpt-agent.openai.com/a2a"
        auth_type: "oauth2"
        client_id: "${OPENAI_CLIENT_ID}"
        client_secret: "${OPENAI_CLIENT_SECRET}"
        capabilities: ["generation", "completion"]
  
  # 认证配置
  auth:
    # 入站认证（作为服务器）
    inbound:
      enabled: true
      methods: ["api_key", "oauth2"]
      api_keys:
        - key: "${A2A_API_KEY_1}"
          name: "client_1"
          permissions: ["read", "write"]
        - key: "${A2A_API_KEY_2}"
          name: "client_2"
          permissions: ["read"]
      
      oauth2:
        issuer: "https://auth.example.com"
        audience: "a2a-server"
        algorithms: ["RS256"]
    
    # 出站认证（作为客户端）
    outbound:
      default_auth_type: "api_key"
      oauth2_config:
        token_endpoint: "https://auth.example.com/token"
        scope: "a2a:access"
  
  # 监控配置
  monitoring:
    enable_metrics: true
    enable_tracing: true
    log_requests: true
    log_responses: true
    performance_tracking: true
    
  # 协议配置
  protocol:
    version: "1.0"
    strict_validation: true
    max_task_size: 1048576  # 1MB
    max_artifact_size: 10485760  # 10MB
    supported_content_types:
      - "text/plain"
      - "application/json"
      - "image/jpeg"
      - "image/png"
      - "audio/wav"
      - "video/mp4"
```

## 与现有架构集成

### 1. BIR路由器增强

```python
# 修改 src/communication/dispatcher/bir_router.py
class BIRRouter:
    def __init__(self, ...):
        # ... 现有代码 ...
        
        # 新增A2A支持
        self.a2a_adapter = None
        if config.get("a2a", {}).get("enabled", False):
            self.a2a_adapter = A2AAdapter(self)
    
    async def route_external_request(
        self,
        protocol: str,
        request: Any
    ) -> Any:
        """路由外部协议请求"""
        
        if protocol == "a2a" and self.a2a_adapter:
            return await self.a2a_adapter.handle_external_task(request)
        
        raise ValueError(f"Unsupported protocol: {protocol}")
    
    async def register_external_agent(
        self,
        agent_info: ExternalAgentInfo
    ) -> bool:
        """注册外部智能体"""
        
        if agent_info.protocol == "a2a":
            return await self.a2a_adapter.register_external_agent(agent_info)
        
        return False
```

### 2. 外部智能体注册表

```python
# src/core/agent/external/external_agent_registry.py
class ExternalAgentRegistry:
    """外部智能体注册表"""
    
    def __init__(self, a2a_client: A2AClient):
        """
        初始化外部智能体注册表
        
        Args:
            a2a_client: A2A客户端
        """
        
    async def register_agent(self, agent_url: str) -> ExternalAgentInfo:
        """
        注册外部智能体
        
        Args:
            agent_url: 智能体URL
            
        Returns:
            外部智能体信息
        """
        
    async def discover_agents(
        self,
        capabilities: List[str]
    ) -> List[ExternalAgentInfo]:
        """
        发现具有特定能力的智能体
        
        Args:
            capabilities: 所需能力列表
            
        Returns:
            匹配的智能体列表
        """
        
    async def monitor_agent_health(
        self,
        agent_id: str
    ) -> HealthStatus:
        """
        监控智能体健康状态
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            健康状态
        """
        
    async def get_agent_stats(self) -> Dict[str, Any]:
        """获取智能体统计信息"""
```

## 开发计划集成

### 里程碑2.1：A2A协议基础（第5-6周）

#### 第5周：协议核心实现
- [ ] 实现A2A协议类型定义 (a2a_types.py)
- [ ] 实现Agent Card管理 (agent_card.py)
- [ ] 实现A2A服务器核心 (a2a_server.py)
- [ ] 实现A2A客户端核心 (a2a_client.py)
- [ ] 实现任务管理器 (task_manager.py)
- [ ] 基础功能单元测试

#### 第6周：协议完善和验证
- [ ] 实现认证管理器 (auth_manager.py)
- [ ] 实现协议验证器 (protocol_validator.py)
- [ ] 实现HTTP端点 (endpoints/)
- [ ] 实现WebSocket支持
- [ ] A2A协议兼容性测试
- [ ] 与外部A2A智能体集成测试

### 里程碑2.2：适配器层（第7-8周）

#### 第7周：适配器实现
- [ ] 实现A2A适配器 (a2a_adapter.py)
- [ ] 实现协议桥接器 (protocol_bridge.py)
- [ ] 实现外部智能体注册表
- [ ] BIR路由器A2A增强
- [ ] 适配器功能测试

#### 第8周：集成和优化
- [ ] 与现有架构深度集成
- [ ] 性能优化和调优
- [ ] 错误处理和恢复机制
- [ ] 监控和追踪集成
- [ ] 端到端A2A流程测试

## 监控和追踪

### A2A操作追踪

```python
# A2A操作的追踪记录
class A2ATraceWriter:
    """A2A操作追踪写入器"""
    
    async def record_a2a_request(
        self,
        request_type: str,
        agent_endpoint: str,
        task_data: Dict[str, Any],
        trace_id: str
    ):
        """记录A2A请求"""
        
    async def record_a2a_response(
        self,
        response_data: Dict[str, Any],
        duration: float,
        status: str,
        trace_id: str
    ):
        """记录A2A响应"""
        
    async def record_protocol_conversion(
        self,
        conversion_type: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        trace_id: str
    ):
        """记录协议转换"""
```

### 性能指标

#### 关键指标
- **A2A调用延迟**：平均 < 500ms，P99 < 1000ms
- **协议转换时间**：平均 < 50ms
- **并发连接数**：支持 100+ 并发连接
- **成功率**：A2A调用成功率 > 99%
- **兼容性**：与主流A2A实现兼容率 > 95%

## 安全考虑

### 1. 认证和授权
- 支持API密钥和OAuth 2.0认证
- 细粒度权限控制
- 请求签名验证
- 访问频率限制

### 2. 数据安全
- HTTPS强制加密传输
- 敏感数据脱敏
- 请求和响应大小限制
- 内容类型验证

### 3. 网络安全
- IP白名单支持
- DDoS防护
- 恶意请求检测
- 网络隔离

## 总结

本A2A协议集成方案在保持现有企业级架构优势的基础上，实现了与外部A2A生态的无缝互操作。方案具有以下特点：

### 技术优势
1. **标准兼容**：严格遵循A2A协议规范
2. **双向通信**：既能调用外部智能体，也能对外提供服务
3. **企业级特性**：保持完整的监控、追踪、安全机制
4. **高性能**：优化的协议转换和并发处理
5. **可扩展性**：支持多种认证方式和外部智能体

### 实施价值
1. **生态互联**：接入更广泛的A2A智能体生态
2. **能力扩展**：利用外部智能体的专业能力
3. **标准化**：遵循行业标准，降低集成成本
4. **灵活部署**：支持混合云和多云部署
5. **未来兼容**：为A2A生态演进做好准备

该方案为企业级Agent系统提供了强大的跨平台协作能力，是实现智能体生态互联的重要基础设施。 