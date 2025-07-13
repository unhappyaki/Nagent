"""
ACP协议演示示例
展示ACP Client、Server和Control Adapter的基本用法
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import asyncio
import time
import logging
from typing import Dict, Any

from src.communication.protocols.acp import (
    ACPServer, ACPClient, ACPPayload, ACPCommandType,
    ControlDispatcher, ControlResult, ActionType
)
from src.monitoring.tracing.trace_writer import TraceWriter


async def demo_acp_server():
    """演示ACP服务器启动"""
    print("启动ACP服务器演示...")
    
    # 创建trace写入器
    trace_writer = TraceWriter()
    
    # 启动ACP服务器
    server = ACPServer(
        host="localhost", 
        port=8765, 
        trace_writer=trace_writer
    )
    
    try:
        await server.start()
        print("ACP服务器启动成功，监听 localhost:8765")
        
        # 保持服务器运行一段时间
        await asyncio.sleep(5)
        
    except Exception as e:
        print(f"ACP服务器启动失败: {e}")
    finally:
        await server.stop()
        print("ACP服务器已停止")


async def demo_acp_client():
    """演示ACP客户端使用"""
    print("ACP客户端演示...")
    
    # 创建trace写入器
    trace_writer = TraceWriter()
    
    # 创建客户端
    client = ACPClient("ws://localhost:8765", trace_writer)
    
    try:
        # 连接到服务器
        success = await client.connect()
        if success:
            print("客户端连接成功")
            
            # 创建载荷
            payload = ACPPayload(
                command_type=ACPCommandType.CALL.value,
                action_type=ActionType.TOOL_EXEC.value,
                data={
                    "tool_name": "text_processor",
                    "tool_params": {"text": "这是测试文本"}
                },
                parameters={},
                metadata={
                    "permissions": ["read", "write"],
                    "context": {"session_id": "demo_session"},
                    "trace_id": f"trace_{int(time.time())}",
                    "context_id": f"ctx_{int(time.time())}",
                    "timestamp": int(time.time()),
                    "source_id": "demo_client"
                }
            )
            
            # 发送载荷
            result = await client._send_payload(payload)
            if result:
                print("载荷发送成功")
            else:
                print("载荷发送失败")
                
        else:
            print("客户端连接失败")
            
    except Exception as e:
        print(f"客户端演示失败: {e}")
    finally:
        client.disconnect()
        print("客户端已断开连接")


async def demo_control_dispatcher():
    """演示控制分发器使用"""
    print("控制分发器演示...")
    
    # 创建trace写入器
    trace_writer = TraceWriter()
    
    # 创建控制分发器
    dispatcher = ControlDispatcher(trace_writer)
    
    # 测试API控制适配器
    print("\n测试API控制适配器...")
    api_payload = ACPPayload(
        command_type=ACPCommandType.CALL.value,
        action_type=ActionType.API_CALL.value,
        data={
            "endpoint": "https://api.example.com/test",
            "method": "POST",
            "params": {"key": "value"},
            "action_type": ActionType.API_CALL.value
        },
        parameters={},
        metadata={
            "permissions": ["read", "write"],
            "context": {"session_id": "api_session"},
            "trace_id": f"api_trace_{int(time.time())}",
            "context_id": f"api_ctx_{int(time.time())}",
            "timestamp": int(time.time()),
            "source_id": "api_client"
        }
    )
    
    api_result = await dispatcher.dispatch(api_payload)
    print(f"API调用结果: {api_result.status}")
    print(f"API输出: {api_result.output}")
    
    # 测试工具控制适配器
    print("\n测试工具控制适配器...")
    
    # 先注册一个测试工具
    async def test_tool(params: Dict[str, Any]) -> str:
        text = params.get("text", "")
        return f"已处理文本: {text}"
    
    # 获取工具适配器并注册工具
    for adapter in dispatcher.adapters:
        if hasattr(adapter, 'register_tool'):
            adapter.register_tool("text_processor", test_tool)
            break
    
    tool_payload = ACPPayload(
        command_type=ACPCommandType.CALL.value,
        action_type=ActionType.TOOL_EXEC.value,
        data={
            "tool_name": "text_processor",
            "tool_params": {"text": "Hello, ACP!"},
            "action_type": ActionType.TOOL_EXEC.value
        },
        parameters={},
        metadata={
            "permissions": ["read", "write"],
            "context": {"session_id": "tool_session"},
            "trace_id": f"tool_trace_{int(time.time())}",
            "context_id": f"tool_ctx_{int(time.time())}",
            "timestamp": int(time.time()),
            "source_id": "tool_client"
        }
    )
    
    tool_result = await dispatcher.dispatch(tool_payload)
    print(f"工具执行结果: {tool_result.status}")
    print(f"工具输出: {tool_result.output}")
    
    # 测试模型控制适配器
    print("\n测试模型控制适配器...")
    model_payload = ACPPayload(
        command_type=ACPCommandType.CALL.value,
        action_type=ActionType.MODEL_CALL.value,
        data={
            "model_id": "gpt-4",
            "prompt": "请生成一个关于ACP协议的简短描述",
            "parameters": {"temperature": 0.7},
            "action_type": ActionType.MODEL_CALL.value
        },
        parameters={},
        metadata={
            "permissions": ["read", "write"],
            "context": {"session_id": "model_session"},
            "trace_id": f"model_trace_{int(time.time())}",
            "context_id": f"model_ctx_{int(time.time())}",
            "timestamp": int(time.time()),
            "source_id": "model_client"
        }
    )
    
    model_result = await dispatcher.dispatch(model_payload)
    print(f"模型调用结果: {model_result.status}")
    print(f"模型输出: {model_result.output}")
    
    # 显示支持的动作类型
    print(f"\n支持的动作类型: {dispatcher.get_supported_actions()}")


async def main():
    """主演示函数"""
    print("ACP协议完整演示\n")
    
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    try:
        # 演示控制分发器（不需要服务器）
        await demo_control_dispatcher()
        
        print("\n" + "="*50)
        print("ACP演示说明:")
        print("1. 控制分发器演示完成 - 展示了不同类型适配器的工作方式")
        print("2. API适配器模拟了HTTP请求的处理")
        print("3. 工具适配器展示了自定义工具的注册和执行")
        print("4. 模型适配器模拟了大模型调用的处理")
        print("\n要测试完整的Client-Server通信，请:")
        print("- 先运行服务器: python -c 'from examples.acp_demo import demo_acp_server; import asyncio; asyncio.run(demo_acp_server())'")
        print("- 再运行客户端: python -c 'from examples.acp_demo import demo_acp_client; import asyncio; asyncio.run(demo_acp_client())'")
        
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
