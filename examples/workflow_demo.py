"""
工作流功能演示示例

展示如何使用工作流生成Agent创建和执行工作流。
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import asyncio
import json
from typing import Dict, Any

from src.core.reasoning.workflow_generation_agent import (
    WorkflowGenerationAgent,
    LLMConfig
)
from src.communication.adapters.base_adapter import WorkflowEngineType


async def demo_workflow_generation():
    """演示工作流生成功能"""
    print("=== 工作流生成演示 ===\n")
    
    # 创建LLM配置
    llm_config = LLMConfig(
        model_name="gpt-3.5-turbo",
        api_key="your_api_key_here"  # 请替换为实际的API密钥
    )
    
    # 创建工作流生成Agent
    agent = WorkflowGenerationAgent(llm_config)
    
    # 示例请求列表
    requests = [
        "创建一个数据处理工作流，从数据库读取用户数据，进行数据清洗，然后生成报告",
        "创建一个邮件自动化工作流，每天从CRM系统获取销售数据，生成销售报告并发送给管理层",
        "创建一个文件处理工作流，监控指定文件夹，当有新文件时自动上传到云存储并发送通知",
        "创建一个API集成工作流，从多个外部API获取数据，合并处理后存储到数据库"
    ]
    
    for i, request in enumerate(requests, 1):
        print(f"请求 {i}: {request}")
        print("-" * 50)
        
        try:
            # 生成工作流
            result = await agent.generate_workflow(request)
            
            print(f"生成的工作流:")
            print(f"  - ID: {result.workflow_definition.id}")
            print(f"  - 名称: {result.workflow_definition.name}")
            print(f"  - 描述: {result.workflow_definition.description}")
            print(f"  - 引擎类型: {result.workflow_definition.engine_type.value}")
            print(f"  - 置信度: {result.confidence:.2f}")
            print(f"  - 推理过程: {result.reasoning}")
            print()
            
        except Exception as e:
            print(f"生成失败: {e}")
            print()


async def demo_workflow_analysis():
    """演示工作流分析功能"""
    print("=== 工作流分析演示 ===\n")
    
    # 创建LLM配置
    llm_config = LLMConfig(
        model_name="gpt-3.5-turbo",
        api_key="your_api_key_here"
    )
    
    # 创建工作流生成Agent
    agent = WorkflowGenerationAgent(llm_config)
    
    # 测试不同类型的请求分析
    test_requests = [
        ("数据处理", "从数据库读取数据并处理"),
        ("邮件自动化", "发送邮件报告"),
        ("文件处理", "处理上传的文件"),
        ("API集成", "调用外部API"),
        ("通用工作流", "创建一个工作流")
    ]
    
    for request_type, request in test_requests:
        print(f"请求类型: {request_type}")
        print(f"请求内容: {request}")
        
        # 分析请求
        analysis = agent._analyze_request(request)
        print(f"分析结果: {analysis}")
        print("-" * 30)


async def demo_workflow_definition_generation():
    """演示工作流定义生成功能"""
    print("=== 工作流定义生成演示 ===\n")
    
    # 创建LLM配置
    llm_config = LLMConfig(
        model_name="gpt-3.5-turbo",
        api_key="your_api_key_here"
    )
    
    # 创建工作流生成Agent
    agent = WorkflowGenerationAgent(llm_config)
    
    # 测试不同类型的工作流定义生成
    test_analyses = [
        {"type": "data_processing"},
        {"type": "email_automation"},
        {"type": "file_processing"},
        {"type": "api_integration"},
        {"type": "general"}
    ]
    
    for analysis in test_analyses:
        print(f"分析类型: {analysis['type']}")
        
        # 生成工作流定义
        workflow_def = agent._generate_workflow_definition(analysis)
        
        print(f"生成的工作流定义:")
        print(f"  - ID: {workflow_def.id}")
        print(f"  - 名称: {workflow_def.name}")
        print(f"  - 描述: {workflow_def.description}")
        print(f"  - 引擎类型: {workflow_def.engine_type.value}")
        print(f"  - 创建时间: {workflow_def.created_at}")
        print(f"  - 更新时间: {workflow_def.updated_at}")
        print(f"  - 定义结构: {list(workflow_def.definition.keys())}")
        print("-" * 40)


def print_workflow_engine_types():
    """打印支持的工作流引擎类型"""
    print("=== 支持的工作流引擎类型 ===\n")
    
    for engine_type in WorkflowEngineType:
        print(f"  - {engine_type.value}: {engine_type.name}")
    
    print()


async def main():
    """主函数"""
    print("企业级Agent系统 - 工作流功能演示")
    print("=" * 50)
    print()
    
    # 打印支持的工作流引擎类型
    print_workflow_engine_types()
    
    # 演示工作流分析
    await demo_workflow_analysis()
    
    # 演示工作流定义生成
    await demo_workflow_definition_generation()
    
    # 演示完整的工作流生成
    await demo_workflow_generation()
    
    print("演示完成！")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main()) 