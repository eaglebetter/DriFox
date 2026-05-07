# -*- coding: utf-8 -*-
"""
ChatBackend - 纯核心后端接口
不依赖任何 UI 框架，通过回调与前端通信
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

from loguru import logger


@dataclass
class BackendCallbacks:
    """前端回调接口 - Backend 通过这些回调通知前端"""
    on_session_created: Callable[[str], None] = None          # session_id
    on_session_changed: Callable[[str], None] = None        # session_id
    on_session_deleted: Callable[[int], None] = None        # index
    on_message_added: Callable[[dict], None] = None          # message
    on_stream_started: Callable[[], None] = None
    on_stream_chunk: Callable[[str], None] = None           # content
    on_stream_finished: Callable[[dict], None] = None       # final_message
    on_reasoning_content: Callable[[str], None] = None      # content
    on_tool_call_started: Callable[[str, str, dict], None] = None  # tool_call_id, tool_name, args
    on_tool_call_result: Callable[[str, str, dict, bool], None] = None  # tool_call_id, name, result, success
    on_error: Callable[[str], None] = None                   # error_msg
    on_permission_requested: Callable[[str, str, dict], None] = None  # tool_call_id, tool_name, args
    on_subagent_started: Callable[[str], None] = None        # task_id
    on_subagent_finished: Callable[[str, str], None] = None # task_id, result
    on_context_updated: Callable[[int, int], None] = None   # token_count, limit


class ChatBackend:
    """
    聊天后端 - 纯核心业务逻辑
    
    职责：
    1. 管理会话状态
    2. 管理 ChatEngine 实例
    3. 通过回调通知前端（不依赖任何 UI 框架）
    
    使用方式：
    ```python
    # 方式1: 通过回调
    backend = ChatBackend()
    backend.set_callbacks(on_stream_chunk=lambda c: print(c, end=''))
    backend.send_message("Hello")
    
    # 方式2: 继承
    class MyBackend(ChatBackend):
        def on_stream_chunk(self, content):
            print(content, end='')
    ```
    """
    
    def __init__(self):
        # 回调
        self._callbacks: BackendCallbacks = BackendCallbacks()
        
        # 核心组件
        self._session_manager = None
        self._chat_engine = None
        self._tool_executor = None
        self._agent_manager = None
        self._memory_manager = None
        
        # 配置回调
        self._get_model_config: Optional[Callable] = None
        
        # 初始化状态
        self._initialized = False
    
    # ========== 回调设置 ==========
    
    def set_callbacks(self, callbacks: BackendCallbacks):
        """设置前端回调"""
        self._callbacks = callbacks
    
    def set_callback(self, name: str, func: Callable):
        """设置单个回调"""
        if hasattr(self._callbacks, name):
            setattr(self._callbacks, name, func)
        else:
            logger.warning(f"[ChatBackend] Unknown callback: {name}")
    
    # ========== 属性 ==========
    
    @property
    def session_manager(self):
        return self._session_manager
    
    @property
    def chat_engine(self):
        return self._chat_engine
    
    @property
    def tool_executor(self):
        return self._tool_executor
    
    @property
    def agent_manager(self):
        return self._agent_manager
    
    @property
    def memory_manager(self):
        return self._memory_manager
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    # ========== 初始化 ==========
    
    def initialize(
        self,
        get_model_config: Callable,
        tool_executor,
        agent_manager,
        memory_manager,
        session_manager=None,
        chat_engine=None,
    ):
        """
        初始化后端组件
        
        Args:
            get_model_config: 获取模型配置的回调
            tool_executor: 工具执行器实例
            agent_manager: Agent 管理器实例
            memory_manager: 记忆管理器实例
            session_manager: 会话管理器实例
            chat_engine: 已有的 ChatEngine 实例（可选）
        """
        logger.info("[ChatBackend] 初始化中...")
        
        self._get_model_config = get_model_config
        self._tool_executor = tool_executor
        self._agent_manager = agent_manager
        self._memory_manager = memory_manager
        self._session_manager = session_manager
        
        if chat_engine is not None:
            self._chat_engine = chat_engine
        elif session_manager is not None:
            from app.core.chat_engine import ChatEngine
            self._chat_engine = ChatEngine(
                session_manager=session_manager,
                get_model_config=get_model_config,
                tool_executor=tool_executor,
                agent_manager=agent_manager,
            )
        
        # 设置 ChatEngine 回调
        self._setup_chat_engine_callbacks()
        
        self._initialized = True
        logger.info("[ChatBackend] 初始化完成")
    
    def _setup_chat_engine_callbacks(self):
        """设置 ChatEngine 的回调"""
        if not self._chat_engine:
            return
        
        self._chat_engine.set_callback("content_received", self._on_content_received)
        self._chat_engine.set_callback("reasoning_content_received", self._on_reasoning_content_received)
        self._chat_engine.set_callback("tool_call_started", self._on_tool_call_started)
        self._chat_engine.set_callback("tool_result_received", self._on_tool_result_received)
        self._chat_engine.set_callback("stream_started", self._on_stream_started)
        self._chat_engine.set_callback("stream_finished", self._on_stream_finished)
        self._chat_engine.set_callback("messages_updated", self._on_messages_updated)
        self._chat_engine.set_callback("error", self._on_error)
        self._chat_engine.set_callback("user_message_added", self._on_user_message_added)
        self._chat_engine.set_callback("permission_approval_requested", self._on_permission_requested)
    
    # ========== 内部回调处理 ==========
    
    def _on_content_received(self, content: str):
        if self._callbacks.on_stream_chunk:
            self._callbacks.on_stream_chunk(content)
    
    def _on_reasoning_content_received(self, content: str):
        if self._callbacks.on_reasoning_content:
            self._callbacks.on_reasoning_content(content)
    
    def _on_error(self, error: str):
        if self._callbacks.on_error:
            self._callbacks.on_error(error)
    
    def _on_stream_started(self):
        if self._callbacks.on_stream_started:
            self._callbacks.on_stream_started()
    
    def _on_stream_finished(self, response: str = ""):
        if self._callbacks.on_stream_finished:
            self._callbacks.on_stream_finished({"content": response})
    
    def _on_messages_updated(self, messages: List[Dict]):
        pass  # 可以通知前端
    
    def _on_user_message_added(self, user_text: str):
        if self._callbacks.on_message_added:
            self._callbacks.on_message_added({
                "role": "user",
                "content": user_text
            })
    
    def _on_tool_call_started(self, tool_call_id: str, tool_name: str, arguments: dict):
        if self._callbacks.on_tool_call_started:
            self._callbacks.on_tool_call_started(tool_call_id, tool_name, arguments)
    
    def _on_tool_result_received(self, tool_call_id: str, tool_name: str, result: dict, success: bool):
        if self._callbacks.on_tool_call_result:
            self._callbacks.on_tool_call_result(tool_call_id, tool_name, result, success)
    
    def _on_permission_requested(self, tool_call_id: str, tool_name: str, arguments: dict):
        if self._callbacks.on_permission_requested:
            self._callbacks.on_permission_requested(tool_call_id, tool_name, arguments)
    
    # ========== 会话管理 ==========
    
    def create_session(self):
        """创建新会话"""
        if not self._session_manager:
            from app.core.chat_session import SessionManager
            self._session_manager = SessionManager()
        
        session = self._session_manager.create_new_session()
        
        if self._callbacks.on_session_created:
            self._callbacks.on_session_created(session.session_id)
        if self._callbacks.on_session_changed:
            self._callbacks.on_session_changed(session.session_id)
        
        return session
    
    def get_current_session(self):
        """获取当前会话"""
        if self._session_manager:
            return self._session_manager.get_current_session()
        return None
    
    def switch_session(self, index: int):
        """切换会话"""
        if self._session_manager:
            self._session_manager.switch_to_session(index)
            session = self.get_current_session()
            if session and self._callbacks.on_session_changed:
                self._callbacks.on_session_changed(session.session_id)
    
    def delete_session(self, index: int) -> bool:
        """删除会话"""
        if self._session_manager:
            result = self._session_manager.delete_session(index)
            if result and self._callbacks.on_session_deleted:
                self._callbacks.on_session_deleted(index)
            return result
        return False
    
    def get_all_sessions(self) -> List:
        """获取所有会话"""
        if self._session_manager:
            return self._session_manager.get_all_sessions()
        return []
    
    # ========== 对话操作 ==========
    
    def send_message(self, text: str, agent_name: str = None, **kwargs):
        """
        发送消息
        
        Args:
            text: 消息内容
            agent_name: Agent 名称（可选）
            **kwargs: 其他参数
        """
        session = self.get_current_session()
        if not session:
            session = self.create_session()
        
        # 添加用户消息
        session.add_user_message(text, params=kwargs)
        
        # 发送到 ChatEngine
        if self._chat_engine:
            self._chat_engine.send_message(
                text,
                session=session,
                agent_name=agent_name,
            )
    
    def stop_streaming(self):
        """停止当前流式输出"""
        if self._chat_engine and hasattr(self._chat_engine, '_current_worker'):
            worker = self._chat_engine._current_worker
            if worker and hasattr(worker, 'stop'):
                worker.stop()
    
    def approve_permission(self, tool_call_id: str, auto_allow: bool = False):
        """批准工具调用权限"""
        if self._chat_engine:
            self._chat_engine.approve_tool_permission(tool_call_id, auto_allow)
    
    def deny_permission(self, tool_call_id: str):
        """拒绝工具调用权限"""
        if self._chat_engine:
            self._chat_engine.deny_tool_permission(tool_call_id)
    
    # ========== 状态查询 ==========
    
    def get_current_agent(self) -> str:
        """获取当前 Agent"""
        if self._chat_engine:
            return getattr(self._chat_engine, '_current_agent', 'plan')
        return 'plan'
    
    def set_current_agent(self, agent_name: str):
        """设置当前 Agent"""
        if self._chat_engine:
            self._chat_engine._current_agent = agent_name
