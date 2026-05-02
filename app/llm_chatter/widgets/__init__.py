# -*- coding: utf-8 -*-
"""
llm_chatter widgets - 大模型对话框 UI 组件
"""

# 核心卡片
from app.llm_chatter.widgets.base_settings_card import BaseSettingsCard
from app.llm_chatter.widgets.llm_settings_card import LLMSettingsCard
from app.llm_chatter.widgets.history_card import HistoryCard, get_message_preview
from app.llm_chatter.widgets.message_card import MessageCard, create_welcome_card
from app.llm_chatter.widgets.model_config_card import ModelConfigCard
from app.llm_chatter.widgets.model_selector_popup import ModelSelectorPopup

# 悬浮组件
from app.llm_chatter.widgets.tool_floating_widget import ToolFloatingWidget
from app.llm_chatter.widgets.sub_agent_floating_widget import SubAgentFloatingWidget
from app.llm_chatter.widgets.todo_floating_widget import TodoFloatingWidget
from app.llm_chatter.widgets.question_floating_widget import QuestionFloatingWidget

# 对话组件
from app.llm_chatter.widgets.bottom_input_area import SendableTextEdit
from app.llm_chatter.widgets.context_usage_ring import ContextUsageRing
from app.llm_chatter.widgets.conversation_node_preview import ConversationNodePreview
from app.llm_chatter.widgets.memory_manager import MemoryManagerDialog, MemoryItemWidget

# 对话框
from app.llm_chatter.widgets.file_undo_dialog import FileUndoPreviewDialog

__all__ = [
    # 核心卡片
    "BaseSettingsCard",
    "LLMSettingsCard",
    "HistoryCard",
    "get_message_preview",
    "MessageCard",
    "create_welcome_card",
    "ModelConfigCard",
    "ModelSelectorPopup",
    # 悬浮组件
    "ToolFloatingWidget",
    "SubAgentFloatingWidget",
    "TodoFloatingWidget",
    "QuestionFloatingWidget",
    # 对话组件
    "SendableTextEdit",
    "ContextUsageRing",
    "ConversationNodePreview",
    "MemoryManagerDialog",
    "MemoryItemWidget",
    # 对话框
    "FileUndoPreviewDialog",
]
