"""
工作流引擎适配器模块

提供与各种工作流引擎的集成接口，包括n8n、dify等。
"""

from .base_adapter import WorkflowEngineAdapter
from .n8n_adapter import N8nAdapter
# from .dify_adapter import DifyAdapter  # 暂时注释，文件不存在

__all__ = [
    'WorkflowEngineAdapter',
    'N8nAdapter', 
    # 'DifyAdapter'  # 暂时注释
] 