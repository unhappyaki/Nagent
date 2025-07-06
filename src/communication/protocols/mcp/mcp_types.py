"""
MCP协议类型定义

定义MCP协议相关的数据类型和枚举
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class Transport(Enum):
    """传输协议类型"""
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


class ConnectionStatus(Enum):
    """连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    AUTHENTICATING = "authenticating"


class MessageType(Enum):
    """消息类型"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class MCPErrorCode(Enum):
    """MCP错误码"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR = -32000


@dataclass
class MCPError:
    """MCP错误"""
    code: int
    message: str
    data: Optional[Any] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPError':
        """从字典创建MCPError"""
        return cls(
            code=data.get("code", MCPErrorCode.INTERNAL_ERROR.value),
            message=data.get("message", "Unknown error"),
            data=data.get("data")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "code": self.code,
            "message": self.message
        }
        if self.data is not None:
            result["data"] = self.data
        return result


@dataclass
class MCPMessage:
    """MCP消息"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[MCPError] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """从字典创建MCPMessage"""
        error_data = data.get("error")
        error = MCPError.from_dict(error_data) if error_data else None
        
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=error
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {"jsonrpc": self.jsonrpc}
        
        if self.id is not None:
            result["id"] = self.id
        if self.method is not None:
            result["method"] = self.method
        if self.params is not None:
            result["params"] = self.params
        if self.result is not None:
            result["result"] = self.result
        if self.error is not None:
            result["error"] = self.error.to_dict()
            
        return result
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPMessage':
        """从JSON字符串创建"""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except Exception as e:
            logger.warning("Failed to parse MCP message", error=str(e))
            raise ValueError(f"Invalid MCP message JSON: {e}")


@dataclass
class MCPTool:
    """MCP工具定义"""
    name: str
    description: Optional[str] = None
    inputSchema: Optional[Dict[str, Any]] = None
    capabilities: List[str] = field(default_factory=list)
    timeout: int = 30
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPTool':
        """从字典创建MCPTool"""
        return cls(
            name=data["name"],
            description=data.get("description"),
            inputSchema=data.get("inputSchema"),
            capabilities=data.get("capabilities", []),
            timeout=data.get("timeout", 30)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {"name": self.name}
        
        if self.description is not None:
            result["description"] = self.description
        if self.inputSchema is not None:
            result["inputSchema"] = self.inputSchema
        if self.capabilities:
            result["capabilities"] = self.capabilities
        if self.timeout != 30:
            result["timeout"] = self.timeout
            
        return result


@dataclass 
class MCPResource:
    """MCP资源定义"""
    uri: str
    name: Optional[str] = None
    description: Optional[str] = None
    mimeType: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPResource':
        """从字典创建MCPResource"""
        return cls(
            uri=data["uri"],
            name=data.get("name"),
            description=data.get("description"),
            mimeType=data.get("mimeType")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {"uri": self.uri}
        
        if self.name is not None:
            result["name"] = self.name
        if self.description is not None:
            result["description"] = self.description
        if self.mimeType is not None:
            result["mimeType"] = self.mimeType
            
        return result


@dataclass
class MCPResourceContent:
    """MCP资源内容"""
    uri: str
    mimeType: Optional[str] = None
    text: Optional[str] = None
    blob: Optional[bytes] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPResourceContent':
        """从字典创建MCPResourceContent"""
        return cls(
            uri=data["uri"],
            mimeType=data.get("mimeType"),
            text=data.get("text"),
            blob=data.get("blob")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {"uri": self.uri}
        
        if self.mimeType is not None:
            result["mimeType"] = self.mimeType
        if self.text is not None:
            result["text"] = self.text
        if self.blob is not None:
            result["blob"] = self.blob
            
        return result


@dataclass
class MCPResult:
    """MCP执行结果"""
    content: Any = None
    isError: bool = False
    error: Optional[str] = None
    
    @classmethod
    def success(cls, content: Any) -> 'MCPResult':
        """创建成功结果"""
        return cls(content=content, isError=False)
    
    @classmethod
    def error(cls, error_message: str) -> 'MCPResult':
        """创建错误结果"""
        return cls(isError=True, error=error_message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        if self.isError:
            return {
                "isError": True,
                "error": self.error
            }
        else:
            return {
                "isError": False,
                "content": self.content
            }


@dataclass
class TransportConfig:
    """传输配置基类"""
    type: Transport
    timeout: int = 30
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransportConfig':
        """从字典创建传输配置"""
        transport_type = Transport(data["type"])
        
        if transport_type == Transport.STDIO:
            return StdioTransportConfig.from_dict(data)
        elif transport_type == Transport.HTTP:
            return HttpTransportConfig.from_dict(data)
        elif transport_type == Transport.WEBSOCKET:
            return WebSocketTransportConfig.from_dict(data)
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")


@dataclass
class StdioTransportConfig(TransportConfig):
    """Stdio传输配置"""
    command: List[str] = field(default_factory=list)
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    
    def __init__(self, command=None, args=None, env=None, timeout=30):
        self.type = Transport.STDIO
        self.command = command or []
        self.args = args or []
        self.env = env or {}
        self.timeout = timeout
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StdioTransportConfig':
        """从字典创建Stdio传输配置"""
        return cls(
            command=data.get("command", []),
            args=data.get("args", []),
            env=data.get("env", {}),
            timeout=data.get("timeout", 30)
        )


@dataclass
class HttpTransportConfig(TransportConfig):
    """HTTP传输配置"""
    url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    
    def __init__(self, url="", headers=None, timeout=30):
        self.type = Transport.HTTP
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HttpTransportConfig':
        """从字典创建HTTP传输配置"""
        return cls(
            url=data.get("url", ""),
            headers=data.get("headers", {}),
            timeout=data.get("timeout", 30)
        )


@dataclass
class WebSocketTransportConfig(TransportConfig):
    """WebSocket传输配置"""
    url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    
    def __init__(self, url="", headers=None, timeout=30):
        self.type = Transport.WEBSOCKET
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebSocketTransportConfig':
        """从字典创建WebSocket传输配置"""
        return cls(
            url=data.get("url", ""),
            headers=data.get("headers", {}),
            timeout=data.get("timeout", 30)
        )


@dataclass
class MCPServerConfig:
    """MCP服务器配置"""
    name: str
    description: str = ""
    transport: TransportConfig = None
    capabilities: List[str] = field(default_factory=list)
    enabled: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPServerConfig':
        """从字典创建服务器配置"""
        transport_data = data.get("transport", {})
        transport = TransportConfig.from_dict(transport_data) if transport_data else None
        
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            transport=transport,
            capabilities=data.get("capabilities", []),
            enabled=data.get("enabled", True)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "enabled": self.enabled
        }
        
        if self.transport is not None:
            if isinstance(self.transport, StdioTransportConfig):
                result["transport"] = {
                    "type": "stdio",
                    "command": self.transport.command,
                    "args": self.transport.args,
                    "env": self.transport.env,
                    "timeout": self.transport.timeout
                }
            elif isinstance(self.transport, HttpTransportConfig):
                result["transport"] = {
                    "type": "http",
                    "url": self.transport.url,
                    "headers": self.transport.headers,
                    "timeout": self.transport.timeout
                }
            elif isinstance(self.transport, WebSocketTransportConfig):
                result["transport"] = {
                    "type": "websocket",
                    "url": self.transport.url,
                    "headers": self.transport.headers,
                    "timeout": self.transport.timeout
                }
        
        return result


@dataclass
class MCPClientConfig:
    """MCP客户端配置"""
    default_timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 1
    connection_pool_size: int = 20
    keep_alive: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPClientConfig':
        """从字典创建客户端配置"""
        return cls(
            default_timeout=data.get("default_timeout", 30),
            max_retries=data.get("max_retries", 3),
            retry_delay=data.get("retry_delay", 1),
            connection_pool_size=data.get("connection_pool_size", 20),
            keep_alive=data.get("keep_alive", True)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "default_timeout": self.default_timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "connection_pool_size": self.connection_pool_size,
            "keep_alive": self.keep_alive
        } 