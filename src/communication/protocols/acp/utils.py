"""
ACP协议工具辅助模块
包含日志、时间戳、配置等辅助功能
"""

import time
import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
import structlog

logger = structlog.get_logger(__name__)


class TimeUtils:
    """时间工具类"""
    
    @staticmethod
    def get_current_timestamp() -> str:
        """获取当前时间戳 (ISO格式)"""
        return datetime.utcnow().isoformat() + 'Z'
    
    @staticmethod
    def get_current_unix_timestamp() -> float:
        """获取当前Unix时间戳"""
        return time.time()
    
    @staticmethod
    def parse_iso_timestamp(timestamp: str) -> datetime:
        """解析ISO格式时间戳"""
        # 移除尾部的Z
        if timestamp.endswith('Z'):
            timestamp = timestamp[:-1]
        
        try:
            return datetime.fromisoformat(timestamp)
        except ValueError:
            # 处理带有时区信息的情况
            return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    @staticmethod
    def is_timestamp_expired(timestamp: str, ttl_seconds: int) -> bool:
        """检查时间戳是否过期"""
        try:
            ts_datetime = TimeUtils.parse_iso_timestamp(timestamp)
            current_datetime = datetime.utcnow()
            elapsed = (current_datetime - ts_datetime).total_seconds()
            return elapsed > ttl_seconds
        except Exception:
            return True
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """格式化持续时间"""
        if seconds < 1:
            return f"{int(seconds * 1000)}ms"
        elif seconds < 60:
            return f"{seconds:.2f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m{secs:.1f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h{minutes}m"


class IDGenerator:
    """ID生成器"""
    
    @staticmethod
    def generate_uuid() -> str:
        """生成UUID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_short_id(length: int = 8) -> str:
        """生成短ID"""
        return str(uuid.uuid4()).replace('-', '')[:length]
    
    @staticmethod
    def generate_trace_id() -> str:
        """生成追踪ID"""
        return f"trace-{str(uuid.uuid4())}"
    
    @staticmethod
    def generate_correlation_id() -> str:
        """生成关联ID"""
        return f"corr-{str(uuid.uuid4())}"
    
    @staticmethod
    def generate_session_id() -> str:
        """生成会话ID"""
        return f"sess-{str(uuid.uuid4())}"
    
    @staticmethod
    def generate_message_id() -> str:
        """生成消息ID"""
        return f"msg-{str(uuid.uuid4())}"


class HashUtils:
    """哈希工具类"""
    
    @staticmethod
    def compute_md5(data: Union[str, bytes]) -> str:
        """计算MD5哈希"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.md5(data).hexdigest()
    
    @staticmethod
    def compute_sha256(data: Union[str, bytes]) -> str:
        """计算SHA256哈希"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def compute_message_hash(message_dict: Dict[str, Any]) -> str:
        """计算消息哈希"""
        # 创建消息的规范化表示
        canonical_message = json.dumps(message_dict, sort_keys=True, separators=(',', ':'))
        return HashUtils.compute_sha256(canonical_message)


class ConfigUtils:
    """配置工具类"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        "message": {
            "default_ttl": 300,  # 5分钟
            "max_retry_count": 3,
            "heartbeat_interval": 30,  # 30秒
            "default_timeout": 60  # 1分钟
        },
        "agent": {
            "registration_timeout": 30,
            "heartbeat_timeout": 60,
            "max_concurrent_tasks": 10,
            "default_capabilities": []
        },
        "dispatcher": {
            "task_timeout": 300,  # 5分钟
            "max_pending_tasks": 1000,
            "health_check_interval": 30,
            "cleanup_interval": 300  # 5分钟清理一次
        },
        "server": {
            "host": "localhost",
            "port": 8000,
            "max_connections": 100,
            "keepalive_timeout": 300
        }
    }
    
    @staticmethod
    def get_config_value(config: Dict[str, Any], key_path: str, default=None):
        """获取配置值"""
        keys = key_path.split('.')
        value = config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            # 尝试从默认配置获取
            try:
                value = ConfigUtils.DEFAULT_CONFIG
                for key in keys:
                    value = value[key]
                return value
            except (KeyError, TypeError):
                return default


class LogUtils:
    """日志工具类"""
    
    @staticmethod
    def create_structured_log(
        level: str,
        message: str,
        component: str = "acp",
        **kwargs
    ) -> Dict[str, Any]:
        """创建结构化日志"""
        log_entry = {
            "timestamp": TimeUtils.get_current_timestamp(),
            "level": level.upper(),
            "component": component,
            "message": message,
            "trace_id": kwargs.pop("trace_id", None),
            "correlation_id": kwargs.pop("correlation_id", None),
            **kwargs
        }
        
        # 移除None值
        return {k: v for k, v in log_entry.items() if v is not None}


class ValidationUtils:
    """验证工具类"""
    
    @staticmethod
    def is_valid_uuid(uuid_string: str) -> bool:
        """验证UUID格式"""
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_valid_iso_timestamp(timestamp: str) -> bool:
        """验证ISO时间戳格式"""
        try:
            TimeUtils.parse_iso_timestamp(timestamp)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_agent_id(agent_id: str) -> bool:
        """验证Agent ID格式"""
        if not agent_id or not isinstance(agent_id, str):
            return False
        
        # Agent ID应该是有效的标识符
        if len(agent_id) < 3 or len(agent_id) > 64:
            return False
        
        # 可以包含字母、数字、下划线、连字符
        import re
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, agent_id))


# 便捷函数
def get_current_timestamp() -> str:
    """获取当前时间戳"""
    return TimeUtils.get_current_timestamp()


def generate_id() -> str:
    """生成通用ID"""
    return IDGenerator.generate_uuid()


def log_info(message: str, **kwargs):
    """记录信息日志"""
    log_data = LogUtils.create_structured_log("info", message, **kwargs)
    logger.info(message, **log_data) 