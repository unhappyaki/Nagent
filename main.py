"""
企业级Agent架构系统主程序

启动整个Agent系统，包括：
- 配置加载
- 服务初始化
- API服务器启动
- 监控系统启动
"""

import asyncio
import os
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
import structlog

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from examples import agent_routes
from src.core.agent import BaseAgent, AgentConfig, AgentType
from src.communication.acp import ACPServer
from src.coordination.registry import AgentRegistry
from src.monitoring.log import setup_logging
from config.config_manager import ConfigManager


# 配置日志
logger = structlog.get_logger(__name__)


class AgentSystem:
    """
    企业级Agent系统主类
    
    负责整个系统的生命周期管理
    """
    
    def __init__(self):
        """初始化Agent系统"""
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        
        # 初始化组件
        self.agent_registry = AgentRegistry()
        self.acp_server = ACPServer(
            host=self.config["communication"]["acp"]["host"],
            port=self.config["communication"]["acp"]["port"]
        )
        
        # FastAPI应用
        self.app = FastAPI(
            title="企业级Agent架构系统",
            description="基于21个核心模块构建的企业级多智能体协同系统",
            version="1.0.0"
        )
        
        # 系统状态
        self.is_running = False
        
        logger.info("Agent system initialized")
    
    async def start(self):
        """启动系统"""
        try:
            logger.info("Starting agent system...")
            
            # 设置日志
            setup_logging(self.config["monitoring"]["log_level"])
            
            # 启动ACP服务器
            await self.acp_server.start()
            
            # 注册默认Agent
            await self._register_default_agents()
            
            # 设置API路由
            self._setup_api_routes()
            
            self.is_running = True
            
            logger.info("Agent system started successfully")
            
        except Exception as e:
            logger.error("Failed to start agent system", error=str(e))
            raise
    
    async def stop(self):
        """停止系统"""
        try:
            logger.info("Stopping agent system...")
            
            # 停止ACP服务器
            await self.acp_server.stop()
            
            # 停止所有Agent
            await self.agent_registry.stop_all_agents()
            
            self.is_running = False
            
            logger.info("Agent system stopped successfully")
            
        except Exception as e:
            logger.error("Failed to stop agent system", error=str(e))
            raise
    
    async def _register_default_agents(self):
        """注册默认Agent"""
        # 任务Agent
        task_agent_config = AgentConfig(
            agent_id="task_agent_001",
            agent_type=AgentType.TASK,
            name="任务处理Agent",
            description="负责处理各种任务的核心Agent",
            model="gpt-4",
            max_tokens=4000,
            temperature=0.7
        )
        
        # 审查Agent
        review_agent_config = AgentConfig(
            agent_id="review_agent_001",
            agent_type=AgentType.REVIEW,
            name="内容审查Agent",
            description="负责内容审查和质量检查",
            model="gpt-4",
            max_tokens=2000,
            temperature=0.3
        )
        
        # 写作Agent
        writer_agent_config = AgentConfig(
            agent_id="writer_agent_001",
            agent_type=AgentType.WRITER,
            name="内容创作Agent",
            description="负责内容创作和写作",
            model="gpt-4",
            max_tokens=6000,
            temperature=0.8
        )
        
        # 注册Agent
        await self.agent_registry.register_agent(task_agent_config)
        await self.agent_registry.register_agent(review_agent_config)
        await self.agent_registry.register_agent(writer_agent_config)
        
        logger.info("Default agents registered")
    
    def _setup_api_routes(self):
        """设置API路由"""
        from src.api.routes import system_routes, monitoring_routes
        
        # 注册路由
        self.app.include_router(agent_routes.router, prefix="/api/v1/agents", tags=["agents"])
        self.app.include_router(system_routes.router, prefix="/api/v1/system", tags=["system"])
        self.app.include_router(monitoring_routes.router, prefix="/api/v1/monitoring", tags=["monitoring"])
        
        # 健康检查
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "system": "Enterprise Agent System",
                "version": "1.0.0",
                "agents_count": len(self.agent_registry.get_all_agents())
            }
        
        logger.info("API routes configured")
    
    def get_app(self) -> FastAPI:
        """获取FastAPI应用"""
        return self.app


async def main():
    """主函数"""
    # 创建系统实例
    system = AgentSystem()
    
    try:
        # 启动系统
        await system.start()
        
        # 启动FastAPI服务器
        app = system.get_app()
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error("System error", error=str(e))
    finally:
        # 停止系统
        await system.stop()


if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main()) 