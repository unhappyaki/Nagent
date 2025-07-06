# MCP外部服务调度集成方案

## 方案概述

本方案设计了将外部服务调度能力以MCP（Model Context Protocol）服务的形式集成到现有Nagent系统架构中的完整解决方案。通过MCP协议，我们可以将外部服务调度器作为标准化的工具集提供给系统的各个组件使用。

## 设计理念

### 1. 核心优势

**标准化接口**：
- 所有外部服务调度功能通过MCP协议标准化暴露
- 统一的工具调用接口，简化集成复杂度
- 支持动态工具发现和热插拔

**解耦架构**：
- 外部服务调度器作为独立的MCP服务运行
- 与主系统通过MCP协议松耦合
- 可以独立部署、扩展和维护

**生态兼容**：
- 完全兼容MCP协议标准
- 可以与其他MCP工具和服务无缝集成
- 支持现有MCP生态系统的工具

### 2. 架构设计

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Nagent Core System 核心系统                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Reasoning       │  │ Workflow        │  │ Knowledge       │  │ Chat Interface  │ │
│  │ Engine          │  │ Engine          │  │ Manager         │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼ MCP Protocol
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        MCP Interface Layer MCP接口层                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ MCP Client      │  │ Connection      │  │ Tool Registry   │  │ Protocol        │ │
│  │                 │  │ Manager         │  │                 │  │ Handler         │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼ JSON-RPC 2.0
┌─────────────────────────────────────────────────────────────────────────────────┐
│                 External Service Scheduler MCP Server                           │
│                           外部服务调度MCP服务器                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ MCP Server      │  │ Tool Dispatcher │  │ Service         │  │ Policy          │ │
│  │ Runtime         │  │                 │  │ Discovery       │  │ Engine          │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Load Balancer   │  │ Circuit         │  │ Health          │  │ Metrics         │ │
│  │                 │  │ Breaker         │  │ Monitor         │  │ Collector       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼ HTTP/API Calls
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          External Services 外部服务                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ OpenAI/Claude   │  │ Unstructured    │  │ GraphRAG        │  │ Vector DB       │ │
│  │ LLM APIs        │  │ Document API    │  │ Knowledge API   │  │ Chroma/Pinecone │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 核心MCP工具设计

### 1. LLM服务调度工具

```json
{
  "name": "call_llm_service",
  "description": "调用LLM服务，支持智能路由和负载均衡",
  "inputSchema": {
    "type": "object",
    "properties": {
      "model": {
        "type": "string",
        "description": "模型名称，如gpt-4, claude-3-sonnet"
      },
      "messages": {
        "type": "array",
        "description": "对话消息列表"
      },
      "strategy": {
        "type": "string",
        "enum": ["cost_optimized", "latency_optimized", "intelligent"],
        "default": "intelligent"
      },
      "priority": {
        "type": "integer",
        "description": "请求优先级(1-10)",
        "default": 5
      }
    },
    "required": ["model", "messages"]
  }
}
```

### 2. 文档解析工具

```json
{
  "name": "parse_document",
  "description": "解析文档内容，支持多种格式",
  "inputSchema": {
    "type": "object",
    "properties": {
      "file_path": {"type": "string"},
      "file_content": {"type": "string", "description": "base64编码"},
      "filename": {"type": "string"},
      "strategy": {
        "type": "string",
        "enum": ["fast", "hi_res", "ocr_only"],
        "default": "hi_res"
      },
      "extract_tables": {"type": "boolean", "default": true},
      "extract_images": {"type": "boolean", "default": true}
    }
  }
}
```

### 3. 知识图谱构建工具

```json
{
  "name": "build_knowledge_graph",
  "description": "构建知识图谱",
  "inputSchema": {
    "type": "object",
    "properties": {
      "documents": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "title": {"type": "string"},
            "content": {"type": "string"},
            "metadata": {"type": "object"}
          }
        }
      },
      "config": {
        "type": "object",
        "properties": {
          "chunk_size": {"type": "integer", "default": 300},
          "community_algorithm": {"type": "string", "default": "leiden"}
        }
      }
    },
    "required": ["documents"]
  }
}
```

### 4. 向量搜索工具

```json
{
  "name": "vector_search",
  "description": "向量相似性搜索",
  "inputSchema": {
    "type": "object",
    "properties": {
      "collection_name": {"type": "string"},
      "query": {"type": "string"},
      "query_embedding": {"type": "array"},
      "top_k": {"type": "integer", "default": 10},
      "filters": {"type": "object"}
    },
    "required": ["collection_name"]
  }
}
```

### 5. 服务管理工具

```json
{
  "name": "list_external_services",
  "description": "列出所有外部服务及其状态",
  "inputSchema": {
    "type": "object",
    "properties": {
      "service_type": {
        "type": "string",
        "enum": ["llm", "document", "knowledge_graph", "vector_db", "all"],
        "default": "all"
      },
      "include_metrics": {"type": "boolean", "default": true}
    }
  }
}
```

## 使用示例

### 1. 基础使用示例

```python
# examples/mcp_external_service_demo.py
import asyncio
from src.communication.protocols.mcp.adapters.external_service_mcp_client import ExternalServiceMCPClient

async def main():
    """MCP外部服务集成演示"""
    
    client = ExternalServiceMCPClient()
    
    try:
        await client.start()
        print("🚀 MCP外部服务调度器已启动")
        
        # 调用LLM服务
        llm_response = await client.call_llm_service(
            model="gpt-4",
            messages=[{"role": "user", "content": "解释MCP协议"}],
            strategy="cost_optimized"
        )
        print(f"LLM响应: {llm_response['response']}")
        
        # 解析文档
        doc_result = await client.parse_document(
            file_path="example.pdf",
            strategy="hi_res"
        )
        print(f"文档解析完成: {doc_result['metadata']}")
        
        # 向量搜索
        search_result = await client.vector_search(
            collection_name="documents",
            query="MCP协议优势",
            top_k=5
        )
        print(f"搜索结果: {len(search_result['results'])} 个")
        
    finally:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. 推理引擎集成示例

```python
# src/core/reasoning/mcp_enhanced_reasoner.py
from typing import Dict, List, Any
from ..reasoning_engine import ReasoningEngine
from ...communication.protocols.mcp.adapters.external_service_mcp_client import ExternalServiceMCPClient

class MCPEnhancedReasoner(ReasoningEngine):
    """集成MCP外部服务的推理引擎"""
    
    def __init__(self):
        super().__init__()
        self.mcp_client = ExternalServiceMCPClient()
    
    async def initialize(self):
        """初始化推理引擎"""
        await super().initialize()
        await self.mcp_client.start()
    
    async def reason_with_external_services(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用外部服务进行推理"""
        
        # 1. 向量搜索相关文档
        search_results = await self.mcp_client.vector_search(
            collection_name="knowledge_base",
            query=query,
            top_k=10
        )
        
        # 2. 构建增强的上下文
        enhanced_context = {
            **context,
            "relevant_documents": search_results["results"]
        }
        
        # 3. 调用LLM进行推理
        reasoning_result = await self.mcp_client.call_llm_service(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个智能推理助手"},
                {"role": "user", "content": f"查询: {query}\n上下文: {enhanced_context}"}
            ],
            strategy="intelligent",
            priority=8
        )
        
        return {
            "query": query,
            "reasoning": reasoning_result["response"],
            "sources": search_results["results"],
            "metadata": {
                "model_used": reasoning_result["model"],
                "search_count": len(search_results["results"]),
                "processing_time": reasoning_result["metadata"]["response_time"]
            }
        }
```

### 3. 工作流引擎集成示例

```python
# src/core/reasoning/workflow_generation_agent.py (增强版)
from typing import Dict, List, Any
from ...communication.protocols.mcp.adapters.external_service_mcp_client import ExternalServiceMCPClient

class MCPEnhancedWorkflowAgent:
    """集成MCP外部服务的工作流生成代理"""
    
    def __init__(self):
        self.mcp_client = ExternalServiceMCPClient()
    
    async def generate_document_processing_workflow(
        self,
        documents: List[str],
        target_format: str = "knowledge_graph"
    ) -> Dict[str, Any]:
        """生成文档处理工作流"""
        
        workflow_steps = []
        
        # 1. 文档解析步骤
        for doc_path in documents:
            parse_step = {
                "id": f"parse_{doc_path.split('/')[-1]}",
                "type": "mcp_tool",
                "tool": "parse_document",
                "parameters": {
                    "file_path": doc_path,
                    "strategy": "hi_res",
                    "extract_tables": True,
                    "extract_images": True
                }
            }
            workflow_steps.append(parse_step)
        
        # 2. 知识图谱构建步骤
        if target_format == "knowledge_graph":
            graph_step = {
                "id": "build_knowledge_graph",
                "type": "mcp_tool",
                "tool": "build_knowledge_graph",
                "parameters": {
                    "documents": "{{parse_results}}",
                    "config": {
                        "chunk_size": 300,
                        "community_algorithm": "leiden"
                    }
                },
                "depends_on": [step["id"] for step in workflow_steps]
            }
            workflow_steps.append(graph_step)
        
        # 3. 向量化步骤
        vector_step = {
            "id": "vectorize_documents",
            "type": "mcp_tool", 
            "tool": "vector_search",
            "parameters": {
                "collection_name": "processed_documents",
                "operation": "add_documents",
                "documents": "{{processed_documents}}"
            },
            "depends_on": ["build_knowledge_graph"] if target_format == "knowledge_graph" else [step["id"] for step in workflow_steps]
        }
        workflow_steps.append(vector_step)
        
        return {
            "workflow_id": f"doc_processing_{len(documents)}_docs",
            "description": f"处理 {len(documents)} 个文档并构建{target_format}",
            "steps": workflow_steps,
            "estimated_time": len(documents) * 30,  # 每个文档预计30秒
            "resource_requirements": {
                "cpu": "2 cores",
                "memory": "4GB",
                "external_services": ["unstructured", "graphrag", "chroma"]
            }
        }
```

## 配置和部署

### 1. MCP服务器配置

```yaml
# config/mcp_external_service_scheduler.yaml
mcp_server:
  name: "external-service-scheduler"
  version: "1.0.0"
  description: "智能外部服务调度和管理工具集"
  
  transport:
    type: "stdio"
    timeout: 30
    
  external_services:
    llm_services:
      openai:
        api_key: "${OPENAI_API_KEY}"
        models: ["gpt-4", "gpt-3.5-turbo"]
        cost_per_1k_tokens:
          gpt-4: 0.03
          gpt-3.5-turbo: 0.002
          
      anthropic:
        api_key: "${ANTHROPIC_API_KEY}"
        models: ["claude-3-sonnet", "claude-3-haiku"]
    
    document_services:
      unstructured:
        base_url: "http://unstructured-api:8000"
        timeout: 300
        
    knowledge_graph_services:
      graphrag:
        base_url: "http://graphrag-api:8001"
        timeout: 600
        
    vector_databases:
      chroma:
        base_url: "http://chroma:8000"
        collections: ["documents", "chunks", "embeddings"]
  
  scheduling:
    default_strategy: "intelligent"
    load_balancing:
      strategies:
        llm: "cost_optimized"
        document: "least_loaded"
        knowledge_graph: "weighted_round_robin"
    
    circuit_breaker:
      failure_threshold: 5
      timeout: 60
      
  monitoring:
    metrics_enabled: true
    health_check_interval: 30
```

### 2. 系统集成配置

```yaml
# config/system_mcp_integration.yaml
mcp:
  enabled: true
  servers:
    - name: "external-service-scheduler"
      description: "智能外部服务调度和管理"
      transport:
        type: "stdio"
        command: ["python", "-m", "src.communication.protocols.mcp.servers.external_service_scheduler_server"]
        args: ["--config", "config/mcp_external_service_scheduler.yaml"]
      capabilities:
        - "llm_service_routing"
        - "document_processing"
        - "knowledge_graph_building"
        - "vector_search"
        - "service_management"
      enabled: true

system:
  reasoning_engine:
    mcp_integration:
      enabled: true
      preferred_servers: ["external-service-scheduler"]
      
  workflow_engine:
    mcp_integration:
      enabled: true
      external_service_tools:
        - "call_llm_service"
        - "parse_document"
        - "build_knowledge_graph"
        - "vector_search"
      
  knowledge_manager:
    mcp_integration:
      enabled: true
      document_processing_tool: "parse_document"
      knowledge_graph_tool: "build_knowledge_graph"
```

## 部署方案

### 1. Docker Compose部署

```yaml
# docker-compose.mcp.yml
version: '3.8'

services:
  # MCP外部服务调度器
  mcp-external-scheduler:
    build:
      context: .
      dockerfile: docker/mcp-external-scheduler.Dockerfile
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - UNSTRUCTURED_API_URL=http://unstructured:8000
      - GRAPHRAG_API_URL=http://graphrag:8001
      - CHROMA_API_URL=http://chroma:8000
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    restart: unless-stopped
    
  # Nagent核心系统
  nagent-core:
    build: .
    environment:
      - MCP_EXTERNAL_SCHEDULER_ENABLED=true
    volumes:
      - ./config:/app/config
    depends_on:
      - mcp-external-scheduler
    restart: unless-stopped
    
  # 外部服务
  unstructured:
    image: unstructured/unstructured-api:latest
    ports:
      - "8000:8000"
    
  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma
      
volumes:
  chroma_data:
```

### 2. Kubernetes部署

```yaml
# k8s/mcp-external-scheduler.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-external-scheduler
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mcp-external-scheduler
  template:
    metadata:
      labels:
        app: mcp-external-scheduler
    spec:
      containers:
      - name: mcp-external-scheduler
        image: nagent/mcp-external-scheduler:latest
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: openai-key
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: anthropic-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        volumeMounts:
        - name: config
          mountPath: /app/config
      volumes:
      - name: config
        configMap:
          name: mcp-config
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-external-scheduler
spec:
  selector:
    app: mcp-external-scheduler
  ports:
  - port: 8080
    targetPort: 8080
```

## 监控和运维

### 1. 监控指标

```python
# 关键监控指标
MCP_METRICS = {
    "mcp_tool_calls_total": "MCP工具调用总数",
    "mcp_tool_call_duration": "MCP工具调用耗时",
    "mcp_tool_call_success_rate": "MCP工具调用成功率",
    "external_service_requests_total": "外部服务请求总数",
    "external_service_response_time": "外部服务响应时间",
    "external_service_error_rate": "外部服务错误率",
    "mcp_connection_status": "MCP连接状态",
    "scheduler_queue_length": "调度器队列长度"
}
```

### 2. 告警规则

```yaml
# monitoring/alerts.yml
groups:
- name: mcp-external-scheduler
  rules:
  - alert: MCPToolCallHighErrorRate
    expr: rate(mcp_tool_call_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "MCP工具调用错误率过高"
      
  - alert: ExternalServiceDown
    expr: external_service_up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "外部服务不可用"
      
  - alert: SchedulerQueueTooLong
    expr: scheduler_queue_length > 100
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "调度器队列过长"
```

## 优势总结

### 🎯 **核心价值**

1. **标准化集成**：基于MCP协议，确保兼容性和可扩展性
2. **模块化架构**：外部服务调度器独立运行，便于管理
3. **智能调度**：提供多种调度策略和优化算法
4. **生态兼容**：完全兼容MCP生态系统

### 🔧 **技术优势**

1. **8个核心工具**：覆盖主要外部服务调度需求
2. **多种调度策略**：成本优化、性能优化、智能调度
3. **完整监控**：指标收集、健康检查、告警机制
4. **灵活部署**：支持Docker、Kubernetes等多种部署方式

### 🚀 **业务价值**

1. **降低复杂度**：统一的工具接口，简化集成
2. **提高效率**：智能调度和负载均衡
3. **增强可靠性**：熔断器和故障处理机制
4. **成本优化**：智能成本控制和资源优化

这个MCP集成方案让我们能够以标准化、模块化的方式实现外部服务的统一调度，同时保持系统的灵活性和可扩展性！ 