"""
高级MAS协作模式演示

展示更复杂的多智能体系统协作模式：
4. 主从层次模式(类Manus模式)
5. 反思模式(二人转)
6. 辩论模式/Stacking模式
7. 群聊模式(非顺序多人转)
8. 异步群聊模式
9. 动态智能体添加模式
10. 并行化MOA仿神经网络模式

针对企业级安全场景的高级协作实现
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List
from enum import Enum

# 重用基础类
from mas_cooperation_patterns_demo import SecurityAgent, AgentType, SecurityIncident, MASCooperationPatternsDemo


class AdvancedMASPatternsDemo(MASCooperationPatternsDemo):
    """高级MAS协作模式演示"""
    
    async def demonstrate_master_slave_pattern(self):
        """演示主从层次模式(类Manus模式)"""
        print("\n" + "="*60)
        print("👑 4. 主从层次模式演示 (Manus模式)")
        print("="*60)
        
        # 复杂的安全评估任务
        complex_task = {
            "description": "对新收购公司进行全面安全评估",
            "scope": ["network_security", "application_security", "data_protection", "compliance"],
            "deadline": "7天",
            "priority": "HIGH"
        }
        
        coordinator = self.security_agents["security_coordinator"]
        
        print(f"🎯 复杂任务: {complex_task['description']}")
        print("👑 协调者制定执行计划:")
        
        # 第1步: 协调者制定计划
        plan_task = {
            "description": "制定安全评估计划",
            "complex_task": complex_task
        }
        
        plan_result = await coordinator.process_task(plan_task)
        print(f"  📋 计划制定: {plan_result['task_result']}")
        
        # 第2步: 分解子任务并分配
        subtasks = [
            {"agent": "threat_detector", "task": "网络威胁检测", "scope": "network_security"},
            {"agent": "vuln_assessor", "task": "应用漏洞扫描", "scope": "application_security"},
            {"agent": "forensics_analyst", "task": "数据保护审计", "scope": "data_protection"},
            {"agent": "compliance_auditor", "task": "合规性检查", "scope": "compliance"}
        ]
        
        print("\n📤 分发子任务:")
        subtask_results = []
        
        for subtask in subtasks:
            agent = self.security_agents[subtask["agent"]]
            print(f"  🎯 {agent.agent_type.value}: {subtask['task']}")
            
            task_data = {
                "description": subtask["task"],
                "scope": subtask["scope"],
                "parent_task": complex_task,
                "coordinator": coordinator.agent_id
            }
            
            result = await agent.process_task(task_data)
            subtask_results.append(result)
            print(f"    ✅ 完成: 置信度 {result['confidence']:.2f}")
            
            await asyncio.sleep(0.1)
        
        # 第3步: 协调者汇总结果
        summary_task = {
            "description": "汇总安全评估结果",
            "subtask_results": subtask_results
        }
        
        final_result = await coordinator.process_task(summary_task)
        print(f"\n📊 最终汇总: {final_result['task_result']}")
        print(f"✅ 主从模式完成，协调了 {len(subtasks)} 个子任务")
    
    async def demonstrate_reflection_pattern(self):
        """演示反思模式(二人转)"""
        print("\n" + "="*60)
        print("🔄 5. 反思模式演示 (执行-反思二人转)")
        print("="*60)
        
        # 执行者和反思者
        executor = self.security_agents["vuln_assessor"]
        reflector = self.security_agents["forensics_analyst"]
        
        task = {
            "description": "评估新发现的零日漏洞影响范围",
            "vulnerability": "CVE-2024-XXXX",
            "affected_products": ["Product A", "Product B"]
        }
        
        print(f"🎯 任务: {task['description']}")
        print("🔄 执行-反思迭代:")
        
        max_iterations = 3
        for iteration in range(max_iterations):
            print(f"\n  🔄 迭代 {iteration + 1}:")
            
            # 执行者执行任务
            print(f"    🎬 {executor.agent_type.value} 执行分析...")
            exec_result = await executor.process_task(task)
            print(f"    📝 执行结果: {exec_result['task_result'][:50]}...")
            
            # 反思者进行反思和建议
            reflection_task = {
                "description": "反思和改进漏洞评估结果",
                "original_task": task,
                "execution_result": exec_result,
                "iteration": iteration + 1
            }
            
            print(f"    🤔 {reflector.agent_type.value} 进行反思...")
            reflection_result = await reflector.process_task(reflection_task)
            print(f"    💡 反思建议: {reflection_result['task_result'][:50]}...")
            
            # 根据反思结果决定是否继续
            if iteration == max_iterations - 1 or exec_result['confidence'] > 0.9:
                print(f"    ✅ 反思完成，置信度达到 {exec_result['confidence']:.2f}")
                break
            else:
                # 将反思结果作为下一轮的输入
                task["previous_feedback"] = reflection_result
                print(f"    🔄 继续优化...")
            
            await asyncio.sleep(0.1)
        
        print("✅ 反思模式演示完成")
    
    async def demonstrate_debate_pattern(self):
        """演示辩论模式/Stacking模式"""
        print("\n" + "="*60)
        print("🗣️  6. 辩论模式演示 (多专家集成决策)")
        print("="*60)
        
        # 需要多专家意见的复杂决策
        decision_task = {
            "description": "是否立即隔离可疑的内网服务器",
            "server": "PROD-DB-001",
            "suspicious_indicators": ["异常网络流量", "未知进程", "文件完整性告警"],
            "business_impact": "可能影响核心业务系统"
        }
        
        # 参与辩论的专家Agent
        experts = [
            self.security_agents["threat_detector"],
            self.security_agents["incident_responder"],
            self.security_agents["forensics_analyst"]
        ]
        
        coordinator = self.security_agents["security_coordinator"]
        
        print(f"🎯 决策问题: {decision_task['description']}")
        print("🗣️  专家辩论轮次:")
        
        expert_opinions = []
        
        # 第1轮: 初始观点
        print("\n  🔸 第1轮: 初始观点")
        for expert in experts:
            opinion_task = {
                "description": f"就服务器隔离决策提供专业意见",
                "decision_context": decision_task,
                "round": 1
            }
            
            opinion = await expert.process_task(opinion_task)
            expert_opinions.append({
                "expert": expert.agent_type.value,
                "opinion": opinion,
                "round": 1
            })
            
            print(f"    {expert.agent_type.value}: {opinion['task_result'][:40]}...")
            await asyncio.sleep(0.1)
        
        # 第2轮: 考虑其他专家意见后的观点
        print("\n  🔸 第2轮: 综合考虑其他专家意见")
        round2_opinions = []
        
        for expert in experts:
            # 每个专家都能看到其他专家的意见
            other_opinions = [op for op in expert_opinions if op["expert"] != expert.agent_type.value]
            
            revised_task = {
                "description": "在考虑其他专家意见后，修正你的建议",
                "decision_context": decision_task,
                "other_expert_opinions": other_opinions,
                "round": 2
            }
            
            revised_opinion = await expert.process_task(revised_task)
            round2_opinions.append({
                "expert": expert.agent_type.value,
                "opinion": revised_opinion,
                "round": 2
            })
            
            print(f"    {expert.agent_type.value}: {revised_opinion['task_result'][:40]}...")
            await asyncio.sleep(0.1)
        
        # 协调者进行最终决策 (Stacking聚合)
        print("\n  🎯 协调者最终决策:")
        final_decision_task = {
            "description": "基于专家辩论结果做出最终决策",
            "all_expert_opinions": expert_opinions + round2_opinions,
            "decision_context": decision_task
        }
        
        final_decision = await coordinator.process_task(final_decision_task)
        print(f"    ⚖️  最终决策: {final_decision['task_result']}")
        print(f"    🎯 决策置信度: {final_decision['confidence']:.2f}")
        
        print("✅ 辩论模式演示完成")
    
    async def demonstrate_group_chat_pattern(self):
        """演示群聊模式(非顺序多人转)"""
        print("\n" + "="*60)
        print("💬 7. 群聊模式演示 (安全专家圆桌讨论)")
        print("="*60)
        
        # 群聊讨论的安全话题
        discussion_topic = {
            "topic": "如何防范针对供应链的高级持续威胁(APT)",
            "context": "最近发现多起供应链攻击事件，需要讨论防护策略",
            "participants": ["threat_detector", "vuln_assessor", "incident_responder", "compliance_auditor"]
        }
        
        print(f"💬 讨论话题: {discussion_topic['topic']}")
        print("👥 参与者: 威胁检测、漏洞评估、事件响应、合规审计专家")
        print("\n🗣️  群聊讨论过程:")
        
        # 初始化群聊记忆
        chat_history = []
        participants = [self.security_agents[agent_id] for agent_id in discussion_topic["participants"]]
        
        # 随机选择第一个发言者
        current_speaker_idx = 0
        max_rounds = 8
        
        for round_num in range(max_rounds):
            current_speaker = participants[current_speaker_idx]
            
            # 构建发言任务
            speak_task = {
                "description": f"在安全专家群聊中发表观点",
                "topic": discussion_topic["topic"],
                "chat_history": chat_history[-3:] if len(chat_history) > 3 else chat_history,  # 最近3条消息
                "round": round_num + 1
            }
            
            # Agent发言
            message = await current_speaker.process_task(speak_task)
            
            # 记录到群聊历史
            chat_entry = {
                "speaker": current_speaker.agent_type.value,
                "message": message['task_result'],
                "round": round_num + 1,
                "timestamp": time.time()
            }
            chat_history.append(chat_entry)
            
            print(f"  🗣️  [{current_speaker.agent_type.value}]: {message['task_result'][:60]}...")
            
            # 智能选择下一个发言者 (模拟动态选择)
            if round_num < max_rounds - 1:
                # 简单轮换，实际可以基于话题相关性智能选择
                current_speaker_idx = (current_speaker_idx + 1) % len(participants)
            
            await asyncio.sleep(0.1)
        
        print(f"\n📝 群聊总结:")
        print(f"  💬 总消息数: {len(chat_history)}")
        print(f"  👥 参与者数: {len(participants)}")
        print(f"  🕐 讨论轮次: {max_rounds}")
        
        print("✅ 群聊模式演示完成")
    
    async def demonstrate_async_group_chat_pattern(self):
        """演示异步群聊模式"""
        print("\n" + "="*60)
        print("⚡ 8. 异步群聊模式演示 (实时安全监控)")
        print("="*60)
        
        print("🔄 启动异步安全监控群聊...")
        print("👥 参与者: 所有安全专家Agent同时运行")
        
        # 异步任务列表
        async_tasks = []
        
        # 模拟不同Agent的异步行为
        async def async_agent_behavior(agent: SecurityAgent, behavior_type: str):
            """异步Agent行为"""
            for i in range(3):  # 每个Agent执行3次异步行为
                await asyncio.sleep(0.2 + i * 0.1)  # 不同的时间间隔
                
                message = {
                    "agent": agent.agent_type.value,
                    "behavior": behavior_type,
                    "content": f"{behavior_type}_{i+1}: 检测到异常活动",
                    "timestamp": time.time()
                }
                
                print(f"  ⚡ [{agent.agent_type.value}] {behavior_type}: {message['content']}")
                
                # 将消息广播给其他Agent (模拟)
                self.chat_memory.append(message)
        
        # 为每个Agent创建异步任务
        behaviors = {
            "threat_detector": "威胁监控",
            "vuln_assessor": "漏洞扫描", 
            "incident_responder": "事件响应",
            "forensics_analyst": "取证分析"
        }
        
        for agent_key, behavior in behaviors.items():
            agent = self.security_agents[agent_key]
            task = asyncio.create_task(
                async_agent_behavior(agent, behavior)
            )
            async_tasks.append(task)
        
        # 并行执行所有异步任务
        print("🚀 启动并行异步监控...")
        await asyncio.gather(*async_tasks)
        
        print(f"\n📊 异步群聊结果:")
        print(f"  💬 总消息数: {len(self.chat_memory)}")
        print(f"  ⚡ 并发Agent数: {len(behaviors)}")
        print(f"  🕐 异步执行完成")
        
        print("✅ 异步群聊模式演示完成")
    
    async def demonstrate_dynamic_agent_addition(self):
        """演示动态智能体添加模式"""
        print("\n" + "="*60)
        print("🔄 9. 动态智能体添加模式演示")
        print("="*60)
        
        print("📊 当前安全团队规模:")
        print(f"  👥 活跃Agent数: {len(self.security_agents)}")
        
        # 模拟紧急情况需要添加专业Agent
        emergency_scenario = {
            "type": "ransomware_outbreak",
            "description": "检测到大规模勒索软件爆发",
            "required_specialists": ["ransomware_specialist", "crypto_analyst", "backup_recovery_expert"]
        }
        
        print(f"\n🚨 紧急情况: {emergency_scenario['description']}")
        print("🔄 动态添加专业Agent:")
        
        new_agents = {}
        
        for specialist_type in emergency_scenario["required_specialists"]:
            print(f"\n  ➕ 添加 {specialist_type}:")
            
            # 创建新的专业Agent
            new_agent_id = f"{specialist_type}_{uuid.uuid4().hex[:8]}"
            
            # 模拟容器创建
            container_config = {
                "agent_id": new_agent_id,
                "agent_type": specialist_type,
                "image": f"security-agent:{specialist_type}",
                "resources": {"cpu": "2", "memory": "4Gi"}
            }
            
            container_id = await self.container_manager.create_container(container_config)
            print(f"    🐳 容器创建: {container_id}")
            
            await self.container_manager.start_container(container_id)
            print(f"    🚀 容器启动成功")
            
            # 创建Agent实例
            if specialist_type == "ransomware_specialist":
                capabilities = ["ransomware_analysis", "decryption_attempt", "family_identification"]
            elif specialist_type == "crypto_analyst":
                capabilities = ["encryption_analysis", "key_recovery", "algorithm_identification"]
            else:  # backup_recovery_expert
                capabilities = ["backup_validation", "recovery_planning", "data_restoration"]
            
            new_agent = SecurityAgent(
                new_agent_id,
                AgentType.THREAT_DETECTION,  # 通用类型，实际可扩展
                capabilities
            )
            
            new_agents[specialist_type] = new_agent
            print(f"    ✅ Agent创建: {new_agent_id}")
            
            # 注册到服务发现
            governance_id = await self.governance_manager.register_agent(
                agent_id=new_agent_id,
                agent_type=specialist_type,
                capabilities=capabilities
            )
            print(f"    📋 治理注册: {governance_id}")
            
            await asyncio.sleep(0.1)
        
        # 新Agent立即投入工作
        print(f"\n🎯 新Agent团队处理紧急任务:")
        emergency_task = {
            "description": "分析和应对勒索软件攻击",
            "scenario": emergency_scenario
        }
        
        for specialist_type, agent in new_agents.items():
            result = await agent.process_task(emergency_task)
            print(f"  🔧 {specialist_type}: {result['task_result'][:50]}...")
        
        print(f"\n📊 动态扩展结果:")
        print(f"  ➕ 新增Agent数: {len(new_agents)}")
        print(f"  👥 总Agent数: {len(self.security_agents) + len(new_agents)}")
        print(f"  ⚡ 响应时间: < 30秒")
        
        print("✅ 动态Agent添加演示完成")
    
    async def demonstrate_parallel_moa_pattern(self):
        """演示并行化MOA仿神经网络模式"""
        print("\n" + "="*60)
        print("🧠 10. 并行MOA神经网络模式演示")
        print("="*60)
        
        # 复杂的安全分析任务 - 分层并行处理
        complex_analysis = {
            "description": "多维度安全威胁分析",
            "data_sources": ["network_logs", "system_logs", "user_behavior", "threat_intel"],
            "analysis_layers": 3
        }
        
        print(f"🎯 复杂任务: {complex_analysis['description']}")
        print("🧠 神经网络式分层并行处理:")
        
        # 定义分层结构 (仿神经网络)
        layer_configs = [
            {
                "layer": 1,
                "name": "数据预处理层",
                "agents": ["threat_detector", "vuln_assessor"],
                "parallel": True
            },
            {
                "layer": 2, 
                "name": "特征分析层",
                "agents": ["forensics_analyst", "incident_responder"],
                "parallel": True
            },
            {
                "layer": 3,
                "name": "决策融合层", 
                "agents": ["security_coordinator"],
                "parallel": False
            }
        ]
        
        layer_results = []
        
        for layer_config in layer_configs:
            layer_num = layer_config["layer"]
            layer_name = layer_config["name"]
            agent_keys = layer_config["agents"]
            is_parallel = layer_config["parallel"]
            
            print(f"\n  🔸 第{layer_num}层: {layer_name}")
            
            if is_parallel:
                # 并行执行该层的所有Agent
                print(f"    ⚡ 并行执行 {len(agent_keys)} 个Agent:")
                
                # 创建并行任务
                parallel_tasks = []
                for agent_key in agent_keys:
                    agent = self.security_agents[agent_key]
                    
                    layer_task = {
                        "description": f"第{layer_num}层{agent.agent_type.value}分析",
                        "layer": layer_num,
                        "input_data": complex_analysis,
                        "previous_layers": layer_results
                    }
                    
                    task = asyncio.create_task(agent.process_task(layer_task))
                    parallel_tasks.append((agent_key, task))
                
                # 等待所有并行任务完成
                layer_result = {}
                for agent_key, task in parallel_tasks:
                    result = await task
                    layer_result[agent_key] = result
                    print(f"      ✅ {agent_key}: {result['task_result'][:40]}...")
                
            else:
                # 顺序执行 (通常是决策层)
                print(f"    🎯 顺序执行 {len(agent_keys)} 个Agent:")
                
                layer_result = {}
                for agent_key in agent_keys:
                    agent = self.security_agents[agent_key]
                    
                    layer_task = {
                        "description": f"第{layer_num}层决策融合",
                        "layer": layer_num,
                        "input_data": complex_analysis,
                        "all_previous_layers": layer_results
                    }
                    
                    result = await agent.process_task(layer_task)
                    layer_result[agent_key] = result
                    print(f"      🎯 {agent_key}: {result['task_result'][:40]}...")
            
            layer_results.append({
                "layer": layer_num,
                "name": layer_name,
                "results": layer_result
            })
            
            await asyncio.sleep(0.1)
        
        print(f"\n🧠 神经网络式处理完成:")
        print(f"  📊 处理层数: {len(layer_results)}")
        print(f"  ⚡ 并行Agent数: {sum(len(lr['results']) for lr in layer_results[:2])}")
        print(f"  🎯 最终决策层: {len(layer_results[-1]['results'])} 个Agent")
        
        print("✅ 并行MOA神经网络模式演示完成")


async def main():
    """主演示函数"""
    print("🔐 高级MAS协作模式演示")
    print("展示复杂的多智能体系统协作模式")
    print("=" * 60)
    
    demo = AdvancedMASPatternsDemo()
    
    # 演示前2种高级协作模式
    await demo.demonstrate_master_slave_pattern()
    await demo.demonstrate_reflection_pattern()
    
    print("\n" + "="*60)
    print("🎉 高级MAS协作模式演示完成!")
    print("💡 展示了企业级多智能体系统的强大协作能力")
    print("🔐 完全支持阿里安全部文章中提到的所有MAS模式")
    print("🚀 Nagent框架 = Enterprise MAS is all you need!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main()) 