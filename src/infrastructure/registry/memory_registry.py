"""
Memory注册器
基础设施层组件，支持短时/长时/冻结/加密模式配置
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger(__name__)


class MemoryMode:
    """记忆模式"""
    SHORT_TERM = "short_term"      # 短时记忆
    LONG_TERM = "long_term"        # 长时记忆
    FROZEN = "frozen"              # 冻结记忆
    ENCRYPTED = "encrypted"        # 加密记忆


class MemoryType:
    """记忆类型"""
    SEMANTIC = "semantic"          # 语义记忆
    EPISODIC = "episodic"         # 情节记忆
    PROCEDURAL = "procedural"     # 程序记忆
    WORKING = "working"           # 工作记忆
    VECTOR = "vector"             # 向量记忆


class MemoryRegistry:
    """
    记忆注册器
    
    基础设施层组件，负责：
    - 记忆模式配置：短时/长时/冻结/加密模式
    - 记忆生命周期管理：TTL、持久化、清理
    - 记忆类型管理：语义、情节、程序、工作、向量记忆
    - 记忆安全管理：加密、权限控制
    """
    
    def __init__(self, parent_registry):
        """
        初始化记忆注册器
        
        Args:
            parent_registry: 父注册中心
        """
        self.parent_registry = parent_registry
        self.registered_memories = {}
        self.memory_modes = {}
        self.memory_metadata = {}
        self.memory_encryption_keys = {}
        self.memory_access_logs = {}
        
        logger.info("MemoryRegistry initialized")
    
    async def register(
        self,
        memory_id: str,
        memory_config: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        注册记忆类型
        
        Args:
            memory_id: 记忆唯一标识
            memory_config: 记忆配置
            metadata: 元数据
            
        Returns:
            str: 注册成功的记忆ID
        """
        try:
            # 1. 配置记忆模式
            memory_mode = memory_config.get("mode", MemoryMode.SHORT_TERM)
            
            # 根据模式配置默认参数
            default_ttl = self._get_default_ttl(memory_mode)
            default_persistence = memory_mode in [MemoryMode.LONG_TERM, MemoryMode.FROZEN]
            
            mode_config = {
                "mode": memory_mode,
                "ttl": memory_config.get("ttl", default_ttl),
                "encryption": memory_config.get("encryption", memory_mode == MemoryMode.ENCRYPTED),
                "frozen": memory_config.get("frozen", memory_mode == MemoryMode.FROZEN),
                "persistence": memory_config.get("persistence", default_persistence),
                "compression": memory_config.get("compression", False),
                "replication": memory_config.get("replication", memory_mode == MemoryMode.LONG_TERM)
            }
            self.memory_modes[memory_id] = mode_config
            
            # 2. 元数据增强
            enhanced_metadata = {
                "memory_id": memory_id,
                "memory_type": memory_config.get("memory_type", MemoryType.SEMANTIC),
                "version": memory_config.get("version", "1.0.0"),
                "description": memory_config.get("description", ""),
                "tags": memory_config.get("tags", []),
                "max_size": memory_config.get("max_size", 1024 * 1024),  # 1MB默认
                "access_pattern": memory_config.get("access_pattern", "read_write"),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "expires_at": self._calculate_expiry(mode_config["ttl"]),
                "status": "active",
                **(metadata or {})
            }
            self.memory_metadata[memory_id] = enhanced_metadata
            
            # 3. 加密密钥管理
            if mode_config["encryption"]:
                encryption_key = await self._generate_encryption_key(memory_id)
                self.memory_encryption_keys[memory_id] = encryption_key
            
            # 4. Memory实例化配置
            memory_instance_config = {
                "memory_id": memory_id,
                "memory_class": memory_config.get("memory_class"),
                "memory_module": memory_config.get("memory_module"),
                "init_params": memory_config.get("init_params", {}),
                "mode_config": mode_config,
                "metadata": enhanced_metadata,
                "encryption_key": self.memory_encryption_keys.get(memory_id),
                "config": memory_config
            }
            
            self.registered_memories[memory_id] = memory_instance_config
            
            # 5. 初始化访问日志
            self.memory_access_logs[memory_id] = []
            
            # 6. 通知配置管理器更新
            if self.parent_registry.config_manager:
                await self.parent_registry.config_manager.update_memory_config(
                    memory_id, memory_instance_config
                )
            
            logger.info(
                "Memory registered successfully",
                memory_id=memory_id,
                mode=memory_mode,
                ttl=mode_config["ttl"],
                encryption=mode_config["encryption"],
                persistence=mode_config["persistence"]
            )
            
            return memory_id
            
        except Exception as e:
            logger.error(
                "Failed to register memory",
                memory_id=memory_id,
                error=str(e)
            )
            raise
    
    async def unregister(self, memory_id: str) -> bool:
        """
        注销记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            bool: 注销是否成功
        """
        try:
            if memory_id not in self.registered_memories:
                return False
            
            # 清理相关数据
            self.registered_memories.pop(memory_id, None)
            self.memory_modes.pop(memory_id, None)
            self.memory_metadata.pop(memory_id, None)
            self.memory_encryption_keys.pop(memory_id, None)
            self.memory_access_logs.pop(memory_id, None)
            
            # 通知配置管理器
            if self.parent_registry.config_manager:
                await self.parent_registry.config_manager.remove_memory_config(memory_id)
            
            logger.info("Memory unregistered successfully", memory_id=memory_id)
            return True
            
        except Exception as e:
            logger.error(
                "Failed to unregister memory",
                memory_id=memory_id,
                error=str(e)
            )
            return False
    
    async def get_memory_config(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        获取记忆配置
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            Optional[Dict[str, Any]]: 记忆配置
        """
        return self.registered_memories.get(memory_id)
    
    async def get_memory_mode(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        获取记忆模式配置
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            Optional[Dict[str, Any]]: 记忆模式配置
        """
        return self.memory_modes.get(memory_id)
    
    async def get_memory_encryption_key(self, memory_id: str) -> Optional[str]:
        """
        获取记忆加密密钥
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            Optional[str]: 加密密钥
        """
        return self.memory_encryption_keys.get(memory_id)
    
    async def update_memory_mode(
        self,
        memory_id: str,
        new_mode: str,
        mode_config: Dict[str, Any] = None
    ) -> bool:
        """
        更新记忆模式
        
        Args:
            memory_id: 记忆ID
            new_mode: 新模式
            mode_config: 模式配置
            
        Returns:
            bool: 更新是否成功
        """
        try:
            if memory_id not in self.registered_memories:
                return False
            
            # 检查模式切换是否允许
            current_mode = self.memory_modes[memory_id]["mode"]
            if current_mode == MemoryMode.FROZEN and new_mode != MemoryMode.FROZEN:
                logger.warning(
                    "Cannot change frozen memory mode",
                    memory_id=memory_id,
                    current_mode=current_mode,
                    new_mode=new_mode
                )
                return False
            
            # 更新模式配置
            updated_mode_config = self.memory_modes[memory_id].copy()
            updated_mode_config["mode"] = new_mode
            
            if mode_config:
                updated_mode_config.update(mode_config)
            
            # 处理加密模式切换
            if new_mode == MemoryMode.ENCRYPTED and memory_id not in self.memory_encryption_keys:
                encryption_key = await self._generate_encryption_key(memory_id)
                self.memory_encryption_keys[memory_id] = encryption_key
            elif new_mode != MemoryMode.ENCRYPTED and memory_id in self.memory_encryption_keys:
                self.memory_encryption_keys.pop(memory_id, None)
            
            self.memory_modes[memory_id] = updated_mode_config
            self.registered_memories[memory_id]["mode_config"] = updated_mode_config
            
            # 更新元数据
            self.memory_metadata[memory_id]["updated_at"] = datetime.utcnow().isoformat()
            
            # 通知配置管理器
            if self.parent_registry.config_manager:
                await self.parent_registry.config_manager.update_memory_config(
                    memory_id, self.registered_memories[memory_id]
                )
            
            logger.info(
                "Memory mode updated",
                memory_id=memory_id,
                old_mode=current_mode,
                new_mode=new_mode
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to update memory mode",
                memory_id=memory_id,
                error=str(e)
            )
            return False
    
    async def cleanup_expired_memories(self) -> int:
        """
        清理过期记忆
        
        Returns:
            int: 清理的记忆数量
        """
        cleaned_count = 0
        current_time = datetime.utcnow()
        
        expired_memories = []
        for memory_id, metadata in self.memory_metadata.items():
            expires_at = metadata.get("expires_at")
            if expires_at and datetime.fromisoformat(expires_at) < current_time:
                mode = self.memory_modes.get(memory_id, {})
                # 冻结记忆不会过期
                if mode.get("mode") != MemoryMode.FROZEN:
                    expired_memories.append(memory_id)
        
        for memory_id in expired_memories:
            success = await self.unregister(memory_id)
            if success:
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(
                "Cleaned up expired memories",
                cleaned_count=cleaned_count
            )
        
        return cleaned_count
    
    async def list(self, filter_by: Dict[str, Any] = None) -> List[str]:
        """
        列出记忆
        
        Args:
            filter_by: 过滤条件
            
        Returns:
            List[str]: 记忆ID列表
        """
        if not filter_by:
            return list(self.registered_memories.keys())
        
        # 根据过滤条件返回记忆列表
        filtered_memories = []
        for memory_id, config in self.registered_memories.items():
            if self._matches_filter(config, filter_by):
                filtered_memories.append(memory_id)
        
        return filtered_memories
    
    async def search_memories(
        self,
        query: str = None,
        memory_type: str = None,
        mode: str = None,
        encrypted: bool = None,
        status: str = None
    ) -> List[Dict[str, Any]]:
        """
        搜索记忆
        
        Args:
            query: 搜索关键词
            memory_type: 记忆类型
            mode: 记忆模式
            encrypted: 是否加密
            status: 状态
            
        Returns:
            List[Dict[str, Any]]: 匹配的记忆信息
        """
        results = []
        
        for memory_id, config in self.registered_memories.items():
            metadata = self.memory_metadata.get(memory_id, {})
            mode_config = self.memory_modes.get(memory_id, {})
            
            # 文本搜索
            if query:
                text_fields = [
                    metadata.get("description", ""),
                    memory_id,
                    str(metadata.get("tags", []))
                ]
                if not any(query.lower() in field.lower() for field in text_fields):
                    continue
            
            # 类型过滤
            if memory_type and metadata.get("memory_type") != memory_type:
                continue
            
            # 模式过滤
            if mode and mode_config.get("mode") != mode:
                continue
            
            # 加密过滤
            if encrypted is not None and mode_config.get("encryption", False) != encrypted:
                continue
            
            # 状态过滤
            if status and metadata.get("status") != status:
                continue
            
            results.append({
                "memory_id": memory_id,
                "config": config,
                "metadata": metadata,
                "mode_config": mode_config,
                "encryption_key": self.memory_encryption_keys.get(memory_id)
            })
        
        return results
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        获取记忆统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        total_memories = len(self.registered_memories)
        
        # 按模式统计
        mode_stats = {}
        for memory_id in self.registered_memories:
            mode_config = self.memory_modes.get(memory_id, {})
            mode = mode_config.get("mode", "unknown")
            mode_stats[mode] = mode_stats.get(mode, 0) + 1
        
        # 按类型统计
        type_stats = {}
        for memory_id in self.registered_memories:
            metadata = self.memory_metadata.get(memory_id, {})
            memory_type = metadata.get("memory_type", "unknown")
            type_stats[memory_type] = type_stats.get(memory_type, 0) + 1
        
        # 加密统计
        encrypted_count = sum(
            1 for mode_config in self.memory_modes.values()
            if mode_config.get("encryption", False)
        )
        
        # 持久化统计
        persistent_count = sum(
            1 for mode_config in self.memory_modes.values()
            if mode_config.get("persistence", False)
        )
        
        return {
            "total_memories": total_memories,
            "mode_distribution": mode_stats,
            "type_distribution": type_stats,
            "encrypted_count": encrypted_count,
            "persistent_count": persistent_count,
            "frozen_count": mode_stats.get(MemoryMode.FROZEN, 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_default_ttl(self, mode: str) -> int:
        """
        获取默认TTL（秒）
        
        Args:
            mode: 记忆模式
            
        Returns:
            int: TTL秒数
        """
        ttl_map = {
            MemoryMode.SHORT_TERM: 3600,        # 1小时
            MemoryMode.LONG_TERM: 86400 * 30,   # 30天
            MemoryMode.FROZEN: -1,              # 永不过期
            MemoryMode.ENCRYPTED: 86400 * 7     # 7天
        }
        return ttl_map.get(mode, 3600)
    
    def _calculate_expiry(self, ttl: int) -> Optional[str]:
        """
        计算过期时间
        
        Args:
            ttl: TTL秒数
            
        Returns:
            Optional[str]: 过期时间ISO格式
        """
        if ttl <= 0:
            return None
        
        expiry_time = datetime.utcnow() + timedelta(seconds=ttl)
        return expiry_time.isoformat()
    
    async def _generate_encryption_key(self, memory_id: str) -> str:
        """
        生成加密密钥
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            str: 加密密钥
        """
        import secrets
        import hashlib
        
        # 生成随机密钥
        random_key = secrets.token_hex(32)
        
        # 结合记忆ID生成最终密钥
        combined = f"{memory_id}:{random_key}"
        final_key = hashlib.sha256(combined.encode()).hexdigest()
        
        return final_key
    
    def _matches_filter(self, config: Dict[str, Any], filter_by: Dict[str, Any]) -> bool:
        """
        检查配置是否匹配过滤条件
        
        Args:
            config: 记忆配置
            filter_by: 过滤条件
            
        Returns:
            bool: 是否匹配
        """
        for key, value in filter_by.items():
            if key in config:
                if isinstance(value, list):
                    if not any(v in config[key] for v in value):
                        return False
                else:
                    if config[key] != value:
                        return False
            else:
                return False
        
        return True 