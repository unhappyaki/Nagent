"""
框架功能测试脚本
验证Nagent框架的核心功能是否正常工作
"""

import asyncio
import logging
import time
from typing import Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_basic_components():
    """测试基础组件"""
    logger.info("=== 测试基础组件 ===")
    
    try:
        # 测试导入
        from src.communication.dispatcher.bir_router import BIRRouter, BehaviorDispatcher
        from src.communication.acp.acp_client import ACPClient, ACPClientManager
        from src.state.context.session import Session, SessionManager
        from src.state.memory.memory import MemoryEngine
        from src.core.tools.tool_registry import ToolRegistry
        from src.core.tools.base_tool import BaseTool
        from src.monitoring.tracing.trace_writer import TraceWriter
        from src.config.config_manager import ConfigManager
        
        logger.info("✓ 所有模块导入成功")
        
        # 测试配置管理器
        config_manager = ConfigManager()
        logger.info("✓ 配置管理器创建成功")
        
        # 测试追踪写入器
        trace_writer = TraceWriter()
        logger.info("✓ 追踪写入器创建成功")
        
        # 测试内存引擎
        memory_engine = MemoryEngine()
        logger.info("✓ 内存引擎创建成功")
        
        # 测试会话管理器
        session_manager = SessionManager()
        logger.info("✓ 会话管理器创建成功")
        
        # 测试工具注册表
        tool_registry = ToolRegistry()
        logger.info("✓ 工具注册表创建成功")
        
        # 测试ACP客户端管理器
        acp_client_manager = ACPClientManager()
        acp_client = acp_client_manager.create_client("test", "http://localhost:8000", trace_writer)
        logger.info("✓ ACP客户端管理器创建成功")
        
        # 测试BIR路由器
        bir_router = BIRRouter(acp_client=acp_client, trace_writer=trace_writer)
        logger.info("✓ BIR路由器创建成功")
        
        # 测试行为分发器
        behavior_dispatcher = BehaviorDispatcher()
        behavior_dispatcher.register_router("test", bir_router)
        logger.info("✓ 行为分发器创建成功")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 基础组件测试失败: {e}")
        return False


async def test_session_management():
    """测试会话管理"""
    logger.info("=== 测试会话管理 ===")
    
    try:
        from src.state.context.session import Session, SessionManager
        
        session_manager = SessionManager()
        
        # 创建会话
        context_id = f"test-context-{int(time.time())}"
        session = session_manager.create_session(
            context_id=context_id,
            agent_id="test-agent",
            tenant_id="test-tenant",
            timeout=3600
        )
        
        logger.info(f"✓ 会话创建成功: {session.session_id}")
        
        # 测试会话数据操作
        session.set_data("test_key", "test_value")
        value = session.get_data("test_key")
        assert value == "test_value"
        logger.info("✓ 会话数据操作成功")
        
        # 测试内存条目
        session.add_memory_entry({
            "type": "test_entry",
            "data": {"message": "test message"},
            "timestamp": int(time.time())
        })
        
        entries = session.get_memory_entries()
        assert len(entries) == 1
        logger.info("✓ 内存条目操作成功")
        
        # 测试会话快照
        snapshot = session.create_snapshot()
        logger.info(f"✓ 会话快照创建成功: {snapshot.snapshot_id}")
        
        # 测试会话统计
        stats = session_manager.get_session_stats()
        assert stats["total_sessions"] > 0
        logger.info("✓ 会话统计获取成功")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 会话管理测试失败: {e}")
        return False


async def test_tool_registry():
    """测试工具注册表"""
    logger.info("=== 测试工具注册表 ===")
    
    try:
        from src.core.tools.tool_registry import ToolRegistry
        from src.core.tools.base_tool import BaseTool
        
        class TestTool(BaseTool):
            def __init__(self):
                super().__init__("test_tool", "测试工具")
            
            def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
                return {"success": True, "result": "test result"}
        
        tool_registry = ToolRegistry()
        
        # 注册工具
        test_tool = TestTool()
        tool_registry.register_tool(test_tool)
        logger.info("✓ 工具注册成功")
        
        # 获取工具
        tool = tool_registry.get_tool("test_tool")
        assert tool is not None
        logger.info("✓ 工具获取成功")
        
        # 执行工具
        result = tool.execute({"test_param": "test_value"})
        assert result["success"] is True
        logger.info("✓ 工具执行成功")
        
        # 列出工具
        tools = tool_registry.list_tools()
        assert len(tools) > 0
        logger.info("✓ 工具列表获取成功")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 工具注册表测试失败: {e}")
        return False


async def test_trace_writer():
    """测试追踪写入器"""
    logger.info("=== 测试追踪写入器 ===")
    
    try:
        from src.monitoring.tracing.trace_writer import TraceWriter, TraceType, TraceLevel
        
        trace_writer = TraceWriter()
        
        # 记录追踪
        trace_id = f"test-trace-{int(time.time())}"
        context_id = f"test-context-{int(time.time())}"
        
        trace_writer.record_trace(
            trace_id=trace_id,
            context_id=context_id,
            trace_type=TraceType.BEHAVIOR,
            message="测试追踪消息",
            data={"test_data": "test_value"},
            level=TraceLevel.INFO
        )
        logger.info("✓ 追踪记录成功")
        
        # 获取追踪链
        trace_chain = trace_writer.get_trace_chain(trace_id)
        assert len(trace_chain) > 0
        logger.info("✓ 追踪链获取成功")
        
        # 记录行为追踪
        trace_writer.record_behavior_trace(
            trace_id=trace_id,
            context_id=context_id,
            intent="测试意图",
            from_agent="test_user",
            to_agent="test_agent",
            intent_type="test_type"
        )
        logger.info("✓ 行为追踪记录成功")
        
        # 获取追踪统计
        stats = trace_writer.get_trace_stats()
        assert stats["total_entries"] > 0
        logger.info("✓ 追踪统计获取成功")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 追踪写入器测试失败: {e}")
        return False


async def test_bir_router():
    """测试BIR路由器"""
    logger.info("=== 测试BIR路由器 ===")
    
    try:
        from src.communication.dispatcher.bir_router import BIRRouter
        from src.monitoring.tracing.trace_writer import TraceWriter
        from src.communication.acp.acp_client import ACPClientManager
        
        trace_writer = TraceWriter()
        acp_client_manager = ACPClientManager()
        acp_client = acp_client_manager.create_client("test", "http://localhost:8000", trace_writer)
        
        bir_router = BIRRouter(acp_client=acp_client, trace_writer=trace_writer)
        
        # 分发行为
        context_id = f"test-context-{int(time.time())}"
        behavior_package = bir_router.dispatch(
            intent="测试行为",
            from_agent="test_user",
            to_agent="test_agent",
            context_id=context_id,
            payload={"test": "data"}
        )
        
        assert behavior_package is not None
        assert behavior_package.trace_id is not None
        logger.info(f"✓ 行为分发成功: {behavior_package.trace_id}")
        
        # 验证行为包
        is_valid = bir_router.validate_behavior_package(behavior_package)
        assert is_valid is True
        logger.info("✓ 行为包验证成功")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ BIR路由器测试失败: {e}")
        return False


async def test_integration():
    """测试集成功能"""
    logger.info("=== 测试集成功能 ===")
    
    try:
        from src.communication.dispatcher.bir_router import BIRRouter
        from src.state.context.session import SessionManager
        from src.monitoring.tracing.trace_writer import TraceWriter
        from src.communication.acp.acp_client import ACPClientManager
        from src.core.tools.tool_registry import ToolRegistry
        from src.core.tools.base_tool import BaseTool
        
        # 创建组件
        trace_writer = TraceWriter()
        session_manager = SessionManager()
        tool_registry = ToolRegistry()
        acp_client_manager = ACPClientManager()
        acp_client = acp_client_manager.create_client("test", "http://localhost:8000", trace_writer)
        bir_router = BIRRouter(acp_client=acp_client, trace_writer=trace_writer)
        
        # 创建测试工具
        class IntegrationTool(BaseTool):
            def __init__(self):
                super().__init__("integration_tool", "集成测试工具")
            
            def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
                return {"success": True, "message": "集成测试成功"}
        
        tool_registry.register_tool(IntegrationTool())
        
        # 创建会话
        context_id = f"integration-context-{int(time.time())}"
        session = session_manager.create_session(
            context_id=context_id,
            agent_id="integration-agent",
            tenant_id="test-tenant"
        )
        
        # 分发行为
        behavior_package = bir_router.dispatch(
            intent="集成测试",
            from_agent="test_user",
            to_agent="integration-agent",
            context_id=context_id,
            payload={"test": "integration"}
        )
        
        # 执行工具
        tool = tool_registry.get_tool("integration_tool")
        result = tool.execute({"test": "integration"})
        
        # 记录到会话
        session.add_memory_entry({
            "type": "integration_test",
            "data": result,
            "timestamp": int(time.time())
        })
        
        # 记录追踪
        trace_writer.record_trace(
            trace_id=behavior_package.trace_id,
            context_id=context_id,
            trace_type=trace_writer.TraceType.BEHAVIOR,
            message="集成测试完成",
            data=result
        )
        
        logger.info("✓ 集成测试完成")
        return True
        
    except Exception as e:
        logger.error(f"✗ 集成测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    logger.info("开始框架功能测试...")
    
    tests = [
        ("基础组件", test_basic_components),
        ("会话管理", test_session_management),
        ("工具注册表", test_tool_registry),
        ("追踪写入器", test_trace_writer),
        ("BIR路由器", test_bir_router),
        ("集成功能", test_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"测试 {test_name} 发生异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果
    logger.info("\n=== 测试结果汇总 ===")
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        logger.info("🎉 所有测试通过！框架功能正常。")
    else:
        logger.warning("⚠️ 部分测试失败，请检查相关功能。")
    
    return passed == total


if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(main())
    exit(0 if success else 1) 