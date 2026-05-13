# -*- coding: utf-8 -*-
"""
任务执行器
使用 EngineScheduler 分配空闲引擎执行任务
"""
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from loguru import logger
from .models import TaskConfig, TaskResult, SessionMode
from .database import Database
from .engine_scheduler import get_engine_scheduler, EngineScheduler


class TaskExecutor:
    """任务执行器
    
    通过 EngineScheduler 分配空闲的 ChatEngine 执行任务
    """

    def __init__(
            self,
            scheduler: Optional[EngineScheduler] = None,
            event_bus: Optional[Any] = None,
            db: Optional[Database] = None
    ):
        """初始化任务执行器
        
        Args:
            scheduler: 引擎调度器（默认使用全局调度器）
            event_bus: 事件总线（可选）
            db: 数据库实例（可选）
        """
        self._scheduler = scheduler or get_engine_scheduler()
        self._event_bus = event_bus
        self._db = db or Database.get_instance()

        # 任务执行回调
        self._callbacks: Dict[str, Callable] = {}

        # 任务状态追踪
        self._current_task: Optional[TaskConfig] = None
        self._current_engine_id: Optional[str] = None
        self._current_session_id: Optional[str] = None
        self._current_project: Optional[str] = None
        self._collected_content: List[str] = []
        self._task_start_time: Optional[float] = None

        # 回调 ID（用于清理）
        self._engine_callback_ids: List[str] = []

    def set_callback(self, event: str, callback: Callable) -> None:
        """设置任务事件回调
        
        Args:
            event: 事件名 (task_started/task_completed/task_failed)
            callback: 回调函数
        """
        self._callbacks[event] = callback

    def _emit(self, event: str, *args) -> None:
        """触发事件"""
        callback = self._callbacks.get(event)
        if callback:
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"[TaskExecutor] 回调错误 {event}: {e}")

        if self._event_bus:
            self._event_bus.emit(event, *args)

    def execute(self, config: TaskConfig, queue_id: Optional[int] = None) -> None:
        """执行任务（非阻塞，事件驱动）
        
        Args:
            config: 任务配置
            queue_id: 队列项 ID（用于更新状态）
        """
        # 分配引擎
        allocation = self._scheduler.allocate_engine(config.id, config.context.session_id)
        if not allocation:
            logger.error("[TaskExecutor] 无法分配引擎")
            self._emit("task_failed", config, "没有可用的 ChatEngine")
            return

        engine_id, chat_engine, session_manager, session_project = allocation

        # 保存任务状态
        self._current_task = config
        self._current_engine_id = engine_id
        self._current_session_id = None
        self._current_project = session_project
        self._collected_content = []
        self._task_start_time = time.time()

        logger.info(f"[TaskExecutor] 开始执行任务: {config.id}, engine={engine_id}, project={session_project}")
        self._emit("task_started", config)

        try:
            # 注册引擎回调
            self._register_engine_callbacks(chat_engine)

            # 1. 创建会话
            session_id = self._create_session(session_manager, config, session_project)
            if not session_id:
                raise Exception("创建会话失败")

            self._current_session_id = session_id

            # 2. 注入任务内容
            self._inject_task_content(session_manager, session_id, config)

            # 3. 调用 ChatEngine 发送消息
            success = self._send_to_engine(chat_engine, session_manager, session_id, config)
            if not success:
                raise Exception("ChatEngine 发送消息失败")

            # 注意：结果将在 stream_finished 回调中处理
        except Exception as e:
            self._handle_error(str(e))

    def _register_engine_callbacks(self, chat_engine: Any) -> None:
        """注册 ChatEngine 的回调"""
        # 清空之前的回调
        for cb_id in self._engine_callback_ids:
            # 尝试移除之前的回调（如果 ChatEngine 支持）
            pass

        self._engine_callback_ids = [
            "content_received",
            "stream_finished",
            "error",
            "tool_call_started",
            "tool_result_received",
            "messages_updated"
        ]

        # 流式内容接收
        chat_engine.set_callback("content_received", self._on_content_received)
        chat_engine.set_callback("stream_finished", self._on_stream_finished)
        chat_engine.set_callback("error", self._on_engine_error)
        chat_engine.set_callback("tool_call_started", self._on_tool_started)
        chat_engine.set_callback("tool_result_received", self._on_tool_result)
        chat_engine.set_callback("messages_updated", self._on_messages_updated)

    def _on_content_received(self, chunk: str) -> None:
        """接收到流式内容片段"""
        self._collected_content.append(chunk)

    def _on_tool_started(self, tool_call_id: str, tool_name: str, arguments: dict) -> None:
        """工具调用开始"""
        self._emit("tool_call_started", self._current_task, tool_call_id, tool_name, arguments)

    def _on_tool_result(self, tool_call_id: str, tool_name: str, result: str, success: bool) -> None:
        """工具调用结果"""
        self._emit("tool_call_result", self._current_task, tool_call_id, tool_name, result, success)

    def _on_messages_updated(self, messages: List[Dict]) -> None:
        """消息更新"""
        self._emit("messages_updated", self._current_task, messages)

    def _on_engine_error(self, error: str) -> None:
        """引擎错误"""
        self._handle_error(error)

    def _handle_error(self, error_msg: str) -> None:
        """处理错误"""
        logger.error(f"[TaskExecutor] 任务执行失败: {error_msg}")
        self._log_execution(
            self._current_task,
            self._current_session_id,
            "failed",
            error_msg=error_msg
        )
        self._emit("task_failed", self._current_task, error_msg)
        self._release_current_engine()
        self._reset_state()

    def _create_session(self, session_manager, config: TaskConfig, project: str) -> Optional[str]:
        """创建或继续会话"""
        from app.core.chat_session import ChatSession

        if config.context.session_mode == SessionMode.NEW:
            session = session_manager.create_new_session()
            session.project = project
            return session.session_id

        elif config.context.session_mode == SessionMode.FROM_SESSION_ID:
            # 从指定会话 ID 继续
            target_id = config.context.session_id
            sessions = session_manager.get_all_sessions()
            for session in sessions:
                if session.session_id == target_id:
                    return session.session_id
            logger.error(f"[TaskExecutor] 指定会话不存在: {target_id}")
            return None

        # CONTINUE: 使用当前会话
        current = session_manager.get_current_session()
        if current:
            return current.session_id

        # 如果没有当前会话，创建新的
        session = session_manager.create_new_session()
        session.project = project
        return session.session_id

    def _inject_task_content(self, session_manager, session_id: str, config: TaskConfig) -> None:
        """注入任务内容到会话"""
        sessions = session_manager.get_all_sessions()
        for session in sessions:
            if session.session_id == session_id:
                if config.content:
                    session.add_user_message(config.content)
                break

    def _send_to_engine(self, chat_engine, session_manager, session_id: str, config: TaskConfig) -> bool:
        """发送消息到引擎"""
        # 获取会话
        sessions = session_manager.get_all_sessions()
        session = None
        for s in sessions:
            if s.session_id == session_id:
                session = s
                break

        if not session:
            logger.error("[TaskExecutor] 会话不存在: {session_id}")
            return False

        # 发送消息（任务内容已经注入，这里触发执行）
        last_message = None
        for msg in reversed(session.messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break

        if not last_message:
            last_message = config.content or ""

        chat_engine.send_message(
            last_message,
            session=session,
            agent_name=config.context.agent
        )

        return True

    def _release_current_engine(self) -> None:
        """释放当前引擎"""
        if self._current_engine_id:
            self._scheduler.release_engine(self._current_engine_id)

    def _reset_state(self) -> None:
        """重置状态"""
        self._current_task = None
        self._current_engine_id = None
        self._current_session_id = None
        self._current_project = None
        self._collected_content = []
        self._task_start_time = None
        self._engine_callback_ids = []

    def _on_stream_finished(self, full_content: str) -> None:
        """当 ChatEngine 流结束时调用此方法
        
        Args:
            full_content: 完整的回复内容
        """
        if not self._current_task:
            return

        config = self._current_task
        execution_time = time.time() - (self._task_start_time or time.time())
        logger.info(f"[TaskExecutor] 任务完成: {config.id}, 耗时: {execution_time:.2f}s")

        # 合并收集的内容
        if not full_content and self._collected_content:
            full_content = "".join(self._collected_content)

        # 记录执行日志
        self._log_execution(config, self._current_session_id, "completed", full_content)

        # 构建结果
        result = TaskResult(
            success=True,
            task_id=config.id,
            session_id=self._current_session_id,
            output_content=full_content,
            execution_time=execution_time
        )

        self._emit("task_completed", config, result)

        # 释放引擎
        self._release_current_engine()

        # 重置状态
        self._reset_state()

    def _log_execution(
            self,
            config: TaskConfig,
            session_id: Optional[str],
            status: str,
            result_summary: Optional[str] = None,
            error_msg: Optional[str] = None
    ) -> None:
        """记录执行日志"""
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self._db.execute(
                """
                INSERT INTO task_execution_logs 
                (task_id, session_id, started_at, completed_at, status, result_summary)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (config.id, session_id, now, now, status, result_summary or error_msg)
            )
            self._db.commit()
        except Exception as e:
            logger.error(f"[TaskExecutor] 记录执行日志失败: {e}")

    def cancel(self) -> bool:
        """取消当前任务"""
        if not self._current_task:
            return False

        try:
            # 尝试取消 ChatEngine
            # 注意：ChatEngine 可能没有 cancel 方法
            self._handle_error("任务被取消")
            return True
        except Exception as e:
            logger.error(f"[TaskExecutor] 取消任务失败: {e}")
            return False

    @property
    def is_running(self) -> bool:
        """是否正在执行"""
        return self._current_task is not None

    @property
    def current_task(self) -> Optional[TaskConfig]:
        """当前任务配置"""
        return self._current_task

    @property
    def scheduler(self) -> EngineScheduler:
        """获取调度器"""
        return self._scheduler

    def get_execution_logs(
            self,
            task_id: Optional[str] = None,
            limit: int = 100
    ) -> list:
        """获取执行日志"""
        try:
            if task_id:
                rows = self._db.fetch_all(
                    "SELECT * FROM task_execution_logs WHERE task_id = ? ORDER BY started_at DESC LIMIT ?",
                    (task_id, limit)
                )
            else:
                rows = self._db.fetch_all(
                    "SELECT * FROM task_execution_logs ORDER BY started_at DESC LIMIT ?",
                    (limit,)
                )

            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"[TaskExecutor] 获取执行日志失败: {e}")
            return []
