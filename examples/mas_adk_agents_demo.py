import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.adk import AgentBase, AgentRegistry, RuntimeExecutor, log

# 1. 定义安全智能体
class ThreatDetectorAgent(AgentBase):
    def __init__(self, name):
        super().__init__(name)
        self.register_callback("detect_threat", self.detect_threat)

    def detect_threat(self, memory, incident):
        log(f"[{self.name}] 检测威胁: {incident['description']}")
        result = f"威胁检测完成: {incident['description']}"
        memory.remember("last_incident", incident)
        return result

class VulnAssessorAgent(AgentBase):
    def __init__(self, name):
        super().__init__(name)
        self.register_callback("assess_vuln", self.assess_vuln)

    def assess_vuln(self, memory, system):
        log(f"[{self.name}] 漏洞评估: {system}")
        result = f"漏洞评估完成: {system}"
        memory.remember("last_system", system)
        return result

if __name__ == "__main__":
    # 2. 注册所有agent
    registry = AgentRegistry()
    threat_agent = ThreatDetectorAgent("threat_detector_001")
    vuln_agent = VulnAssessorAgent("vuln_assessor_001")
    registry.register_agent("threat_detector", threat_agent)
    registry.register_agent("vuln_assessor", vuln_agent)

    # 3. 调度执行
    executor = RuntimeExecutor(threat_agent)
    incident = {"description": "检测到可疑恶意软件活动"}
    result1 = executor.run_task("detect_threat", incident)
    print("ThreatDetector结果:", result1)

    executor2 = RuntimeExecutor(vuln_agent)
    result2 = executor2.run_task("assess_vuln", "server_001")
    print("VulnAssessor结果:", result2)

    # 4. 多Agent顺序协作
    print("\n多Agent顺序协作：")
    incident2 = {"description": "大规模数据泄露"}
    result1 = registry.get_agent("threat_detector").on_task("detect_threat", incident2)
    result2 = registry.get_agent("vuln_assessor").on_task("assess_vuln", "database_prod")
    print("顺序协作结果:", result1, "->", result2) 