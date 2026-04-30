# -*- coding: utf-8 -*-
"""
消息卡片模块 - 向后兼容层

此文件保留用于向后兼容，新代码应使用：
- app.llm_chatter.widgets.message.card.MessageCard
- app.llm_chatter.widgets.message.viewer.CodeWebViewer
- app.llm_chatter.widgets.message.viewer.PlainTextViewer
"""
# 向后兼容导出
from app.llm_chatter.widgets.message.card import (
    MessageCard,
    TagWidget,
    create_welcome_card,
)
from app.llm_chatter.widgets.message.viewer import (
    CodeWebViewer,
    PlainTextViewer,
    ConsoleMonitorPage,
)
from app.llm_chatter.widgets.message.renderer import (
    render_markdown,
    render_tool_block,
    render_thinking_box,
    unwrap_code_blocks_with_context_links,
    strip_code_blocks,
    get_action_color,
    wrap_html_with_css,
    StreamingRenderer,
)

__all__ = [
    "MessageCard",
    "TagWidget",
    "create_welcome_card",
    "CodeWebViewer",
    "PlainTextViewer",
    "ConsoleMonitorPage",
    "render_markdown",
    "render_tool_block",
    "render_thinking_box",
    "unwrap_code_blocks_with_context_links",
    "strip_code_blocks",
    "get_action_color",
    "wrap_html_with_css",
    "StreamingRenderer",
]
