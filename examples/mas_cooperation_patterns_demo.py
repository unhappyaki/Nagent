"""
多智能体系统(MAS)协作模式演示

基于阿里安全部探索的多智能体协作方式，展示如何在Nagent框架中实现各种MAS协作模式：
1. ReACT Agent模式
2. 路由模式 
3. 简单顺序模式/狼人杀模式
4. 主从层次模式(类Manus模式)
5. 反思模式(二人转)
6. 辩论模式/Stacking模式
7. 群聊模式(非顺序多人转)
8. 异步群聊模式
9. 动态智能体添加模式
10. 并行化MOA仿神经网络模式

针对网络安全场景的虚拟安全专家团队实现
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from src.adk import BIRRouter, TaskScheduler, ServiceRegistry, ContainerManager, AgentGovernanceManager

# 模拟导入框架核心模块
class MockBIRRouter:
    async def dispatch(self, intent, from_agent, to_agent, context_id, payload): 
        return {"routed": True, "intent": intent}

class MockTaskScheduler:
    async def submit_task(self, **kwargs): 
        return f"task_{uuid.uuid4().hex[:8]}"

class MockServiceRegistry:
    async def find_services(self, **kwargs): 
        return [{"agent_id": f"agent_{i}", "capabilities": ["security"]} for i in range(3)]

class MockContainerManager:
    async def create_container(self, config): 
        return f"container_{uuid.uuid4().hex[:8]}"
    async def start_container(self, container_id): 
        return True

class MockAgentGovernanceManager:
    async def register_agent(self, **kwargs): 
        return f"governance_{uuid.uuid4().hex[:8]}"


class AgentType(Enum):
    """智能体类型"""
    THREAT_DETECTION = "threat_detection"
    VULNERABILITY_ASSESSMENT = "vulnerability_assessment"
    INCIDENT_RESPONSE = "incident_response"
    FORENSICS = "forensics"
    COMPLIANCE_AUDIT = "compliance_audit"
    COORDINATOR = "coordinator"


@dataclass
class SecurityIncident:
    """安全事件"""
    incident_id: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    event_type: str
    description: str
    affected_systems: List[str]
    timestamp: float


class SecurityAgent:
    """安全智能体基类"""
    
    def __init__(self, agent_id: str, agent_type: AgentType, capabilities: List[str]):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.capabilities = capabilities
        self.memory = []
        self.is_active = True
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务"""
        await asyncio.sleep(0.1)  # 模拟处理时间
        
        result = {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "task_result": f"完成任务: {task.get('description', '未知任务')}",
            "confidence": 0.85,
            "recommendations": [f"建议_{i}" for i in range(2)]
        }
        
        # 保存到记忆
        self.memory.append({
            "task": task,
            "result": result,
            "timestamp": time.time()
        })
        
        return result


class MASCooperationPatternsDemo:
    """MAS协作模式演示"""
    
    def __init__(self):
        """初始化演示环境"""
        self.setup_infrastructure()
        self.setup_security_agents()
        print("MAS协作模式演示初始化完成")
    
    def setup_infrastructure(self):
        """设置基础设施"""
        self.bir_router = MockBIRRouter()
        self.task_scheduler = MockTaskScheduler()
        self.service_registry = MockServiceRegistry()
        self.container_manager = MockContainerManager()
        self.governance_manager = MockAgentGovernanceManager()
        
        # 运行时状态
        self.active_agents = {}
        self.chat_memory = []
        self.execution_results = {}
    
    def setup_security_agents(self):
        """设置安全智能体团队"""
        self.security_agents = {
            "threat_detector": SecurityAgent(
                "threat_detector_001", 
                AgentType.THREAT_DETECTION,
                ["malware_analysis", "anomaly_detection", "threat_hunting"]
            ),
            "vuln_assessor": SecurityAgent(
                "vuln_assessor_001",
                AgentType.VULNERABILITY_ASSESSMENT,
                ["code_scan", "penetration_test", "risk_assessment"]
            ),
            "incident_responder": SecurityAgent(
                "incident_responder_001",
                AgentType.INCIDENT_RESPONSE,
                ["containment", "eradication", "recovery"]
            ),
            "forensics_analyst": SecurityAgent(
                "forensics_analyst_001",
                AgentType.FORENSICS,
                ["evidence_collection", "timeline_analysis", "attribution"]
            ),
            "compliance_auditor": SecurityAgent(
                "compliance_auditor_001",
                AgentType.COMPLIANCE_AUDIT,
                ["policy_check", "audit_trail", "compliance_validation"]
            ),
            "security_coordinator": SecurityAgent(
                "security_coordinator_001",
                AgentType.COORDINATOR,
                ["task_planning", "resource_allocation", "decision_making"]
            )
        }
    
    async def demonstrate_react_agent_pattern(self):
        """演示ReACT Agent模式"""
        print("\n" + "="*60)
        print("1. ReACT Agent模式演示")
        print("="*60)
        
        agent = self.security_agents["threat_detector"]
        incident = SecurityIncident(
            incident_id="INC_001",
            severity="HIGH",
            event_type="malware_detection",
            description="检测到可疑恶意软件活动",
            affected_systems=["server_001", "workstation_045"],
            timestamp=time.time()
        )
        
        print(f"安全事件: {incident.description}")
        print("ReACT循环处理:")
        
        # ReACT: Reason -> Act -> Observe 循环
        for cycle in range(3):
            print(f"\n  循环 {cycle + 1}:")
            
            # Reason: 分析当前状态
            print(f"    推理: 分析恶意软件特征和影响范围")
            
            # Act: 执行行动
            action_task = {
                "description": f"执行威胁检测行动 {cycle + 1}",
                "incident": incident.__dict__,
                "cycle": cycle
            }
            result = await agent.process_task(action_task)
            print(f"    行动: {result['task_result']}")
            
            # Observe: 观察结果
            print(f"    观察: 置信度 {result['confidence']:.2f}, 发现 {len(result['recommendations'])} 个建议")
            
            await asyncio.sleep(0.1)
        
        print(f"ReACT模式完成，Agent记忆中有 {len(agent.memory)} 条记录")
    
    async def demonstrate_routing_pattern(self):
        """演示路由模式"""
        print("\n" + "="*60)
        print("2. 路由模式演示")
        print("="*60)
        
        # 不同类型的安全请求
        security_requests = [
            {"type": "threat_analysis", "description": "分析新发现的APT攻击样本"},
            {"type": "vulnerability_scan", "description": "对新部署系统进行漏洞扫描"},
            {"type": "incident_investigation", "description": "调查数据泄露事件"},
            {"type": "compliance_check", "description": "执行季度合规性检查"}
        ]
        
        print("智能路由安全请求到专业Agent:")
        
        for request in security_requests:
            # 路由决策
            if "threat" in request["type"]:
                target_agent = self.security_agents["threat_detector"]
            elif "vulnerability" in request["type"]:
                target_agent = self.security_agents["vuln_assessor"]
            elif "incident" in request["type"]:
                target_agent = self.security_agents["incident_responder"]
            elif "compliance" in request["type"]:
                target_agent = self.security_agents["compliance_auditor"]
            else:
                target_agent = self.security_agents["security_coordinator"]
            
            print(f"\n  请求: {request['description']}")
            print(f"  路由到: {target_agent.agent_id} ({target_agent.agent_type.value})")
            
            # 执行任务
            result = await target_agent.process_task(request)
            print(f"  结果: {result['task_result'][:50]}...")
            
            await asyncio.sleep(0.1)
        
        print("路由模式演示完成")
    
    async def demonstrate_sequential_pattern(self):
        """演示简单顺序模式/狼人杀模式"""
        print("\n" + "="*60)
        print("3. 顺序协作模式演示 (安全事件响应流程)")
        print("="*60)
        
        incident = SecurityIncident(
            incident_id="INC_002",
            severity="CRITICAL",
            event_type="data_breach",
            description="检测到大规模数据泄露事件",
            affected_systems=["database_prod", "api_gateway"],
            timestamp=time.time()
        )
        
        # 安全事件响应的标准顺序流程
        response_sequence = [
            ("threat_detector", "初始威胁检测和分类"),
            ("incident_responder", "立即响应和遏制"),
            ("forensics_analyst", "取证分析和证据收集"),
            ("vuln_assessor", "漏洞评估和风险分析"),
            ("compliance_auditor", "合规性检查和报告"),
            ("security_coordinator", "总结和后续行动计划")
        ]
        
        print(f"处理安全事件: {incident.description}")
        print("按标准流程顺序执行:")
        
        context = {"incident": incident.__dict__, "previous_results": []}
        
        for i, (agent_key, task_description) in enumerate(response_sequence):
            agent = self.security_agents[agent_key]
            
            print(f"\n  步骤 {i+1}: {agent.agent_type.value}")
            print(f"    任务: {task_description}")
            
            # 每个Agent都能看到前面的结果
            task = {
                "description": task_description,
                "context": context,
                "step": i + 1
            }
            
            result = await agent.process_task(task)
            context["previous_results"].append(result)
            
            print(f"    完成: {result['task_result'][:60]}...")
            
            await asyncio.sleep(0.1)
        
        print(f"\n顺序协作完成，共 {len(context['previous_results'])} 个步骤")


async def main():
    """主演示函数"""
    print("多智能体系统(MAS)协作模式演示")
    print("基于阿里安全部探索的多智能体协作方式")
    print("=" * 60)
    
    demo = MASCooperationPatternsDemo()
    
    # 演示前3种基础模式
    await demo.demonstrate_react_agent_pattern()
    await demo.demonstrate_routing_pattern()
    await demo.demonstrate_sequential_pattern()
    
    print("\n" + "="*60)
    print("基础MAS协作模式演示完成!")
    print("Nagent框架支持企业级多智能体协作")
    print("特别适合安全场景的虚拟专家团队构建")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main()) 