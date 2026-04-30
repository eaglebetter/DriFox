# -*- coding: utf-8 -*-
"""交互状态定义"""
from enum import Enum


class InteractionState(Enum):
    """交互状态枚举"""
    IDLE = "idle"
    STREAMING = "streaming"
    WAITING_PERMISSION = "waiting_permission"
    WAITING_QUESTION = "waiting_question"
    PAUSED = "paused"


class StreamState:
    """流式响应状态"""
    
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.is_streaming = False
        self.tool_call_depth = 0
        self.pending_tool_calls = 0
        self.first_tool_result = True
        self.tool_cancelled_by_user = False
        self.cancelled_tool_call_id = None
        self.processed_tool_ids = set()
        
    def start_stream(self):
        self.is_streaming = True
        
    def stop_stream(self):
        self.is_streaming = False
        
    def enter_tool_call(self):
        self.tool_call_depth += 1
        self.pending_tool_calls += 1
        self.first_tool_result = True
        
    def exit_tool_call(self):
        if self.pending_tool_calls > 0:
            self.pending_tool_calls -= 1
            
    def mark_tool_processed(self, tool_id: str):
        self.processed_tool_ids.add(tool_id)
        
    def is_tool_processed(self, tool_id: str) -> bool:
        return tool_id in self.processed_tool_ids