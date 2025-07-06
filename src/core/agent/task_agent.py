"""
任务Agent

一个具体的Agent实现，用于处理各种任务
"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

import structlog

from .base_agent import BaseAgent, AgentConfig, AgentType, AgentMessage


logger = structlog.get_logger(__name__)


class TaskAgent(BaseAgent):
    """
    任务Agent
    
    专门用于处理各种任务的Agent实现
    """
    
    def __init__(self, config: AgentConfig):
        """
        初始化任务Agent
        
        Args:
            config: Agent配置
        """
        super().__init__(config)
        
        # 任务Agent特有的属性
        self.task_history: List[Dict[str, Any]] = []
        self.task_templates: Dict[str, Dict[str, Any]] = {}
        self.skill_set: List[str] = []
        
        # 初始化任务模板
        self._init_task_templates()
        
        logger.info("Task agent initialized", agent_id=self.agent_id)
    
    async def _on_start(self) -> None:
        """Agent启动时的自定义逻辑"""
        logger.info("Task agent starting", agent_id=self.agent_id)
        
        # 加载技能集
        await self._load_skill_set()
        
        # 初始化任务模板
        await self._init_task_templates()
        
        logger.info("Task agent started", agent_id=self.agent_id)
    
    async def _on_stop(self) -> None:
        """Agent停止时的自定义逻辑"""
        logger.info("Task agent stopping", agent_id=self.agent_id)
        
        # 保存任务历史
        await self._save_task_history()
        
        # 清理资源
        self.task_history.clear()
        self.task_templates.clear()
        
        logger.info("Task agent stopped", agent_id=self.agent_id)
    
    async def _on_message_received(self, message: AgentMessage) -> None:
        """收到消息时的处理逻辑"""
        logger.info(
            "Task agent received message",
            agent_id=self.agent_id,
            message_id=message.message_id,
            sender_id=message.sender_id
        )
        
        # 根据消息类型处理
        if message.message_type == "task_request":
            await self._handle_task_request(message)
        elif message.message_type == "task_update":
            await self._handle_task_update(message)
        elif message.message_type == "task_cancel":
            await self._handle_task_cancel(message)
        else:
            # 默认处理：将消息内容作为任务执行
            await self.execute_task(message.content)
    
    async def _handle_task_request(self, message: AgentMessage) -> None:
        """处理任务请求"""
        try:
            task_data = message.metadata.get("task_data", {})
            task_type = task_data.get("type", "general")
            task_content = task_data.get("content", message.content)
            
            # 创建任务
            task_id = await self.submit_task(
                task_content,
                priority=message.metadata.get("priority", 0),
                task_type=task_type,
                **task_data
            )
            
            # 发送确认消息
            response_message = AgentMessage(
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                content=f"任务已接收，任务ID: {task_id}",
                message_type="task_confirmation",
                metadata={"task_id": task_id}
            )
            
            # 这里应该通过消息系统发送响应
            logger.info("Task request handled", task_id=task_id)
            
        except Exception as e:
            logger.error("Failed to handle task request", error=str(e))
    
    async def _handle_task_update(self, message: AgentMessage) -> None:
        """处理任务更新"""
        task_id = message.metadata.get("task_id")
        if task_id and task_id in self.active_tasks:
            # 更新任务
            task = self.active_tasks[task_id]
            task.task_data.update(message.metadata.get("updates", {}))
            logger.info("Task updated", task_id=task_id)
    
    async def _handle_task_cancel(self, message: AgentMessage) -> None:
        """处理任务取消"""
        task_id = message.metadata.get("task_id")
        if task_id and task_id in self.active_tasks:
            # 取消任务
            del self.active_tasks[task_id]
            logger.info("Task cancelled", task_id=task_id)
    
    async def _load_skill_set(self) -> None:
        """加载技能集"""
        # 从配置或数据库加载技能集
        self.skill_set = [
            "text_processing",
            "data_analysis", 
            "web_search",
            "file_operations",
            "http_requests",
            "mathematical_calculations"
        ]
        
        logger.info("Skill set loaded", skills=self.skill_set)
    
    def _init_task_templates(self) -> None:
        """初始化任务模板"""
        self.task_templates = {
            "text_processing": {
                "description": "文本处理任务",
                "required_skills": ["text_processing"],
                "estimated_time": 60,
                "priority": 1
            },
            "data_analysis": {
                "description": "数据分析任务",
                "required_skills": ["data_analysis", "mathematical_calculations"],
                "estimated_time": 300,
                "priority": 2
            },
            "web_search": {
                "description": "网络搜索任务",
                "required_skills": ["web_search"],
                "estimated_time": 120,
                "priority": 1
            },
            "file_operations": {
                "description": "文件操作任务",
                "required_skills": ["file_operations"],
                "estimated_time": 180,
                "priority": 2
            }
        }
    
    async def _init_task_templates(self) -> None:
        """异步初始化任务模板"""
        # 这里可以从数据库或配置文件加载模板
        logger.info("Task templates initialized")
    
    async def _save_task_history(self) -> None:
        """保存任务历史"""
        # 这里应该将任务历史保存到数据库或文件
        logger.info("Task history saved", history_count=len(self.task_history))
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            return {
                "task_id": task_id,
                "status": "active",
                "created_at": task.created_at.isoformat(),
                "task_type": task.task_type,
                "priority": task.priority
            }
        
        # 检查历史任务
        for history_task in self.task_history:
            if history_task.get("task_id") == task_id:
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "created_at": history_task.get("created_at"),
                    "completed_at": history_task.get("completed_at"),
                    "result": history_task.get("result")
                }
        
        return None
    
    async def get_task_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取任务历史
        
        Args:
            limit: 返回数量限制
            
        Returns:
            任务历史列表
        """
        return self.task_history[-limit:] if self.task_history else []
    
    async def estimate_task_time(self, task_type: str) -> int:
        """
        估算任务执行时间
        
        Args:
            task_type: 任务类型
            
        Returns:
            估算时间（秒）
        """
        template = self.task_templates.get(task_type, {})
        return template.get("estimated_time", 60)
    
    async def can_handle_task(self, task_type: str) -> bool:
        """
        检查是否能处理指定类型的任务
        
        Args:
            task_type: 任务类型
            
        Returns:
            是否能处理
        """
        template = self.task_templates.get(task_type, {})
        required_skills = template.get("required_skills", [])
        
        return all(skill in self.skill_set for skill in required_skills)
    
    async def get_available_task_types(self) -> List[Dict[str, Any]]:
        """
        获取可用的任务类型
        
        Returns:
            任务类型列表
        """
        available_types = []
        
        for task_type, template in self.task_templates.items():
            if await self.can_handle_task(task_type):
                available_types.append({
                    "type": task_type,
                    "description": template["description"],
                    "estimated_time": template["estimated_time"],
                    "priority": template["priority"]
                })
        
        return available_types


# 创建任务Agent的工厂函数
def create_task_agent(
    agent_id: str,
    name: str,
    description: str = "",
    model: str = "gpt-4",
    **kwargs
) -> TaskAgent:
    """
    创建任务Agent
    
    Args:
        agent_id: Agent ID
        name: Agent名称
        description: Agent描述
        model: 使用的模型
        **kwargs: 其他配置参数
        
    Returns:
        任务Agent实例
    """
    config = AgentConfig(
        agent_id=agent_id,
        agent_type=AgentType.TASK,
        name=name,
        description=description,
        model=model,
        **kwargs
    )
    
    return TaskAgent(config) 