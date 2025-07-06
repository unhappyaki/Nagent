"""
网络安全场景MAS协作演示

基于真实网络安全事件，展示多智能体系统如何协作处理各种安全威胁
模拟阿里安全部提到的"虚拟网络安全专家团队"工作模式
"""

import asyncio
import time
import random
from typing import Dict, Any, List
from enum import Enum
from dataclasses import dataclass

from mas_cooperation_patterns_demo import SecurityAgent, AgentType


class ThreatLevel(Enum):
    """威胁等级"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    CRITICAL = "严重"


class SecurityEventType(Enum):
    """安全事件类型"""
    MALWARE_DETECTION = "恶意软件检测"
    PHISHING_ATTACK = "钓鱼攻击"
    DATA_BREACH = "数据泄露"
    APT_ATTACK = "高级持续威胁"
    RANSOMWARE = "勒索软件"


@dataclass
class SecurityEvent:
    """安全事件"""
    event_id: str
    event_type: SecurityEventType
    threat_level: ThreatLevel
    description: str
    affected_assets: List[str]
    indicators: List[str]
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "threat_level": self.threat_level.value,
            "description": self.description,
            "affected_assets": self.affected_assets,
            "indicators": self.indicators,
            "timestamp": self.timestamp
        }


class SecurityTeamMAS:
    """网络安全团队多智能体系统"""
    
    def __init__(self):
        self.setup_security_team()
        self.event_history = []
        
    def setup_security_team(self):
        """设置安全团队"""
        self.security_team = {
            # SOC分析师
            "soc_analyst": SecurityAgent(
                "soc_analyst_001",
                AgentType.THREAT_DETECTION,
                ["事件分析", "威胁分类", "初步响应"]
            ),
            
            # 恶意软件分析师
            "malware_analyst": SecurityAgent(
                "malware_analyst_001",
                AgentType.THREAT_DETECTION,
                ["恶意软件逆向", "行为分析", "IOC提取"]
            ),
            
            # 网络取证专家
            "forensics_expert": SecurityAgent(
                "forensics_expert_001",
                AgentType.FORENSICS,
                ["数字取证", "证据收集", "攻击链重建"]
            ),
            
            # 事件响应专家
            "incident_commander": SecurityAgent(
                "incident_commander_001",
                AgentType.INCIDENT_RESPONSE,
                ["事件指挥", "响应协调", "决策制定"]
            ),
            
            # 威胁情报分析师
            "threat_intel_analyst": SecurityAgent(
                "threat_intel_001",
                AgentType.THREAT_DETECTION,
                ["威胁情报", "归因分析", "趋势预测"]
            ),
            
            # 安全架构师
            "security_architect": SecurityAgent(
                "security_architect_001",
                AgentType.VULNERABILITY_ASSESSMENT,
                ["安全架构", "防护建议", "风险评估"]
            )
        }
    
    async def simulate_security_event(self, event_type: SecurityEventType) -> SecurityEvent:
        """模拟安全事件"""
        event_templates = {
            SecurityEventType.MALWARE_DETECTION: {
                "description": "在员工工作站检测到疑似恶意软件",
                "assets": ["workstation_025", "file_server_01"],
                "indicators": ["suspicious_process.exe", "网络连接异常", "文件加密行为"]
            },
            SecurityEventType.APT_ATTACK: {
                "description": "发现高级持续威胁攻击迹象",
                "assets": ["domain_controller", "critical_servers"],
                "indicators": ["横向移动", "权限提升", "数据收集"]
            }
        }
        
        template = event_templates.get(event_type, event_templates[SecurityEventType.MALWARE_DETECTION])
        
        event = SecurityEvent(
            event_id=f"SEC_{int(time.time())}_{random.randint(1000, 9999)}",
            event_type=event_type,
            threat_level=ThreatLevel.HIGH,
            description=template["description"],
            affected_assets=template["assets"],
            indicators=template["indicators"],
            timestamp=time.time()
        )
        
        return event
    
    async def demonstrate_incident_response_workflow(self):
        """演示事件响应工作流程"""
        print("🔐 网络安全事件响应工作流程演示")
        print("=" * 60)
        
        # 模拟安全事件
        event = await self.simulate_security_event(SecurityEventType.MALWARE_DETECTION)
        
        print(f"🚨 安全事件触发:")
        print(f"   ID: {event.event_id}")
        print(f"   类型: {event.event_type.value}")
        print(f"   等级: {event.threat_level.value}")
        print(f"   描述: {event.description}")
        
        # 标准事件响应流程
        print(f"\n📋 启动标准事件响应流程:")
        
        # 第1步: SOC分析师初步分析
        print(f"\n🔍 第1步: SOC分析师初步分析")
        soc_result = await self.security_team["soc_analyst"].process_task({
            "description": "初步分析安全事件",
            "event": event.to_dict(),
            "step": "initial_analysis"
        })
        print(f"   结果: {soc_result['task_result'][:60]}...")
        
        # 第2步: 事件指挥官风险评估
        print(f"\n⚡ 第2步: 事件指挥官风险评估")
        commander_result = await self.security_team["incident_commander"].process_task({
            "description": "评估事件风险和影响",
            "event": event.to_dict(),
            "soc_analysis": soc_result,
            "step": "risk_assessment"
        })
        print(f"   决策: {commander_result['task_result'][:60]}...")
        
        # 第3步: 恶意软件分析师深度分析
        print(f"\n🔬 第3步: 恶意软件分析师深度分析")
        malware_result = await self.security_team["malware_analyst"].process_task({
            "description": "深度分析恶意软件样本",
            "event": event.to_dict(),
            "step": "malware_analysis"
        })
        print(f"   发现: {malware_result['task_result'][:60]}...")
        
        print(f"\n✅ 事件响应流程演示完成")
        print(f"   参与专家: {len(self.security_team)} 名")
        print(f"   分析步骤: 3 步")
    
    async def demonstrate_collaborative_investigation(self):
        """演示协作调查模式"""
        print("\n🔍 多专家协作调查演示")
        print("=" * 60)
        
        # 模拟复杂APT攻击
        apt_event = await self.simulate_security_event(SecurityEventType.APT_ATTACK)
        
        print(f"🎯 复杂安全事件: {apt_event.description}")
        print(f"威胁等级: {apt_event.threat_level.value}")
        
        # 并行调查 - 多个专家同时工作
        print(f"\n⚡ 启动并行调查:")
        
        investigation_tasks = []
        
        # 恶意软件分析师分析样本
        malware_task = self.security_team["malware_analyst"].process_task({
            "description": "分析APT攻击中的恶意软件",
            "event": apt_event.to_dict(),
            "focus": "malware_analysis"
        })
        investigation_tasks.append(("恶意软件分析", malware_task))
        
        # 取证专家分析攻击路径
        forensics_task = self.security_team["forensics_expert"].process_task({
            "description": "重建APT攻击路径",
            "event": apt_event.to_dict(),
            "focus": "attack_path_reconstruction"
        })
        investigation_tasks.append(("攻击路径重建", forensics_task))
        
        # 威胁情报分析师进行归因
        intel_task = self.security_team["threat_intel_analyst"].process_task({
            "description": "APT攻击归因分析",
            "event": apt_event.to_dict(),
            "focus": "attribution_analysis"
        })
        investigation_tasks.append(("归因分析", intel_task))
        
        print(f"   🚀 启动 {len(investigation_tasks)} 个并行调查任务")
        
        # 等待所有调查完成
        results = []
        for task_name, task in investigation_tasks:
            result = await task
            results.append((task_name, result))
            print(f"   ✅ {task_name}: {result['task_result'][:50]}...")
        
        # 事件指挥官汇总分析
        print(f"\n📊 事件指挥官汇总分析:")
        summary = await self.security_team["incident_commander"].process_task({
            "description": "汇总APT调查结果",
            "event": apt_event.to_dict(),
            "investigation_results": [result[1] for result in results]
        })
        print(f"   📋 汇总结论: {summary['task_result'][:80]}...")
        
        print(f"\n✅ 协作调查完成")
        print(f"   并行任务: {len(investigation_tasks)} 个")


async def main():
    """主演示函数"""
    print("🔐 网络安全场景MAS协作演示")
    print("模拟阿里安全部的'虚拟网络安全专家团队'")
    print("=" * 60)
    
    security_mas = SecurityTeamMAS()
    
    scenarios = [
        ("标准事件响应工作流程", security_mas.demonstrate_incident_response_workflow),
        ("多专家协作调查", security_mas.demonstrate_collaborative_investigation)
    ]
    
    for i, (scenario_name, demo_func) in enumerate(scenarios):
        print(f"\n🎬 [{i+1}/{len(scenarios)}] {scenario_name}")
        await demo_func()
        
        if i < len(scenarios) - 1:
            print("\n" + "-" * 60)
            await asyncio.sleep(1)
    
    print(f"\n🎉 网络安全MAS协作演示完成!")
    print(f"💡 展示了企业级安全团队的多智能体协作能力")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main()) 