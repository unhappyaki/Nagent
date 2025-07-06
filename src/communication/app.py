"""
ACP协议Flask主服务端入口
提供HTTP接口层，用于管理和监控ACP协议服务
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import structlog

from .acp_server import ACPServer
from .dispatcher import TaskDispatcher, DispatchStrategy
from .utils import TimeUtils, ValidationUtils, ConfigUtils
from .message_schema import ACPMessageBuilder, MessagePriority

logger = structlog.get_logger(__name__)


class ACPFlaskApp:
    """ACP协议Flask应用"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or ConfigUtils.DEFAULT_CONFIG
        self.app = Flask(__name__)
        CORS(self.app)  # 启用CORS
        
        # 初始化组件
        self.acp_server = None
        self.dispatcher = None
        self.message_builder = ACPMessageBuilder("acp_flask_app")
        
        # 应用状态
        self.is_running = False
        self.start_time = None
        
        # 注册路由
        self._register_routes()
        
        logger.info("ACPFlaskApp initialized")
    
    def _register_routes(self):
        """注册Flask路由"""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """健康检查"""
            return jsonify({
                "status": "healthy" if self.is_running else "stopped",
                "timestamp": TimeUtils.get_current_timestamp(),
                "uptime": self._get_uptime() if self.start_time else 0,
                "version": "1.0.0"
            })
        
        @self.app.route('/status', methods=['GET'])
        def status():
            """获取服务状态"""
            server_stats = {}
            dispatcher_stats = {}
            
            if self.acp_server:
                server_stats = self.acp_server.get_server_stats()
            
            if self.dispatcher:
                dispatcher_stats = self.dispatcher.get_dispatcher_stats()
            
            return jsonify({
                "service_status": "running" if self.is_running else "stopped",
                "start_time": self.start_time,
                "uptime": self._get_uptime() if self.start_time else 0,
                "server_stats": server_stats,
                "dispatcher_stats": dispatcher_stats,
                "config": self._get_public_config()
            })
        
        @self.app.route('/agents', methods=['GET'])
        def list_agents():
            """获取已注册的Agent列表"""
            if not self.acp_server:
                return jsonify({"error": "ACP server not initialized"}), 503
            
            try:
                agents = self.acp_server.get_registered_agents()
                return jsonify({
                    "agents": agents,
                    "count": len(agents),
                    "timestamp": TimeUtils.get_current_timestamp()
                })
            except Exception as e:
                logger.error("Failed to list agents", error=str(e))
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/agents/<agent_id>', methods=['GET'])
        def get_agent(agent_id: str):
            """获取特定Agent信息"""
            if not self.acp_server:
                return jsonify({"error": "ACP server not initialized"}), 503
            
            try:
                agent_info = self.acp_server.get_agent_info(agent_id)
                if not agent_info:
                    return jsonify({"error": "Agent not found"}), 404
                
                return jsonify({
                    "agent": agent_info,
                    "timestamp": TimeUtils.get_current_timestamp()
                })
            except Exception as e:
                logger.error("Failed to get agent info", agent_id=agent_id, error=str(e))
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/agents/<agent_id>', methods=['DELETE'])
        def unregister_agent(agent_id: str):
            """注销Agent"""
            if not self.acp_server:
                return jsonify({"error": "ACP server not initialized"}), 503
            
            try:
                success = asyncio.run(self.acp_server.unregister_agent(agent_id))
                if success:
                    return jsonify({
                        "message": f"Agent {agent_id} unregistered successfully",
                        "timestamp": TimeUtils.get_current_timestamp()
                    })
                else:
                    return jsonify({"error": "Failed to unregister agent"}), 400
            except Exception as e:
                logger.error("Failed to unregister agent", agent_id=agent_id, error=str(e))
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/tasks', methods=['POST'])
        def submit_task():
            """提交任务"""
            if not self.dispatcher:
                return jsonify({"error": "Task dispatcher not initialized"}), 503
            
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "JSON data required"}), 400
                
                # 验证必填字段
                required_fields = ['task_type', 'task_data']
                for field in required_fields:
                    if field not in data:
                        return jsonify({"error": f"Missing required field: {field}"}), 400
                
                # 提交任务
                task_id = asyncio.run(self.dispatcher.submit_task(
                    task_type=data['task_type'],
                    task_data=data['task_data'],
                    required_capabilities=data.get('required_capabilities', []),
                    priority=data.get('priority', MessagePriority.NORMAL.value),
                    timeout=data.get('timeout', 300),
                    max_retries=data.get('max_retries', 3)
                ))
                
                return jsonify({
                    "task_id": task_id,
                    "message": "Task submitted successfully",
                    "timestamp": TimeUtils.get_current_timestamp()
                }), 201
                
            except Exception as e:
                logger.error("Failed to submit task", error=str(e))
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/tasks', methods=['GET'])
        def list_tasks():
            """获取任务列表"""
            if not self.dispatcher:
                return jsonify({"error": "Task dispatcher not initialized"}), 503
            
            try:
                stats = self.dispatcher.get_dispatcher_stats()
                return jsonify({
                    "stats": stats,
                    "timestamp": TimeUtils.get_current_timestamp()
                })
            except Exception as e:
                logger.error("Failed to list tasks", error=str(e))
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/tasks/<task_id>', methods=['GET'])
        def get_task(task_id: str):
            """获取任务状态"""
            if not self.dispatcher:
                return jsonify({"error": "Task dispatcher not initialized"}), 503
            
            try:
                task_status = asyncio.run(self.dispatcher.get_task_status(task_id))
                if not task_status:
                    return jsonify({"error": "Task not found"}), 404
                
                return jsonify({
                    "task": task_status,
                    "timestamp": TimeUtils.get_current_timestamp()
                })
            except Exception as e:
                logger.error("Failed to get task status", task_id=task_id, error=str(e))
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/tasks/<task_id>', methods=['DELETE'])
        def cancel_task(task_id: str):
            """取消任务"""
            if not self.dispatcher:
                return jsonify({"error": "Task dispatcher not initialized"}), 503
            
            try:
                success = asyncio.run(self.dispatcher.cancel_task(task_id))
                if success:
                    return jsonify({
                        "message": f"Task {task_id} cancelled successfully",
                        "timestamp": TimeUtils.get_current_timestamp()
                    })
                else:
                    return jsonify({"error": "Failed to cancel task or task not found"}), 400
            except Exception as e:
                logger.error("Failed to cancel task", task_id=task_id, error=str(e))
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/config', methods=['GET'])
        def get_config():
            """获取配置信息"""
            return jsonify({
                "config": self._get_public_config(),
                "timestamp": TimeUtils.get_current_timestamp()
            })
        
        @self.app.route('/config', methods=['PUT'])
        def update_config():
            """更新配置"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "JSON data required"}), 400
                
                # 这里可以添加配置验证和更新逻辑
                # 当前只是示例，实际应用中需要更复杂的配置管理
                
                return jsonify({
                    "message": "Configuration update not implemented",
                    "timestamp": TimeUtils.get_current_timestamp()
                }), 501
                
            except Exception as e:
                logger.error("Failed to update config", error=str(e))
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/metrics', methods=['GET'])
        def get_metrics():
            """获取指标信息"""
            try:
                metrics = {
                    "service": {
                        "uptime": self._get_uptime() if self.start_time else 0,
                        "status": "running" if self.is_running else "stopped"
                    }
                }
                
                if self.acp_server:
                    metrics["server"] = self.acp_server.get_server_stats()
                
                if self.dispatcher:
                    metrics["dispatcher"] = self.dispatcher.get_dispatcher_stats()
                
                return jsonify({
                    "metrics": metrics,
                    "timestamp": TimeUtils.get_current_timestamp()
                })
                
            except Exception as e:
                logger.error("Failed to get metrics", error=str(e))
                return jsonify({"error": str(e)}), 500
        
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                "error": "Not Found",
                "message": "The requested resource was not found",
                "timestamp": TimeUtils.get_current_timestamp()
            }), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "timestamp": TimeUtils.get_current_timestamp()
            }), 500
    
    async def start_services(self):
        """启动ACP服务"""
        try:
            # 启动ACP服务器
            server_config = self.config.get('server', {})
            self.acp_server = ACPServer(
                host=server_config.get('host', 'localhost'),
                port=server_config.get('port', 8000)
            )
            await self.acp_server.start()
            
            # 启动任务分发器
            dispatcher_config = self.config.get('dispatcher', {})
            strategy_name = dispatcher_config.get('strategy', 'capability_match')
            strategy = DispatchStrategy(strategy_name)
            
            self.dispatcher = TaskDispatcher(
                strategy=strategy,
                acp_client=None  # 可以连接到自己的服务器
            )
            await self.dispatcher.start()
            
            self.is_running = True
            self.start_time = TimeUtils.get_current_timestamp()
            
            logger.info("ACP services started successfully")
            
        except Exception as e:
            logger.error("Failed to start ACP services", error=str(e))
            raise
    
    async def stop_services(self):
        """停止ACP服务"""
        try:
            if self.dispatcher:
                await self.dispatcher.stop()
            
            if self.acp_server:
                await self.acp_server.stop()
            
            self.is_running = False
            
            logger.info("ACP services stopped successfully")
            
        except Exception as e:
            logger.error("Failed to stop ACP services", error=str(e))
            raise
    
    def run(self, host: str = None, port: int = None, debug: bool = False):
        """运行Flask应用"""
        # 获取配置
        flask_config = self.config.get('flask', {})
        host = host or flask_config.get('host', '0.0.0.0')
        port = port or flask_config.get('port', 5000)
        
        # 启动ACP服务
        try:
            asyncio.run(self.start_services())
        except Exception as e:
            logger.error("Failed to start ACP services", error=str(e))
            return
        
        try:
            # 启动Flask应用
            logger.info(f"Starting Flask app on {host}:{port}")
            self.app.run(host=host, port=port, debug=debug, threaded=True)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            # 停止ACP服务
            try:
                asyncio.run(self.stop_services())
            except Exception as e:
                logger.error("Failed to stop ACP services", error=str(e))
    
    def _get_uptime(self) -> float:
        """获取运行时间（秒）"""
        if not self.start_time:
            return 0
        
        try:
            start_dt = TimeUtils.parse_iso_timestamp(self.start_time)
            current_dt = datetime.utcnow()
            return (current_dt - start_dt).total_seconds()
        except Exception:
            return 0
    
    def _get_public_config(self) -> Dict[str, Any]:
        """获取公开配置（移除敏感信息）"""
        public_config = {}
        
        # 只包含非敏感配置
        safe_keys = ['message', 'agent', 'dispatcher']
        for key in safe_keys:
            if key in self.config:
                public_config[key] = self.config[key]
        
        # 添加服务器信息（移除敏感信息）
        if 'server' in self.config:
            server_config = self.config['server'].copy()
            # 移除敏感信息
            server_config.pop('secret_key', None)
            server_config.pop('password', None)
            public_config['server'] = server_config
        
        return public_config


def create_app(config: Dict[str, Any] = None) -> ACPFlaskApp:
    """创建ACP Flask应用实例"""
    return ACPFlaskApp(config)


def main():
    """主函数，用于直接运行"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ACP Protocol Flask Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--config', help='Path to configuration file')
    
    args = parser.parse_args()
    
    # 加载配置
    config = ConfigUtils.DEFAULT_CONFIG
    if args.config:
        try:
            with open(args.config, 'r') as f:
                custom_config = json.load(f)
                # 合并配置
                for key, value in custom_config.items():
                    if key in config and isinstance(config[key], dict) and isinstance(value, dict):
                        config[key].update(value)
                    else:
                        config[key] = value
        except Exception as e:
            logger.error("Failed to load config file", config_file=args.config, error=str(e))
            return
    
    # 创建并运行应用
    app = create_app(config)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main() 