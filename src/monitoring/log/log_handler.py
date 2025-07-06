"""
日志处理器

提供文件轮转、多目标输出等日志处理功能。
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional, List, Dict, Any


class LogHandler(logging.Handler):
    """
    自定义日志处理器
    
    支持：
    - 文件轮转
    - 多目标输出
    - 异步写入
    - 自定义过滤
    """
    
    def __init__(self, log_file: str, max_file_size: int = 100, 
                 backup_count: int = 5, encoding: str = 'utf-8'):
        """
        初始化日志处理器
        
        Args:
            log_file: 日志文件路径
            max_file_size: 最大文件大小(MB)
            backup_count: 备份文件数量
            encoding: 文件编码
        """
        super().__init__()
        
        self.log_file = log_file
        self.max_file_size = max_file_size * 1024 * 1024  # 转换为字节
        self.backup_count = backup_count
        self.encoding = encoding
        
        # 创建日志目录
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # 创建轮转文件处理器
        self.rotating_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=self.max_file_size,
            backupCount=backup_count,
            encoding=encoding
        )
        
        # 设置格式化器
        self.rotating_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        # 添加处理器到根日志记录器
        logging.getLogger().addHandler(self.rotating_handler)
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        发送日志记录
        
        Args:
            record: 日志记录
        """
        try:
            # 使用轮转处理器发送记录
            self.rotating_handler.emit(record)
        except Exception:
            self.handleError(record)
    
    def close(self) -> None:
        """关闭处理器"""
        self.rotating_handler.close()
        super().close()


class MultiTargetHandler(logging.Handler):
    """
    多目标日志处理器
    
    支持同时输出到多个目标：
    - 文件
    - 控制台
    - 网络
    - 数据库
    """
    
    def __init__(self, targets: List[Dict[str, Any]]):
        """
        初始化多目标处理器
        
        Args:
            targets: 目标配置列表
                - type: 目标类型 (file, console, network, database)
                - config: 目标配置
        """
        super().__init__()
        
        self.targets = []
        
        for target_config in targets:
            target_type = target_config.get('type', 'file')
            config = target_config.get('config', {})
            
            handler = self._create_handler(target_type, config)
            if handler:
                self.targets.append(handler)
    
    def _create_handler(self, target_type: str, config: Dict[str, Any]) -> Optional[logging.Handler]:
        """
        创建指定类型的处理器
        
        Args:
            target_type: 目标类型
            config: 配置
            
        Returns:
            日志处理器
        """
        if target_type == 'file':
            return self._create_file_handler(config)
        elif target_type == 'console':
            return self._create_console_handler(config)
        elif target_type == 'network':
            return self._create_network_handler(config)
        elif target_type == 'database':
            return self._create_database_handler(config)
        else:
            return None
    
    def _create_file_handler(self, config: Dict[str, Any]) -> logging.Handler:
        """创建文件处理器"""
        log_file = config.get('file', 'logs/app.log')
        max_size = config.get('max_size', 100) * 1024 * 1024
        backup_count = config.get('backup_count', 5)
        encoding = config.get('encoding', 'utf-8')
        
        # 创建目录
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        return logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding=encoding
        )
    
    def _create_console_handler(self, config: Dict[str, Any]) -> logging.Handler:
        """创建控制台处理器"""
        return logging.StreamHandler()
    
    def _create_network_handler(self, config: Dict[str, Any]) -> logging.Handler:
        """创建网络处理器"""
        host = config.get('host', 'localhost')
        port = config.get('port', 514)
        
        return logging.handlers.SocketHandler(host, port)
    
    def _create_database_handler(self, config: Dict[str, Any]) -> logging.Handler:
        """创建数据库处理器"""
        # 这里可以实现数据库处理器
        # 暂时返回None，需要根据具体数据库实现
        return None
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        发送日志记录到所有目标
        
        Args:
            record: 日志记录
        """
        for handler in self.targets:
            try:
                handler.emit(record)
            except Exception:
                # 记录错误但不中断其他处理器
                continue
    
    def close(self) -> None:
        """关闭所有处理器"""
        for handler in self.targets:
            try:
                handler.close()
            except Exception:
                continue
        super().close()


class AsyncLogHandler(logging.Handler):
    """
    异步日志处理器
    
    使用队列异步处理日志，提高性能。
    """
    
    def __init__(self, target_handler: logging.Handler, queue_size: int = 1000):
        """
        初始化异步处理器
        
        Args:
            target_handler: 目标处理器
            queue_size: 队列大小
        """
        super().__init__()
        
        import queue
        import threading
        
        self.target_handler = target_handler
        self.queue = queue.Queue(maxsize=queue_size)
        self.worker_thread = None
        self.running = False
        
        # 启动工作线程
        self._start_worker()
    
    def _start_worker(self) -> None:
        """启动工作线程"""
        import threading
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
    
    def _worker_loop(self) -> None:
        """工作线程循环"""
        while self.running:
            try:
                # 从队列获取记录
                record = self.queue.get(timeout=1)
                if record is None:  # 停止信号
                    break
                
                # 发送到目标处理器
                self.target_handler.emit(record)
                
            except queue.Empty:
                continue
            except Exception:
                continue
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        发送日志记录到队列
        
        Args:
            record: 日志记录
        """
        try:
            # 非阻塞方式添加到队列
            self.queue.put_nowait(record)
        except queue.Full:
            # 队列满时，丢弃最旧的记录
            try:
                self.queue.get_nowait()
                self.queue.put_nowait(record)
            except queue.Empty:
                pass
    
    def close(self) -> None:
        """关闭异步处理器"""
        self.running = False
        
        # 发送停止信号
        try:
            self.queue.put_nowait(None)
        except queue.Full:
            pass
        
        # 等待工作线程结束
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        
        # 关闭目标处理器
        self.target_handler.close()
        super().close() 