"""
回调控制模块

实现企业级架构的回调机制，支持：
- 状态锚点：将工具执行结果写入memory
- 审计锚点：将callback行为写入trace
- 链路锚点：决定是否继续执行后续行为
- 异常链回调与中断恢复
- 多Agent协同下的回调权限管理
"""

from .callback_handler import CallbackHandler, CallbackType, CallbackStatus, CallbackResult

__all__ = [
    "CallbackHandler",
    "CallbackType", 
    "CallbackStatus",
    "CallbackResult"
] 