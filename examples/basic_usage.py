"""
企业级Agent系统基本使用示例

演示如何：
- 创建和配置Agent
- 执行任务
- 处理结果
- 监控系统状态
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.agent import BaseAgent, AgentConfig, AgentType, AgentMessage
from src.core.reasoning import ReasoningEngine, ReasoningStrategy
from src.state.context import Context
from src.state.memory import Memory
from src.core.tools import LocalToolRegistry


class TaskAgent(BaseAgent):
    """任务处理Agent示例"""
    
    async def _on_start(self) -> None:
        """Agent启动时的钩子方法"""
        print(f"任务Agent {self.name} 已启动")
    
    async def _on_stop(self) -> None:
        """Agent停止时的钩子方法"""
        print(f"任务Agent {self.name} 已停止")
    
    async def _on_message_received(self, message: AgentMessage) -> None:
        """收到消息时的钩子方法"""
        print(f"收到消息: {message.content}")


async def main():
    """主函数"""
    print("=== 企业级Agent系统基本使用示例 ===\n")
    
    # 1. 创建Agent配置
    print("1. 创建Agent配置...")
    config = AgentConfig(
        agent_id="demo_task_agent",
        agent_type=AgentType.TASK,
        name="演示任务Agent",
        description="用于演示的示例Agent",
        model="gpt-4",
        max_tokens=4000,
        temperature=0.7
    )
    
    # 2. 创建Agent实例
    print("2. 创建Agent实例...")
    agent = TaskAgent(config)
    
    # 3. 启动Agent
    print("3. 启动Agent...")
    await agent.start()
    
    # 4. 执行任务示例
    print("\n4. 执行任务示例...")
    
    tasks = [
        "搜索最新的AI技术发展",
        "计算 15 * 23 + 8",
        "获取当前时间",
        "生成一份周报大纲"
    ]
    
    for i, task in enumerate(tasks, 1):
        print(f"\n任务 {i}: {task}")
        print("-" * 50)
        
        try:
            # 执行任务
            result = await agent.execute_task(task)
            
            # 显示结果
            if result["success"]:
                print(f"✅ 任务执行成功")
                print(f"   执行时间: {result.get('execution_time', 0):.2f}秒")
                print(f"   追踪ID: {result.get('trace_id', 'N/A')}")
                
                execution_result = result.get("result", {})
                action = execution_result.get("action", "unknown")
                print(f"   执行动作: {action}")
                
                if action == "tool_call":
                    tool_name = execution_result.get("parameters", {}).get("tool_name", "unknown")
                    print(f"   调用工具: {tool_name}")
                elif action == "respond":
                    response = execution_result.get("parameters", {}).get("response", "")
                    print(f"   响应内容: {response}")
                
            else:
                print(f"❌ 任务执行失败")
                print(f"   错误信息: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ 任务执行异常: {str(e)}")
    
    # 5. 获取Agent状态
    print("\n5. 获取Agent状态...")
    status = await agent.get_status()
    print(f"Agent ID: {status['agent_id']}")
    print(f"Agent名称: {status['name']}")
    print(f"Agent类型: {status['type']}")
    print(f"当前状态: {status['status']}")
    print(f"创建时间: {status['created_at']}")
    print(f"最后活跃: {status['last_active']}")
    print(f"完成任务数: {status['stats']['tasks_completed']}")
    print(f"平均响应时间: {status['stats']['average_response_time']:.2f}秒")
    
    # 6. 发送消息示例
    print("\n6. 发送消息示例...")
    message = AgentMessage(
        sender_id="user",
        receiver_id=agent.agent_id,
        content="你好，这是一个测试消息"
    )
    await agent.send_message(message)
    
    # 7. 停止Agent
    print("\n7. 停止Agent...")
    await agent.stop()
    
    print("\n=== 示例完成 ===")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main()) 