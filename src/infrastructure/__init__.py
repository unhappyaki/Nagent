"""
基础设施层模块
提供跨域的横切关注点支持，包括注册、网关、认证、配置、发现等核心能力
"""

from .registry import UnifiedModuleRegistry, ToolRegistry, AgentRegistry, MemoryRegistry, ReasonerRegistry
from .gateway import UnifiedAPIGateway
from .auth import UnifiedAuthManager
from .config import UnifiedConfigManager
from .discovery import ServiceDiscovery

__all__ = [
    # 注册中心
    "UnifiedModuleRegistry",
    "ToolRegistry", 
    "AgentRegistry",
    "MemoryRegistry",
    "ReasonerRegistry",
    
    # 网关
    "UnifiedAPIGateway",
    
    # 认证
    "UnifiedAuthManager",
    
    # 配置
    "UnifiedConfigManager",
    
    # 服务发现
    "ServiceDiscovery"
] 