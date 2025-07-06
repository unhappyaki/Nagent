"""
告警管理器

提供告警规则管理、告警触发和通知功能。
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import json


class AlertSeverity(Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertRule:
    """告警规则"""
    
    def __init__(self, name: str, metric_name: str, condition: str, 
                 threshold: float, severity: AlertSeverity = AlertSeverity.WARNING,
                 duration: int = 0, tags: Optional[Dict[str, str]] = None):
        self.name = name
        self.metric_name = metric_name
        self.condition = condition
        self.threshold = threshold
        self.severity = severity
        self.duration = duration
        self.tags = tags or {}
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'metric_name': self.metric_name,
            'condition': self.condition,
            'threshold': self.threshold,
            'severity': self.severity.value,
            'duration': self.duration,
            'tags': self.tags,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertRule':
        return cls(
            name=data['name'],
            metric_name=data['metric_name'],
            condition=data['condition'],
            threshold=data['threshold'],
            severity=AlertSeverity(data['severity']),
            duration=data.get('duration', 0),
            tags=data.get('tags', {})
        )


class Alert:
    """告警"""
    
    def __init__(self, rule: AlertRule, value: float, message: str = ""):
        self.rule = rule
        self.value = value
        self.message = message or f"{rule.metric_name} {rule.condition} {rule.threshold} (current: {value})"
        self.timestamp = datetime.now()
        self.status = "active"
        self.resolved_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'rule_name': self.rule.name,
            'metric_name': self.rule.metric_name,
            'value': self.value,
            'message': self.message,
            'severity': self.rule.severity.value,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }
    
    def resolve(self) -> None:
        """解决告警"""
        self.status = "resolved"
        self.resolved_at = datetime.now()


class AlertManager:
    """告警管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.check_interval = self.config.get('check_interval', 30)
        self.max_alerts = self.config.get('max_alerts', 1000)
        
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_handlers: List[Callable] = []
        self._lock = threading.Lock()
        self.metrics_collector = None
        
        self._start_alert_check_task()
    
    def add_rule(self, rule: AlertRule) -> None:
        with self._lock:
            self.rules[rule.name] = rule
    
    def remove_rule(self, rule_name: str) -> None:
        with self._lock:
            if rule_name in self.rules:
                del self.rules[rule_name]
    
    def get_rules(self) -> List[AlertRule]:
        with self._lock:
            return list(self.rules.values())
    
    def set_metrics_collector(self, collector) -> None:
        self.metrics_collector = collector
    
    def add_notification_handler(self, handler: Callable) -> None:
        self.notification_handlers.append(handler)
    
    def check_alerts(self, metrics_data: Optional[Dict[str, Any]] = None) -> List[Alert]:
        if not self.metrics_collector and not metrics_data:
            return []
        
        new_alerts = []
        
        with self._lock:
            for rule in self.rules.values():
                if metrics_data and rule.metric_name in metrics_data:
                    current_value = metrics_data[rule.metric_name]
                elif self.metrics_collector:
                    stats = self.metrics_collector.get_metric_statistics(
                        rule.metric_name, 
                        time_range=timedelta(minutes=5),
                        tags=rule.tags
                    )
                    current_value = stats.get('latest', 0)
                else:
                    continue
                
                if self._check_condition(current_value, rule.condition, rule.threshold):
                    alert_key = f"{rule.name}:{rule.metric_name}"
                    
                    if alert_key not in self.active_alerts:
                        alert = Alert(rule, current_value)
                        self.active_alerts[alert_key] = alert
                        new_alerts.append(alert)
                        
                        self.alert_history.append(alert)
                        if len(self.alert_history) > self.max_alerts:
                            self.alert_history.pop(0)
                        
                        self._send_notification(alert)
                else:
                    alert_key = f"{rule.name}:{rule.metric_name}"
                    if alert_key in self.active_alerts:
                        self.active_alerts[alert_key].resolve()
                        del self.active_alerts[alert_key]
        
        return new_alerts
    
    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        if condition == ">":
            return value > threshold
        elif condition == "<":
            return value < threshold
        elif condition == ">=":
            return value >= threshold
        elif condition == "<=":
            return value <= threshold
        elif condition == "==":
            return value == threshold
        elif condition == "!=":
            return value != threshold
        else:
            return False
    
    def _send_notification(self, alert: Alert) -> None:
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                print(f"Notification handler error: {e}")
    
    def get_active_alerts(self) -> List[Alert]:
        with self._lock:
            return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        with self._lock:
            return self.alert_history[-limit:]
    
    def resolve_alert(self, rule_name: str, metric_name: str) -> bool:
        with self._lock:
            alert_key = f"{rule_name}:{metric_name}"
            if alert_key in self.active_alerts:
                self.active_alerts[alert_key].resolve()
                del self.active_alerts[alert_key]
                return True
            return False
    
    def _start_alert_check_task(self) -> None:
        def check_worker():
            while True:
                try:
                    time.sleep(self.check_interval)
                    self.check_alerts()
                except Exception as e:
                    print(f"Alert check error: {e}")
        
        thread = threading.Thread(target=check_worker, daemon=True)
        thread.start()
    
    def export_rules(self, format: str = 'json') -> str:
        rules = self.get_rules()
        
        if format.lower() == 'json':
            return json.dumps([rule.to_dict() for rule in rules], 
                            indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def import_rules(self, rules_data: str, format: str = 'json') -> None:
        if format.lower() == 'json':
            rules_list = json.loads(rules_data)
            for rule_data in rules_list:
                rule = AlertRule.from_dict(rule_data)
                self.add_rule(rule)
        else:
            raise ValueError(f"Unsupported format: {format}")


def console_notification_handler(alert: Alert) -> None:
    """控制台通知处理器"""
    print(f"[{alert.timestamp}] {alert.rule.severity.value.upper()}: {alert.message}")


def email_notification_handler(alert: Alert) -> None:
    """邮件通知处理器"""
    pass


def webhook_notification_handler(alert: Alert) -> None:
    """Webhook通知处理器"""
    pass 