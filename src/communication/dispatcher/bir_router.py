"""
BIR (Agent-to-Agent) 消息调度路由器
实现行为分发的起点，负责将输入意图解析成可被系统接收、执行、追踪的行为指令包
"""

import time
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class IntentType(Enum):
    """行为意图类型枚举"""
    TASK_EXECUTION = "task_execution"  # 任务执行
    DATA_QUERY = "data_query"         # 数据查询
    TOOL_CALL = "tool_call"           # 工具调用
    STATUS_UPDATE = "status_update"   # 状态更新
    COLLABORATION = "collaboration"   # 协作请求


@dataclass
class BehaviorPackage:
    """行为指令包结构"""
    intent: str                    # 行为意图
    from_agent: str               # 发起方智能体ID
    to_agent: str                 # 目标智能体ID
    context_id: str               # 上下文ID
    trace_id: str                 # 追踪ID
    timestamp: int                # 时间戳
    payload: Dict[str, Any]       # 载荷数据
    intent_type: IntentType       # 意图类型
    priority: int = 0             # 优先级
    timeout: Optional[int] = None # 超时时间


class BIRRouter:
    """
    BIR消息调度路由器
    负责将用户输入意图解析成标准化的行为指令包
    """
    
    def __init__(self, acp_client=None, trace_writer=None):
        """
        初始化BIR路由器
        
        Args:
            acp_client: ACP客户端实例
            trace_writer: 追踪写入器实例
        """
        self.acp_client = acp_client
        self.trace_writer = trace_writer
        self._intent_patterns = self._init_intent_patterns()
    
    def _init_intent_patterns(self) -> Dict[str, IntentType]:
        """初始化意图模式匹配规则"""
        return {
            r"生成|创建|制作|编写": IntentType.TASK_EXECUTION,
            r"查询|搜索|获取|查找": IntentType.DATA_QUERY,
            r"调用|使用|执行|运行": IntentType.TOOL_CALL,
            r"更新|修改|调整|变更": IntentType.STATUS_UPDATE,
            r"协作|合作|协助|帮助": IntentType.COLLABORATION
        }
    
    def dispatch(self, 
                 intent: str, 
                 from_agent: str, 
                 to_agent: str, 
                 context_id: str, 
                 payload: Dict[str, Any],
                 priority: int = 0) -> BehaviorPackage:
        """
        分发行为指令
        
        Args:
            intent: 行为意图描述
            from_agent: 发起方智能体ID
            to_agent: 目标智能体ID
            context_id: 上下文ID
            payload: 载荷数据
            priority: 优先级
            
        Returns:
            BehaviorPackage: 行为指令包
        """
        # 生成追踪ID
        trace_id = self._generate_trace_id(intent, context_id)
        
        # 解析意图类型
        intent_type = self._parse_intent_type(intent)
        
        # 构建行为包
        behavior_package = BehaviorPackage(
            intent=intent,
            from_agent=from_agent,
            to_agent=to_agent,
            context_id=context_id,
            trace_id=trace_id,
            timestamp=int(time.time()),
            payload=payload,
            intent_type=intent_type,
            priority=priority
        )
        
        # 记录追踪信息
        if self.trace_writer:
            self.trace_writer.record_behavior_trace(
                trace_id=trace_id,
                context_id=context_id,
                intent=intent,
                from_agent=from_agent,
                to_agent=to_agent,
                intent_type=intent_type.value
            )
        
        # 发送到ACP客户端
        if self.acp_client:
            self.acp_client.send_behavior_package(behavior_package)
        
        return behavior_package
    
    def _generate_trace_id(self, intent: str, context_id: str) -> str:
        """生成追踪ID"""
        # 使用意图和上下文ID生成唯一追踪ID
        unique_id = str(uuid.uuid4())[:8]
        return f"trace-{context_id}-{unique_id}"
    
    def _parse_intent_type(self, intent: str) -> IntentType:
        """解析意图类型"""
        import re
        
        for pattern, intent_type in self._intent_patterns.items():
            if re.search(pattern, intent):
                return intent_type
        
        # 默认返回任务执行类型
        return IntentType.TASK_EXECUTION
    
    def route_behavior(self, behavior_package: BehaviorPackage) -> str:
        """
        路由行为到目标智能体
        
        Args:
            behavior_package: 行为指令包
            
        Returns:
            str: 路由结果
        """
        # 这里可以实现更复杂的路由逻辑
        # 比如基于负载均衡、智能体能力匹配等
        
        return f"routed_to_{behavior_package.to_agent}"
    
    def validate_behavior_package(self, package: BehaviorPackage) -> bool:
        """
        验证行为指令包的有效性
        
        Args:
            package: 行为指令包
            
        Returns:
            bool: 是否有效
        """
        required_fields = ['intent', 'from_agent', 'to_agent', 'context_id', 'trace_id']
        
        for field in required_fields:
            if not hasattr(package, field) or not getattr(package, field):
                return False
        
        return True


class BehaviorDispatcher:
    """
    行为分发器
    负责管理和调度多个BIR路由器
    """
    
    def __init__(self):
        self.routers = {}
        self.behavior_queue = []
    
    def register_router(self, name: str, router: BIRRouter):
        """注册路由器"""
        self.routers[name] = router
    
    def dispatch_behavior(self, 
                         router_name: str,
                         intent: str,
                         from_agent: str,
                         to_agent: str,
                         context_id: str,
                         payload: Dict[str, Any]) -> Optional[BehaviorPackage]:
        """
        通过指定路由器分发行为
        
        Args:
            router_name: 路由器名称
            intent: 行为意图
            from_agent: 发起方智能体
            to_agent: 目标智能体
            context_id: 上下文ID
            payload: 载荷数据
            
        Returns:
            Optional[BehaviorPackage]: 行为指令包
        """
        if router_name not in self.routers:
            raise ValueError(f"Router {router_name} not found")
        
        router = self.routers[router_name]
        return router.dispatch(intent, from_agent, to_agent, context_id, payload)
    
    def get_behavior_history(self, context_id: str) -> list:
        """获取行为历史"""
        return [pkg for pkg in self.behavior_queue if pkg.context_id == context_id] 