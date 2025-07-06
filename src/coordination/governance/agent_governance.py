"""
智能体治理层

实现统一管理内部和外部智能体，提供SLA、成本、合规管控
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Enum
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class AgentType(Enum):
    """智能体类型"""
    INTERNAL = "internal"        # 内部智能体
    A2A_EXTERNAL = "a2a_external"  # 外部A2A智能体
    MCP_EXTERNAL = "mcp_external"  # 外部MCP工具
    HYBRID = "hybrid"           # 混合智能体


class SLAStatus(Enum):
    """SLA状态"""
    HEALTHY = "healthy"         # 健康
    WARNING = "warning"         # 警告
    CRITICAL = "critical"       # 严重
    BREACHED = "breached"       # 违约


class ComplianceLevel(Enum):
    """合规级别"""
    PUBLIC = "public"           # 公开数据
    INTERNAL = "internal"       # 内部数据
    CONFIDENTIAL = "confidential"  # 机密数据
    RESTRICTED = "restricted"   # 限制数据


@dataclass
class SLAMetrics:
    """SLA指标"""
    availability_target: float = 99.9      # 可用性目标 (%)
    response_time_target: float = 500.0    # 响应时间目标 (ms)
    throughput_target: int = 1000          # 吞吐量目标 (requests/min)
    error_rate_target: float = 1.0         # 错误率目标 (%)
    
    # 当前指标
    current_availability: float = 0.0
    current_response_time: float = 0.0
    current_throughput: int = 0
    current_error_rate: float = 0.0
    
    # 统计窗口
    measurement_window: int = 3600  # 测量窗口 (秒)
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass 
class CostMetrics:
    """成本指标"""
    # 成本配置
    cost_per_request: float = 0.01         # 每请求成本
    cost_per_token: float = 0.0001         # 每Token成本
    cost_per_minute: float = 0.1           # 每分钟成本
    monthly_budget: float = 1000.0         # 月度预算
    
    # 当前成本
    current_daily_cost: float = 0.0
    current_monthly_cost: float = 0.0
    total_requests: int = 0
    total_tokens: int = 0
    total_minutes: int = 0
    
    # 成本控制
    budget_alert_threshold: float = 80.0   # 预算警告阈值 (%)
    budget_limit_threshold: float = 95.0   # 预算限制阈值 (%)
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CompliancePolicy:
    """合规策略"""
    data_classification: ComplianceLevel = ComplianceLevel.INTERNAL
    allowed_regions: List[str] = field(default_factory=lambda: ["CN", "US", "EU"])
    data_retention_days: int = 90
    encryption_required: bool = True
    audit_logging: bool = True
    pii_detection: bool = True
    external_agent_allowed: bool = True
    cross_border_transfer: bool = False
    
    # 违规行为记录
    compliance_violations: List[Dict[str, Any]] = field(default_factory=list)
    last_audit: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentGovernanceInfo:
    """智能体治理信息"""
    agent_id: str
    agent_name: str
    agent_type: AgentType
    
    # SLA管理
    sla_metrics: SLAMetrics = field(default_factory=SLAMetrics)
    sla_status: SLAStatus = SLAStatus.HEALTHY
    
    # 成本控制
    cost_metrics: CostMetrics = field(default_factory=CostMetrics)
    cost_status: str = "normal"
    
    # 合规管控
    compliance_policy: CompliancePolicy = field(default_factory=CompliancePolicy)
    compliance_status: str = "compliant"
    
    # 统计信息
    registration_time: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    total_invocations: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type.value,
            "sla_metrics": {
                "availability_target": self.sla_metrics.availability_target,
                "response_time_target": self.sla_metrics.response_time_target,
                "current_availability": self.sla_metrics.current_availability,
                "current_response_time": self.sla_metrics.current_response_time,
            },
            "sla_status": self.sla_status.value,
            "cost_metrics": {
                "monthly_budget": self.cost_metrics.monthly_budget,
                "current_monthly_cost": self.cost_metrics.current_monthly_cost,
                "total_requests": self.cost_metrics.total_requests,
            },
            "cost_status": self.cost_status,
            "compliance_status": self.compliance_status,
            "total_invocations": self.total_invocations,
            "registration_time": self.registration_time.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }


class AgentGovernanceManager:
    """
    智能体治理管理器
    
    负责统一管理内部和外部智能体，提供SLA、成本、合规管控
    """
    
    def __init__(
        self,
        service_registry,
        task_scheduler,
        trace_writer,
        config: Dict[str, Any] = None
    ):
        """
        初始化治理管理器
        
        Args:
            service_registry: 服务注册中心
            task_scheduler: 任务调度器
            trace_writer: 追踪写入器
            config: 配置信息
        """
        self.service_registry = service_registry
        self.task_scheduler = task_scheduler
        self.trace_writer = trace_writer
        self.config = config or {}
        
        # 治理数据存储
        self.governance_info: Dict[str, AgentGovernanceInfo] = {}
        
        # 全局治理策略
        self.global_sla_policy = SLAMetrics()
        self.global_cost_policy = CostMetrics()
        self.global_compliance_policy = CompliancePolicy()
        
        # 监控任务
        self.monitoring_tasks = []
        
        # 统计信息
        self.governance_stats = {
            "total_agents": 0,
            "internal_agents": 0,
            "external_agents": 0,
            "sla_compliant_agents": 0,
            "cost_alert_agents": 0,
            "compliance_violations": 0,
            "total_governance_cost": 0.0
        }
        
        logger.info("Agent governance manager initialized")
    
    async def initialize(self) -> None:
        """初始化治理管理器"""
        try:
            logger.info("Initializing agent governance manager")
            
            # 启动监控任务
            self.monitoring_tasks = [
                asyncio.create_task(self._sla_monitoring_loop()),
                asyncio.create_task(self._cost_monitoring_loop()),
                asyncio.create_task(self._compliance_monitoring_loop()),
                asyncio.create_task(self._governance_report_loop())
            ]
            
            logger.info("Agent governance manager initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize agent governance manager", error=str(e))
            raise
    
    async def register_agent(
        self,
        agent_id: str,
        agent_name: str,
        agent_type: AgentType,
        sla_config: Dict[str, Any] = None,
        cost_config: Dict[str, Any] = None,
        compliance_config: Dict[str, Any] = None
    ) -> str:
        """
        注册智能体到治理系统
        
        Args:
            agent_id: 智能体ID
            agent_name: 智能体名称
            agent_type: 智能体类型
            sla_config: SLA配置
            cost_config: 成本配置
            compliance_config: 合规配置
            
        Returns:
            治理ID
        """
        governance_id = str(uuid.uuid4())
        
        try:
            logger.info(
                "Registering agent for governance",
                agent_id=agent_id,
                agent_name=agent_name,
                agent_type=agent_type.value
            )
            
            # 创建治理信息
            governance_info = AgentGovernanceInfo(
                agent_id=agent_id,
                agent_name=agent_name,
                agent_type=agent_type
            )
            
            # 配置SLA策略
            if sla_config:
                governance_info.sla_metrics = SLAMetrics(**sla_config)
            
            # 配置成本策略
            if cost_config:
                governance_info.cost_metrics = CostMetrics(**cost_config)
            
            # 配置合规策略
            if compliance_config:
                governance_info.compliance_policy = CompliancePolicy(**compliance_config)
            
            # 存储治理信息
            self.governance_info[governance_id] = governance_info
            
            # 更新统计
            self.governance_stats["total_agents"] += 1
            if agent_type == AgentType.INTERNAL:
                self.governance_stats["internal_agents"] += 1
            else:
                self.governance_stats["external_agents"] += 1
            
            logger.info(
                "Agent registered for governance successfully",
                agent_id=agent_id,
                governance_id=governance_id
            )
            
            return governance_id
            
        except Exception as e:
            logger.error(
                "Failed to register agent for governance",
                agent_id=agent_id,
                error=str(e)
            )
            raise
    
    async def update_agent_metrics(
        self,
        agent_id: str,
        response_time: float,
        success: bool,
        cost: float = 0.0,
        tokens: int = 0
    ) -> None:
        """
        更新智能体指标
        
        Args:
            agent_id: 智能体ID
            response_time: 响应时间
            success: 是否成功
            cost: 成本
            tokens: Token数量
        """
        governance_info = await self._find_governance_info_by_agent_id(agent_id)
        if not governance_info:
            return
        
        try:
            # 更新SLA指标
            await self._update_sla_metrics(governance_info, response_time, success)
            
            # 更新成本指标
            await self._update_cost_metrics(governance_info, cost, tokens)
            
            # 更新活动时间
            governance_info.last_activity = datetime.utcnow()
            governance_info.total_invocations += 1
            
            # 检查SLA状态
            await self._check_sla_compliance(governance_info)
            
            # 检查成本状态
            await self._check_cost_limits(governance_info)
            
        except Exception as e:
            logger.error(
                "Failed to update agent metrics",
                agent_id=agent_id,
                error=str(e)
            )
    
    async def get_agent_governance_status(
        self,
        agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取智能体治理状态
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            治理状态信息
        """
        governance_info = await self._find_governance_info_by_agent_id(agent_id)
        if not governance_info:
            return None
        
        return governance_info.to_dict()
    
    async def get_governance_dashboard(self) -> Dict[str, Any]:
        """
        获取治理仪表板数据
        
        Returns:
            仪表板数据
        """
        dashboard_data = {
            "overview": self.governance_stats.copy(),
            "sla_summary": await self._get_sla_summary(),
            "cost_summary": await self._get_cost_summary(),
            "compliance_summary": await self._get_compliance_summary(),
            "top_cost_agents": await self._get_top_cost_agents(),
            "sla_violations": await self._get_sla_violations(),
            "compliance_violations": await self._get_compliance_violations()
        }
        
        return dashboard_data
    
    async def _find_governance_info_by_agent_id(
        self,
        agent_id: str
    ) -> Optional[AgentGovernanceInfo]:
        """根据智能体ID查找治理信息"""
        for governance_info in self.governance_info.values():
            if governance_info.agent_id == agent_id:
                return governance_info
        return None
    
    async def _update_sla_metrics(
        self,
        governance_info: AgentGovernanceInfo,
        response_time: float,
        success: bool
    ) -> None:
        """更新SLA指标"""
        sla = governance_info.sla_metrics
        
        # 更新响应时间（移动平均）
        if sla.current_response_time == 0:
            sla.current_response_time = response_time
        else:
            sla.current_response_time = (sla.current_response_time * 0.9 + response_time * 0.1)
        
        # 更新错误率（需要维护窗口内的统计）
        # 这里简化为基于成功率的计算
        if success:
            sla.current_error_rate = max(0, sla.current_error_rate - 0.1)
        else:
            sla.current_error_rate = min(100, sla.current_error_rate + 1.0)
        
        sla.last_updated = datetime.utcnow()
    
    async def _update_cost_metrics(
        self,
        governance_info: AgentGovernanceInfo,
        cost: float,
        tokens: int
    ) -> None:
        """更新成本指标"""
        cost_metrics = governance_info.cost_metrics
        
        # 更新请求计数和成本
        cost_metrics.total_requests += 1
        cost_metrics.total_tokens += tokens
        cost_metrics.current_daily_cost += cost
        cost_metrics.current_monthly_cost += cost
        
        # 更新统计
        cost_metrics.last_updated = datetime.utcnow()
        
        # 更新全局成本统计
        self.governance_stats["total_governance_cost"] += cost
    
    async def _check_sla_compliance(
        self,
        governance_info: AgentGovernanceInfo
    ) -> None:
        """检查SLA合规性"""
        sla = governance_info.sla_metrics
        
        # 检查响应时间
        response_time_ok = sla.current_response_time <= sla.response_time_target
        
        # 检查错误率
        error_rate_ok = sla.current_error_rate <= sla.error_rate_target
        
        # 确定SLA状态
        if response_time_ok and error_rate_ok:
            governance_info.sla_status = SLAStatus.HEALTHY
        elif sla.current_response_time > sla.response_time_target * 1.5 or sla.current_error_rate > sla.error_rate_target * 2:
            governance_info.sla_status = SLAStatus.CRITICAL
        else:
            governance_info.sla_status = SLAStatus.WARNING
    
    async def _check_cost_limits(
        self,
        governance_info: AgentGovernanceInfo
    ) -> None:
        """检查成本限制"""
        cost = governance_info.cost_metrics
        
        # 计算预算使用率
        budget_usage = (cost.current_monthly_cost / cost.monthly_budget) * 100
        
        if budget_usage >= cost.budget_limit_threshold:
            governance_info.cost_status = "limit_exceeded"
            # 可以在这里实施成本控制措施，如暂停服务
        elif budget_usage >= cost.budget_alert_threshold:
            governance_info.cost_status = "alert"
        else:
            governance_info.cost_status = "normal"
    
    async def _sla_monitoring_loop(self) -> None:
        """SLA监控循环"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                # 更新SLA统计
                sla_compliant_count = 0
                for governance_info in self.governance_info.values():
                    if governance_info.sla_status == SLAStatus.HEALTHY:
                        sla_compliant_count += 1
                
                self.governance_stats["sla_compliant_agents"] = sla_compliant_count
                
            except Exception as e:
                logger.error("Error in SLA monitoring loop", error=str(e))
    
    async def _cost_monitoring_loop(self) -> None:
        """成本监控循环"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟检查一次
                
                # 重置每日成本（在午夜）
                now = datetime.utcnow()
                if now.hour == 0 and now.minute < 5:
                    for governance_info in self.governance_info.values():
                        governance_info.cost_metrics.current_daily_cost = 0.0
                
                # 重置每月成本（在月初）
                if now.day == 1 and now.hour == 0 and now.minute < 5:
                    for governance_info in self.governance_info.values():
                        governance_info.cost_metrics.current_monthly_cost = 0.0
                
                # 更新成本告警统计
                cost_alert_count = 0
                for governance_info in self.governance_info.values():
                    if governance_info.cost_status in ["alert", "limit_exceeded"]:
                        cost_alert_count += 1
                
                self.governance_stats["cost_alert_agents"] = cost_alert_count
                
            except Exception as e:
                logger.error("Error in cost monitoring loop", error=str(e))
    
    async def _compliance_monitoring_loop(self) -> None:
        """合规监控循环"""
        while True:
            try:
                await asyncio.sleep(3600)  # 每小时检查一次
                
                # 检查合规违规
                violation_count = 0
                for governance_info in self.governance_info.values():
                    violations = len(governance_info.compliance_policy.compliance_violations)
                    violation_count += violations
                
                self.governance_stats["compliance_violations"] = violation_count
                
            except Exception as e:
                logger.error("Error in compliance monitoring loop", error=str(e))
    
    async def _governance_report_loop(self) -> None:
        """治理报告循环"""
        while True:
            try:
                await asyncio.sleep(86400)  # 每天生成一次报告
                
                # 生成每日治理报告
                await self._generate_daily_governance_report()
                
            except Exception as e:
                logger.error("Error in governance report loop", error=str(e))
    
    async def _get_sla_summary(self) -> Dict[str, Any]:
        """获取SLA摘要"""
        healthy_count = 0
        warning_count = 0
        critical_count = 0
        
        for governance_info in self.governance_info.values():
            if governance_info.sla_status == SLAStatus.HEALTHY:
                healthy_count += 1
            elif governance_info.sla_status == SLAStatus.WARNING:
                warning_count += 1
            elif governance_info.sla_status == SLAStatus.CRITICAL:
                critical_count += 1
        
        return {
            "healthy": healthy_count,
            "warning": warning_count,
            "critical": critical_count,
            "total": len(self.governance_info)
        }
    
    async def _get_cost_summary(self) -> Dict[str, Any]:
        """获取成本摘要"""
        total_cost = 0.0
        total_budget = 0.0
        alert_count = 0
        
        for governance_info in self.governance_info.values():
            cost = governance_info.cost_metrics
            total_cost += cost.current_monthly_cost
            total_budget += cost.monthly_budget
            
            if governance_info.cost_status in ["alert", "limit_exceeded"]:
                alert_count += 1
        
        return {
            "total_cost": total_cost,
            "total_budget": total_budget,
            "budget_usage": (total_cost / total_budget * 100) if total_budget > 0 else 0,
            "alert_count": alert_count
        }
    
    async def _get_compliance_summary(self) -> Dict[str, Any]:
        """获取合规摘要"""
        compliant_count = 0
        violation_count = 0
        
        for governance_info in self.governance_info.values():
            if governance_info.compliance_status == "compliant":
                compliant_count += 1
            else:
                violation_count += 1
        
        return {
            "compliant": compliant_count,
            "violations": violation_count,
            "compliance_rate": (compliant_count / len(self.governance_info) * 100) if self.governance_info else 100
        }
    
    async def _get_top_cost_agents(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取成本最高的智能体"""
        agents = []
        for governance_info in self.governance_info.values():
            agents.append({
                "agent_id": governance_info.agent_id,
                "agent_name": governance_info.agent_name,
                "monthly_cost": governance_info.cost_metrics.current_monthly_cost,
                "budget_usage": (governance_info.cost_metrics.current_monthly_cost / 
                               governance_info.cost_metrics.monthly_budget * 100)
            })
        
        # 按成本排序
        agents.sort(key=lambda x: x["monthly_cost"], reverse=True)
        return agents[:limit]
    
    async def _get_sla_violations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取SLA违规记录"""
        # 这里应该从trace_writer中查询SLA违规记录
        # 简化实现，返回当前状态不健康的智能体
        violations = []
        for governance_info in self.governance_info.values():
            if governance_info.sla_status != SLAStatus.HEALTHY:
                violations.append({
                    "agent_id": governance_info.agent_id,
                    "agent_name": governance_info.agent_name,
                    "sla_status": governance_info.sla_status.value,
                    "response_time": governance_info.sla_metrics.current_response_time,
                    "error_rate": governance_info.sla_metrics.current_error_rate
                })
        
        return violations[:limit]
    
    async def _get_compliance_violations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取合规违规记录"""
        violations = []
        for governance_info in self.governance_info.values():
            for violation in governance_info.compliance_policy.compliance_violations:
                violations.append({
                    "agent_id": governance_info.agent_id,
                    "agent_name": governance_info.agent_name,
                    "violation_type": violation.get("type", "unknown"),
                    "description": violation.get("description", ""),
                    "timestamp": violation.get("timestamp", "")
                })
        
        # 按时间排序
        violations.sort(key=lambda x: x["timestamp"], reverse=True)
        return violations[:limit]
    
    async def _generate_daily_governance_report(self) -> None:
        """生成每日治理报告"""
        try:
            report_data = await self.get_governance_dashboard()
            
            logger.info("Daily governance report generated", report_data=report_data)
            
        except Exception as e:
            logger.error("Failed to generate daily governance report", error=str(e)) 