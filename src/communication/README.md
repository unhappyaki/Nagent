# 通信域模块 (Communication Domain)

## 模块概述

通信域模块负责智能体间的消息传递、路由调度和协议管理，是企业级Agent系统的通信基础设施。

## 模块组成

### 1. BIR路由模块 (`dispatcher/`)
- **功能**: 智能体间消息路由、消息格式标准化、负载均衡和故障转移
- **核心类**: `BIRRouter`
- **主要接口**:
  - `route_message(message)`: 路由消息
  - `register_agent(agent_id, endpoint)`: 注册Agent
  - `get_agent_endpoint(agent_id)`: 获取Agent端点

### 2. ACP通信模块 (`acp/`)
- **功能**: ACP协议实现、客户端和服务器端、协议版本管理
- **核心类**: `ACPClient`, `ACPServer`
- **主要接口**:
  - `connect(server_url)`: 连接服务器
  - `send_request(request)`: 发送请求
  - `disconnect()`: 断开连接

### 3. 消息调度器模块 (`dispatcher/`)
- **功能**: 消息队列管理、消息优先级处理、消息持久化
- **核心类**: `MessageDispatcher`
- **主要接口**:
  - `dispatch_message(message)`: 分发消息
  - `set_priority(message_id, priority)`: 设置优先级
  - `get_message_status(message_id)`: 获取消息状态

## 技术架构

### 设计原则
- **高可用性**: 支持故障转移和负载均衡
- **可扩展性**: 支持水平扩展
- **可靠性**: 消息持久化和重试机制
- **性能优化**: 异步处理和连接池

### 依赖关系
```
MessageDispatcher
├── BIRRouter
├── ACPClient
└── ACPServer
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
from src.communication.dispatcher import BIRRouter
from src.communication.acp import ACPClient

# 创建路由器
router = BIRRouter()

# 注册Agent
router.register_agent("agent1", "http://localhost:8001")
router.register_agent("agent2", "http://localhost:8002")

# 路由消息
result = router.route_message(message)

# 创建ACP客户端
client = ACPClient()
client.connect("http://localhost:8000")

# 发送请求
response = client.send_request(request)
```

## 测试

```bash
# 运行单元测试
pytest tests/unit/communication/

# 运行集成测试
pytest tests/integration/communication/

# 生成测试覆盖率报告
pytest --cov=src/communication tests/unit/communication/
```

## 部署

通信域模块需要配置网络和消息队列：

```yaml
# docker-compose.yml
services:
  communication:
    build: .
    ports:
      - "8000:8000"
    environment:
      - RABBITMQ_URL=amqp://localhost:5672
      - REDIS_URL=redis://localhost:6379
    volumes:
      - ./config:/app/config
```

## 监控

- **性能指标**: 消息延迟、吞吐量、错误率
- **资源使用**: CPU、内存、网络
- **业务指标**: 消息传递成功率、路由准确率

## 版本历史

- **v1.0.0**: 初始版本，基础功能实现
- **v1.1.0**: 添加负载均衡功能
- **v1.2.0**: 优化消息持久化机制 