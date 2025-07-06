"""
任务Agent演示

展示如何使用完善的基础框架创建和运行任务Agent
"""

import asyncio
import uuid
from datetime import datetime

from src.core.agent.task_agent import create_task_agent
from src.core.agent.base_agent import AgentMessage


async def main():
    """主函数"""
    print("=== 任务Agent演示 ===")
    
    # 创建任务Agent
    agent = create_task_agent(
        agent_id=f"task_agent_{uuid.uuid4().hex[:8]}",
        name="智能任务处理Agent",
        description="一个专门处理各种任务的智能Agent",
        model="gpt-4",
        max_concurrent_tasks=3,
        enable_auto_recovery=True
    )
    
    try:
        # 启动Agent
        print("1. 启动Agent...")
        await agent.start()
        
        # 获取Agent状态
        print("2. 获取Agent状态...")
        status = await agent.get_status()
        print(f"   Agent状态: {status['status']}")
        print(f"   Agent类型: {status['agent_type']}")
        print(f"   Agent名称: {status['name']}")
        
        # 获取健康状态
        print("3. 检查健康状态...")
        health = await agent.get_health()
        print(f"   整体健康: {health['overall_health']}")
        print(f"   组件状态: {health['components']}")
        
        # 获取可用任务类型
        print("4. 获取可用任务类型...")
        task_types = await agent.get_available_task_types()
        print(f"   可用任务类型数量: {len(task_types)}")
        for task_type in task_types:
            print(f"   - {task_type['type']}: {task_type['description']}")
        
        # 执行简单任务
        print("5. 执行简单任务...")
        result = await agent.execute_task("请告诉我当前时间")
        print(f"   任务结果: {result['status']}")
        if result['status'] == 'success':
            print(f"   执行结果: {result['result']}")
        
        # 发送消息
        print("6. 发送消息...")
        message = AgentMessage(
            sender_id="user",
            receiver_id=agent.agent_id,
            content="请计算 15 + 27 的结果",
            message_type="task_request",
            metadata={
                "task_data": {
                    "type": "calculation",
                    "content": "计算 15 + 27"
                },
                "priority": 1
            }
        )
        await agent.send_message(message)
        
        # 获取工具信息
        print("7. 获取工具信息...")
        tools = agent.tool_registry.get_available_tools()
        print(f"   可用工具数量: {len(tools)}")
        for tool in tools[:3]:  # 只显示前3个工具
            print(f"   - {tool['name']}: {tool['description']}")
        
        # 获取工具统计
        print("8. 获取工具统计...")
        tool_stats = agent.tool_registry.get_tool_stats()
        print(f"   总工具数: {tool_stats['total_tools']}")
        print(f"   可用工具数: {tool_stats['available_tools']}")
        print(f"   总调用次数: {tool_stats['total_calls']}")
        print(f"   成功率: {tool_stats['success_rate']:.2%}")
        
        # 获取推理引擎统计
        print("9. 获取推理引擎统计...")
        reasoning_stats = agent.reasoning_engine.get_stats()
        print(f"   总推理次数: {reasoning_stats['total_reasoning_calls']}")
        print(f"   成功推理: {reasoning_stats['successful_reasoning']}")
        print(f"   失败推理: {reasoning_stats['failed_reasoning']}")
        print(f"   策略使用情况: {reasoning_stats['strategy_usage']}")
        
        # 执行复杂任务
        print("10. 执行复杂任务...")
        complex_result = await agent.execute_task(
            "请搜索关于人工智能的最新信息，并总结主要观点"
        )
        print(f"   复杂任务结果: {complex_result['status']}")
        if complex_result['status'] == 'success':
            print(f"   推理结果: {complex_result['reasoning']}")
        
        # 获取最终状态
        print("11. 获取最终状态...")
        final_status = await agent.get_status()
        print(f"   完成的任务数: {final_status['stats']['tasks_completed']}")
        print(f"   失败的任务数: {final_status['stats']['tasks_failed']}")
        print(f"   平均响应时间: {final_status['stats']['average_response_time']:.2f}秒")
        print(f"   处理的消息数: {final_status['stats']['messages_processed']}")
        print(f"   错误次数: {final_status['stats']['errors_count']}")
        
        print("\n=== 演示完成 ===")
        
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        
    finally:
        # 停止Agent
        print("停止Agent...")
        await agent.stop()
        print("Agent已停止")


async def performance_test():
    """性能测试"""
    print("\n=== 性能测试 ===")
    
    agent = create_task_agent(
        agent_id=f"perf_test_{uuid.uuid4().hex[:8]}",
        name="性能测试Agent",
        description="用于性能测试的Agent"
    )
    
    try:
        await agent.start()
        
        # 并发任务测试
        print("执行并发任务测试...")
        tasks = []
        for i in range(5):
            task = agent.execute_task(f"测试任务 {i+1}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'success')
        print(f"并发任务成功率: {success_count}/{len(tasks)} ({success_count/len(tasks)*100:.1f}%)")
        
        # 工具调用性能测试
        print("执行工具调用性能测试...")
        tool_tasks = []
        for i in range(10):
            task = agent.tool_registry.execute_tool("calculator", {"expression": f"{i}+{i}"})
            tool_tasks.append(task)
        
        tool_results = await asyncio.gather(*tool_tasks, return_exceptions=True)
        
        tool_success_count = sum(1 for r in tool_results if not isinstance(r, Exception))
        print(f"工具调用成功率: {tool_success_count}/{len(tool_tasks)} ({tool_success_count/len(tool_tasks)*100:.1f}%)")
        
    except Exception as e:
        print(f"性能测试出现错误: {e}")
        
    finally:
        await agent.stop()


if __name__ == "__main__":
    # 运行主演示
    asyncio.run(main())
    
    # 运行性能测试
    asyncio.run(performance_test()) 