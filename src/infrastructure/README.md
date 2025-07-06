# 基础设施层说明

本目录包含企业级智能体系统的基础设施能力模块，包括注册中心、网关、认证、配置中心等。

## 配置管理
- 统一通过 src/infrastructure/config/unified_config.py 获取各模块配置
- 推荐每个模块有独立的配置文件和README
- 支持热加载和环境变量覆盖

## 示例
- from src.infrastructure.config.unified_config import UnifiedConfigManager
- config = UnifiedConfigManager().get_llm_gateway_config() 