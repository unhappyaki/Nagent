# 本模块已废弃，推荐统一使用 src.monitoring.log.trace_writer.TraceWriter 进行日志/事件记录。
# 详见 src/monitoring/log/README.md
"""
日志格式化器

提供多种日志格式支持，包括结构化JSON格式和传统文本格式。
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, Optional


class LogFormatter:
    """
    日志格式化器
    
    支持多种日志格式：
    - JSON格式：结构化日志，便于解析
    - 文本格式：人类可读的传统格式
    - 自定义格式：支持自定义模板
    """
    
    def __init__(self, format_type: str = 'json'):
        """
        初始化格式化器
        
        Args:
            format_type: 格式类型 (json, text, custom)
        """
        self.format_type = format_type.lower()
        
        # 预定义格式模板
        self.templates = {
            'json': self._format_json,
            'text': self._format_text,
            'simple': self._format_simple,
            'detailed': self._format_detailed
        }
    
    def format_log(self, log_entry: Dict[str, Any]) -> str:
        """
        格式化日志条目
        
        Args:
            log_entry: 日志条目字典
            
        Returns:
            格式化后的日志字符串
        """
        if self.format_type in self.templates:
            return self.templates[self.format_type](log_entry)
        else:
            return self._format_json(log_entry)  # 默认使用JSON格式
    
    def _format_json(self, log_entry: Dict[str, Any]) -> str:
        """
        JSON格式
        
        Args:
            log_entry: 日志条目
            
        Returns:
            JSON格式的日志字符串
        """
        # 确保时间戳格式一致
        formatted_entry = log_entry.copy()
        if 'timestamp' in formatted_entry:
            # 如果时间戳是datetime对象，转换为ISO格式
            if isinstance(formatted_entry['timestamp'], datetime):
                formatted_entry['timestamp'] = formatted_entry['timestamp'].isoformat()
        
        return json.dumps(formatted_entry, ensure_ascii=False, separators=(',', ':'))
    
    def _format_text(self, log_entry: Dict[str, Any]) -> str:
        """
        传统文本格式
        
        Args:
            log_entry: 日志条目
            
        Returns:
            文本格式的日志字符串
        """
        timestamp = log_entry.get('timestamp', '')
        level = log_entry.get('level', 'INFO')
        message = log_entry.get('message', '')
        context = log_entry.get('context', {})
        
        # 格式化时间戳
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        # 格式化上下文
        context_str = ''
        if context:
            context_str = f" | {json.dumps(context, ensure_ascii=False)}"
        
        return f"[{timestamp}] {level}: {message}{context_str}"
    
    def _format_simple(self, log_entry: Dict[str, Any]) -> str:
        """
        简单格式
        
        Args:
            log_entry: 日志条目
            
        Returns:
            简单格式的日志字符串
        """
        timestamp = log_entry.get('timestamp', '')
        level = log_entry.get('level', 'INFO')
        message = log_entry.get('message', '')
        
        # 简化时间戳
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp = dt.strftime('%H:%M:%S')
            except:
                pass
        
        return f"[{timestamp}] {level}: {message}"
    
    def _format_detailed(self, log_entry: Dict[str, Any]) -> str:
        """
        详细格式
        
        Args:
            log_entry: 日志条目
            
        Returns:
            详细格式的日志字符串
        """
        timestamp = log_entry.get('timestamp', '')
        level = log_entry.get('level', 'INFO')
        message = log_entry.get('message', '')
        context = log_entry.get('context', {})
        thread_id = log_entry.get('thread_id', '')
        process_id = log_entry.get('process_id', '')
        
        # 格式化时间戳
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            except:
                pass
        
        # 格式化上下文
        context_str = ''
        if context:
            context_str = f"\nContext: {json.dumps(context, ensure_ascii=False, indent=2)}"
        
        # 格式化线程和进程信息
        process_info = f"[T:{thread_id}]" if thread_id else ""
        
        return f"[{timestamp}] {level} {process_info}: {message}{context_str}"
    
    def set_format(self, format_type: str) -> None:
        """
        设置格式类型
        
        Args:
            format_type: 格式类型
        """
        if format_type.lower() in self.templates:
            self.format_type = format_type.lower()
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
    
    def add_custom_template(self, name: str, template_func) -> None:
        """
        添加自定义模板
        
        Args:
            name: 模板名称
            template_func: 模板函数
        """
        self.templates[name] = template_func
    
    def get_supported_formats(self) -> list:
        """
        获取支持的格式列表
        
        Returns:
            支持的格式列表
        """
        return list(self.templates.keys()) 