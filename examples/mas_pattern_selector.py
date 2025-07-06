"""
多智能体系统(MAS)协作模式选择器

基于阿里安全部探索的多智能体协作方式，提供交互式选择器让用户体验不同的协作模式
"""

import asyncio
import sys
from typing import Dict, Any, List, Callable

from mas_cooperation_patterns_demo import MASCooperationPatternsDemo, SecurityAgent, AgentType


class DebatePatternAgent(SecurityAgent):
    """支持辩论模式的增强安全智能体"""
    
    async def provide_expert_opinion(self, decision_context: Dict[str, Any], round_num: int = 1) -> Dict[str, Any]:
        """提供专家意见"""
        opinion_task = {
            "description": "作为安全专家提供决策意见",
            "decision_context": decision_context,
            "round": round_num,
            "expert_type": self.agent_type.value
        }
        return await self.process_task(opinion_task)
    
    async def revise_opinion(self, original_opinion: Dict[str, Any], other_opinions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """基于其他专家意见修正自己的观点"""
        revision_task = {
            "description": "基于其他专家意见修正观点",
            "original_opinion": original_opinion,
            "other_opinions": other_opinions,
            "round": 2
        }
        return await self.process_task(revision_task)


class InteractiveMASPatternsDemo(MASCooperationPatternsDemo):
    """交互式MAS协作模式演示"""
    
    def __init__(self):
        super().__init__()
        self.available_patterns = {
            "1": ("ReACT Agent模式", self.demonstrate_react_agent_pattern),
            "2": ("路由模式", self.demonstrate_routing_pattern),
            "3": ("顺序协作模式", self.demonstrate_sequential_pattern),
            "4": ("主从层次模式", self.demonstrate_master_slave_pattern),
            "5": ("反思模式", self.demonstrate_reflection_pattern),
            "6": ("辩论模式", self.demonstrate_debate_pattern),
            "7": ("群聊模式", self.demonstrate_group_chat_pattern),
            "8": ("全部演示", self.demonstrate_selected_patterns)
        }
    
    def display_menu(self):
        """显示选择菜单"""
        print("\n🔐 MAS协作模式演示器")
        print("=" * 50)
        print("请选择要演示的协作模式:")
        print()
        
        for key, (name, _) in self.available_patterns.items():
            if key == "8":
                print(f"  {key}. 🎉 {name}")
            else:
                print(f"  {key}. {name}")
        
        print("\n  0. 退出")
        print("=" * 50)
    
    async def demonstrate_master_slave_pattern(self):
        """演示主从层次模式"""
        print("\n👑 主从层次模式(类Manus模式)")
        print("-" * 40)
        
        coordinator = self.security_agents["security_coordinator"]
        
        # 模拟复杂安全评估任务
        assessment_task = {
            "description": "企业网络安全全面评估",
            "components": ["网络基础设施", "应用系统", "数据安全", "合规检查"]
        }
        
        print(f"🎯 任务: {assessment_task['description']}")
        
        # 协调者分配任务
        print("\n👑 协调者分配子任务:")
        subtasks = [
            ("threat_detector", "网络威胁扫描"),
            ("vuln_assessor", "漏洞评估分析"),
            ("forensics_analyst", "数据安全审计"),
            ("compliance_auditor", "合规性检查")
        ]
        
        results = []
        for agent_key, task_desc in subtasks:
            agent = self.security_agents[agent_key]
            print(f"  📤 分配给 {agent.agent_type.value}: {task_desc}")
            
            result = await agent.process_task({
                "description": task_desc,
                "context": assessment_task
            })
            results.append(result)
            print(f"    ✅ 完成，置信度: {result['confidence']:.2f}")
        
        # 协调者汇总
        print(f"\n👑 协调者汇总 {len(results)} 个子任务结果")
        print("✅ 主从模式演示完成")
    
    async def demonstrate_reflection_pattern(self):
        """演示反思模式"""
        print("\n🔄 反思模式(二人转)")
        print("-" * 40)
        
        executor = self.security_agents["vuln_assessor"]
        reflector = self.security_agents["incident_responder"]
        
        task = {
            "description": "分析新型网络攻击手法",
            "attack_vector": "未知恶意软件样本"
        }
        
        print(f"🎯 任务: {task['description']}")
        print("🔄 执行-反思循环:")
        
        for i in range(2):  # 简化为2轮
            print(f"\n  第{i+1}轮:")
            
            # 执行者分析
            print(f"  🎬 {executor.agent_type.value} 执行分析")
            exec_result = await executor.process_task(task)
            print(f"    结果: {exec_result['task_result'][:40]}...")
            
            # 反思者评估
            print(f"  🤔 {reflector.agent_type.value} 进行反思")
            reflection = await reflector.process_task({
                "description": "反思分析结果的完整性",
                "execution_result": exec_result
            })
            print(f"    反思: {reflection['task_result'][:40]}...")
        
        print("✅ 反思模式演示完成")
    
    async def demonstrate_debate_pattern(self):
        """演示辩论模式"""
        print("\n🗣️ 辩论模式(多专家决策)")
        print("-" * 40)
        
        # 决策场景
        decision = {
            "question": "是否需要立即隔离可疑服务器?",
            "context": "检测到异常网络活动，可能影响业务"
        }
        
        experts = [
            self.security_agents["threat_detector"],
            self.security_agents["incident_responder"],
            self.security_agents["forensics_analyst"]
        ]
        
        print(f"🎯 决策问题: {decision['question']}")
        print("🗣️ 专家观点:")
        
        opinions = []
        for expert in experts:
            opinion = await expert.process_task({
                "description": "就服务器隔离决策提供意见",
                "decision_context": decision
            })
            opinions.append(opinion)
            print(f"  {expert.agent_type.value}: {opinion['task_result'][:50]}...")
        
        # 协调者最终决策
        coordinator = self.security_agents["security_coordinator"]
        final_decision = await coordinator.process_task({
            "description": "基于专家意见做最终决策",
            "expert_opinions": opinions,
            "decision_context": decision
        })
        
        print(f"\n⚖️ 最终决策: {final_decision['task_result'][:60]}...")
        print("✅ 辩论模式演示完成")
    
    async def demonstrate_group_chat_pattern(self):
        """演示群聊模式"""
        print("\n💬 群聊模式(专家圆桌)")
        print("-" * 40)
        
        topic = "如何应对零日漏洞威胁"
        participants = [
            self.security_agents["threat_detector"],
            self.security_agents["vuln_assessor"],
            self.security_agents["incident_responder"]
        ]
        
        print(f"💬 讨论主题: {topic}")
        print("🗣️ 群聊讨论:")
        
        for i, participant in enumerate(participants):
            message = await participant.process_task({
                "description": f"就{topic}发表专业观点",
                "round": i + 1
            })
            print(f"  [{participant.agent_type.value}]: {message['task_result'][:50]}...")
        
        print("✅ 群聊模式演示完成")
    
    async def demonstrate_selected_patterns(self):
        """演示选定的模式"""
        print("\n🎉 开始基础模式演示")
        print("=" * 50)
        
        patterns_to_demo = [
            ("1", self.demonstrate_react_agent_pattern),
            ("2", self.demonstrate_routing_pattern),
            ("3", self.demonstrate_sequential_pattern),
            ("4", self.demonstrate_master_slave_pattern),
            ("5", self.demonstrate_reflection_pattern)
        ]
        
        for i, (pattern_id, demo_func) in enumerate(patterns_to_demo):
            pattern_name = self.available_patterns[pattern_id][0]
            print(f"\n🔄 [{i+1}/{len(patterns_to_demo)}] {pattern_name}")
            await demo_func()
            if i < len(patterns_to_demo) - 1:
                await asyncio.sleep(0.5)  # 间隔
        
        print("\n🎉 基础模式演示完成!")
    
    async def run_interactive_demo(self):
        """运行交互式演示"""
        print("🔐 欢迎使用MAS协作模式演示器")
        print("基于阿里安全部多智能体协作方式研究")
        
        while True:
            self.display_menu()
            
            try:
                choice = input("\n请选择模式 (0-8): ").strip()
                
                if choice == "0":
                    print("👋 感谢使用，再见!")
                    break
                
                if choice in self.available_patterns:
                    pattern_name, demo_func = self.available_patterns[choice]
                    print(f"\n🚀 开始演示: {pattern_name}")
                    await demo_func()
                    
                    input("\n按Enter键继续...")
                else:
                    print("❌ 无效选择，请重新输入")
                    
            except KeyboardInterrupt:
                print("\n\n👋 用户中断，退出演示器")
                break
            except Exception as e:
                print(f"❌ 发生错误: {str(e)}")
                continue


def main():
    """主函数"""
    try:
        demo = InteractiveMASPatternsDemo()
        asyncio.run(demo.run_interactive_demo())
    except KeyboardInterrupt:
        print("\n👋 退出演示")
    except Exception as e:
        print(f"❌ 程序错误: {str(e)}")


if __name__ == "__main__":
    main() 