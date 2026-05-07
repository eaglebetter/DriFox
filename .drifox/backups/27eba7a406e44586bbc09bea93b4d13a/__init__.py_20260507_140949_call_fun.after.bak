# -*- coding: utf-8 -*-
"""
LLM Chatter 核心模块
提供聊天引擎、工具执行器、记忆管理等核心功能
"""

from app.core.chat_engine import ChatEngine
from app.core.tool_executor import (
    ToolExecutor,
)
from app.core.memory_manager import (
    MemoryManagerCore,
)
from app.core.agent import (
    Agent,
    AgentManager,
    create_agent_manager,
)
from app.core.worker import OpenAIChatWorker
from app.core.message_content import (
    consolidate_messages,
    content_to_text,
    to_api_message,
    messages_to_api,
)
from app.core.retry_helper import (
    create_api_call_with_retry,
    retry_on_api_error,
)
from app.core.token_estimator import (
    estimate_tokens,
    count_messages_tokens,
    TokenCounter,
)
from app.core.chat_session import (
    ChatSession,
    SessionManager,
)

__all__ = [
    # 引擎与执行器
    "ChatEngine",
    "ToolExecutor",
    "MemoryManagerCore",
    # Agent 系统
    "Agent",
    "AgentManager",
    "create_agent_manager",
    # Worker
    "OpenAIChatWorker",
    # 消息处理
    "consolidate_messages",
    "content_to_text",
    "to_api_message",
    "messages_to_api",
    # 重试
    "create_api_call_with_retry",
    "retry_on_api_error",
    # Token
    "estimate_tokens",
    "count_messages_tokens",
    "TokenCounter",
    # 会话
    "ChatSession",
    "SessionManager",
]
