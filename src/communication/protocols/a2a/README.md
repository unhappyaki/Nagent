# A2A协议实现说明

本目录实现了标准A2A协议的核心骨架，支持Agent Card能力描述、注册、能力发现、任务流转等，所有Agent注册均通过统一注册中心（UnifiedModuleRegistry）完成。

## 主要模块
- `a2a_types.py`：A2A协议核心类型定义（AgentCard、A2AAgentRegistration等）
- `a2a_server.py`：A2A协议Server端，负责本地Agent注册、能力发布、注册中心对接
- `a2a_client.py`：A2A协议Client端，负责发现外部Agent并注册到统一注册中心
- `a2a_adapter.py`：A2A协议注册适配器，桥接A2A协议与统一注册中心

## 注册流程
1. 构建AgentCard能力卡片，描述agent_id、name、capabilities、endpoints等
2. 通过A2AServer注册本地Agent到统一注册中心
3. 通过A2AClient发现外部Agent并注册到统一注册中心
4. 所有注册、能力发现、健康监控等均走UnifiedModuleRegistry统一入口

## 集成方式
- 业务模块只需依赖A2AAdapter和UnifiedModuleRegistry即可实现本地/外部Agent的标准化注册与能力发现
- 支持与MCP/ACP等协议注册中心无缝对接，实现企业级智能体系统的能力中台 