# 统一配置管理说明

本目录用于企业级智能体系统的统一配置管理，支持多模块分层配置与聚合加载。

## 配置原则
- 全局基础配置放在 config/system.yaml
- 各基础设施模块（如llm_gateway、registry、auth等）单独配置，放在 config/llm_gateway.yaml 等文件
- 统一通过 ConfigManager/UnifiedConfigManager 加载和获取

## 扩展新模块配置
1. 在 config/ 下新建 {模块名}.yaml
2. 在 config_manager.py 的 _load_all_configs 方法中添加模块名
3. 在 unified_config.py 中添加 get_{模块名}_config 方法

## 获取模块配置示例

```python
from src.infrastructure.config.unified_config import UnifiedConfigManager
llm_config = UnifiedConfigManager().get_llm_gateway_config()
``` 