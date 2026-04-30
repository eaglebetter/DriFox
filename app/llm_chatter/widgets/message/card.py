# -*- coding: utf-8 -*-
"""消息卡片模块 - 向后兼容层

此文件作为向后兼容层，保留原 message_card.py 的所有导出。
新代码应使用 message.card 或直接从 widgets 导入。
"""
# 重新导出所有原有导出
from app.llm_chatter.widgets.message_card import (
    MessageCard,
    create_welcome_card,
)

__all__ = ["MessageCard", "create_welcome_card"]