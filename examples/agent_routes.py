"""
Agent API路由

实现用户指令到BIR路由器的完整流程：
1. 接收用户指令
2. 解析和验证
3. 路由到BIR
4. 返回结果
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
import asyncio
import uuid
from datetime import datetime

from ..src.communication.dispatcher.bir_router import BIRRouter, BehaviorPackage
from ..src.communication.acp.acp_client import ACPClient
from ..src.monitoring.tracing import TraceWriter
from ..src.state.context import Context
from ..src.core.agent import AgentMessage

router = APIRouter()


class UserInstruction(BaseModel):
    """用户指令模型"""
    instruction: str
    user_id: str
    session_id: Optional[str] = None
    priority: int = 0
    timeout: Optional[int] = None
    metadata: Dict[str, Any] = {}


class InstructionResponse(BaseModel):
    """指令响应模型"""
    request_id: str
    trace_id: str
    status: str
    message: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}


class InstructionProcessor:
    """指令处理器"""
    
    def __init__(self):
        self.bir_router = BIRRouter()
        self.acp_client = ACPClient()
        self.trace_writer = TraceWriter()
        self.context_manager = {}
    
    async def process_instruction(self, instruction: UserInstruction) -> InstructionResponse:
        """
        处理用户指令的完整流程
        
        Args:
            instruction: 用户指令
            
        Returns:
            InstructionResponse: 处理结果
        """
        request_id = str(uuid.uuid4())
        trace_id = f"trace-{request_id[:8]}"
        
        try:
            # 1. 初始化追踪
            await self._init_trace(request_id, trace_id, instruction)
            
            # 2. 创建或获取上下文
            context_id = await self._get_or_create_context(instruction)
            
            # 3. 解析指令意图
            intent_analysis = await self._analyze_intent(instruction.instruction)
            
            # 4. 确定目标Agent
            target_agent = await self._determine_target_agent(intent_analysis)
            
            # 5. 构建行为包
            behavior_package = await self._build_behavior_package(
                instruction, intent_analysis, target_agent, context_id, trace_id
            )
            
            # 6. 通过BIR路由器分发
            routing_result = await self._route_behavior(behavior_package)
            
            # 7. 记录结果
            await self._record_result(request_id, trace_id, routing_result)
            
            return InstructionResponse(
                request_id=request_id,
                trace_id=trace_id,
                status="success",
                message="指令处理成功",
                timestamp=datetime.utcnow(),
                metadata={
                    "intent_type": intent_analysis.get("intent_type"),
                    "target_agent": target_agent,
                    "routing_result": routing_result
                }
            )
            
        except Exception as e:
            # 错误处理
            await self._handle_error(request_id, trace_id, str(e))
            
            return InstructionResponse(
                request_id=request_id,
                trace_id=trace_id,
                status="error",
                message=f"指令处理失败: {str(e)}",
                timestamp=datetime.utcnow(),
                metadata={"error": str(e)}
            )
    
    async def _init_trace(self, request_id: str, trace_id: str, instruction: UserInstruction):
        """初始化追踪"""
        await self.trace_writer.record_trace(
            trace_id=trace_id,
            context_id=instruction.session_id or "default",
            intent=instruction.instruction,
            from_agent="user",
            to_agent="system",
            intent_type="user_instruction"
        )
    
    async def _get_or_create_context(self, instruction: UserInstruction) -> str:
        """获取或创建上下文"""
        session_id = instruction.session_id or f"session-{instruction.user_id}"
        
        if session_id not in self.context_manager:
            context = Context(agent_id=f"user_{instruction.user_id}")
            await context.initialize()
            await context.set_session_id(session_id)
            self.context_manager[session_id] = context
        
        return session_id
    
    async def _analyze_intent(self, instruction: str) -> Dict[str, Any]:
        """分析指令意图"""
        # 简单的意图分析逻辑
        intent_type = "task_execution"
        
        if any(word in instruction for word in ["查询", "搜索", "获取", "查找"]):
            intent_type = "data_query"
        elif any(word in instruction for word in ["调用", "使用", "执行", "运行"]):
            intent_type = "tool_call"
        elif any(word in instruction for word in ["更新", "修改", "调整", "变更"]):
            intent_type = "status_update"
        elif any(word in instruction for word in ["协作", "合作", "协助", "帮助"]):
            intent_type = "collaboration"
        
        return {
            "intent_type": intent_type,
            "confidence": 0.8,
            "keywords": self._extract_keywords(instruction)
        }
    
    def _extract_keywords(self, instruction: str) -> list:
        """提取关键词"""
        # 简单的关键词提取
        keywords = []
        for word in instruction.split():
            if len(word) > 1:
                keywords.append(word)
        return keywords
    
    async def _determine_target_agent(self, intent_analysis: Dict[str, Any]) -> str:
        """确定目标Agent"""
        intent_type = intent_analysis.get("intent_type", "task_execution")
        
        # 根据意图类型选择Agent
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
        instruction: UserInstruction,
        intent_analysis: Dict[str, Any],
        target_agent: str,
        context_id: str,
        trace_id: str
    ) -> BehaviorPackage:
        """构建行为包"""
        return self.bir_router.dispatch(
            intent=instruction.instruction,
            from_agent=f"user_{instruction.user_id}",
            to_agent=target_agent,
            context_id=context_id,
            payload={
                "instruction": instruction.instruction,
                "user_id": instruction.user_id,
                "intent_analysis": intent_analysis,
                "priority": instruction.priority,
                "metadata": instruction.metadata
            },
            priority=instruction.priority
        )
    
    async def _route_behavior(self, behavior_package: BehaviorPackage) -> str:
        """路由行为"""
        return self.bir_router.route_behavior(behavior_package)
    
    async def _record_result(self, request_id: str, trace_id: str, result: str):
        """记录结果"""
        await self.trace_writer.record_trace(
            trace_id=trace_id,
            context_id="system",
            intent=f"Request {request_id} completed",
            from_agent="system",
            to_agent="user",
            intent_type="result_record",
            metadata={"result": result}
        )
    
    async def _handle_error(self, request_id: str, trace_id: str, error: str):
        """处理错误"""
        await self.trace_writer.record_trace(
            trace_id=trace_id,
            context_id="system",
            intent=f"Request {request_id} failed",
            from_agent="system",
            to_agent="user",
            intent_type="error_handling",
            metadata={"error": error}
        )


# 全局指令处理器
instruction_processor = InstructionProcessor()


@router.post("/process-instruction", response_model=InstructionResponse)
async def process_user_instruction(
    instruction: UserInstruction,
    background_tasks: BackgroundTasks
):
    """
    处理用户指令
    
    完整的用户指令处理流程：
    1. 接收用户指令
    2. 解析和验证
    3. 路由到BIR
    4. 返回结果
    """
    try:
        # 异步处理指令
        response = await instruction_processor.process_instruction(instruction)
        
        # 添加后台任务（可选）
        background_tasks.add_task(
            _background_processing,
            instruction,
            response.trace_id
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instruction-status/{request_id}")
async def get_instruction_status(request_id: str):
    """获取指令处理状态"""
    try:
        # 这里应该从存储中获取状态
        # 暂时返回模拟数据
        return {
            "request_id": request_id,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail="Request not found")


async def _background_processing(instruction: UserInstruction, trace_id: str):
    """后台处理任务"""
    # 这里可以添加额外的后台处理逻辑
    # 比如日志记录、统计分析等
    pass 