"""
用户指令到BIR路由器完整流程演示

演示用户指令从输入到BIR路由器的完整处理流程：
1. 用户输入指令
2. API接收和验证
3. 意图分析
4. 目标Agent确定
5. BIR路由器分发
6. 结果返回
"""

import asyncio
import sys
from pathlib import Path
import json
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.communication.dispatcher.bir_router import BIRRouter, BehaviorPackage
from src.communication.protocols.acp.acp_client import ACPClient
from src.monitoring.tracing.trace_writer import TraceWriter
from src.state.context import Context


class UserInstructionFlowDemo:
    """用户指令流程演示"""
    
    def __init__(self):
        """初始化演示组件"""
        self.bir_router = BIRRouter()
        self.acp_client = ACPClient()
        self.trace_writer = TraceWriter()
        self.context_manager = {}
        
        # 演示用的用户指令
        self.demo_instructions = [
            {
                "instruction": "帮我搜索最新的AI技术发展",
                "user_id": "user_001",
                "session_id": "session_001",
                "priority": 1,
                "expected_intent": "data_query"
            },
            {
                "instruction": "调用计算器计算 15 * 23 + 8",
                "user_id": "user_001",
                "session_id": "session_001",
                "priority": 2,
                "expected_intent": "tool_call"
            },
            {
                "instruction": "更新我的个人资料信息",
                "user_id": "user_002",
                "session_id": "session_002",
                "priority": 1,
                "expected_intent": "status_update"
            },
            {
                "instruction": "协作完成项目报告",
                "user_id": "user_003",
                "session_id": "session_003",
                "priority": 3,
                "expected_intent": "collaboration"
            }
        ]
    
    async def run_demo(self):
        """运行完整演示"""
        print("=== 用户指令到BIR路由器完整流程演示 ===\n")
        
        # 初始化组件
        await self._initialize_components()
        
        # 处理每个演示指令
        for i, instruction_data in enumerate(self.demo_instructions, 1):
            print(f"演示 {i}: {instruction_data['instruction']}")
            print("=" * 60)
            
            try:
                # 执行完整流程
                result = await self._process_instruction_flow(instruction_data)
                
                # 显示结果
                self._display_result(result, instruction_data)
                
            except Exception as e:
                print(f"处理失败: {str(e)}")
            
            print("\n" + "=" * 60 + "\n")
        
        # 显示统计信息
        await self._show_statistics()
    
    async def _initialize_components(self):
        """初始化组件"""
        print("初始化组件...")
        
        # 初始化追踪写入器（TraceWriter 无需 initialize）
        # await self.trace_writer.initialize()
        
        # 初始化ACP客户端
        await self.acp_client.connect()
        
        print("组件初始化完成\n")
    
    async def _process_instruction_flow(self, instruction_data: dict) -> dict:
        """处理指令的完整流程"""
        instruction = instruction_data["instruction"]
        user_id = instruction_data["user_id"]
        session_id = instruction_data["session_id"]
        priority = instruction_data["priority"]
        
        print(f"接收用户指令: {instruction}")
        
        # 步骤1: 创建或获取上下文
        context_id = await self._get_or_create_context(user_id, session_id)
        print(f"获取上下文: {context_id}")
        
        # 步骤2: 分析指令意图
        intent_analysis = await self._analyze_intent(instruction)
        print(f"意图分析: {intent_analysis['intent_type']} (置信度: {intent_analysis['confidence']})")
        
        # 步骤3: 确定目标Agent
        target_agent = await self._determine_target_agent(intent_analysis)
        print(f"目标Agent: {target_agent}")
        
        # 步骤4: 构建行为包
        behavior_package = await self._build_behavior_package(
            instruction, user_id, target_agent, context_id, intent_analysis, priority
        )
        print(f"构建行为包: {behavior_package.trace_id}")
        
        # 步骤5: 通过BIR路由器分发
        routing_result = await self._route_behavior(behavior_package)
        print(f"路由结果: {routing_result}")
        
        # 步骤6: 发送到ACP客户端
        acp_result = await self._send_to_acp(behavior_package)
        print(f"ACP发送: {'成功' if acp_result else '失败'}")
        
        return {
            "instruction": instruction,
            "context_id": context_id,
            "intent_analysis": intent_analysis,
            "target_agent": target_agent,
            "behavior_package": behavior_package,
            "routing_result": routing_result,
            "acp_result": acp_result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _get_or_create_context(self, user_id: str, session_id: str) -> str:
        """获取或创建上下文"""
        if session_id not in self.context_manager:
            context = Context(agent_id=f"user_{user_id}")
            await context.initialize()
            await context.set_session_id(session_id)
            self.context_manager[session_id] = context
        
        return session_id
    
    async def _analyze_intent(self, instruction: str) -> dict:
        """分析指令意图"""
        intent_type = "task_execution"
        confidence = 0.8
        
        # 意图识别逻辑
        if any(word in instruction for word in ["查询", "搜索", "获取", "查找"]):
            intent_type = "data_query"
            confidence = 0.9
        elif any(word in instruction for word in ["调用", "使用", "执行", "运行"]):
            intent_type = "tool_call"
            confidence = 0.85
        elif any(word in instruction for word in ["更新", "修改", "调整", "变更"]):
            intent_type = "status_update"
            confidence = 0.9
        elif any(word in instruction for word in ["协作", "合作", "协助", "帮助"]):
            intent_type = "collaboration"
            confidence = 0.8
        
        return {
            "intent_type": intent_type,
            "confidence": confidence,
            "keywords": self._extract_keywords(instruction)
        }
    
    def _extract_keywords(self, instruction: str) -> list:
        """提取关键词"""
        keywords = []
        for word in instruction.split():
            if len(word) > 1:
                keywords.append(word)
        return keywords
    
    async def _determine_target_agent(self, intent_analysis: dict) -> str:
        """确定目标Agent"""
        intent_type = intent_analysis.get("intent_type", "task_execution")
        
        # Agent映射
        agent_mapping = {
            "task_execution": "task_agent_001",
            "data_query": "task_agent_001",
            "tool_call": "task_agent_001",
            "status_update": "review_agent_001",
            "collaboration": "task_agent_001"
        }
        
        return agent_mapping.get(intent_type, "task_agent_001")
    
    async def _build_behavior_package(
        self,
        instruction: str,
        user_id: str,
        target_agent: str,
        context_id: str,
        intent_analysis: dict,
        priority: int
    ) -> BehaviorPackage:
        """构建行为包"""
        return self.bir_router.dispatch(
            intent=instruction,
            from_agent=f"user_{user_id}",
            to_agent=target_agent,
            context_id=context_id,
            payload={
                "instruction": instruction,
                "user_id": user_id,
                "intent_analysis": intent_analysis,
                "priority": priority
            },
            priority=priority
        )
    
    async def _route_behavior(self, behavior_package: BehaviorPackage) -> str:
        """路由行为"""
        return self.bir_router.route_behavior(behavior_package)
    
    async def _send_to_acp(self, behavior_package: BehaviorPackage) -> bool:
        """发送到ACP客户端"""
        return self.acp_client.send_behavior_package(behavior_package)
    
    def _display_result(self, result: dict, instruction_data: dict):
        """显示处理结果"""
        print("\n处理结果:")
        print(f"   指令: {result['instruction']}")
        print(f"   上下文ID: {result['context_id']}")
        print(f"   意图类型: {result['intent_analysis']['intent_type']}")
        print(f"   置信度: {result['intent_analysis']['confidence']}")
        print(f"   目标Agent: {result['target_agent']}")
        print(f"   追踪ID: {result['behavior_package'].trace_id}")
        print(f"   路由结果: {result['routing_result']}")
        print(f"   ACP发送: {'成功' if result['acp_result'] else '失败'}")
        
        # 验证意图分析是否正确
        expected_intent = instruction_data.get("expected_intent")
        actual_intent = result['intent_analysis']['intent_type']
        if expected_intent == actual_intent:
            print(f"   意图分析正确")
        else:
            print(f"   意图分析错误 (期望: {expected_intent}, 实际: {actual_intent})")
    
    async def _show_statistics(self):
        """显示统计信息"""
        print("处理统计:")
        print(f"   总指令数: {len(self.demo_instructions)}")
        print(f"   上下文数: {len(self.context_manager)}")
        print(f"   追踪记录: {len(self.trace_writer.get_traces()) if hasattr(self.trace_writer, 'get_traces') else 'N/A'}")


async def main():
    """主函数"""
    demo = UserInstructionFlowDemo()
    await demo.run_demo()


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main()) 