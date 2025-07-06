"""
配置管理器

负责加载、验证和管理系统配置，支持：
- YAML配置文件加载
- 环境变量覆盖
- 配置验证
- 热重载
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
import structlog

logger = structlog.get_logger(__name__)


class ConfigManager:
    """
    配置管理器
    
    负责系统配置的加载、验证和管理
    """
    
    def __init__(self):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_all_configs()
    
    def _load_yaml(self, path):
        """加载单个YAML配置文件"""
        if not os.path.exists(path):
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def _load_all_configs(self):
        """加载所有配置文件并合并"""
        config = self._load_yaml('config/system.yaml')
        # 合并其他模块配置
        for name in ['llm_gateway']:
            file = f'config/{name}.yaml'
            if os.path.exists(file):
                config[name] = self._load_yaml(file).get(name, {})
        return config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "system": {
                "name": "Enterprise Agent System",
                "version": "1.0.0",
                "environment": "development",
                "debug": True
            },
            "agent": {
                "max_concurrent": 10,
                "timeout": 300,
                "retry_count": 3,
                "default_model": "gpt-4",
                "fallback_model": "gpt-3.5-turbo"
            },
            "memory": {
                "type": "redis",
                "ttl": 3600,
                "max_size": "1GB"
            },
            "reasoning": {
                "default_strategy": "llm",
                "enable_fallback": True,
                "max_iterations": 10
            },
            "communication": {
                "acp": {
                    "host": "0.0.0.0",
                    "port": 8000,
                    "protocol": "http"
                }
            },
            "monitoring": {
                "enable_tracing": True,
                "log_level": "INFO"
            }
        }
    
    def _apply_environment_overrides(self):
        """应用环境变量覆盖"""
        # 系统配置
        if os.getenv("AGENT_SYSTEM_NAME"):
            self.config["system"]["name"] = os.getenv("AGENT_SYSTEM_NAME")
        
        if os.getenv("AGENT_SYSTEM_ENVIRONMENT"):
            self.config["system"]["environment"] = os.getenv("AGENT_SYSTEM_ENVIRONMENT")
        
        # Agent配置
        if os.getenv("AGENT_MAX_CONCURRENT"):
            self.config["agent"]["max_concurrent"] = int(os.getenv("AGENT_MAX_CONCURRENT"))
        
        if os.getenv("AGENT_TIMEOUT"):
            self.config["agent"]["timeout"] = int(os.getenv("AGENT_TIMEOUT"))
        
        if os.getenv("AGENT_DEFAULT_MODEL"):
            self.config["agent"]["default_model"] = os.getenv("AGENT_DEFAULT_MODEL")
        
        # 内存配置
        if os.getenv("MEMORY_TYPE"):
            self.config["memory"]["type"] = os.getenv("MEMORY_TYPE")
        
        # 推理配置
        if os.getenv("REASONING_STRATEGY"):
            self.config["reasoning"]["default_strategy"] = os.getenv("REASONING_STRATEGY")
        
        # 通信配置
        if os.getenv("ACP_HOST"):
            self.config["communication"]["acp"]["host"] = os.getenv("ACP_HOST")
        
        if os.getenv("ACP_PORT"):
            self.config["communication"]["acp"]["port"] = int(os.getenv("ACP_PORT"))
        
        # 监控配置
        if os.getenv("LOG_LEVEL"):
            self.config["monitoring"]["log_level"] = os.getenv("LOG_LEVEL")
        
        logger.info("Environment overrides applied")
    
    def _validate_config(self):
        """验证配置"""
        required_sections = ["system", "agent", "memory", "reasoning", "communication", "monitoring"]
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # 验证Agent配置
        agent_config = self.config["agent"]
        if agent_config["max_concurrent"] <= 0:
            raise ValueError("max_concurrent must be positive")
        
        if agent_config["timeout"] <= 0:
            raise ValueError("timeout must be positive")
        
        # 验证通信配置
        acp_config = self.config["communication"]["acp"]
        if acp_config["port"] <= 0 or acp_config["port"] > 65535:
            raise ValueError("Invalid ACP port number")
        
        logger.info("Configuration validation passed")
    
    def get_config(self, section: Optional[str] = None) -> Dict[str, Any]:
        """获取配置"""
        if section:
            return self.config.get(section, {})
        return self.config
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取指定部分的配置"""
        return self.config.get(section, {})
    
    def get_value(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key_path: 配置键路径，如 "agent.max_concurrent"
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key_path.split(".")
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_value(self, key_path: str, value: Any):
        """
        设置配置值
        
        Args:
            key_path: 配置键路径
            value: 配置值
        """
        keys = key_path.split(".")
        config = self.config
        
        # 导航到父级
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # 设置值
        config[keys[-1]] = value
        
        logger.info("Configuration value updated", key=key_path, value=value)
    
    def reload(self):
        """重新加载配置"""
        logger.info("Reloading configuration...")
        self.config = self._load_all_configs() # Reload all configs
    
    def save(self, path: Optional[str] = None):
        """
        保存配置到文件
        
        Args:
            path: 保存路径
        """
        save_path = path or "config/system.yaml" # Default to system.yaml
        
        try:
            # 确保目录存在
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info("Configuration saved", path=save_path)
            
        except Exception as e:
            logger.error("Failed to save configuration", error=str(e))
            raise
    
    def get_environment_info(self) -> Dict[str, Any]:
        """获取环境信息"""
        return {
            "config_path": "config/system.yaml", # Assuming system.yaml is the primary config
            "environment": self.config["system"]["environment"],
            "debug": self.config["system"]["debug"],
            "version": self.config["system"]["version"]
        } 