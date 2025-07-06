"""
工作流生成功能单元测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from src.workflow.generation.workflow_generation_agent import (
    WorkflowGenerationAgent,
    LLMConfig,
    GeneratedWorkflow
)
from src.workflow.adapters.base_adapter import WorkflowEngineType


class TestWorkflowGenerationAgent:
    """工作流生成Agent测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.llm_config = LLMConfig(
            model_name="gpt-3.5-turbo",
            api_key="test_key"
        )
        self.agent = WorkflowGenerationAgent(self.llm_config)
    
    @pytest.mark.asyncio
    async def test_generate_workflow_data_processing(self):
        """测试数据预处理工作流生成"""
        request = "创建一个数据处理工作流，从数据库读取数据并处理"
        
        result = await self.agent.generate_workflow(request)
        
        assert isinstance(result, GeneratedWorkflow)
        assert result.workflow_definition.engine_type == WorkflowEngineType.N8N
        assert "data_processing" in result.workflow_definition.name
        assert result.confidence > 0
    
    @pytest.mark.asyncio
    async def test_generate_workflow_email_automation(self):
        """测试邮件自动化工作流生成"""
        request = "创建一个邮件自动化工作流，每天发送报告邮件"
        
        result = await self.agent.generate_workflow(request)
        
        assert isinstance(result, GeneratedWorkflow)
        assert result.workflow_definition.engine_type == WorkflowEngineType.N8N
        assert "email_automation" in result.workflow_definition.name
        assert result.confidence > 0
    
    @pytest.mark.asyncio
    async def test_generate_workflow_general(self):
        """测试通用工作流生成"""
        request = "创建一个通用工作流"
        
        result = await self.agent.generate_workflow(request)
        
        assert isinstance(result, GeneratedWorkflow)
        assert result.workflow_definition.engine_type == WorkflowEngineType.N8N
        assert "general" in result.workflow_definition.name
        assert result.confidence > 0
    
    def test_analyze_request_data_processing(self):
        """测试数据预处理请求分析"""
        request = "从数据库读取数据并处理"
        analysis = self.agent._analyze_request(request)
        
        assert analysis["type"] == "data_processing"
    
    def test_analyze_request_email_automation(self):
        """测试邮件自动化请求分析"""
        request = "发送邮件报告"
        analysis = self.agent._analyze_request(request)
        
        assert analysis["type"] == "email_automation"
    
    def test_analyze_request_general(self):
        """测试通用请求分析"""
        request = "创建一个工作流"
        analysis = self.agent._analyze_request(request)
        
        assert analysis["type"] == "general"
    
    def test_generate_workflow_definition(self):
        """测试工作流定义生成"""
        analysis = {"type": "data_processing"}
        workflow_def = self.agent._generate_workflow_definition(analysis)
        
        assert workflow_def.engine_type == WorkflowEngineType.N8N
        assert "data_processing" in workflow_def.name
        assert workflow_def.definition is not None


class TestLLMConfig:
    """LLM配置测试类"""
    
    def test_llm_config_creation(self):
        """测试LLM配置创建"""
        config = LLMConfig(
            model_name="gpt-3.5-turbo",
            api_key="test_key",
            base_url="https://api.openai.com"
        )
        
        assert config.model_name == "gpt-3.5-turbo"
        assert config.api_key == "test_key"
        assert config.base_url == "https://api.openai.com"
    
    def test_llm_config_defaults(self):
        """测试LLM配置默认值"""
        config = LLMConfig(
            model_name="gpt-3.5-turbo",
            api_key="test_key"
        )
        
        assert config.base_url is None


class TestGeneratedWorkflow:
    """生成工作流测试类"""
    
    def test_generated_workflow_creation(self):
        """测试生成工作流创建"""
        from src.workflow.adapters.base_adapter import WorkflowDefinition
        
        workflow_def = WorkflowDefinition(
            id="test-id",
            name="Test Workflow",
            description="Test Description",
            definition={},
            engine_type=WorkflowEngineType.N8N,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00"
        )
        
        generated = GeneratedWorkflow(
            workflow_definition=workflow_def,
            confidence=0.8,
            reasoning="Test reasoning"
        )
        
        assert generated.workflow_definition == workflow_def
        assert generated.confidence == 0.8
        assert generated.reasoning == "Test reasoning" 