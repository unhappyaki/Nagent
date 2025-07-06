"""
MCP适配器集成演示

展示如何使用MCP适配器与现有Nagent架构进行集成
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from src.communication.protocols.mcp.adapters import (
    MCPAdapter,
    MCPToolWrapper,
    ExternalToolRegistry,
    MCPMonitoringIntegration,
    MCPExecutorIntegration
)
from src.communication.protocols.mcp import (
    MCPConnectionManager,
    MCPServerConfig,
    Transport,
    StdioTransportConfig
)
from src.core.tools.tool_registry import ToolRegistry
# 注释掉可能缺失依赖的模块
# from src.monitoring.log.log_manager import LogManager
# from src.monitoring.metrics.metrics_collector import MetricsCollector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPIntegrationDemo:
    """MCP集成演示"""
    
    def __init__(self):
        """初始化演示"""
        self.tool_registry = None
        self.mcp_adapter = None
        self.monitoring_integration = None
        self.executor_integration = None
        self.connection_manager = None
        
    async def setup(self):
        """设置演示环境"""
        logger.info("Setting up MCP integration demo...")
        
        # 1. 创建现有工具注册表
        self.tool_registry = ToolRegistry()
        await self.tool_registry.initialize()
        
        # 2. 创建MCP连接管理器
        self.connection_manager = MCPConnectionManager()
        
        # 3. 创建MCP适配器
        self.mcp_adapter = MCPAdapter(
            tool_registry=self.tool_registry,
            connection_manager=self.connection_manager
        )
        
        # 4. 创建监控集成（模拟监控组件）
        self.monitoring_integration = MCPMonitoringIntegration(
            mcp_adapter=self.mcp_adapter,
            external_registry=self.mcp_adapter.external_registry,
            metrics_collector=None,  # 这里可以传入真实的MetricsCollector
            log_manager=None,        # 这里可以传入真实的LogManager
            alert_manager=None       # 这里可以传入真实的AlertManager
        )
        
        # 5. 创建执行器集成
        self.executor_integration = MCPExecutorIntegration(
            mcp_adapter=self.mcp_adapter,
            monitoring_integration=self.monitoring_integration
        )
        
        logger.info("MCP integration demo setup completed")
    
    async def demo_add_mcp_server(self):
        """演示添加MCP服务器"""
        logger.info("=== Demo: Adding MCP Server ===")
        
        # 配置一个示例MCP服务器（这里使用文件系统工具服务器作为示例）
        transport_config = StdioTransportConfig(
            command=["python", "-m", "mcp_filesystem_server"],  # 示例命令
            args=[],
            env={}
        )
        
        server_config = MCPServerConfig(
            name="filesystem_server",
            description="File system MCP server",
            transport=transport_config,
            capabilities=["tools"],
            enabled=True
        )
        
        # 添加服务器
        success = await self.mcp_adapter.add_mcp_server(server_config)
        
        if success:
            logger.info(f"Successfully added MCP server: {server_config.name}")
        else:
            logger.error(f"Failed to add MCP server: {server_config.name}")
            return False
        
        return True
    
    async def demo_list_mcp_tools(self):
        """演示列出MCP工具"""
        logger.info("=== Demo: Listing MCP Tools ===")
        
        # 列出所有MCP工具
        tools = await self.mcp_adapter.list_mcp_tools()
        
        logger.info(f"Found {len(tools)} MCP tools:")
        for tool in tools:
            logger.info(f"- {tool['name']} ({tool['server_name']}): {tool['description']}")
        
        return tools
    
    async def demo_execute_mcp_tool(self, tools):
        """演示执行MCP工具"""
        if not tools:
            logger.warning("No MCP tools available for execution demo")
            return
        
        logger.info("=== Demo: Executing MCP Tool ===")
        
        # 选择第一个工具进行演示
        tool = tools[0]
        tool_name = tool['name']
        
        # 准备示例参数（这里需要根据具体工具调整）
        arguments = {
            "path": "/tmp",  # 示例参数
        }
        
        logger.info(f"Executing tool: {tool_name}")
        
        try:
            # 通过执行器集成执行工具
            result = await self.executor_integration.execute_mcp_tool(
                tool_name=tool_name,
                arguments=arguments,
                timeout=10.0,
                user_context={"demo": True, "user": "demo_user"}
            )
            
            if result.success:
                logger.info(f"Tool execution successful: {result.result}")
            else:
                logger.error(f"Tool execution failed: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool: {e}")
            return None
    
    async def demo_batch_execution(self, tools):
        """演示批量执行"""
        if len(tools) < 2:
            logger.warning("Need at least 2 tools for batch execution demo")
            return
        
        logger.info("=== Demo: Batch Execution ===")
        
        # 准备批量请求
        batch_requests = []
        for i, tool in enumerate(tools[:3]):  # 最多执行3个工具
            batch_requests.append({
                "tool_name": tool['name'],
                "arguments": {"demo_param": f"value_{i}"},
                "timeout": 5.0,
                "user_context": {"batch_id": i}
            })
        
        logger.info(f"Executing {len(batch_requests)} tools in batch")
        
        try:
            results = await self.executor_integration.execute_mcp_tools_batch(
                tool_requests=batch_requests,
                max_concurrent=2,
                timeout=30.0
            )
            
            logger.info("Batch execution completed:")
            for i, result in enumerate(results):
                status = "SUCCESS" if result.success else "FAILED"
                logger.info(f"  Tool {i+1}: {status} - {result.tool_name}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch execution: {e}")
            return None
    
    async def demo_monitoring_stats(self):
        """演示监控统计"""
        logger.info("=== Demo: Monitoring Statistics ===")
        
        # 获取适配器统计
        adapter_stats = self.mcp_adapter.get_stats()
        logger.info("MCP Adapter Stats:")
        for key, value in adapter_stats.items():
            logger.info(f"  {key}: {value}")
        
        # 获取监控统计
        monitoring_stats = self.monitoring_integration.get_monitoring_stats()
        logger.info("Monitoring Integration Stats:")
        for key, value in monitoring_stats.items():
            logger.info(f"  {key}: {value}")
        
        # 获取执行统计
        execution_stats = await self.executor_integration.get_integration_stats()
        logger.info("Executor Integration Stats:")
        for key, value in execution_stats.items():
            logger.info(f"  {key}: {value}")
        
        # 获取执行历史
        execution_history = await self.executor_integration.get_execution_history(limit=5)
        logger.info(f"Recent {len(execution_history)} executions:")
        for i, execution in enumerate(execution_history):
            status = "SUCCESS" if execution['success'] else "FAILED"
            logger.info(f"  {i+1}. {execution['tool_name']}: {status} ({execution['duration']:.2f}s)")
    
    async def demo_external_tool_registry(self):
        """演示外部工具注册表功能"""
        logger.info("=== Demo: External Tool Registry ===")
        
        registry = self.mcp_adapter.external_registry
        
        # 获取所有工具
        all_tools = registry.list_tools()
        logger.info(f"Total tools in registry: {len(all_tools)}")
        
        # 按分类列出工具
        from src.communication.protocols.mcp.adapters.external_tool_registry import ToolCategory
        
        for category in ToolCategory:
            category_tools = registry.get_tools_by_category(category)
            if category_tools:
                logger.info(f"{category.value.title()} tools: {len(category_tools)}")
                for tool in category_tools[:3]:  # 只显示前3个
                    logger.info(f"  - {tool.name} ({tool.server_name})")
        
        # 搜索工具
        search_results = registry.list_tools(pattern="file")
        logger.info(f"Tools matching 'file': {len(search_results)}")
        
        # 获取注册表统计
        registry_stats = registry.get_stats()
        logger.info("Registry Statistics:")
        for key, value in registry_stats.items():
            logger.info(f"  {key}: {value}")
    
    async def demo_health_check(self):
        """演示健康检查"""
        logger.info("=== Demo: Health Check ===")
        
        # MCP适配器健康检查
        adapter_health = await self.mcp_adapter.health_check()
        logger.info("MCP Adapter Health:")
        for key, value in adapter_health.items():
            logger.info(f"  {key}: {value}")
        
        # 执行器集成健康检查
        executor_health = await self.executor_integration.health_check()
        logger.info("Executor Integration Health:")
        for key, value in executor_health.items():
            logger.info(f"  {key}: {value}")
    
    async def demo_callbacks(self):
        """演示回调功能"""
        logger.info("=== Demo: Callbacks ===")
        
        # 定义回调函数
        async def pre_execution_callback(execution_info):
            logger.info(f"PRE-EXECUTION: {execution_info['tool_name']} starting...")
        
        async def post_execution_callback(execution_info, result):
            status = "SUCCESS" if result.success else "FAILED"
            logger.info(f"POST-EXECUTION: {result.tool_name} completed with {status}")
        
        async def error_callback(execution_info, error):
            logger.info(f"ERROR: {execution_info['tool_name']} failed with {error}")
        
        async def monitoring_callback(event_type, event):
            logger.info(f"MONITORING: {event_type} event for {event.tool_name}")
        
        # 注册回调
        self.executor_integration.add_pre_execution_callback(pre_execution_callback)
        self.executor_integration.add_post_execution_callback(post_execution_callback)
        self.executor_integration.add_error_callback(error_callback)
        self.monitoring_integration.add_execution_callback(monitoring_callback)
        
        logger.info("Callbacks registered successfully")
    
    async def demo_error_handling(self):
        """演示错误处理"""
        logger.info("=== Demo: Error Handling ===")
        
        # 尝试执行一个不存在的工具
        result = await self.executor_integration.execute_mcp_tool(
            tool_name="non_existent_tool",
            arguments={},
            timeout=5.0
        )
        
        logger.info(f"Non-existent tool result: success={result.success}, error='{result.error}'")
        
        # 尝试添加一个无效的服务器
        invalid_transport_config = StdioTransportConfig(
            command=["non_existent_command"],
            args=[],
            env={}
        )
        
        invalid_server_config = MCPServerConfig(
            name="invalid_server",
            description="Invalid test server",
            transport=invalid_transport_config,
            capabilities=["tools"],
            enabled=True
        )
        
        success = await self.mcp_adapter.add_mcp_server(invalid_server_config)
        logger.info(f"Invalid server addition result: {success}")
    
    async def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up demo resources...")
        
        try:
            # 停止监控集成
            if self.monitoring_integration:
                await self.monitoring_integration.stop()
            
            # 停止MCP适配器
            if self.mcp_adapter:
                await self.mcp_adapter.stop()
            
            logger.info("Demo cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def run_full_demo(self):
        """运行完整演示"""
        try:
            await self.setup()
            
            # 启动MCP适配器和监控
            await self.mcp_adapter.start()
            await self.monitoring_integration.start()
            
            # 注册回调
            await self.demo_callbacks()
            
            # 注意：以下演示需要真实的MCP服务器才能正常工作
            # 在实际环境中，您需要：
            # 1. 安装并配置MCP服务器（如文件系统服务器）
            # 2. 更新服务器配置以匹配您的环境
            
            logger.info("=== MCP Integration Demo Starting ===")
            
            # 1. 添加MCP服务器（注释掉，因为需要真实服务器）
            # server_added = await self.demo_add_mcp_server()
            # if not server_added:
            #     logger.warning("Skipping tool demos due to server setup failure")
            #     return
            
            # 模拟一些工具（用于演示其他功能）
            mock_tools = [
                {
                    'name': 'mcp_filesystem_server_read_file',
                    'server_name': 'filesystem_server',
                    'description': 'Read a file from filesystem'
                },
                {
                    'name': 'mcp_filesystem_server_list_directory',
                    'server_name': 'filesystem_server', 
                    'description': 'List directory contents'
                }
            ]
            
            # 2. 列出工具
            # tools = await self.demo_list_mcp_tools()
            tools = mock_tools  # 使用模拟工具
            
            # 3. 执行单个工具（注释掉，需要真实服务器）
            # await self.demo_execute_mcp_tool(tools)
            
            # 4. 批量执行（注释掉，需要真实服务器）
            # await self.demo_batch_execution(tools)
            
            # 5. 外部工具注册表演示
            await self.demo_external_tool_registry()
            
            # 6. 监控统计
            await self.demo_monitoring_stats()
            
            # 7. 健康检查
            await self.demo_health_check()
            
            # 8. 错误处理演示
            await self.demo_error_handling()
            
            logger.info("=== MCP Integration Demo Completed ===")
            
        except Exception as e:
            logger.error(f"Demo failed: {e}")
            raise
        finally:
            await self.cleanup()


async def main():
    """主函数"""
    demo = MCPIntegrationDemo()
    
    try:
        await demo.run_full_demo()
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main()) 