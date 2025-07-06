"""
MCP工具包装器

将MCP工具包装为BaseTool接口，提供无缝集成
"""

import asyncio
import time
import json
from typing import Any, Dict, Optional
import structlog

from src.core.tools.base_tool import BaseTool
from ..mcp_types import MCPTool, MCPResult
from ..mcp_client import MCPClient

logger = structlog.get_logger(__name__)


class MCPToolWrapper(BaseTool):
    """MCP工具包装器，将MCPTool包装为BaseTool接口"""
    
    def __init__(
        self,
        mcp_tool: MCPTool,
        mcp_client: MCPClient,
        server_name: str
    ):
        """
        初始化MCP工具包装器
        
        Args:
            mcp_tool: MCP工具定义
            mcp_client: MCP客户端
            server_name: 服务器名称
        """
        super().__init__(
            name=mcp_tool.name,
            description=mcp_tool.description or f"MCP tool from {server_name}"
        )
        
        self.mcp_tool = mcp_tool
        self.mcp_client = mcp_client
        self.server_name = server_name
        
        # 执行统计
        self.stats = {
            "calls": 0,
            "success": 0,
            "errors": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
            "last_call": None,
            "last_error": None
        }
        
        # 缓存解析的输入模式
        self._parsed_input_schema = None
        self._parse_input_schema()
        
        logger.debug(
            "MCP tool wrapper created",
            tool_name=mcp_tool.name,
            server_name=server_name
        )
    
    def _parse_input_schema(self) -> None:
        """解析输入模式"""
        try:
            if self.mcp_tool.inputSchema:
                if isinstance(self.mcp_tool.inputSchema, dict):
                    self._parsed_input_schema = self.mcp_tool.inputSchema
                elif isinstance(self.mcp_tool.inputSchema, str):
                    self._parsed_input_schema = json.loads(self.mcp_tool.inputSchema)
                else:
                    logger.warning(
                        "Unsupported input schema type",
                        tool_name=self.name,
                        schema_type=type(self.mcp_tool.inputSchema)
                    )
        except Exception as e:
            logger.error(
                "Error parsing input schema",
                tool_name=self.name,
                error=str(e)
            )
    
    async def execute(self, **kwargs) -> Any:
        """
        执行MCP工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            执行结果
        """
        start_time = time.time()
        self.stats["calls"] += 1
        self.stats["last_call"] = start_time
        
        try:
            # 验证参数
            validated_args = await self._validate_arguments(kwargs)
            
            # 调用MCP工具
            logger.debug(
                "Executing MCP tool",
                tool_name=self.name,
                server_name=self.server_name,
                arguments_count=len(validated_args)
            )
            
            result = await self.mcp_client.call_tool(
                self.mcp_tool.name,
                validated_args
            )
            
            # 处理结果
            if result.isError:
                raise RuntimeError(f"MCP tool execution failed: {result.error}")
            
            # 更新统计
            execution_time = time.time() - start_time
            self.stats["success"] += 1
            self.stats["total_time"] += execution_time
            self.stats["avg_time"] = self.stats["total_time"] / self.stats["calls"]
            
            logger.debug(
                "MCP tool executed successfully",
                tool_name=self.name,
                server_name=self.server_name,
                execution_time=execution_time
            )
            
            return result.content
            
        except Exception as e:
            # 更新错误统计
            execution_time = time.time() - start_time
            self.stats["errors"] += 1
            self.stats["total_time"] += execution_time
            self.stats["avg_time"] = self.stats["total_time"] / self.stats["calls"]
            self.stats["last_error"] = str(e)
            
            logger.error(
                "Error executing MCP tool",
                tool_name=self.name,
                server_name=self.server_name,
                error=str(e),
                execution_time=execution_time
            )
            
            raise
    
    async def _validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证工具参数
        
        Args:
            arguments: 输入参数
            
        Returns:
            验证后的参数
        """
        if not self._parsed_input_schema:
            # 没有模式定义，直接返回
            return arguments
        
        try:
            # 基础验证：检查必需参数
            schema_properties = self._parsed_input_schema.get("properties", {})
            required_fields = self._parsed_input_schema.get("required", [])
            
            # 检查必需字段
            missing_fields = []
            for field in required_fields:
                if field not in arguments:
                    missing_fields.append(field)
            
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            # 类型转换和验证
            validated_args = {}
            for field_name, field_value in arguments.items():
                if field_name in schema_properties:
                    field_schema = schema_properties[field_name]
                    validated_args[field_name] = await self._validate_field(
                        field_name, field_value, field_schema
                    )
                else:
                    # 未定义的字段，直接保留
                    validated_args[field_name] = field_value
            
            return validated_args
            
        except Exception as e:
            logger.error(
                "Error validating arguments",
                tool_name=self.name,
                error=str(e)
            )
            # 验证失败时返回原始参数
            return arguments
    
    async def _validate_field(
        self,
        field_name: str,
        field_value: Any,
        field_schema: Dict[str, Any]
    ) -> Any:
        """
        验证单个字段
        
        Args:
            field_name: 字段名
            field_value: 字段值
            field_schema: 字段模式
            
        Returns:
            验证后的字段值
        """
        field_type = field_schema.get("type")
        
        if field_type == "string":
            return str(field_value)
        elif field_type == "integer":
            try:
                return int(field_value)
            except (ValueError, TypeError):
                raise ValueError(f"Field '{field_name}' must be an integer")
        elif field_type == "number":
            try:
                return float(field_value)
            except (ValueError, TypeError):
                raise ValueError(f"Field '{field_name}' must be a number")
        elif field_type == "boolean":
            if isinstance(field_value, bool):
                return field_value
            elif isinstance(field_value, str):
                return field_value.lower() in ("true", "1", "yes", "on")
            else:
                return bool(field_value)
        elif field_type == "array":
            if not isinstance(field_value, (list, tuple)):
                raise ValueError(f"Field '{field_name}' must be an array")
            return list(field_value)
        elif field_type == "object":
            if not isinstance(field_value, dict):
                raise ValueError(f"Field '{field_name}' must be an object")
            return field_value
        else:
            # 未知类型，直接返回
            return field_value
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取工具信息
        
        Returns:
            工具信息
        """
        info = super().get_info()
        
        # 添加MCP特有信息
        info.update({
            "source": "mcp",
            "server_name": self.server_name,
            "original_name": self.mcp_tool.name,
            "input_schema": self.mcp_tool.inputSchema,
            "mcp_tool_data": self.mcp_tool.to_dict(),
            "stats": self.stats
        })
        
        return info
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        获取执行统计信息
        
        Returns:
            统计信息
        """
        return self.stats.copy()
    
    def get_input_schema(self) -> Optional[Dict[str, Any]]:
        """
        获取输入模式
        
        Returns:
            输入模式
        """
        return self._parsed_input_schema
    
    def get_mcp_tool(self) -> MCPTool:
        """
        获取原始MCP工具定义
        
        Returns:
            MCP工具定义
        """
        return self.mcp_tool
    
    def is_healthy(self) -> bool:
        """
        检查工具是否健康
        
        Returns:
            健康状态
        """
        # 检查MCP客户端连接状态
        if not self.mcp_client.is_healthy():
            return False
        
        # 检查错误率
        if self.stats["calls"] > 0:
            error_rate = self.stats["errors"] / self.stats["calls"]
            # 如果错误率超过50%，认为不健康
            if error_rate > 0.5:
                return False
        
        return True
    
    async def test_connection(self) -> bool:
        """
        测试工具连接
        
        Returns:
            连接测试结果
        """
        try:
            # 尝试获取工具列表来测试连接
            tools = await self.mcp_client.list_tools()
            
            # 检查当前工具是否在列表中
            tool_exists = any(
                tool.name == self.mcp_tool.name 
                for tool in tools
            )
            
            if not tool_exists:
                logger.warning(
                    "MCP tool not found in server tools list",
                    tool_name=self.name,
                    server_name=self.server_name
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(
                "Error testing MCP tool connection",
                tool_name=self.name,
                server_name=self.server_name,
                error=str(e)
            )
            return False
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"MCPToolWrapper({self.name}@{self.server_name})"
    
    def __repr__(self) -> str:
        """调试表示"""
        return (
            f"MCPToolWrapper("
            f"name='{self.name}', "
            f"server='{self.server_name}', "
            f"calls={self.stats['calls']}, "
            f"success_rate={self.stats['success']/max(1, self.stats['calls']):.2%}"
            f")"
        ) 