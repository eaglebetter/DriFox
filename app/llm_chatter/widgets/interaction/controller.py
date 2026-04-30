# -*- coding: utf-8 -*-
"""交互控制器 - 管理 Agent 切换、权限确认、状态同步"""
from typing import Optional, Dict, Any
from loguru import logger

from app.llm_chatter.widgets.interaction.state import InteractionState, StreamState


class InteractionController:
    """交互状态机：管理 Agent 切换、权限确认、状态同步"""
    
    def __init__(self, event_bus):
        self._event_bus = event_bus
        self._state = InteractionState.IDLE
        self._stream_state = StreamState()
        self._current_agent = "plan"
        self._permission_queue = []
        self._question_tool_call_id = None
        
        # 注册事件监听
        self._event_bus.on("stream_started", self._on_stream_started)
        self._event_bus.on("stream_finished", self._on_stream_finished)
        self._event_bus.on("tool_call_started", self._on_tool_call_started)
        self._event_bus.on("tool_result_received", self._on_tool_result_received)
        
    @property
    def state(self) -> InteractionState:
        return self._state
        
    @property
    def stream_state(self) -> StreamState:
        return self._stream_state
        
    @property
    def current_agent(self) -> str:
        return self._current_agent
        
    @property
    def is_streaming(self) -> bool:
        return self._stream_state.is_streaming
        
    def set_agent(self, agent: str):
        """设置当前 Agent"""
        if agent != self._current_agent:
            old_agent = self._current_agent
            self._current_agent = agent
            self._event_bus.emit("agent_changed", old_agent, agent)
            
    def start_stream(self):
        """开始流式响应"""
        self._state = InteractionState.STREAMING
        self._stream_state.start_stream()
        self._event_bus.emit("stream_started")
        
    def stop_stream(self):
        """停止流式响应"""
        self._state = InteractionState.IDLE
        self._stream_state.stop_stream()
        self._event_bus.emit("stream_finished")
        
    def request_permission(self, tool_call_id: str, details: Dict):
        """请求权限"""
        self._state = InteractionState.WAITING_PERMISSION
        self._permission_queue.append((tool_call_id, details))
        self._event_bus.emit("permission_requested", tool_call_id, details)
        
    def confirm_permission(self):
        """确认权限"""
        if self._permission_queue:
            tool_call_id, _ = self._permission_queue.pop(0)
            self._state = InteractionState.STREAMING if self._stream_state.is_streaming else InteractionState.IDLE
            self._event_bus.emit("permission_confirmed", tool_call_id)
            
    def cancel_permission(self):
        """取消权限"""
        if self._permission_queue:
            tool_call_id, _ = self._permission_queue.pop(0)
            self._stream_state.tool_cancelled_by_user = True
            self._stream_state.cancelled_tool_call_id = tool_call_id
            self._state = InteractionState.IDLE
            self._event_bus.emit("permission_cancelled", tool_call_id)
            
    def ask_question(self, tool_call_id: str, question: str):
        """询问用户问题"""
        self._state = InteractionState.WAITING_QUESTION
        self._question_tool_call_id = tool_call_id
        self._event_bus.emit("question_asked", tool_call_id, question)
        
    def answer_question(self, answer: str):
        """回答问题"""
        tool_call_id = self._question_tool_call_id
        self._question_tool_call_id = None
        self._state = InteractionState.IDLE if not self._stream_state.is_streaming else InteractionState.STREAMING
        self._event_bus.emit("question_answered", tool_call_id, answer)
        
    def cancel_question(self):
        """取消问题"""
        tool_call_id = self._question_tool_call_id
        self._question_tool_call_id = None
        self._state = InteractionState.IDLE
        self._event_bus.emit("question_cancelled", tool_call_id)
        
    def reset(self):
        """重置状态"""
        self._state = InteractionState.IDLE
        self._stream_state.reset()
        self._permission_queue.clear()
        self._question_tool_call_id = None
        
    def _on_stream_started(self):
        self._stream_state.start_stream()
        if self._state != InteractionState.WAITING_PERMISSION and self._state != InteractionState.WAITING_QUESTION:
            self._state = InteractionState.STREAMING
        
    def _on_stream_finished(self):
        self._stream_state.stop_stream()
        if self._state not in (InteractionState.WAITING_PERMISSION, InteractionState.WAITING_QUESTION):
            self._state = InteractionState.IDLE
        
    def _on_tool_call_started(self, tool_call_id: str, tool_name: str, arguments: dict, round_id: str):
        self._stream_state.enter_tool_call()
        self._stream_state.mark_tool_processed(tool_call_id)
        
    def _on_tool_result_received(self, tool_call_id: str, result: Any, success: bool):
        self._stream_state.exit_tool_call()