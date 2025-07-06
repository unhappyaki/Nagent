"""
ACP协议模块
Agent Communication Protocol - 智能体通信协议

本模块提供完整的ACP协议实现，包括：
- 客户端和服务器端通信
- 消息格式定义和构建
- 任务分发和调度
- Agent注册管理
- 控制适配器系统
- 工具辅助函数

基于企业级架构设计，支持：
- 三段式载荷结构（Meta、Context、Command）
- 双栈通信架构（Client-Server-Adapter）
- 完整的生命周期管理
- 全链路追踪和监控
"""

# 核心通信组件
from .acp_client import ACPClient, ACPClientManager
from .acp_server import ACPServer, ACPGateway, ACPRouter, AgentContainer
from .control_adapter import (
    ControlAdapter, ControlDispatcher, 
    APIControlAdapter, ToolControlAdapter, ModelControlAdapter,
    ControlResult, ActionType
)

# 消息格式和构建
from .message_schema import (
    ACPMessage, ACPPayload, MessageMeta, MessageContext,
    ACPMessageType, ACPCommandType, ACPActionType, MessagePriority,
    ACPMessageBuilder
)

# 任务分发
from .dispatcher import (
    TaskDispatcher, TaskInfo, AgentInfo,
    TaskStatus, DispatchStrategy
)

# Agent注册管理
from src.infrastructure.registry.agent_registry import (
    ACPAgentRegistry, AgentRegistration, AgentStatus
)

# Flask Web服务
from .app import ACPFlaskApp, create_app

# 工具辅助
from .utils import (
    TimeUtils, IDGenerator, HashUtils, ConfigUtils,
    LogUtils, ValidationUtils,
    get_current_timestamp, generate_id, log_info
)

# 版本信息
__version__ = "1.0.0"
__author__ = "Nagent Team"
__description__ = "Agent Communication Protocol Implementation"

# 导出的主要类
__all__ = [
    # 核心通信
    "ACPClient",
    "ACPClientManager", 
    "ACPServer",
    "ACPGateway",
    "ACPRouter",
    "AgentContainer",
    
    # 控制适配器
    "ControlAdapter",
    "ControlDispatcher",
    "APIControlAdapter",
    "ToolControlAdapter", 
    "ModelControlAdapter",
    "ControlResult",
    "ActionType",
    
    # 消息格式
    "ACPMessage",
    "ACPPayload",
    "MessageMeta",
    "MessageContext",
    "ACPMessageType",
    "ACPCommandType", 
    "ACPActionType",
    "MessagePriority",
    "ACPMessageBuilder",
    
    # 任务分发
    "TaskDispatcher",
    "TaskInfo",
    "AgentInfo",
    "TaskStatus",
    "DispatchStrategy",
    
    # Agent注册
    "ACPAgentRegistry",
    "AgentRegistration", 
    "AgentStatus",
    
    # Web服务
    "ACPFlaskApp",
    "create_app",
    
    # 工具类
    "TimeUtils",
    "IDGenerator",
    "HashUtils", 
    "ConfigUtils",
    "LogUtils",
    "ValidationUtils",
    "get_current_timestamp",
    "generate_id",
    "log_info",
]


def get_acp_info():
    """获取ACP协议信息"""
    return {
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "components": {
            "client": "ACP客户端 - 支持异步WebSocket通信",
            "server": "ACP服务器 - 三层架构(Gateway-Router-Container)",
            "message": "消息格式 - 三段式载荷结构",
            "dispatcher": "任务分发器 - 智能任务调度",
            "registry": "Agent注册中心 - 生命周期管理",
            "adapter": "控制适配器 - 多种执行模式",
            "app": "Flask Web服务 - HTTP管理接口",
            "utils": "工具辅助 - 时间、ID、验证等"
        },
        "features": [
            "三段式载荷结构（Meta-Context-Command）",
            "双栈通信架构（Client-Server-Adapter）", 
            "任务智能分发和调度",
            "Agent生命周期管理",
            "全链路追踪和监控",
            "多策略负载均衡",
            "心跳检测和健康监控",
            "HTTP管理接口",
            "企业级架构设计"
        ]
    }


# 便捷创建函数
def create_acp_client(server_url: str, agent_id: str = None, **kwargs) -> ACPClient:
    """
    创建ACP客户端
    
    Args:
        server_url: 服务器URL
        agent_id: Agent ID
        **kwargs: 其他参数
        
    Returns:
        ACPClient: 客户端实例
    """
    return ACPClient(
        server_url=server_url,
        agent_id=agent_id or generate_id(),
        **kwargs
    )


def create_acp_server(host: str = "localhost", port: int = 8000, **kwargs) -> ACPServer:
    """
    创建ACP服务器
    
    Args:
        host: 主机地址
        port: 端口号
        **kwargs: 其他参数
        
    Returns:
        ACPServer: 服务器实例
    """
    return ACPServer(host=host, port=port, **kwargs)


def create_task_dispatcher(strategy: str = "capability_match", **kwargs) -> TaskDispatcher:
    """
    创建任务分发器
    
    Args:
        strategy: 分发策略
        **kwargs: 其他参数
        
    Returns:
        TaskDispatcher: 分发器实例
    """
    return TaskDispatcher(
        strategy=DispatchStrategy(strategy),
        **kwargs
    )


def create_agent_registry(**kwargs) -> ACPAgentRegistry:
    """
    创建Agent注册中心
    
    Args:
        **kwargs: 其他参数
        
    Returns:
        ACPAgentRegistry: 注册中心实例
    """
    return ACPAgentRegistry(**kwargs) 