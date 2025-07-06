# config 目录说明

本目录用于存放系统全局及各基础设施模块的配置文件。

- system.yaml：全局基础配置（不含具体模块大块配置）
- llm_gateway.yaml：大模型API网关与路由配置
- config_manager.py：统一配置加载与聚合逻辑

所有配置通过 config_manager.py 聚合加载，支持分模块扩展。 