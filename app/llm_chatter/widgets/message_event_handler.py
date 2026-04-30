# -*- coding: utf-8 -*-
"""
消息事件处理器 - 处理流式消息事件

从 main_widget.py 提取的消息事件处理逻辑。
使用 EventBus 进行解耦。
"""
from typing import Optional, Callable, Any, List, Dict
from PyQt5.QtCore import QTimer

from app.llm_chatter.widgets.message import MessageCard


class MessageEventHandler:
    """
    消息事件处理器
    
    负责处理消息相关的 UI 更新事件：
    1. 内容接收（流式/非流式）
    2. 思考内容接收
    3. 工具调用开始/结束
    4. 消息更新
    """
    
    def __init__(
        self,
        event_bus,
        get_current_card: Callable[[], Optional[MessageCard]],
        scroll_to_bottom: Callable[[], None],
        update_context_usage: Callable[[], None],
    ):
        self._event_bus = event_bus
        self._get_current_card = get_current_card
        self._scroll_to_bottom = scroll_to_bottom
        self._update_context_usage = update_context_usage
        
        # 缓冲区和状态
        self._content_buffer = []
        self._thinking_buffer = []
        self._update_timer: Optional[QTimer] = None
        self._pending_scroll = False
        
        # 注册事件
        self._register_events()
        
    def _register_events(self):
        """注册需要处理的事件"""
        self._event_bus.on("content_received", self._on_content_received)
        self._event_bus.on("reasoning_content_received", self._on_reasoning_content_received)
        self._event_bus.on("tool_result_received", self._on_tool_result_received)
        self._event_bus.on("stream_finished", self._on_stream_finished)
        
    def cleanup(self):
        """清理事件注册"""
        self._event_bus.off("content_received", self._on_content_received)
        self._event_bus.off("reasoning_content_received", self._on_reasoning_content_received)
        self._event_bus.off("tool_result_received", self._on_tool_result_received)
        self._event_bus.off("stream_finished", self._on_stream_finished)
        
    def _on_content_received(self, content_piece: str):
        """处理接收到的内容"""
        self._content_buffer.append(content_piece)
        card = self._get_current_card()
        if card:
            card.append_text(content_piece)
        self._schedule_update()
        
    def _on_reasoning_content_received(self, reasoning_piece: str):
        """处理接收到的思考内容"""
        self._thinking_buffer.append(reasoning_piece)
        # 思考内容通常不直接显示，需要特殊处理
        
    def _on_tool_result_received(self, tool_call_id: str, result: Any, success: bool):
        """处理工具执行结果"""
        card = self._get_current_card()
        if card:
            card.append_tool_result(tool_call_id, result, success)
            
    def _on_stream_finished(self):
        """流式响应结束"""
        self._flush_buffers()
        if self._update_context_usage:
            self._update_context_usage()
            
    def _schedule_update(self):
        """调度 UI 更新"""
        if self._update_timer is None:
            self._update_timer = QTimer()
            self._update_timer.setSingleShot(True)
            self._update_timer.timeout.connect(self._do_update)
            
        if not self._update_timer.isActive():
            self._update_timer.start(50)  # 50ms 防抖
            
    def _do_update(self):
        """执行 UI 更新"""
        if self._pending_scroll:
            self._scroll_to_bottom()
            self._pending_scroll = False
            
    def _flush_buffers(self):
        """刷新缓冲区"""
        self._content_buffer.clear()
        self._thinking_buffer.clear()
        
    def get_buffered_content(self) -> str:
        """获取缓冲的内容"""
        return "".join(self._content_buffer)
        
    def get_buffered_thinking(self) -> str:
        """获取缓冲的思考内容"""
        return "".join(self._thinking_buffer)