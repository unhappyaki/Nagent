"""
日志管理器

提供统一的日志记录接口，支持结构化日志、级别管理、查询和导出。
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import threading
from pathlib import Path

from .log_formatter import LogFormatter
from .log_handler import LogHandler
from .log_aggregator import LogAggregator


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogManager:
    """
    日志管理器
    
    提供统一的日志记录接口，支持：
    - 结构化日志记录
    - 日志级别管理
    - 日志查询和过滤
    - 日志导出
    - 日志聚合分析
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化日志管理器
        
        Args:
            config: 配置字典
                - log_level: 日志级别
                - log_file: 日志文件路径
                - max_file_size: 最大文件大小(MB)
                - backup_count: 备份文件数量
                - format: 日志格式
                - handlers: 处理器配置
        """
        self.config = config or {}
        self.log_level = LogLevel(self.config.get('log_level', LogLevel.INFO.value))
        self.log_file = self.config.get('log_file', 'logs/agent.log')
        self.max_file_size = self.config.get('max_file_size', 100)  # MB
        self.backup_count = self.config.get('backup_count', 5)
        
        # 创建日志目录
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化组件
        self.formatter = LogFormatter(self.config.get('format'))
        self.handler = LogHandler(
            log_file=self.log_file,
            max_file_size=self.max_file_size,
            backup_count=self.backup_count
        )
        self.aggregator = LogAggregator()
        
        # 设置日志记录器
        self.logger = logging.getLogger('agent_system')
        self.logger.setLevel(self.log_level.value)
        self.logger.addHandler(self.handler)
        self.handler.setFormatter(self.formatter)
        
        # 线程锁
        self._lock = threading.Lock()
        
        # 内存日志缓存
        self._log_cache: List[Dict[str, Any]] = []
        self._cache_size = self.config.get('cache_size', 1000)
        
        # 启动日志聚合任务
        self._start_aggregation_task()
    
    def log(self, level: Union[str, LogLevel], message: str, 
            context: Optional[Dict[str, Any]] = None) -> None:
        """
        记录日志
        
        Args:
            level: 日志级别
            message: 日志消息
            context: 上下文信息
        """
        if isinstance(level, str):
            level = LogLevel[level.upper()]
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level.name,
            'message': message,
            'context': context or {},
            'thread_id': threading.get_ident(),
            'process_id': threading.current_thread().ident
        }
        
        with self._lock:
            # 添加到缓存
            self._log_cache.append(log_entry)
            if len(self._log_cache) > self._cache_size:
                self._log_cache.pop(0)
            
            # 记录到文件
            self.logger.log(level.value, self.formatter.format_log(log_entry))
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """记录调试日志"""
        self.log(LogLevel.DEBUG, message, context)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """记录信息日志"""
        self.log(LogLevel.INFO, message, context)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """记录警告日志"""
        self.log(LogLevel.WARNING, message, context)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """记录错误日志"""
        self.log(LogLevel.ERROR, message, context)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """记录严重错误日志"""
        self.log(LogLevel.CRITICAL, message, context)
    
    def set_log_level(self, level: Union[str, LogLevel]) -> None:
        """
        设置日志级别
        
        Args:
            level: 日志级别
        """
        if isinstance(level, str):
            level = LogLevel[level.upper()]
        
        self.log_level = level
        self.logger.setLevel(level.value)
        self.info(f"Log level changed to {level.name}")
    
    def get_logs(self, filters: Optional[Dict[str, Any]] = None, 
                 limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取日志
        
        Args:
            filters: 过滤条件
                - level: 日志级别
                - start_time: 开始时间
                - end_time: 结束时间
                - message: 消息关键词
                - context: 上下文关键词
            limit: 返回数量限制
            
        Returns:
            日志列表
        """
        filters = filters or {}
        
        with self._lock:
            logs = self._log_cache.copy()
        
        # 应用过滤条件
        if 'level' in filters:
            level = filters['level']
            if isinstance(level, str):
                level = level.upper()
            logs = [log for log in logs if log['level'] == level]
        
        if 'start_time' in filters:
            start_time = datetime.fromisoformat(filters['start_time'])
            logs = [log for log in logs 
                   if datetime.fromisoformat(log['timestamp']) >= start_time]
        
        if 'end_time' in filters:
            end_time = datetime.fromisoformat(filters['end_time'])
            logs = [log for log in logs 
                   if datetime.fromisoformat(log['timestamp']) <= end_time]
        
        if 'message' in filters:
            keyword = filters['message'].lower()
            logs = [log for log in logs if keyword in log['message'].lower()]
        
        if 'context' in filters:
            keyword = filters['context'].lower()
            logs = [log for log in logs 
                   if any(keyword in str(v).lower() for v in log['context'].values())]
        
        # 按时间倒序排列
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return logs[:limit]
    
    def export_logs(self, format: str = 'json', 
                   filters: Optional[Dict[str, Any]] = None) -> str:
        """
        导出日志
        
        Args:
            format: 导出格式 (json, csv, txt)
            filters: 过滤条件
            
        Returns:
            导出的日志内容
        """
        logs = self.get_logs(filters)
        
        if format.lower() == 'json':
            return json.dumps(logs, indent=2, ensure_ascii=False)
        
        elif format.lower() == 'csv':
            if not logs:
                return ""
            
            headers = ['timestamp', 'level', 'message', 'context']
            lines = [','.join(headers)]
            
            for log in logs:
                context_str = json.dumps(log['context'], ensure_ascii=False)
                line = [
                    log['timestamp'],
                    log['level'],
                    f'"{log["message"]}"',
                    f'"{context_str}"'
                ]
                lines.append(','.join(line))
            
            return '\n'.join(lines)
        
        elif format.lower() == 'txt':
            lines = []
            for log in logs:
                context_str = json.dumps(log['context'], ensure_ascii=False)
                line = f"[{log['timestamp']}] {log['level']}: {log['message']} {context_str}"
                lines.append(line)
            
            return '\n'.join(lines)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_log_statistics(self, time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """
        获取日志统计信息
        
        Args:
            time_range: 时间范围
            
        Returns:
            统计信息
        """
        with self._lock:
            logs = self._log_cache.copy()
        
        if time_range:
            cutoff_time = datetime.now() - time_range
            logs = [log for log in logs 
                   if datetime.fromisoformat(log['timestamp']) >= cutoff_time]
        
        # 统计各级别日志数量
        level_counts = {}
        for log in logs:
            level = log['level']
            level_counts[level] = level_counts.get(level, 0) + 1
        
        # 统计错误率
        total_logs = len(logs)
        error_logs = len([log for log in logs 
                         if log['level'] in ['ERROR', 'CRITICAL']])
        error_rate = error_logs / total_logs if total_logs > 0 else 0
        
        return {
            'total_logs': total_logs,
            'level_counts': level_counts,
            'error_rate': error_rate,
            'time_range': str(time_range) if time_range else 'all'
        }
    
    def clear_cache(self) -> None:
        """清空日志缓存"""
        with self._lock:
            self._log_cache.clear()
    
    def _start_aggregation_task(self) -> None:
        """启动日志聚合任务"""
        def aggregation_worker():
            while True:
                try:
                    time.sleep(60)  # 每分钟聚合一次
                    with self._lock:
                        logs = self._log_cache.copy()
                    
                    # 执行聚合分析
                    self.aggregator.aggregate(logs)
                    
                except Exception as e:
                    self.error(f"Log aggregation error: {e}")
        
        thread = threading.Thread(target=aggregation_worker, daemon=True)
        thread.start()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if exc_type:
            self.error(f"Exception occurred: {exc_val}", {
                'exception_type': exc_type.__name__,
                'traceback': str(exc_tb)
            }) 