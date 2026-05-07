# -*- coding: utf-8 -*-
"""
向后兼容别名 - 此模块已迁移到 app.core.message_content
请使用 app.core.message_content 或 app.core 导入
"""

# 从 core 重新导出，保持向后兼容
from app.core.message_content import (
    consolidate_messages,
    content_to_text,
    to_api_message,
    messages_to_api,
    ensure_content_blocks,
    make_text_block,
    make_tool_result_block,
    normalize_message,
    extract_text_from_content,
    get_user_round_ranges,
    VALID_MESSAGE_ROLES,
    normalize_content_for_api,
    normalize_content_from_api,
    messages_to_display,
)

__all__ = [
    "consolidate_messages",
    "content_to_text",
    "to_api_message",
    "messages_to_api",
    "ensure_content_blocks",
    "make_text_block",
    "make_tool_result_block",
    "normalize_message",
    "extract_text_from_content",
    "get_user_round_ranges",
    "VALID_MESSAGE_ROLES",
    "normalize_content_for_api",
    "normalize_content_from_api",
    "messages_to_display",
]
