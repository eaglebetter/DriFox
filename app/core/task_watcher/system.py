# -*- coding: utf-8 -*-
"""
TaskWatcher 系统门面
整合所有组件，提供统一的入口
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from loguru import logger
from .database import Database, DRIFOX_DIR
from .config_store import TaskConfigStore
from .parser import TaskParser, TaskParseError
from .queue import TaskQueue
from .watcher import TaskWatcher
from .scheduler import TaskScheduler
from .output_handler import OutputHandler
from .engine_scheduler import get_engine_scheduler, EngineScheduler
from .models import TaskConfig, TaskResult, TriggerMode, QueueStatus
from .task_execution_engine import TaskExecutionEngine, get_task_execution_engine
class TaskWatcherSystem:
    """TaskWatcher 系统门面
    
    整合所有组件，提供统一的入口
    使用独立的 TaskExecutionEngine 执行任务，不复用现有 ChatEngine
    """
    # 默认任务项目名称
    DEFAULT_TASK_PROJECT = "任务执行"
    
    def __init__(
        self,
        scheduler: Optional[EngineScheduler] = None,
        event_bus: Any = None,
        db_path: Optional[str] = None,
        main_widget=None,
    ):
        """初始化 TaskWatcher 系统
        
        Args:
            scheduler: 引擎调度器（默认使用全局调度器）
            event_bus: 事件总线（可选）
            db_path: 数据库路径（可选）
            main_widget: UI 主窗口（用于创建隔离的执行环境）
        """
        # 配置 - 使用项目本地目录
        self._watch_root: Optional[str] = os.path.join(DRIFOX_DIR, "tasks")
        self._main_widget = main_widget
        
        # 初始化数据库
        self._db = Database.get_instance(db_path)
        
        # 初始化引擎调度器（备用）
        self._engine_scheduler = scheduler or get_engine_scheduler()
        self._engine_scheduler.set_default_project(self.DEFAULT_TASK_PROJECT)
        
        # 初始化各组件
        self._config_store = TaskConfigStore(tasks_dir=self._watch_root)
        self._queue = TaskQueue(self._db)
        self._output_handler = OutputHandler()
        self._watcher = TaskWatcher(self._config_store)
        self._scheduler = TaskScheduler(self._config_store)
        self._parser = TaskParser()
        
        # 初始化任务执行引擎（使用独立环境）
        self._task_engine = get_task_execution_engine(main_widget)
        
        # 系统状态
        self._running = False
        self._processing = False
        
        # 回调
        self._callbacks: Dict[str, Callable] = {}
        
        # 任务完成回调映射
        self._pending_tasks: Dict[str, int] = {}  # task_id -> queue_id
        
        # 设置回调
        self._setup_callbacks()
    
    @property
    def task_engine(self) -> TaskExecutionEngine:
        """获取任务执行引擎"""
        return self._task_engine
    def _setup_callbacks(self) -> None:
        """设置内部回调"""
        # 设置调度器回调
        self._scheduler.set_callback(self._on_scheduled_trigger)
        
        # 设置监听器回调
        self._watcher.set_callback(self._on_file_detected)
        
        # 设置任务执行引擎回调
        self._task_engine.set_callback("task_started", self._on_task_started)
        self._task_engine.set_callback("task_completed", self._on_task_completed)
        self._task_engine.set_callback("task_failed", self._on_task_failed)
        self._task_engine.set_callback("task_cancelled", self._on_task_cancelled)
    def _on_scheduled_trigger(self, config: TaskConfig) -> None:
        """定时任务触发回调
        
        Args:
            config: 任务配置
        """
        logger.info(f"[TaskWatcherSystem] 定时任务触发: {config.id}")
        self.enqueue_task(config, trigger_type="scheduled")
    def _on_file_detected(self, file_path: str, config: TaskConfig) -> None:
        """文件检测回调
        
        Args:
            file_path: 文件路径
            config: 任务配置
        """
        logger.info(f"[TaskWatcherSystem] 文件触发任务: {file_path}")
        self.enqueue_task(config, trigger_type="file_change")
    def _on_task_started(self, config: TaskConfig) -> None:
        """任务开始回调
        
        Args:
            config: 任务配置
        """
        logger.info(f"[TaskWatcherSystem] 任务开始执行: {config.id}")
        self._processing = True
        self._emit("task_started", config)
    def _on_task_completed(self, config: TaskConfig, result: TaskResult) -> None:
        """任务完成回调
        
        Args:
            config: 任务配置
            result: 执行结果
        """
        logger.info(f"[TaskWatcherSystem] 任务完成: {config.id}, success={result.success}")
        
        # 输出结果
        if result.success:
            output_success = self._output_handler.handle(config, result)
            logger.debug(f"[TaskWatcherSystem] 输出处理完成: {output_success}")
        
        # 更新队列状态
        queue_id = self._pending_tasks.get(config.id)
        if queue_id:
            self._queue.update_status(queue_id, QueueStatus.COMPLETED)
            if config.id in self._pending_tasks:
                del self._pending_tasks[config.id]
        
        self._processing = False
        self._emit("task_completed", config, result)
        
        # 处理下一个任务
        self._process_next()
    def _on_task_failed(self, config: TaskConfig, error: str) -> None:
        """任务失败回调
        
        Args:
            config: 任务配置
            error: 错误信息
        """
        logger.error(f"[TaskWatcherSystem] 任务失败: {config.id}, error={error}")
        
        # 更新队列状态
        queue_id = self._pending_tasks.get(config.id)
        if queue_id:
            self._queue.increment_retry(queue_id
            if config.retry_count < config.retry:
                self._queue.update_status(queue_id, QueueStatus.FAILED)
                # 重新入队
                self._queue.requeue_failed(1)
            else:
                self._queue.update_status(queue_id, QueueStatus.FAILED)
        
        if config.id in self._pending_tasks:
            del self._pending_tasks[config.id]
        
        self._processing = False
        self._emit("task_failed", config, error)
        self._process_next()
    def _on_task_cancelled(self, config: TaskConfig) -> None:
        """任务取消回调
        
        Args:
            config: 任务配置
        """
        logger.info(f"[TaskWatcherSystem] 任务取消: {config.id}")
        queue_id = self._pending_tasks.get(config.id)
        if queue_id:
            # 删除队列项
            self._queue.cancel(queue_id)
            if config.id in self._pending_tasks:
                del self._pending_tasks[config.id]
        
        self._processing = False
        self._emit("task_cancelled", config)
        self._process_next()
    def _process_next(self) -> None:
        """处理队列中下一个任务"""
        if self._processing:
            return
        
        item = self._queue.dequeue()
        if not item:
            return
        
        # 获取任务配置
        config = self._config_store.get(item.task_id)
        if not config:
            logger.error(f"[TaskWatcherSystem] 队列项找不到任务配置: {item.task_id}")
            self._queue.update_status(item.id, QueueStatus.FAILED)
            return
        
        # 记住 queue_id
        self._pending_tasks[config.id] = item.id
        
        # 更新队列状态
        self._queue.update_status(item.id, QueueStatus.RUNNING)
        
        # 执行任务
        self._task_engine.execute(config)
    def set_callback(self, event: str, callback: Callable) -> None:
        """设置外部回调
        
        Args:
            event: 事件名
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
                logger.error(f"[TaskWatcherSystem] 回调错误 {event}: {e}")
    def start(self) -> bool:
        """启动系统
        
        Returns:
            是否成功
        """
        if self._running:
            logger.debug("[TaskWatcherSystem] 已经在运行中")
            return True
        
        logger.info("[TaskWatcherSystem] 启动 TaskWatcher 系统...")
        
        # 启动文件监听
        if not self._watcher.start():
            logger.warning("[TaskWatcherSystem] 文件监听启动失败，检查 watchdog 是否安装")
        
        # 加载并启动定时任务
        count = self._scheduler.load_all_from_config(self._config_store)
        logger.info(f"[TaskWatcherSystem] 加载了 {count} 个定时任务")
        
        # 从文件系统加载所有任务配置
        self._config_store.load_all()
        
        # 标记运行
        self._running = True
        logger.info("[TaskWatcherSystem] 启动完成")
        
        # 开始处理队列
        self._process_next()
        
        return True
    def stop(self) -> bool:
        """停止系统
        
        Returns:
            是否成功
        """
        if not self._running:
            return True
        
        logger.info("[TaskWatcherSystem] 停止 TaskWatcher 系统...")
        
        # 停止调度器
        self._scheduler.stop()
        
        # 停止监听器
        self._watcher.stop()
        
        # 停止任务执行引擎
        self._task_engine.stop()
        
        self._running = False
        logger.info("[TaskWatcherSystem] 停止完成")
        
        return True
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
    def enqueue_task(self, config: TaskConfig, trigger_type: str = "manual") -> int:
        """将任务加入队列
        
        Args:
            config: 任务配置
            trigger_type: 触发类型
            
        Returns:
            队列项 ID，-1 表示失败
        """
        queue_id = self._queue.enqueue(config, trigger_type)
        if queue_id > 0:
            logger.debug(f"[TaskWatcherSystem] 任务入队: {config.id}, queue_id={queue_id}")
            self._process_next()
        return queue_id
    def parse_and_enqueue(self, file_path: str) -> Optional[TaskConfig]:
        """解析文件并将任务入队
        
        Args:
            file_path: 任务文件路径
            
        Returns:
            解析后的任务配置，None 表示解析失败
        """
        try:
            config = self._parser.parse_file(file_path)
            if config:
                # 保存到配置存储
                if self._config_store.save(config):
                    if config.trigger.mode == TriggerMode.SCHEDULED:
                        # 重新调度
                        self._scheduler.unschedule_task(config.id)
                        self._scheduler.schedule_task(config)
                
                self.enqueue_task(config, "manual")
                return config
        except TaskParseError as e:
            logger.error(f"[TaskWatcherSystem] 解析失败: {e}")
            return None
        return None
    def get_all_tasks(self) -> List[TaskConfig]:
        """获取所有任务配置
        
        Returns:
            任务配置列表
        """
        return self._config_store.load_all()
    def get_task(self, task_id: str) -> Optional[TaskConfig]:
        """获取单个任务配置
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务配置或 None
        """
        return self._config_store.get(task_id)
    def create_task_file(
        self,
        name: str,
        content: str,
        trigger_mode: str = "manual",
        cron: str = None,
        agent: str = "plan",
        output_path: str = None,
        folder: str = None,
    ) -> str:
        """创建任务文件
        
        Args:
            name: 任务名称
            content: 任务内容
            trigger_mode: 触发模式
            cron: cron 表达式（定时任务需要）
            agent: 使用哪个 agent
            output_path: 输出路径
            folder: 保存文件夹（None 使用默认）
            
        Returns:
            创建的文件路径
        """
        import uuid
        
        # 确保 watch_root 已初始化
        if not self._watch_root:
            self._watch_root = os.path.join(DRIFOX_DIR, "tasks")
        
        # 确定保存文件夹
        if not folder:
            folder = self._watch_root
        
        # 确保文件夹存在
        os.makedirs(folder, exist_ok=True)
        
        # 生成任务文件
        task_id = str(uuid.uuid4())
        filename = f"{name.replace(' ', '_')}_{task_id[:8]}.task.md"
        file_path = os.path.join(folder, filename)
        
        # 构建内容
        lines = [
            "---",
            f"id: {task_id}",
            f"name: {name}",
            "type: custom",
            "trigger:",
            f"  mode: {trigger_mode}",
        ]
        
        if cron:
            lines.append(f"  cron: \"{cron}\"")
        
        lines.extend([
            "context:",
            f"  session_mode: new",
            f"  agent: {agent}",
            "output:",
            "  mode: file",
        ])
        
        if output_path:
            lines.append(f"  destination: {output_path}")
        
        lines.append("  format: markdown")
        lines.append("---")
        lines.append("")
        lines.append(content)
        
        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        logger.info(f"[TaskWatcherSystem] 创建任务文件: {file_path}")
        return file_path
    def export_tasks_to_folder(self, folder: str) -> int:
        """导出所有任务到文件夹
        
        Args:
            folder: 目标文件夹
            
        Returns:
            导出的任务数量
        """
        os.makedirs(folder, exist_ok=True)
        
        tasks = self.get_all_tasks()
        count = 0
        
        for config in tasks:
            file_path = os.path.join(folder, f"{config.id}.task.md")
            if self._config_store.export_to_file(config.id, file_path):
                count += 1
        
        return count
    def clear_completed_tasks(self, older_than_hours: int = 24) -> int:
        """清理已完成的旧队列项
        
        Args:
            older_than_hours: 保留最近多少小时内完成的任务
            
        Returns:
            清理数量
        """
        return self._queue.clear_completed(older_than_hours)
    def requeue_failed_tasks(self, max_retries: int = 3) -> int:
        """重新入队失败任务
        
        Args:
            max_retries: 最大重试次数
            
        Returns:
            重新入队的数量
        """
        return self._queue.requeue_failed(max_retries)