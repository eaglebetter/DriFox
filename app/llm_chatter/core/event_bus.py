# -*- coding: utf-8 -*-
"""事件总线 - 解耦模块间通信"""
from typing import Any, Callable, Dict, List
from loguru import logger


class EventBus:
    """事件总线，替代直接回调，解耦模块间通信"""
    
    # 事件类型常量
    CONTENT_RECEIVED = "content_received"
    REASONING_CONTENT_RECEIVED = "reasoning_content_received"
    STREAM_STARTED = "stream_started"
    STREAM_FINISHED = "stream_finished"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_SYNC_REQUESTED = "tool_call_sync_requested"
    TOOL_RESULT_RECEIVED = "tool_result_received"
    MESSAGES_UPDATED = "messages_updated"
    ERROR = "error"
    USER_MESSAGE_ADDED = "user_message_added"
    SKILL_REQUESTED = "skill_requested"
    SHELL_COMMAND_REQUESTED = "shell_command_requested"
    QUESTION_ASKED = "question_asked"
    AGENT_SWITCHED = "agent_switched"
    TASK_STATE_CHANGED = "task_state_changed"
    PERMISSION_APPROVAL_REQUESTED = "permission_approval_requested"
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._event_history: List[tuple] = []  # 用于调试
        self._max_history = 100
        
    def on(self, event_type: str, handler: Callable) -> None:
        """订阅事件"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            
    def off(self, event_type: str, handler: Callable) -> None:
        """退订事件"""
        if event_type in self._handlers:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
                
    def emit(self, event_type: str, *args, **kwargs) -> None:
        """发布事件"""
        # 记录历史
        self._event_history.append((event_type, args, kwargs))
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
            
        # 分发事件
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Event handler error for {event_type}: {e}")
                
    def clear(self, event_type: str = None) -> None:
        """清除事件订阅"""
        if event_type:
            self._handlers.pop(event_type, None)
        else:
            self._handlers.clear()
            
    def get_subscribers(self, event_type: str) -> List[Callable]:
        """获取事件订阅者（用于调试）"""
        return list(self._handlers.get(event_type, []))
    
    def has_listeners(self, event_type: str) -> bool:
        """检查是否有订阅者"""
        return len(self._handlers.get(event_type, [])) > 0