# -*- coding: utf-8 -*-
"""
API 前端适配器
将 Backend 适配到 HTTP API 接口
"""

from typing import Dict, Any
from loguru import logger


class APIFrontendAdapter:
    """
    API 前端适配器
    
    用途：
    1. 将 Backend 适配到 FastAPI/Http 接口
    2. 将 Backend 的回调转换为 HTTP 响应
    3. 支持无 UI 模式运行
    
    使用方式：
    ```python
    from app.core import ChatBackend
    from app.core.api_adapter import APIFrontendAdapter
    
    backend = ChatBackend()
    adapter = APIFrontendAdapter(backend)
    
    # 初始化后端组件
    backend.initialize(
        get_model_config=lambda: {...},
        tool_executor=...,
        agent_manager=...,
        memory_manager=...,
    )
    
    # 处理 API 请求
    response = adapter.handle_send_message({"text": "Hello"})
    ```
    """
    
    def __init__(self, backend):
        self._backend = backend
        self._response_buffer = []
        
        # 设置 Backend 回调
        from app.core.backend import BackendCallbacks
        callbacks = BackendCallbacks(
            on_stream_started=self._on_stream_started,
            on_stream_chunk=self._on_stream_chunk,
            on_stream_finished=self._on_stream_finished,
            on_error=self._on_error,
            on_tool_call_started=self._on_tool_call_started,
        )
        self._backend.set_callbacks(callbacks)
    
    def _on_stream_started(self):
        self._response_buffer = []
    
    def _on_stream_chunk(self, content: str):
        self._response_buffer.append(content)
    
    def _on_stream_finished(self, data: dict):
        self._response_buffer.append("[DONE]")
    
    def _on_error(self, error: str):
        self._response_buffer.append(f"[ERROR] {error}")
    
    def _on_tool_call_started(self, tool_call_id: str, tool_name: str, args: dict):
        logger.info(f"[API] Tool call: {tool_name}")
    
    def handle_send_message(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理发送消息请求
        
        Args:
            request: {"text": "...", "agent": "plan"}
            
        Returns:
            {"content": "...", "messages": [...]}
        """
        text = request.get("text", "")
        agent = request.get("agent")
        
        self._response_buffer = []
        self._backend.send_message(text, agent_name=agent)
        
        # 等待响应（实际应该异步，这里简化）
        import time
        for _ in range(100):  # 最多等待 10 秒
            time.sleep(0.1)
            if "[DONE]" in self._response_buffer or "[ERROR]" in "".join(self._response_buffer):
                break
        
        return {
            "content": "".join(self._response_buffer).replace("[DONE]", ""),
            "session_id": self._backend.get_current_session().session_id if self._backend.get_current_session() else None,
        }
    
    def handle_create_session(self) -> Dict[str, Any]:
        """创建新会话"""
        session = self._backend.create_session()
        return {
            "session_id": session.session_id,
            "name": session.name,
        }
    
    def handle_list_sessions(self) -> Dict[str, Any]:
        """列出所有会话"""
        sessions = self._backend.get_all_sessions()
        return {
            "sessions": [
                {"id": s.session_id, "name": s.name}
                for s in sessions
            ]
        }
    
    def handle_switch_session(self, session_id: str) -> Dict[str, Any]:
        """切换会话"""
        sessions = self._backend.get_all_sessions()
        for i, s in enumerate(sessions):
            if s.session_id == session_id:
                self._backend.switch_session(i)
                return {"success": True}
        return {"success": False, "error": "Session not found"}
