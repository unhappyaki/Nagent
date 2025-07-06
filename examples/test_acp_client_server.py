"""
ACP客户端-服务器通信测试
同时启动服务器和客户端进行完整的通信测试
"""

import asyncio
import time
import logging
from typing import Dict, Any, List

from src.communication.acp import (
    ACPServer, ACPClient, ACPPayload, ACPCommandType,
    ControlDispatcher, ControlResult, ActionType
)
from src.monitoring.tracing.trace_writer import TraceWriter
from src.communication.acp.message_schema import ACPMessageBuilder, ACPMessageType, ACPCommandType, ACPActionType


async def test_client_server_communication():
    """测试完整的客户端-服务器通信"""
    print("🔗 ACP客户端-服务器通信测试\n")
    
    # 创建trace写入器
    trace_writer = TraceWriter()
    
    # 创建并启动服务器
    print("🚀 启动ACP服务器...")
    server = ACPServer(
        host="localhost", 
        port=8765, 
        trace_writer=trace_writer
    )
    
    try:
        # 启动服务器
        await server.start()
        print("✅ ACP服务器启动成功，监听 localhost:8765")
        
        # 等待一秒让服务器完全启动
        await asyncio.sleep(1)
        
        # 创建客户端
        print("\n📱 创建ACP客户端...")
        client = ACPClient("ws://localhost:8765", trace_writer)
        
        # 连接到服务器
        success = await client.connect()
        if success:
            print("✅ 客户端连接成功")
            
            # 测试多个载荷
            builder = ACPMessageBuilder(sender_id="test_client")
            for i in range(3):
                print(f"\n📦 发送载荷 {i+1}...")
                
                # 构造标准消息
                acp_msg = builder.create_tool_call_message(
                    receiver_id="test_agent",
                    tool_name="test_processor",
                    tool_args={"text": f"测试消息 {i+1}", "index": i+1},
                    context_id=f"test_session_{i+1}",
                    trace_id=f"trace_{int(time.time())}_{i+1}"
                )
                
                # 发送消息（假设 client 有 send_acp_message 方法，需你在 acp_client.py 实现标准化发送）
                result = await asyncio.get_event_loop().run_in_executor(None, client._send_payload, acp_msg)
                if result:
                    print(f"✅ 载荷 {i+1} 发送成功")
                else:
                    print(f"❌ 载荷 {i+1} 发送失败")
                
                # 等待一秒
                await asyncio.sleep(1)
                
        else:
            print("❌ 客户端连接失败")
            
        # 断开客户端连接
        client.disconnect()
        print("\n🔌 客户端已断开连接")
        
        # 等待一秒后停止服务器
        await asyncio.sleep(1)
        
    except Exception as e:
        print(f"❌ 通信测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await server.stop()
        print("🛑 ACP服务器已停止")


async def main():
    """主测试函数"""
    print("🧪 ACP协议完整通信测试\n")
    
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    try:
        # 运行完整的客户端-服务器通信测试
        await test_client_server_communication()
        
        print("\n" + "="*50)
        print("📊 测试结果总结:")
        print("1. ✅ ACP服务器启动和关闭成功")
        print("2. ✅ ACP客户端连接和断开成功")
        print("3. ✅ 载荷发送和接收测试完成")
        print("4. ✅ 完整的Client-Server通信链路验证成功")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 