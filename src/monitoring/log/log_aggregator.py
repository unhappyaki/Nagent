# 本模块已废弃，推荐统一使用 src.monitoring.log.trace_writer.TraceWriter 进行日志/事件记录。
# 详见 src/monitoring/log/README.md
"""
日志聚合器

提供日志聚合、分析和统计功能。
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import threading


class LogAggregator:
    """
    日志聚合器
    
    提供：
    - 日志聚合分析
    - 统计信息计算
    - 异常模式识别
    - 性能指标提取
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化日志聚合器
        
        Args:
            config: 配置字典
                - aggregation_window: 聚合窗口(秒)
                - max_patterns: 最大模式数量
                - alert_threshold: 告警阈值
        """
        self.config = config or {}
        self.aggregation_window = self.config.get('aggregation_window', 300)  # 5分钟
        self.max_patterns = self.config.get('max_patterns', 100)
        self.alert_threshold = self.config.get('alert_threshold', 10)
        
        # 聚合数据存储
        self.aggregated_data = {
            'level_counts': defaultdict(int),
            'error_patterns': defaultdict(int),
            'performance_metrics': [],
            'alert_history': []
        }
        
        # 线程锁
        self._lock = threading.Lock()
        
        # 清理任务
        self._start_cleanup_task()
    
    def aggregate(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        聚合日志数据
        
        Args:
            logs: 日志列表
            
        Returns:
            聚合结果
        """
        with self._lock:
            # 按级别统计
            for log in logs:
                level = log.get('level', 'INFO')
                self.aggregated_data['level_counts'][level] += 1
            
            # 分析错误模式
            error_logs = [log for log in logs 
                         if log.get('level') in ['ERROR', 'CRITICAL']]
            self._analyze_error_patterns(error_logs)
            
            # 提取性能指标
            self._extract_performance_metrics(logs)
            
            # 检查告警条件
            alerts = self._check_alerts(logs)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'total_logs': len(logs),
                'level_counts': dict(self.aggregated_data['level_counts']),
                'error_patterns': dict(self.aggregated_data['error_patterns']),
                'performance_metrics': self.aggregated_data['performance_metrics'][-10:],  # 最近10条
                'alerts': alerts
            }
    
    def _analyze_error_patterns(self, error_logs: List[Dict[str, Any]]) -> None:
        """
        分析错误模式
        
        Args:
            error_logs: 错误日志列表
        """
        for log in error_logs:
            message = log.get('message', '')
            context = log.get('context', {})
            
            # 提取错误模式
            pattern = self._extract_error_pattern(message, context)
            if pattern:
                self.aggregated_data['error_patterns'][pattern] += 1
    
    def _extract_error_pattern(self, message: str, context: Dict[str, Any]) -> Optional[str]:
        """
        提取错误模式
        
        Args:
            message: 错误消息
            context: 上下文
            
        Returns:
            错误模式
        """
        # 简单的模式提取逻辑
        # 可以根据需要实现更复杂的模式识别
        
        # 提取异常类型
        if 'exception_type' in context:
            return f"Exception: {context['exception_type']}"
        
        # 提取错误关键词
        error_keywords = ['timeout', 'connection', 'permission', 'not found', 'invalid']
        for keyword in error_keywords:
            if keyword.lower() in message.lower():
                return f"Error: {keyword}"
        
        # 提取HTTP状态码
        if 'status_code' in context:
            return f"HTTP: {context['status_code']}"
        
        return None
    
    def _extract_performance_metrics(self, logs: List[Dict[str, Any]]) -> None:
        """
        提取性能指标
        
        Args:
            logs: 日志列表
        """
        for log in logs:
            context = log.get('context', {})
            
            # 提取响应时间
            if 'response_time' in context:
                metric = {
                    'timestamp': log.get('timestamp'),
                    'type': 'response_time',
                    'value': context['response_time'],
                    'endpoint': context.get('endpoint', 'unknown')
                }
                self.aggregated_data['performance_metrics'].append(metric)
            
            # 提取内存使用
            if 'memory_usage' in context:
                metric = {
                    'timestamp': log.get('timestamp'),
                    'type': 'memory_usage',
                    'value': context['memory_usage'],
                    'unit': 'MB'
                }
                self.aggregated_data['performance_metrics'].append(metric)
            
            # 提取CPU使用
            if 'cpu_usage' in context:
                metric = {
                    'timestamp': log.get('timestamp'),
                    'type': 'cpu_usage',
                    'value': context['cpu_usage'],
                    'unit': '%'
                }
                self.aggregated_data['performance_metrics'].append(metric)
    
    def _check_alerts(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检查告警条件
        
        Args:
            logs: 日志列表
            
        Returns:
            告警列表
        """
        alerts = []
        
        # 检查错误率
        error_count = len([log for log in logs 
                          if log.get('level') in ['ERROR', 'CRITICAL']])
        total_count = len(logs)
        
        if total_count > 0:
            error_rate = error_count / total_count
            if error_rate > 0.1:  # 错误率超过10%
                alert = {
                    'type': 'high_error_rate',
                    'message': f'Error rate is {error_rate:.2%}',
                    'value': error_rate,
                    'threshold': 0.1,
                    'timestamp': datetime.now().isoformat()
                }
                alerts.append(alert)
                self.aggregated_data['alert_history'].append(alert)
        
        # 检查错误模式频率
        for pattern, count in self.aggregated_data['error_patterns'].items():
            if count >= self.alert_threshold:
                alert = {
                    'type': 'frequent_error_pattern',
                    'message': f'Pattern "{pattern}" occurred {count} times',
                    'pattern': pattern,
                    'count': count,
                    'threshold': self.alert_threshold,
                    'timestamp': datetime.now().isoformat()
                }
                alerts.append(alert)
                self.aggregated_data['alert_history'].append(alert)
        
        return alerts
    
    def get_statistics(self, time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """
        获取统计信息
        
        Args:
            time_range: 时间范围
            
        Returns:
            统计信息
        """
        with self._lock:
            # 过滤时间范围内的数据
            if time_range:
                cutoff_time = datetime.now() - time_range
                recent_alerts = [
                    alert for alert in self.aggregated_data['alert_history']
                    if datetime.fromisoformat(alert['timestamp']) >= cutoff_time
                ]
            else:
                recent_alerts = self.aggregated_data['alert_history']
            
            # 计算性能指标统计
            performance_metrics = self.aggregated_data['performance_metrics']
            if time_range:
                cutoff_time = datetime.now() - time_range
                performance_metrics = [
                    metric for metric in performance_metrics
                    if datetime.fromisoformat(metric['timestamp']) >= cutoff_time
                ]
            
            # 计算响应时间统计
            response_times = [
                metric['value'] for metric in performance_metrics
                if metric['type'] == 'response_time'
            ]
            
            response_time_stats = {}
            if response_times:
                response_time_stats = {
                    'count': len(response_times),
                    'min': min(response_times),
                    'max': max(response_times),
                    'avg': sum(response_times) / len(response_times),
                    'p95': self._percentile(response_times, 95),
                    'p99': self._percentile(response_times, 99)
                }
            
            return {
                'level_counts': dict(self.aggregated_data['level_counts']),
                'error_patterns': dict(self.aggregated_data['error_patterns']),
                'alerts': {
                    'total': len(recent_alerts),
                    'recent': recent_alerts[-10:] if recent_alerts else []
                },
                'performance': {
                    'response_time': response_time_stats,
                    'metrics_count': len(performance_metrics)
                }
            }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """
        计算百分位数
        
        Args:
            values: 数值列表
            percentile: 百分位数
            
        Returns:
            百分位数值
        """
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_top_error_patterns(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最常见的错误模式
        
        Args:
            limit: 返回数量限制
            
        Returns:
            错误模式列表
        """
        with self._lock:
            patterns = self.aggregated_data['error_patterns']
            sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
            
            return [
                {'pattern': pattern, 'count': count}
                for pattern, count in sorted_patterns[:limit]
            ]
    
    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取告警历史
        
        Args:
            limit: 返回数量限制
            
        Returns:
            告警历史列表
        """
        with self._lock:
            return self.aggregated_data['alert_history'][-limit:]
    
    def clear_data(self) -> None:
        """清空聚合数据"""
        with self._lock:
            self.aggregated_data = {
                'level_counts': defaultdict(int),
                'error_patterns': defaultdict(int),
                'performance_metrics': [],
                'alert_history': []
            }
    
    def _start_cleanup_task(self) -> None:
        """启动清理任务"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(3600)  # 每小时清理一次
                    self._cleanup_old_data()
                except Exception:
                    continue
        
        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()
    
    def _cleanup_old_data(self) -> None:
        """清理旧数据"""
        with self._lock:
            # 清理旧的性能指标
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.aggregated_data['performance_metrics'] = [
                metric for metric in self.aggregated_data['performance_metrics']
                if datetime.fromisoformat(metric['timestamp']) >= cutoff_time
            ]
            
            # 清理旧的告警历史
            self.aggregated_data['alert_history'] = [
                alert for alert in self.aggregated_data['alert_history']
                if datetime.fromisoformat(alert['timestamp']) >= cutoff_time
            ] 