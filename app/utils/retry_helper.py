# -*- coding: utf-8 -*-
"""
向后兼容别名 - 此模块已迁移到 app.core.retry_helper
请使用 app.core.retry_helper 或 app.core 导入
"""

# 从 core 重新导出，保持向后兼容
from app.core.retry_helper import (
    is_retriable_error,
    get_error_type_name,
    retry_on_api_error,
    create_api_call_with_retry,
)

__all__ = [
    "is_retriable_error",
    "get_error_type_name",
    "retry_on_api_error",
    "create_api_call_with_retry",
]
