"""
企业级Agent演示示例
展示如何使用完整的Nagent框架功能，包括BIR调度、ACP通信、推理引擎、执行器等
"""

import asyncio
import logging
import time
from typing import Dict, Any

# 导入框架核心模块
from src.communication.dispatcher.bir_router import BIRRouter, BehaviorDispatcher
from src.communication.acp.acp_client import ACPClient, ACPClientManager
from src.core.reasoning.reasoning_engine import ReasoningEngine
from src.core.reasoning.llm_reasoner import LLMReasoner
from src.core.tools.tool_registry import ToolRegistry
from src.core.tools.base_tool import BaseTool
from src.state.context.session import Session, SessionManager
from src.state.memory.memory import MemoryEngine
from src.execution.executor import Executor, ExecutionManager
from src.monitoring.tracing.trace_writer import TraceWriter
from src.config.config_manager import ConfigManager


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SearchTool(BaseTool):
    """搜索工具示例"""
    
    def __init__(self):
        super().__init__("search_tool", "搜索信息工具")
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行搜索"""
        query = parameters.get("query", "")
        logger.info(f"Searching for: {query}")
        
        # 模拟搜索结果
        return {
            "success": True,
            "results": [
                {"title": f"搜索结果1: {query}", "content": f"这是关于{query}的内容1"},
                {"title": f"搜索结果2: {query}", "content": f"这是关于{query}的内容2"}
            ],
            "count": 2
        }


class ReportGeneratorTool(BaseTool):
    """报告生成工具示例"""
    
    def __init__(self):
        super().__init__("report_generator", "报告生成工具")
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """生成报告"""
        topic = parameters.get("topic", "")
        data = parameters.get("data", [])
        
        logger.info(f"Generating report for: {topic}")
        
        # 模拟报告生成
        report_content = f"# {topic}报告\n\n"
        for i, item in enumerate(data, 1):
            report_content += f"## 第{i}部分\n{item.get('content', '')}\n\n"
        
        return {
            "success": True,
            "report": report_content,
            "word_count": len(report_content)
        }


class EnterpriseAgentDemo:
    """企业级Agent演示类"""
    
    def __init__(self):
        """初始化演示环境"""
        self.setup_components()
        self.setup_agents()
    
    def setup_components(self):
        """设置核心组件"""
        logger.info("Setting up core components...")
        
        # 1. 配置管理器
        self.config_manager = ConfigManager()
        
        # 2. 追踪写入器
        self.trace_writer = TraceWriter()
        
        # 3. 内存引擎
        self.memory_engine = MemoryEngine()
        
        # 4. 会话管理器
        self.session_manager = SessionManager()
        
        # 5. 工具注册表
        self.tool_registry = ToolRegistry()
        self.tool_registry.register_tool(SearchTool())
        self.tool_registry.register_tool(ReportGeneratorTool())
        
        # 6. 推理引擎
        self.reasoning_engine = ReasoningEngine()
        llm_reasoner = LLMReasoner()
        self.reasoning_engine.register_reasoner("llm", llm_reasoner)
        
        # 7. 执行器
        self.executor = Executor(
            reasoning_engine=self.reasoning_engine,
            tool_registry=self.tool_registry,
            memory_engine=self.memory_engine
        )
        
        # 8. ACP客户端管理器
        self.acp_client_manager = ACPClientManager()
        self.acp_client = self.acp_client_manager.create_client(
            "default", 
            "http://localhost:8000",
            self.trace_writer
        )
        
        # 9. BIR路由器
        self.bir_router = BIRRouter(
            acp_client=self.acp_client,
            trace_writer=self.trace_writer
        )
        
        # 10. 行为分发器
        self.behavior_dispatcher = BehaviorDispatcher()
        self.behavior_dispatcher.register_router("main", self.bir_router)
        
        logger.info("Core components setup completed")
    
    def setup_agents(self):
        """设置智能体"""
        logger.info("Setting up agents...")
        
        # 创建不同类型的智能体
        self.agents = {
            "research_agent": {
                "name": "研究智能体",
                "capabilities": ["search", "analyze"],
                "tools": ["search_tool"]
            },
            "report_agent": {
                "name": "报告智能体", 
                "capabilities": ["generate", "format"],
                "tools": ["report_generator"]
            },
            "coordinator_agent": {
                "name": "协调智能体",
                "capabilities": ["coordinate", "plan"],
                "tools": ["search_tool", "report_generator"]
            }
        }
        
        logger.info(f"Created {len(self.agents)} agents")
    
    async def run_demo_scenario(self):
        """运行演示场景"""
        logger.info("Starting enterprise agent demo scenario...")
        
        # 场景：用户请求生成一份关于"人工智能发展趋势"的报告
        
        # 1. 创建会话
        context_id = f"context-{int(time.time())}"
        session = self.session_manager.create_session(
            context_id=context_id,
            agent_id="coordinator_agent",
            tenant_id="demo_tenant",
            timeout=3600
        )
        
        # 2. 用户输入
        user_input = {
            "intent": "生成一份关于人工智能发展趋势的报告",
            "topic": "人工智能发展趋势",
            "requirements": {
                "length": "2000字",
                "sections": ["技术发展", "应用场景", "未来趋势"],
                "format": "markdown"
            },
            "trace_id": f"trace-{context_id}",
            "metadata": {
                "user_id": "demo_user",
                "priority": "high"
            }
        }
        
        # 3. 通过BIR路由器分发行为
        behavior_package = self.bir_router.dispatch(
            intent=user_input["intent"],
            from_agent="user",
            to_agent="coordinator_agent",
            context_id=context_id,
            payload=user_input
        )
        
        logger.info(f"Behavior package created: {behavior_package.trace_id}")
        
        # 4. 执行智能体任务
        execution_result = await self.executor.run(session, user_input)
        
        if execution_result.status.value == "success":
            logger.info("Task execution completed successfully!")
            
            # 5. 展示结果
            await self.show_results(session, execution_result)
        else:
            logger.error(f"Task execution failed: {execution_result.error}")
        
        # 6. 展示追踪信息
        await self.show_trace_info(behavior_package.trace_id)
        
        # 7. 展示统计信息
        await self.show_statistics()
    
    async def show_results(self, session: Session, execution_result: Any):
        """展示执行结果"""
        logger.info("=== Execution Results ===")
        
        # 会话信息
        session_info = session.to_dict()
        logger.info(f"Session ID: {session_info['session_id']}")
        logger.info(f"Session Status: {session_info['meta']['status']}")
        logger.info(f"Memory Entries: {session_info['memory_entries_count']}")
        
        # 执行结果
        if execution_result.data:
            reasoning_result = execution_result.data.get("reasoning_result", {})
            tool_results = execution_result.data.get("tool_results", [])
            callback_results = execution_result.data.get("callback_results", [])
            
            logger.info(f"Reasoning Success: {reasoning_result.get('success', False)}")
            logger.info(f"Tool Executions: {len(tool_results)}")
            logger.info(f"Callback Executions: {len(callback_results)}")
            
            # 显示工具执行结果
            for tool_result in tool_results:
                if tool_result.get("success"):
                    logger.info(f"Tool {tool_result['tool']} executed successfully")
                else:
                    logger.error(f"Tool {tool_result['tool']} failed: {tool_result.get('error')}")
    
    async def show_trace_info(self, trace_id: str):
        """展示追踪信息"""
        logger.info("=== Trace Information ===")
        
        # 获取追踪链
        trace_chain = self.trace_writer.get_trace_chain(trace_id)
        logger.info(f"Trace Chain Length: {len(trace_chain)}")
        
        # 显示追踪条目
        for i, entry in enumerate(trace_chain):
            logger.info(f"Trace {i+1}: {entry.trace_type.value} - {entry.message}")
        
        # 获取追踪统计
        trace_stats = self.trace_writer.get_trace_stats()
        logger.info(f"Total Trace Entries: {trace_stats['total_entries']}")
        logger.info(f"Trace Types: {trace_stats['type_stats']}")
    
    async def show_statistics(self):
        """展示统计信息"""
        logger.info("=== System Statistics ===")
        
        # 会话统计
        session_stats = self.session_manager.get_session_stats()
        logger.info(f"Session Stats: {session_stats}")
        
        # 执行器统计
        execution_manager = ExecutionManager()
        executor_stats = execution_manager.get_executor_stats()
        logger.info(f"Executor Stats: {executor_stats}")
        
        # 工具统计
        tools = self.tool_registry.list_tools()
        logger.info(f"Registered Tools: {len(tools)}")
        for tool in tools:
            logger.info(f"  - {tool.name}: {tool.description}")
    
    async def run_interactive_demo(self):
        """运行交互式演示"""
        logger.info("=== Interactive Demo Mode ===")
        
        while True:
            print("\n请选择操作:")
            print("1. 生成报告")
            print("2. 搜索信息")
            print("3. 查看追踪")
            print("4. 查看统计")
            print("5. 退出")
            
            choice = input("请输入选择 (1-5): ").strip()
            
            if choice == "1":
                await self.generate_report_interactive()
            elif choice == "2":
                await self.search_info_interactive()
            elif choice == "3":
                await self.view_traces_interactive()
            elif choice == "4":
                await self.view_stats_interactive()
            elif choice == "5":
                logger.info("Demo completed. Goodbye!")
                break
            else:
                print("无效选择，请重试")
    
    async def generate_report_interactive(self):
        """交互式生成报告"""
        topic = input("请输入报告主题: ").strip()
        if not topic:
            print("主题不能为空")
            return
        
        context_id = f"context-{int(time.time())}"
        session = self.session_manager.create_session(
            context_id=context_id,
            agent_id="report_agent",
            tenant_id="interactive"
        )
        
        user_input = {
            "intent": f"生成关于{topic}的报告",
            "topic": topic,
            "trace_id": f"trace-{context_id}"
        }
        
        print(f"正在生成关于'{topic}'的报告...")
        result = await self.executor.run(session, user_input)
        
        if result.status.value == "success":
            print("报告生成成功!")
        else:
            print(f"报告生成失败: {result.error}")
    
    async def search_info_interactive(self):
        """交互式搜索信息"""
        query = input("请输入搜索关键词: ").strip()
        if not query:
            print("关键词不能为空")
            return
        
        # 直接调用搜索工具
        search_tool = self.tool_registry.get_tool("search_tool")
        if search_tool:
            result = search_tool.execute({"query": query})
            if result.get("success"):
                print(f"找到 {result['count']} 个结果:")
                for i, item in enumerate(result['results'], 1):
                    print(f"{i}. {item['title']}")
            else:
                print("搜索失败")
        else:
            print("搜索工具不可用")
    
    async def view_traces_interactive(self):
        """交互式查看追踪"""
        trace_stats = self.trace_writer.get_trace_stats()
        print(f"总追踪条目: {trace_stats['total_entries']}")
        print(f"追踪类型统计: {trace_stats['type_stats']}")
        
        # 显示最近的追踪条目
        recent_traces = self.trace_writer.trace_entries[-5:] if self.trace_writer.trace_entries else []
        if recent_traces:
            print("\n最近的追踪条目:")
            for trace in recent_traces:
                print(f"- {trace.trace_type.value}: {trace.message}")
    
    async def view_stats_interactive(self):
        """交互式查看统计"""
        session_stats = self.session_manager.get_session_stats()
        print(f"会话统计: {session_stats}")
        
        tools = self.tool_registry.list_tools()
        print(f"注册工具数量: {len(tools)}")


async def main():
    """主函数"""
    logger.info("Starting Enterprise Agent Demo")
    
    # 创建演示实例
    demo = EnterpriseAgentDemo()
    
    # 运行演示场景
    await demo.run_demo_scenario()
    
    # 运行交互式演示
    await demo.run_interactive_demo()


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main()) 