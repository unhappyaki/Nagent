"""
工作流生成Agent - 简化版

基于自然语言理解，自动生成工作流定义。
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from communication.adapters.base_adapter import WorkflowDefinition, WorkflowEngineType


@dataclass
class LLMConfig:
    """LLM配置"""
    model_name: str
    api_key: str
    base_url: Optional[str] = None


@dataclass
class GeneratedWorkflow:
    """生成的工作流"""
    workflow_definition: WorkflowDefinition
    confidence: float
    reasoning: str


class WorkflowGenerationAgent:
    """工作流生成Agent"""
    
    def __init__(self, llm_config: LLMConfig):
        self.llm_config = llm_config
    
    async def generate_workflow(self, natural_language_request: str) -> GeneratedWorkflow:
        """从自然语言请求生成工作流"""
        # 简单的关键词分析
        analysis = self._analyze_request(natural_language_request)
        
        # 生成工作流定义
        workflow_definition = self._generate_workflow_definition(analysis)
        
        return GeneratedWorkflow(
            workflow_definition=workflow_definition,
            confidence=0.8,
            reasoning=f"基于关键词'{analysis['type']}'生成"
        )
    
    def _analyze_request(self, request: str) -> Dict[str, Any]:
        """分析自然语言请求"""
        request_lower = request.lower()
        
        if "数据" in request or "database" in request_lower:
            return {"type": "data_processing"}
        elif "邮件" in request or "email" in request_lower:
            return {"type": "email_automation"}
        else:
            return {"type": "general"}
    
    def _generate_workflow_definition(self, analysis: Dict[str, Any]) -> WorkflowDefinition:
        """生成工作流定义"""
        return WorkflowDefinition(
            id=str(uuid.uuid4()),
            name=f"Generated {analysis['type']} Workflow",
            description="自动生成的工作流",
            definition={"nodes": [], "connections": {}},
            engine_type=WorkflowEngineType.N8N,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        ) 