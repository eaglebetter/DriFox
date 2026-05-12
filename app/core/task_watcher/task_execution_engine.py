# -*- coding: utf-8 -*-
"""
任务执行引擎 - 使用独立环境执行任务
参考 IsolatedChatContext 的实现，为任务执行创建完全独立的环境：
1. 独立的 SessionManager（保存在指定 project）
2. 独立的 ToolExecutor
3. 不触发工具卡片 UI
4. 显示绿色任务卡片
这样任务执行与 UI 完全隔离，不会影响用户手动对话。
"""
import uuid
import time
import threading
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime
from loguru import logger
from app.core.chat_engine import ChatEngine
class TaskExecutionEngine:
    """任务执行引擎 - 使用完全隔离的环境执行任务
    
    特点：
    1. 不复用现有对话窗的 ChatEngine
    2. 创建独立的隔离上下文
    3. 会话保存到任务指定的 project
    4. 不触发工具卡片 UI
    5. 支持任务状态回调
    """
    
    # 单例
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self, main_widget=None):
        """初始化任务执行引擎
        
        Args:
            main_widget: UI 主窗口（用于获取可复用的基础组件）
        """
        self._main_widget = main_widget
        self._active_tasks: Dict[str, "TaskContext"] = {}  # task_id -> TaskContext
        self._task_callbacks: Dict[str, List[Callable]] = {}  # event -> callbacks
        
    @classmethod
    def get_instance(cls, main_widget=None) -> "TaskExecutionEngine":
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(main_widget)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置单例（用于测试）"""
        if cls._instance:
            cls._instance.cleanup()
            cls._instance = None
    
    def set_callback(self, event: str, callback: Callable) -> None:
        """设置回调
        
        Args:
            event: 事件名 (task_started/task_progress/task_completed/task_failed)
            callback: 回调函数
        """
        if event not in self._task_callbacks:
            self._task_callbacks[event] = []
        self._task_callbacks[event].append(callback)
    
    def _emit(self, event: str, *args) -> None:
        """触发回调"""
        callbacks = self._task_callbacks.get(event, [])
        for cb in callbacks:
            try:
                cb(*args)
            except Exception as e:
                logger.error(f"[TaskExecutionEngine] 回调错误 {event}: {e}")
    
    def execute_task(
        self,
        task_id: str,
        task_name: str,
        task_content: str,
        project: str = None,
        agent: str = "plan",
        callback: Optional[Callable[[str, bool], None]] = None
    ) -> str:
        """执行任务
        
        Args:
            task_id: 任务 ID
            task_name: 任务名称
            task_content: 任务内容
            project: 指定 project（会话将保存到此 project）
            agent: 使用的智能体
            callback: 完成回调 (result, success)
        
        Returns:
            session_id
        """
        # 创建隔离上下文
        isolated_ctx = self._create_isolated_context(project)
        
        # 创建任务上下文
        task_ctx = TaskContext(
            task_id=task_id,
            task_name=task_name,
            engine=isolated_ctx.engine,
            session_manager=isolated_ctx._session_manager,
            project=project or "任务执行",
            callback=callback,
        )
        
        self._active_tasks[task_id] = task_ctx
        
        # 注册引擎回调
        isolated_ctx.engine.set_callback("content_received", task_ctx.on_content_received)
        isolated_ctx.engine.set_callback("stream_finished", task_ctx.on_stream_finished)
        isolated_ctx.engine.set_callback("error", task_ctx.on_error)
        
        # 发送任务消息
        try:
            session = isolated_ctx._session_manager.get_current_session()
            session_id = session.session_id
            
            logger.info(f"[TaskExecutionEngine] 开始执行任务: {task_id}, session={session_id}")
            self._emit("task_started", task_ctx.config)
            
            return session_id
        except Exception as e:
            logger.error(f"[TaskExecutionEngine] 执行任务失败: {e}")
            self._emit("task_failed", task_id, str(e))
            return ""
    def cancel_task(self, task_id: str) -> bool:
        """取消任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否成功
        """
        if task_id not in self._active_tasks:
            return False
        
        task_ctx = self._active_tasks[task_id]
        task_ctx.cancel()
        del self._active_tasks[task_id]
        logger.info(f"[TaskExecutionEngine] 任务取消: {task_id}")
        self._emit("task_cancelled", task_id)
        return True
    def get_active_tasks(self) -> List[str]:
        """获取所有活跃任务 ID"""
        return list(self._active_tasks.keys())
    def cleanup(self) -> None:
        """清理所有任务"""
        for task_id in list(self._active_tasks.keys()):
            self.cancel_task(task_id)
        self._active_tasks.clear()
    def stop(self) -> None:
        """停止引擎"""
        self.cleanup()
    def _create_isolated_context(self, project: str = None) -> "IsolatedContext":
        """创建隔离的上下文
        
        Args:
            project: project 名称
            
        Returns:
            IsolatedContext
        """
        from app.core.chat_session import SessionManager
        from app.core.tool_executor import ToolExecutor
        from app.core.agent import AgentManager
        
        # 创建独立的 SessionManager
        session_manager = SessionManager()
        
        # 获取工具执行器（从主窗口复用，如果有）
        tool_executor = None
        if self._main_widget:
            tool_executor = getattr(self._main_widget.backend, 'tool_executor', None)
        
        if not tool_executor:
            from app.tools import BuiltinTools
            tools = BuiltinTools()
            tool_executor = ToolExecutor(tools)
        
        # 创建隔离上下文
        ctx = IsolatedContext(
            session_manager=session_manager,
            tool_executor=tool_executor,
            project=project or "任务执行",
            main_widget=self._main_widget,
        )
        
        return ctx
class TaskContext:
    """单个任务的上下文"""
    def __init__(
        self,
        task_id: str,
        task_name: str,
        engine: ChatEngine,
        session_manager: Any,
        project: str,
        callback: Optional[Callable[[str, bool], None]],
    ):
        self.task_id = task_id
        self.task_name = task_name
        self._engine = engine
        self._session_manager = session_manager
        self._project = project
        self._callback = callback
        self._content = []
        self._start_time = time.time()
    def on_content_received(self, chunk: str) -> None:
        """内容接收回调"""
        self._content.append(chunk)
    def on_stream_finished(self, full_content: str) -> None:
        """流结束回调"""
        total_content = "".join(self._content)
        if full_content:
            total_content = full_content
        
        execution_time = time.time() - self._start_time
        logger.info(f"[TaskContext] 任务完成: {self.task_id}, 耗时: {execution_time:.2f}s")
        
        if self._callback:
            self._callback(total_content, True)
        
        # 触发全局回调
        from app.core.task_watcher.models import TaskResult
        result = TaskResult(
            success=True,
            task_id=self.task_id,
            output_content=total_content,
            execution_time=execution_time,
        )
        # 这里应该由 TaskExecutionEngine 触发全局回调
    def on_error(self, error: str) -> None:
        """错误回调"""
        logger.error(f"[TaskContext] 任务错误: {self.task_id}, error={error}")
        if self._callback:
            self._callback(error, False)
    def cancel(self) -> None:
        """取消任务"""
        if hasattr(self._engine, '_current_worker') and self._engine._current_worker:
            try:
                self._engine._current_worker.cancel()
            except Exception:
                pass
class IsolatedContext:
    """隔离的上下文"""
    def __init__(
        self,
        session_manager: SessionManager,
        tool_executor: Any,
        project: str,
        main_widget: Any,
    ):
        self._session_manager = session_manager
        self._tool_executor = tool_executor
        self._project = project
        self._main_widget = main_widget
        self.engine: Optional[ChatEngine] = None
        self._current_stream = None
    def create_engine(self, user_text: str) -> bool:
        """创建 ChatEngine 并发送消息"""
        from app.utils.config import Settings
        
        # 获取模型配置（从主窗口复用）
        model_config = None
        if self._main_widget:
            if hasattr(self._main_widget, '_get_model_config'):
                model_config = self._main_widget._get_model_config()
        
        if not model_config:
            # 默认配置
            model_config = {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "api_key": "sk-dummy",
                "base_url": "https://api.openai.com/v1",
            }
        
        # 获取 agent_manager
        agent_manager = None
        if self._main_widget:
            agent_manager = getattr(self._main_widget, '_agent_manager', None)
        
        # 如果没有 agent_manager，创建一个新的
        if agent_manager is None:
            from app.core.agent import AgentManager
            agent_manager = AgentManager()
            logger.info("[TaskChatEngine] 创建新的 AgentManager")
        
        # 创建 ChatEngine
        engine = ChatEngine(
            session_manager=self._session_manager,
            get_model_config=lambda: model_config,
            tool_executor=self._tool_executor,
            agent_manager=agent_manager,
            get_chat_cards=None,  # 不触发 UI
            get_memory_context=getattr(self._main_widget, '_build_memory_context_for_engine', None) if self._main_widget else None,
            worker_callbacks={
                "content_received": lambda c: self._emit("content_received", c),
                "stream_finished": lambda r: self._on_stream_finished(),
                "error": lambda e: self._emit("error", e),
            },
            api_mode=True,  # API 模式，直接回调
        )
        
        # 保存引用以便清理
        self._actual_engine = engine
        
        # 设置 agent
        if agent:
            engine.switch_agent(agent)
        
        # 发送消息
        return engine.send_message(
            user_text=user_text,
            context_params={},
        )
    
    def _on_stream_finished(self) -> None:
        """流结束回调"""
        session = self._session_manager.get_current_session()
        session_id = session.session_id if session else None
        self._emit("stream_finished", session_id)
    
    def stop_stream(self) -> None:
        """停止流"""
        if self._current_stream:
            try:
                self._current_stream.cancel()
            except Exception:
                pass
        if hasattr(self, '_actual_engine') and self._actual_engine:
            try:
                self._actual_engine.cleanup_worker()
            except Exception:
                pass
# 全局实例获取函数
def get_task_execution_engine(main_widget=None) -> TaskExecutionEngine:
    """获取任务执行引擎单例"""
    return TaskExecutionEngine.get_instance(main_widget)