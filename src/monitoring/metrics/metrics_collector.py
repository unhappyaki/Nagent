"""
指标收集器

提供性能指标收集、存储和查询功能。
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from collections import defaultdict, deque
import json
import psutil
import os


class Metric:
    """指标数据类"""
    
    def __init__(self, name: str, value: float, tags: Optional[Dict[str, str]] = None,
                 timestamp: Optional[datetime] = None, unit: str = ""):
        self.name = name
        self.value = value
        self.tags = tags or {}
        self.timestamp = timestamp or datetime.now()
        self.unit = unit
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'tags': self.tags,
            'timestamp': self.timestamp.isoformat(),
            'unit': self.unit
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Metric':
        return cls(
            name=data['name'],
            value=data['value'],
            tags=data.get('tags', {}),
            timestamp=datetime.fromisoformat(data['timestamp']),
            unit=data.get('unit', '')
        )


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.retention_period = self.config.get('retention_period', 24)
        self.max_metrics = self.config.get('max_metrics', 10000)
        self.collection_interval = self.config.get('collection_interval', 60)
        self.enable_system_metrics = self.config.get('enable_system_metrics', True)
        
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.max_metrics))
        self._lock = threading.Lock()
        
        self.system_collector = None
        if self.enable_system_metrics:
            self.system_collector = SystemMetricsCollector()
        
        self._start_collection_task()
    
    def record_metric(self, metric: Union[Metric, Dict[str, Any]]) -> None:
        if isinstance(metric, dict):
            metric = Metric.from_dict(metric)
        
        with self._lock:
            metric_key = self._generate_metric_key(metric)
            self.metrics[metric_key].append(metric)
    
    def record_metric_simple(self, name: str, value: float, 
                           tags: Optional[Dict[str, str]] = None, unit: str = "") -> None:
        metric = Metric(name=name, value=value, tags=tags, unit=unit)
        self.record_metric(metric)
    
    def get_metrics(self, query: Optional[Dict[str, Any]] = None) -> List[Metric]:
        query = query or {}
        
        with self._lock:
            all_metrics = []
            for metric_key, metrics_deque in self.metrics.items():
                all_metrics.extend(list(metrics_deque))
        
        if 'name' in query:
            all_metrics = [m for m in all_metrics if m.name == query['name']]
        
        if 'tags' in query:
            tags_filter = query['tags']
            all_metrics = [m for m in all_metrics 
                          if all(m.tags.get(k) == v for k, v in tags_filter.items())]
        
        if 'start_time' in query:
            start_time = query['start_time']
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time)
            all_metrics = [m for m in all_metrics if m.timestamp >= start_time]
        
        if 'end_time' in query:
            end_time = query['end_time']
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time)
            all_metrics = [m for m in all_metrics if m.timestamp <= end_time]
        
        all_metrics.sort(key=lambda x: x.timestamp)
        limit = query.get('limit', 1000)
        return all_metrics[-limit:]
    
    def get_metric_statistics(self, name: str, 
                            time_range: Optional[timedelta] = None,
                            tags: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        query = {'name': name}
        if tags:
            query['tags'] = tags
        
        metrics = self.get_metrics(query)
        
        if time_range:
            cutoff_time = datetime.now() - time_range
            metrics = [m for m in metrics if m.timestamp >= cutoff_time]
        
        if not metrics:
            return {'name': name, 'count': 0, 'min': 0, 'max': 0, 'avg': 0, 'sum': 0}
        
        values = [m.value for m in metrics]
        return {
            'name': name,
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'sum': sum(values),
            'latest': values[-1] if values else 0,
            'unit': metrics[0].unit if metrics else ""
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        if not self.system_collector:
            return {}
        return self.system_collector.collect()
    
    def export_metrics(self, format: str = 'json') -> str:
        all_metrics = self.get_metrics()
        
        if format.lower() == 'json':
            return json.dumps([m.to_dict() for m in all_metrics], 
                            indent=2, ensure_ascii=False)
        elif format.lower() == 'prometheus':
            return self._export_prometheus_format(all_metrics)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_prometheus_format(self, metrics: List[Metric]) -> str:
        lines = []
        for metric in metrics:
            tags_str = ""
            if metric.tags:
                tags_list = [f'{k}="{v}"' for k, v in metric.tags.items()]
                tags_str = "{" + ",".join(tags_list) + "}"
            
            line = f"{metric.name}{tags_str} {metric.value}"
            if metric.unit:
                line += f" # {metric.unit}"
            lines.append(line)
        
        return "\n".join(lines)
    
    def _generate_metric_key(self, metric: Metric) -> str:
        tags_str = json.dumps(metric.tags, sort_keys=True)
        return f"{metric.name}:{tags_str}"
    
    def _start_collection_task(self) -> None:
        def collection_worker():
            while True:
                try:
                    time.sleep(self.collection_interval)
                    
                    if self.system_collector:
                        system_metrics = self.system_collector.collect()
                        for name, value in system_metrics.items():
                            self.record_metric_simple(name, value, {'source': 'system'})
                    
                    self._cleanup_old_metrics()
                    
                except Exception as e:
                    print(f"Metrics collection error: {e}")
        
        thread = threading.Thread(target=collection_worker, daemon=True)
        thread.start()
    
    def _cleanup_old_metrics(self) -> None:
        cutoff_time = datetime.now() - timedelta(hours=self.retention_period)
        
        with self._lock:
            for metric_key in list(self.metrics.keys()):
                metrics_deque = self.metrics[metric_key]
                
                while metrics_deque and metrics_deque[0].timestamp < cutoff_time:
                    metrics_deque.popleft()
                
                if not metrics_deque:
                    del self.metrics[metric_key]
    
    def clear_metrics(self) -> None:
        with self._lock:
            self.metrics.clear()


class SystemMetricsCollector:
    """系统指标收集器"""
    
    def collect(self) -> Dict[str, float]:
        metrics = {}
        
        try:
            metrics['cpu_usage_percent'] = psutil.cpu_percent(interval=1)
            
            memory = psutil.virtual_memory()
            metrics['memory_usage_percent'] = memory.percent
            metrics['memory_used_mb'] = memory.used / (1024 * 1024)
            metrics['memory_total_mb'] = memory.total / (1024 * 1024)
            
            disk = psutil.disk_usage('/')
            metrics['disk_usage_percent'] = (disk.used / disk.total) * 100
            metrics['disk_used_gb'] = disk.used / (1024 * 1024 * 1024)
            metrics['disk_total_gb'] = disk.total / (1024 * 1024 * 1024)
            
            network = psutil.net_io_counters()
            metrics['network_bytes_sent'] = network.bytes_sent
            metrics['network_bytes_recv'] = network.bytes_recv
            
            process = psutil.Process(os.getpid())
            metrics['process_cpu_percent'] = process.cpu_percent()
            metrics['process_memory_mb'] = process.memory_info().rss / (1024 * 1024)
            
        except Exception as e:
            print(f"System metrics collection error: {e}")
        
        return metrics 