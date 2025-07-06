"""
MCP资源管理器

管理MCP资源的缓存、索引和访问控制
"""

import asyncio
import time
from typing import Dict, List, Optional, Set
import structlog

from .mcp_types import MCPResource, MCPResourceContent

logger = structlog.get_logger(__name__)


class MCPResourceManager:
    """MCP资源管理器"""
    
    def __init__(
        self,
        cache_enabled: bool = True,
        cache_size_mb: int = 100,
        cache_ttl: int = 1800,  # 30分钟
        max_resource_size_mb: int = 10
    ):
        """
        初始化资源管理器
        
        Args:
            cache_enabled: 是否启用缓存
            cache_size_mb: 缓存大小限制（MB）
            cache_ttl: 缓存存活时间（秒）
            max_resource_size_mb: 单个资源最大大小（MB）
        """
        self.cache_enabled = cache_enabled
        self.cache_size_mb = cache_size_mb
        self.cache_ttl = cache_ttl
        self.max_resource_size_mb = max_resource_size_mb
        
        # 资源缓存
        self._resource_cache: Dict[str, MCPResourceContent] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_sizes: Dict[str, int] = {}  # 字节大小
        self._current_cache_size = 0  # 当前缓存总大小（字节）
        
        # 资源索引
        self._resource_index: Dict[str, MCPResource] = {}
        
        # 访问统计
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "resources_loaded": 0,
            "cache_evictions": 0,
            "total_cache_size": 0
        }
        
        # 清理任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = 300  # 5分钟清理一次
        
        logger.info(
            "Resource manager initialized",
            cache_enabled=cache_enabled,
            cache_size_mb=cache_size_mb,
            cache_ttl=cache_ttl
        )
    
    def add_resource_to_index(self, resource: MCPResource) -> None:
        """
        添加资源到索引
        
        Args:
            resource: MCP资源定义
        """
        self._resource_index[resource.uri] = resource
        logger.debug("Resource added to index", uri=resource.uri)
    
    def remove_resource_from_index(self, uri: str) -> None:
        """
        从索引中移除资源
        
        Args:
            uri: 资源URI
        """
        if uri in self._resource_index:
            del self._resource_index[uri]
            logger.debug("Resource removed from index", uri=uri)
    
    def get_resource_info(self, uri: str) -> Optional[MCPResource]:
        """
        获取资源信息
        
        Args:
            uri: 资源URI
            
        Returns:
            资源信息
        """
        return self._resource_index.get(uri)
    
    def list_resources(self, pattern: Optional[str] = None) -> List[MCPResource]:
        """
        列出资源
        
        Args:
            pattern: 过滤模式
            
        Returns:
            资源列表
        """
        resources = list(self._resource_index.values())
        
        if pattern:
            filtered_resources = []
            pattern_lower = pattern.lower()
            for resource in resources:
                if (pattern_lower in resource.uri.lower() or
                    (resource.name and pattern_lower in resource.name.lower()) or
                    (resource.description and pattern_lower in resource.description.lower())):
                    filtered_resources.append(resource)
            return filtered_resources
        
        return resources
    
    async def get_resource_content(
        self,
        uri: str,
        use_cache: bool = True
    ) -> Optional[MCPResourceContent]:
        """
        获取资源内容（从缓存或通过客户端获取）
        
        Args:
            uri: 资源URI
            use_cache: 是否使用缓存
            
        Returns:
            资源内容
        """
        # 检查缓存
        if use_cache and self.cache_enabled and self._is_cached(uri):
            self.stats["cache_hits"] += 1
            logger.debug("Resource cache hit", uri=uri)
            return self._resource_cache[uri]
        
        self.stats["cache_misses"] += 1
        logger.debug("Resource cache miss", uri=uri)
        
        # 这里应该通过MCP客户端获取资源内容
        # 由于这是资源管理器，实际的获取逻辑在客户端中
        # 这个方法主要用于缓存管理
        return None
    
    async def cache_resource_content(
        self,
        uri: str,
        content: MCPResourceContent
    ) -> bool:
        """
        缓存资源内容
        
        Args:
            uri: 资源URI
            content: 资源内容
            
        Returns:
            缓存是否成功
        """
        if not self.cache_enabled:
            return False
        
        try:
            # 计算内容大小
            content_size = self._calculate_content_size(content)
            max_size_bytes = self.max_resource_size_mb * 1024 * 1024
            
            # 检查单个资源大小限制
            if content_size > max_size_bytes:
                logger.warning(
                    "Resource too large to cache",
                    uri=uri,
                    size_mb=content_size / (1024 * 1024),
                    max_size_mb=self.max_resource_size_mb
                )
                return False
            
            # 确保有足够的缓存空间
            await self._ensure_cache_space(content_size)
            
            # 缓存内容
            self._resource_cache[uri] = content
            self._cache_timestamps[uri] = time.time()
            self._cache_sizes[uri] = content_size
            self._current_cache_size += content_size
            
            self.stats["resources_loaded"] += 1
            self.stats["total_cache_size"] = self._current_cache_size
            
            logger.debug(
                "Resource cached",
                uri=uri,
                size_bytes=content_size,
                total_cache_size_mb=self._current_cache_size / (1024 * 1024)
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to cache resource", uri=uri, error=str(e))
            return False
    
    async def invalidate_cache(self, uri: Optional[str] = None) -> None:
        """
        使缓存失效
        
        Args:
            uri: 特定资源URI，如果为None则清空所有缓存
        """
        if uri:
            # 清除特定资源的缓存
            if uri in self._resource_cache:
                size = self._cache_sizes.get(uri, 0)
                del self._resource_cache[uri]
                del self._cache_timestamps[uri]
                del self._cache_sizes[uri]
                self._current_cache_size -= size
                
                logger.debug("Resource cache invalidated", uri=uri)
        else:
            # 清空所有缓存
            self._resource_cache.clear()
            self._cache_timestamps.clear()
            self._cache_sizes.clear()
            self._current_cache_size = 0
            
            logger.info("All resource cache invalidated")
        
        self.stats["total_cache_size"] = self._current_cache_size
    
    async def start_cleanup_task(self) -> None:
        """开始缓存清理任务"""
        if self._cleanup_task is not None:
            logger.warning("Cleanup task already running")
            return
        
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Resource cache cleanup task started")
    
    async def stop_cleanup_task(self) -> None:
        """停止缓存清理任务"""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Resource cache cleanup task stopped")
    
    def _is_cached(self, uri: str) -> bool:
        """检查资源是否已缓存且未过期"""
        if uri not in self._resource_cache:
            return False
        
        # 检查是否过期
        cached_time = self._cache_timestamps.get(uri, 0)
        if time.time() - cached_time > self.cache_ttl:
            # 过期，删除缓存
            asyncio.create_task(self._remove_from_cache(uri))
            return False
        
        return True
    
    def _calculate_content_size(self, content: MCPResourceContent) -> int:
        """计算内容大小（字节）"""
        size = 0
        
        if content.text:
            size += len(content.text.encode('utf-8'))
        
        if content.blob:
            size += len(content.blob)
        
        # 基础对象开销
        size += 1024  # 估算对象元数据大小
        
        return size
    
    async def _ensure_cache_space(self, required_size: int) -> None:
        """确保有足够的缓存空间"""
        max_cache_bytes = self.cache_size_mb * 1024 * 1024
        
        # 如果当前大小加上所需大小超过限制，需要清理
        while self._current_cache_size + required_size > max_cache_bytes:
            # 找到最旧的缓存项
            oldest_uri = None
            oldest_time = float('inf')
            
            for uri, timestamp in self._cache_timestamps.items():
                if timestamp < oldest_time:
                    oldest_time = timestamp
                    oldest_uri = uri
            
            if oldest_uri:
                await self._remove_from_cache(oldest_uri)
                self.stats["cache_evictions"] += 1
                logger.debug("Cache eviction", uri=oldest_uri)
            else:
                # 没有可清理的项目，直接退出
                break
    
    async def _remove_from_cache(self, uri: str) -> None:
        """从缓存中移除资源"""
        if uri in self._resource_cache:
            size = self._cache_sizes.get(uri, 0)
            del self._resource_cache[uri]
            del self._cache_timestamps[uri]
            del self._cache_sizes[uri]
            self._current_cache_size -= size
            
            self.stats["total_cache_size"] = self._current_cache_size
    
    async def _cleanup_loop(self) -> None:
        """缓存清理循环"""
        logger.debug("Resource cache cleanup loop started")
        
        try:
            while True:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired_cache()
                
        except asyncio.CancelledError:
            logger.debug("Resource cache cleanup loop cancelled")
            raise
        except Exception as e:
            logger.error("Error in resource cache cleanup loop", error=str(e))
    
    async def _cleanup_expired_cache(self) -> None:
        """清理过期的缓存"""
        current_time = time.time()
        expired_uris = []
        
        for uri, timestamp in self._cache_timestamps.items():
            if current_time - timestamp > self.cache_ttl:
                expired_uris.append(uri)
        
        for uri in expired_uris:
            await self._remove_from_cache(uri)
            logger.debug("Expired cache removed", uri=uri)
        
        if expired_uris:
            logger.info(
                "Cache cleanup completed",
                expired_count=len(expired_uris),
                remaining_count=len(self._resource_cache)
            )
    
    def get_stats(self) -> Dict[str, any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats.update({
            "cached_resources": len(self._resource_cache),
            "indexed_resources": len(self._resource_index),
            "cache_size_mb": self._current_cache_size / (1024 * 1024),
            "cache_hit_rate": (
                self.stats["cache_hits"] / 
                (self.stats["cache_hits"] + self.stats["cache_misses"])
                if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0 else 0
            )
        })
        return stats
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start_cleanup_task()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop_cleanup_task() 