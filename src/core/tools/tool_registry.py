# 本地工具注册表，仅服务于Agent内部/推理链路
# 避免与 infrastructure/registry/tool_registry.py 的全局ToolRegistry混淆

import asyncio
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class ToolPermission(Enum):
    """工具权限枚举"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class ToolStatus(Enum):
    """工具状态枚举"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    LOADING = "loading"


class LocalToolRegistry:
    """
    工具注册表
    
    管理所有可用的工具
    """
    
    def __init__(self):
        """初始化工具注册表"""
        self.tools = {}
        self.tool_metadata = {}
        self.tool_permissions = {}
        self.tool_status = {}
        self.tool_stats = {}
        
        # 注册默认工具
        self._register_default_tools()
        
        logger.info("Tool registry initialized")
    
    def register_tool(
        self, 
        name: str, 
        tool_func: Callable, 
        description: str = "", 
        metadata: Dict[str, Any] = None,
        permissions: List[ToolPermission] = None,
        timeout: int = 30
    ):
        """
        注册工具
        
        Args:
            name: 工具名称
            tool_func: 工具函数
            description: 工具描述
            metadata: 工具元数据
            permissions: 工具权限
            timeout: 超时时间
        """
        self.tools[name] = tool_func
        self.tool_metadata[name] = {
            "description": description,
            "metadata": metadata or {},
            "timeout": timeout,
            "registered_at": asyncio.get_event_loop().time()
        }
        self.tool_permissions[name] = permissions or [ToolPermission.EXECUTE]
        self.tool_status[name] = ToolStatus.AVAILABLE
        self.tool_stats[name] = {
            "calls": 0,
            "success": 0,
            "errors": 0,
            "total_time": 0.0
        }
        
        logger.info("Tool registered", name=name, description=description)
    
    def unregister_tool(self, name: str):
        """
        注销工具
        
        Args:
            name: 工具名称
        """
        if name in self.tools:
            del self.tools[name]
        if name in self.tool_metadata:
            del self.tool_metadata[name]
        if name in self.tool_permissions:
            del self.tool_permissions[name]
        if name in self.tool_status:
            del self.tool_status[name]
        if name in self.tool_stats:
            del self.tool_stats[name]
        
        logger.info("Tool unregistered", name=name)
    
    def get_tool(self, name: str):
        """
        获取工具
        
        Args:
            name: 工具名称
            
        Returns:
            工具函数
        """
        return self.tools.get(name)
    
    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取工具信息
        
        Args:
            name: 工具名称
            
        Returns:
            工具信息
        """
        if name not in self.tools:
            return None
        
        metadata = self.tool_metadata.get(name, {})
        permissions = self.tool_permissions.get(name, [])
        status = self.tool_status.get(name, ToolStatus.UNAVAILABLE)
        stats = self.tool_stats.get(name, {})
        
        return {
            "name": name,
            "description": metadata.get("description", ""),
            "metadata": metadata.get("metadata", {}),
            "permissions": [p.value for p in permissions],
            "status": status.value,
            "stats": stats,
            "timeout": metadata.get("timeout", 30)
        }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用工具列表
        
        Returns:
            工具列表
        """
        tools = []
        for name in self.tools:
            tool_info = self.get_tool_info(name)
            if tool_info:
                tools.append(tool_info)
        return tools
    
    def discover_tools(self, pattern: str = None) -> List[Dict[str, Any]]:
        """
        发现工具
        
        Args:
            pattern: 搜索模式
            
        Returns:
            匹配的工具列表
        """
        tools = self.get_available_tools()
        
        if pattern:
            # 简单的模式匹配
            filtered_tools = []
            for tool in tools:
                if (pattern.lower() in tool["name"].lower() or 
                    pattern.lower() in tool["description"].lower()):
                    filtered_tools.append(tool)
            return filtered_tools
        
        return tools
    
    def check_permission(self, name: str, permission: ToolPermission) -> bool:
        """
        检查工具权限
        
        Args:
            name: 工具名称
            permission: 权限类型
            
        Returns:
            是否有权限
        """
        if name not in self.tool_permissions:
            return False
        
        permissions = self.tool_permissions[name]
        return permission in permissions
    
    async def execute_tool(self, name: str, params: Dict[str, Any], **kwargs) -> Any:
        """
        执行工具
        
        Args:
            name: 工具名称
            params: 工具参数
            **kwargs: 额外参数
            
        Returns:
            执行结果
        """
        if name not in self.tools:
            raise ValueError(f"Tool not found: {name}")
        
        # 检查权限
        if not self.check_permission(name, ToolPermission.EXECUTE):
            raise PermissionError(f"No permission to execute tool: {name}")
        
        # 检查状态
        if self.tool_status[name] != ToolStatus.AVAILABLE:
            raise RuntimeError(f"Tool {name} is not available: {self.tool_status[name].value}")
        
        tool_func = self.tools[name]
        metadata = self.tool_metadata[name]
        timeout = metadata.get("timeout", 30)
        
        # 更新统计
        self.tool_stats[name]["calls"] += 1
        start_time = asyncio.get_event_loop().time()
        
        try:
            # 执行工具
            if hasattr(tool_func, '__call__'):
                if hasattr(tool_func, '__await__'):
                    # 异步工具
                    result = await asyncio.wait_for(
                        tool_func(**params, **kwargs),
                        timeout=timeout
                    )
                else:
                    # 同步工具
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: tool_func(**params, **kwargs)
                    )
            else:
                raise ValueError(f"Invalid tool function: {name}")
            
            # 更新成功统计
            self.tool_stats[name]["success"] += 1
            execution_time = asyncio.get_event_loop().time() - start_time
            self.tool_stats[name]["total_time"] += execution_time
            
            logger.debug(
                "Tool executed successfully", 
                name=name, 
                params=params,
                execution_time=execution_time
            )
            return result
            
        except Exception as e:
            # 更新错误统计
            self.tool_stats[name]["errors"] += 1
            
            logger.error("Tool execution failed", name=name, error=str(e))
            raise
    
    async def initialize(self) -> None:
        """初始化工具注册表"""
        try:
            logger.info("Initializing tool registry")
            
            # 检查所有工具的状态
            for name in self.tools:
                await self._check_tool_health(name)
            
            logger.info("Tool registry initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize tool registry", error=str(e))
            raise
    
    async def is_healthy(self) -> bool:
        """检查工具注册表健康状态"""
        try:
            # 检查是否有可用工具
            available_tools = [name for name, status in self.tool_status.items() 
                             if status == ToolStatus.AVAILABLE]
            
            if not available_tools:
                logger.warning("No available tools found")
                return False
            
            # 检查关键工具的健康状态
            critical_tools = ["web_search", "calculator", "http_request"]
            for tool_name in critical_tools:
                if tool_name in self.tools:
                    if self.tool_status[tool_name] != ToolStatus.AVAILABLE:
                        logger.warning(f"Critical tool {tool_name} is not available")
                        return False
            
            return True
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False
    
    async def _check_tool_health(self, name: str) -> None:
        """
        检查工具健康状态
        
        Args:
            name: 工具名称
        """
        try:
            self.tool_status[name] = ToolStatus.LOADING
            
            # 尝试执行一个简单的健康检查
            tool_func = self.tools[name]
            
            # 对于某些工具，可以执行简单的测试
            if name == "get_time":
                # 时间工具总是可用的
                self.tool_status[name] = ToolStatus.AVAILABLE
            elif name == "calculator":
                # 计算工具测试
                test_result = tool_func("1+1")
                if test_result == "计算结果: 2":
                    self.tool_status[name] = ToolStatus.AVAILABLE
                else:
                    self.tool_status[name] = ToolStatus.ERROR
            else:
                # 其他工具默认设为可用
                self.tool_status[name] = ToolStatus.AVAILABLE
            
            logger.debug(f"Tool health check completed", name=name, status=self.tool_status[name].value)
            
        except Exception as e:
            self.tool_status[name] = ToolStatus.ERROR
            logger.error(f"Tool health check failed", name=name, error=str(e))
    
    def get_tool_stats(self) -> Dict[str, Any]:
        """
        获取工具统计信息
        
        Returns:
            统计信息
        """
        total_calls = sum(stats["calls"] for stats in self.tool_stats.values())
        total_success = sum(stats["success"] for stats in self.tool_stats.values())
        total_errors = sum(stats["errors"] for stats in self.tool_stats.values())
        
        return {
            "total_tools": len(self.tools),
            "available_tools": len([s for s in self.tool_status.values() if s == ToolStatus.AVAILABLE]),
            "total_calls": total_calls,
            "success_rate": total_success / total_calls if total_calls > 0 else 0,
            "error_rate": total_errors / total_calls if total_calls > 0 else 0,
            "tool_stats": self.tool_stats
        }
    
    def _register_default_tools(self):
        """注册默认工具"""
        # 搜索工具
        self.register_tool(
            "web_search",
            self._web_search,
            "执行网络搜索"
        )
        
        # 计算工具
        self.register_tool(
            "calculator",
            self._calculator,
            "执行数学计算"
        )
        
        # 时间工具
        self.register_tool(
            "get_time",
            self._get_time,
            "获取当前时间"
        )
        
        # 天气工具
        self.register_tool(
            "get_weather",
            self._get_weather,
            "获取天气信息"
        )
        
        # 文件操作工具
        self.register_tool(
            "file_operations",
            self._file_operations,
            "执行文件操作"
        )
        
        # HTTP请求工具
        self.register_tool(
            "http_request",
            self._http_request,
            "执行HTTP请求"
        )
        
        logger.info("Default tools registered")
    
    def _web_search(self, query: str, **kwargs) -> str:
        """网络搜索工具"""
        # 模拟搜索功能
        return f"搜索结果: {query}"
    
    def _calculator(self, expression: str, **kwargs) -> str:
        """计算工具"""
        try:
            # 安全计算
            allowed_chars = set('0123456789+-*/(). ')
            if not all(c in allowed_chars for c in expression):
                return "错误: 表达式包含不允许的字符"
            
            result = eval(expression)
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"
    
    def _get_time(self, **kwargs) -> str:
        """获取时间工具"""
        from datetime import datetime
        return f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    def _get_weather(self, location: str = "auto", **kwargs) -> str:
        """获取天气工具"""
        # 模拟天气查询
        return f"天气信息: {location} 晴天 25°C"
    
    def _file_operations(self, operation: str, path: str, **kwargs) -> str:
        """文件操作工具"""
        # 模拟文件操作
        return f"文件操作: {operation} {path}"
    
    def _http_request(self, url: str, **kwargs) -> str:
        """HTTP请求工具"""
        # 模拟HTTP请求
        return f"HTTP请求: {url}" 