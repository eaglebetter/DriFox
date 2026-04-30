# -*- coding: utf-8 -*-
"""消息模块 - 包含消息卡片、渲染器、样式定义"""
from app.llm_chatter.widgets.message.style import (
    ACTION_COLOR_MAP,
    DEFAULT_ACTION_COLOR,
    get_card_style,
)
from app.llm_chatter.widgets.message.renderer import (
    render_markdown,
    render_tool_block,
    render_thinking_box,
    get_action_color,
    wrap_html_with_css,
    StreamingRenderer,
)
from app.llm_chatter.widgets.message.viewer import (
    CodeWebViewer,
    PlainTextViewer,
    ConsoleMonitorPage,
)
from app.llm_chatter.widgets.message.card import (
    MessageCard,
    TagWidget,
    create_welcome_card,
)

__all__ = [
    # 样式
    "ACTION_COLOR_MAP",
    "DEFAULT_ACTION_COLOR",
    "get_card_style",
    # 渲染器
    "render_markdown",
    "render_tool_block",
    "render_thinking_box",
    "get_action_color",
    "wrap_html_with_css",
    "StreamingRenderer",
    # 查看器
    "CodeWebViewer",
    "PlainTextViewer",
    "ConsoleMonitorPage",
    # 卡片
    "MessageCard",
    "TagWidget",
    "create_welcome_card",
]
