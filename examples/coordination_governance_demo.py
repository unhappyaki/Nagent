"""
协调域治理层演示

展示如何使用协调域实现统一管理内部和外部智能体，提供SLA、成本、合规管控
"""

import asyncio
import time
from typing import Dict, Any

# 模拟导入
class MockServiceRegistry:
    async def register_service(self, **kwargs): 
        return "service_001"
    async def find_services(self, **kwargs): 
        return []

class MockTaskScheduler:
    async def submit_task(self, **kwargs): 
        return "task_001"
    async def get_scheduler_stats(self): 
        return {"total_tasks": 100}

class MockTraceWriter:
    async def record_trace(self, **kwargs): 
        pass

# 导入治理模块
from src.coordination.governance import (
    AgentGovernanceManager,
    AgentType,
    SLAMetrics,
    CostMetrics,
    CompliancePolicy,
    ComplianceLevel
)


class CoordinationGovernanceDemo:
    """协调域治理层演示"""
    
    def __init__(self):
        """初始化演示"""
        self.service_registry = MockServiceRegistry()
        self.task_scheduler = MockTaskScheduler()
        self.trace_writer = MockTraceWriter()
        
        # 创建治理管理器
        self.governance_manager = AgentGovernanceManager(
            service_registry=self.service_registry,
            task_scheduler=self.task_scheduler,
            trace_writer=self.trace_writer
        )
        
        print("✅ 协调域治理层演示初始化完成")
    
    async def demonstrate_agent_registration(self):
        """演示智能体注册到治理系统"""
        print("\n" + "="*60)
        print("📋 智能体治理注册演示")
        print("="*60)
        
        # 注册内部智能体
        internal_governance_id = await self.governance_manager.register_agent(
            agent_id="internal_agent_001",
            agent_name="任务处理智能体",
            agent_type=AgentType.INTERNAL,
            sla_config={
                "availability_target": 99.9,
                "response_time_target": 200.0,
                "error_rate_target": 0.5
            },
            cost_config={
                "monthly_budget": 500.0,
                "cost_per_request": 0.01
            },
            compliance_config={
                "data_classification": ComplianceLevel.INTERNAL,
                "encryption_required": True,
                "audit_logging": True
            }
        )
        print(f"✅ 内部智能体注册成功: {internal_governance_id}")
        
        # 注册外部A2A智能体
        a2a_governance_id = await self.governance_manager.register_agent(
            agent_id="claude_agent_001",
            agent_name="Claude外部智能体",
            agent_type=AgentType.A2A_EXTERNAL,
            sla_config={
                "availability_target": 99.0,
                "response_time_target": 500.0,
                "error_rate_target": 1.0
            },
            cost_config={
                "monthly_budget": 1000.0,
                "cost_per_request": 0.05,
                "cost_per_token": 0.0001
            },
            compliance_config={
                "data_classification": ComplianceLevel.CONFIDENTIAL,
                "external_agent_allowed": True,
                "cross_border_transfer": True
            }
        )
        print(f"✅ 外部A2A智能体注册成功: {a2a_governance_id}")
        
        # 注册MCP工具
        mcp_governance_id = await self.governance_manager.register_agent(
            agent_id="mcp_tool_001",
            agent_name="外部数据分析工具",
            agent_type=AgentType.MCP_EXTERNAL,
            sla_config={
                "availability_target": 95.0,
                "response_time_target": 1000.0,
                "error_rate_target": 2.0
            },
            cost_config={
                "monthly_budget": 200.0,
                "cost_per_minute": 0.1
            }
        )
        print(f"✅ MCP工具注册成功: {mcp_governance_id}")
        
        return {
            "internal": internal_governance_id,
            "a2a": a2a_governance_id,
            "mcp": mcp_governance_id
        }
    
    async def demonstrate_sla_management(self):
        """演示SLA管理"""
        print("\n" + "="*60)
        print("📊 SLA管理演示")
        print("="*60)
        
        # 模拟不同的调用场景
        scenarios = [
            {"agent_id": "internal_agent_001", "response_time": 150.0, "success": True, "description": "内部智能体正常调用"},
            {"agent_id": "claude_agent_001", "response_time": 800.0, "success": False, "description": "外部智能体超时失败"},
            {"agent_id": "mcp_tool_001", "response_time": 1200.0, "success": True, "description": "MCP工具慢响应"},
            {"agent_id": "internal_agent_001", "response_time": 180.0, "success": True, "description": "内部智能体再次调用"},
            {"agent_id": "claude_agent_001", "response_time": 400.0, "success": True, "description": "外部智能体恢复正常"},
        ]
        
        print("🔄 模拟智能体调用...")
        for scenario in scenarios:
            await self.governance_manager.update_agent_metrics(
                agent_id=scenario["agent_id"],
                response_time=scenario["response_time"],
                success=scenario["success"],
                cost=0.02,
                tokens=100
            )
            print(f"  📈 {scenario['description']}: {scenario['response_time']}ms, 成功: {scenario['success']}")
            await asyncio.sleep(0.1)  # 模拟时间间隔
        
        # 获取SLA状态
        print("\n📊 SLA状态报告:")
        for agent_id in ["internal_agent_001", "claude_agent_001", "mcp_tool_001"]:
            status = await self.governance_manager.get_agent_governance_status(agent_id)
            if status:
                print(f"  🤖 {status['agent_name']} ({status['agent_type']}):")
                print(f"    📊 SLA状态: {status['sla_status']}")
                print(f"    ⏱️  响应时间: {status['sla_metrics']['current_response_time']:.1f}ms (目标: {status['sla_metrics']['response_time_target']}ms)")
                print(f"    💰 月度成本: ¥{status['cost_metrics']['current_monthly_cost']:.2f} / ¥{status['cost_metrics']['monthly_budget']}")
                print(f"    📞 总调用次数: {status['total_invocations']}")
    
    async def demonstrate_cost_management(self):
        """演示成本管理"""
        print("\n" + "="*60)
        print("💰 成本管理演示")
        print("="*60)
        
        # 模拟高成本调用
        high_cost_scenarios = [
            {"agent_id": "claude_agent_001", "cost": 50.0, "tokens": 5000, "description": "大型文档分析"},
            {"agent_id": "claude_agent_001", "cost": 80.0, "tokens": 8000, "description": "复杂推理任务"},
            {"agent_id": "mcp_tool_001", "cost": 30.0, "tokens": 0, "description": "数据处理作业"},
            {"agent_id": "claude_agent_001", "cost": 120.0, "tokens": 12000, "description": "代码生成任务"},
        ]
        
        print("💸 模拟高成本调用...")
        total_cost = 0
        for scenario in high_cost_scenarios:
            await self.governance_manager.update_agent_metrics(
                agent_id=scenario["agent_id"],
                response_time=500.0,
                success=True,
                cost=scenario["cost"],
                tokens=scenario["tokens"]
            )
            total_cost += scenario["cost"]
            print(f"  💰 {scenario['description']}: ¥{scenario['cost']:.2f} ({scenario['tokens']} tokens)")
            await asyncio.sleep(0.1)
        
        print(f"\n💰 总成本: ¥{total_cost:.2f}")
        
        # 获取成本状态
        dashboard = await self.governance_manager.get_governance_dashboard()
        cost_summary = dashboard["cost_summary"]
        
        print("\n📊 成本摘要:")
        print(f"  💰 总成本: ¥{cost_summary['total_cost']:.2f}")
        print(f"  💳 总预算: ¥{cost_summary['total_budget']:.2f}")
        print(f"  📈 预算使用率: {cost_summary['budget_usage']:.1f}%")
        print(f"  🚨 成本告警数: {cost_summary['alert_count']}")
        
        print("\n🏆 成本最高的智能体:")
        for i, agent in enumerate(dashboard["top_cost_agents"][:3], 1):
            print(f"  {i}. {agent['agent_name']}: ¥{agent['monthly_cost']:.2f} ({agent['budget_usage']:.1f}%)")
    
    async def demonstrate_compliance_management(self):
        """演示合规管理"""
        print("\n" + "="*60)
        print("🔒 合规管理演示")
        print("="*60)
        
        # 获取合规摘要
        dashboard = await self.governance_manager.get_governance_dashboard()
        compliance_summary = dashboard["compliance_summary"]
        
        print("📋 合规状态摘要:")
        print(f"  ✅ 合规智能体: {compliance_summary['compliant']}")
        print(f"  ⚠️  违规智能体: {compliance_summary['violations']}")
        print(f"  📊 合规率: {compliance_summary['compliance_rate']:.1f}%")
        
        # 显示智能体合规策略
        print("\n🔐 智能体合规策略:")
        for agent_id in ["internal_agent_001", "claude_agent_001", "mcp_tool_001"]:
            status = await self.governance_manager.get_agent_governance_status(agent_id)
            if status:
                print(f"  🤖 {status['agent_name']} ({status['agent_type']}):")
                print(f"    🔒 合规状态: {status['compliance_status']}")
    
    async def demonstrate_governance_dashboard(self):
        """演示治理仪表板"""
        print("\n" + "="*60)
        print("📊 治理仪表板演示")
        print("="*60)
        
        # 获取完整的治理仪表板
        dashboard = await self.governance_manager.get_governance_dashboard()
        
        print("🎯 系统概览:")
        overview = dashboard["overview"]
        print(f"  🤖 总智能体数: {overview['total_agents']}")
        print(f"  🏠 内部智能体: {overview['internal_agents']}")
        print(f"  🌐 外部智能体: {overview['external_agents']}")
        print(f"  ✅ SLA合规智能体: {overview['sla_compliant_agents']}")
        print(f"  💰 成本告警智能体: {overview['cost_alert_agents']}")
        print(f"  ⚠️  合规违规数: {overview['compliance_violations']}")
        print(f"  💰 总治理成本: ¥{overview['total_governance_cost']:.2f}")
        
        print("\n📊 SLA摘要:")
        sla_summary = dashboard["sla_summary"]
        print(f"  ✅ 健康: {sla_summary['healthy']}")
        print(f"  ⚠️  警告: {sla_summary['warning']}")
        print(f"  🚨 严重: {sla_summary['critical']}")
        
        print("\n💰 成本摘要:")
        cost_summary = dashboard["cost_summary"]
        print(f"  💰 总成本: ¥{cost_summary['total_cost']:.2f}")
        print(f"  💳 总预算: ¥{cost_summary['total_budget']:.2f}")
        print(f"  📈 预算使用率: {cost_summary['budget_usage']:.1f}%")
        
        # SLA违规
        if dashboard["sla_violations"]:
            print("\n🚨 SLA违规记录:")
            for violation in dashboard["sla_violations"][:3]:
                print(f"  ⚠️  {violation['agent_name']}: {violation['sla_status']} "
                      f"(响应时间: {violation['response_time']:.1f}ms, 错误率: {violation['error_rate']:.1f}%)")
    
    async def demonstrate_unified_agent_management(self):
        """演示统一智能体管理"""
        print("\n" + "="*60)
        print("🌟 统一智能体管理演示")
        print("="*60)
        
        print("🎯 治理层实现的统一管理能力:")
        print("  🔧 统一注册: 内部和外部智能体统一注册到治理系统")
        print("  📊 统一监控: 统一的SLA、成本、合规监控")
        print("  🎮 统一策略: 统一的治理策略配置和应用")
        print("  📈 统一报告: 统一的治理仪表板和报告")
        print("  🚨 统一告警: 统一的告警和通知机制")
        
        print("\n💼 企业级治理价值:")
        print("  🎯 SLA管控: 确保服务质量和可用性")
        print("  💰 成本控制: 精细化成本管理和预算控制")
        print("  🔒 合规管理: 数据安全和合规要求保障")
        print("  📊 可视化管理: 实时监控和决策支持")
        print("  🔄 自动化治理: 自动化的策略执行和问题处理")
        
        print("\n🌐 跨平台协作:")
        print("  🏠 内部智能体: 完全控制，最优性能")
        print("  🌍 A2A智能体: 标准协议，生态扩展")  
        print("  🔧 MCP工具: 工具集成，能力补充")
        print("  🤝 混合架构: 灵活组合，优势互补")


async def main():
    """主演示函数"""
    print("🚀 协调域治理层演示开始")
    print("="*80)
    
    demo = CoordinationGovernanceDemo()
    
    try:
        # 初始化治理管理器
        await demo.governance_manager.initialize()
        
        # 演示智能体注册
        governance_ids = await demo.demonstrate_agent_registration()
        
        # 等待一下让监控任务启动
        await asyncio.sleep(1)
        
        # 演示SLA管理
        await demo.demonstrate_sla_management()
        
        # 演示成本管理
        await demo.demonstrate_cost_management()
        
        # 演示合规管理
        await demo.demonstrate_compliance_management()
        
        # 演示治理仪表板
        await demo.demonstrate_governance_dashboard()
        
        # 演示统一管理能力
        await demo.demonstrate_unified_agent_management()
        
        print("\n" + "="*80)
        print("✅ 协调域治理层演示完成")
        print("💡 治理层为企业级Agent系统提供了完整的管控能力!")
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 