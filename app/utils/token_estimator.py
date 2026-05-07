# -*- coding: utf-8 -*-
"""
向后兼容别名 - 此模块已迁移到 app.core.token_estimator
请使用 app.core.token_estimator 或 app.core 导入
"""

# 从 core 重新导出，保持向后兼容
from app.core.token_estimator import (
    estimate_tokens,
    count_messages_tokens,
    truncate_text_by_tokens,
    TokenCounter,
    get_default_counter,
)

__all__ = [
    "estimate_tokens",
    "count_messages_tokens",
    "truncate_text_by_tokens",
    "TokenCounter",
    "get_default_counter",
]
