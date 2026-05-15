# -*- coding: utf-8 -*-
"""
AutoLoop Worker — 后台循环工作线程

每个迭代创建一个 OpenAIChatWorker，等待其完成后检测完成信号，
更新共享笔记，继续下一轮或停止。
"""
import threading
import time
from typing import Dict, List, Optional, Any, Callable

from PyQt5.QtCore import QThread, pyqtSignal
from loguru import logger

from app.core.auto_loop_config import AutoLoopConfig
from app.core.auto_loop_engine import AutoLoopEngine, LoopState
from app.core.workers import OpenAIChatWorker


class AutoLoopWorker(QThread):
    """AutoLoop 后台工作线程"""

    # === 进度信号 ===
    iteration_started = pyqtSignal(int, int)  # (current, max)
    iteration_completed = pyqtSignal(int, str)  # (iteration, summary)
    progress_updated = pyqtSignal(dict)  # progress dict
    loop_completed = pyqtSignal(str)  # 完成消息
    loop_error = pyqtSignal(str)  # 错误消息
    loop_stopped = pyqtSignal()  # 用户手动停止

    # === 迭代过程中的消息转发（用于日志显示）===
    log_signal = pyqtSignal(str)  # 日志消息

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config: Optional[AutoLoopConfig] = None
        self._model_config_getter: Optional[Callable[[], Dict]] = None
        self._tool_executor: Optional[Any] = None
        self._tools_schema: Optional[List[Dict]] = None
        self._agent_system_prompt_getter: Optional[Callable[[str], str]] = None

        self._is_cancelled = False
        self._engine: Optional[AutoLoopEngine] = None
        self._current_worker: Optional[OpenAIChatWorker] = None

    def configure(
            self,
            config: AutoLoopConfig,
            model_config_getter: Callable[[], Dict],
            tool_executor: Any,
            tools_schema: List[Dict],
            agent_system_prompt_getter: Callable[[str], str],
            permission_check_callback: Callable[[str, dict], str] = None,
            permission_cache: Any = None,
            compactor: Any = None,
    ):
        """配置 worker（应在 start() 前调用）"""
        self._config = config
        self._model_config_getter = model_config_getter
        self._tool_executor = tool_executor
        self._tools_schema = tools_schema
        self._agent_system_prompt_getter = agent_system_prompt_getter
        self._permission_check_callback = permission_check_callback
        self._permission_cache = permission_cache
        self._compactor = compactor

    def cancel(self):
        """取消循环"""
        self._is_cancelled = True
        if self._current_worker and self._current_worker.isRunning():
            self._current_worker._is_cancelled = True
        if self._engine:
            self._engine.stop()

    def run(self):
        """主循环"""
        if not self._config or not self._config.task_prompt:
            self.loop_error.emit("未设置任务描述")
            return

        self._is_cancelled = False
        self._engine = AutoLoopEngine(self._config)
        self._engine.start()

        task_prompt = self._config.task_prompt

        for iteration in range(1, self._config.max_iterations + 1):
            if self._is_cancelled:
                break

            self._engine.iteration = iteration
            self.iteration_started.emit(iteration, self._config.max_iterations)
            self._emit_progress()
            # 给主线程时间处理信号并创建 assistant card
            time.sleep(0.2)

            # 构建本轮消息
            messages = self._build_messages(task_prompt, iteration)

            # 创建并运行 worker
            try:
                self._current_worker = self._create_worker(messages)
                
                # 使用本地事件循环等待 worker 完成，保持事件循环运行以便信号转发
                from PyQt5.QtCore import QEventLoop
                loop = QEventLoop()
                self._current_worker.finished.connect(loop.quit)
                self._current_worker.start()
                loop.exec_()  # 等待 worker 完成，但保持事件循环处理信号，这样日志可以正常更新

                response = self._current_worker.full_response or ""
                # 尝试从完整响应中提取 usage（解决某些API不在streaming chunks中返回usage的问题）
                # 确保 _last_usage 一定被设置
                self._extract_usage_from_full_response()
                # 优先使用真实 token 统计，否则按字符数 / 4 估算
                real_usage = self._get_token_usage()
                if real_usage > 0:
                    token_usage = real_usage
                else:
                    token_usage = max(1, len(response) // 4)
                self._engine.add_tokens(token_usage)
                # 立即更新进度显示
                self._emit_progress()
            except Exception as e:
                logger.error(f"[AutoLoop] Worker error on iteration {iteration}: {e}")
                self.loop_error.emit(f"第{iteration}轮出错: {str(e)}")
                self._engine._consecutive_failures += 1
                if self._engine._consecutive_failures >= 3:
                    self.loop_error.emit("连续失败 3 次，已停止")
                    return
                # 更新进度显示
                self._emit_progress()
                continue

            # 生成摘要
            summary = self._extract_summary(response, iteration)
            self.iteration_completed.emit(iteration, summary)

            # 检查完成信号
            if self._engine.check_completion(response):
                self.loop_completed.emit("任务完成 — 检测到完成信号！🎉")
                return

            # 检查预算
            budget_reason = self._engine.check_budget()
            if budget_reason:
                self.loop_completed.emit(f"已停止 — {budget_reason}")
                return

            self._emit_progress()

        # 达到最大迭代次数
        if not self._is_cancelled:
            self._engine.state = LoopState.COMPLETED
            self.loop_completed.emit(f"达到最大迭代次数 ({self._config.max_iterations})，已停止")

    # ========== 内部辅助 ==========

    def _build_messages(self, task_prompt: str, iteration: int) -> List[Dict]:
        """构建本轮对话消息 — 注入接力上下文 + 项目路径"""
        system_prompt = self._agent_system_prompt_getter("auto_loop") if self._agent_system_prompt_getter else ""

        # 注入接力上下文
        workflow_context = self._build_workflow_context(iteration)
        system_content = system_prompt + "\n\n" + workflow_context

        messages = [{"role": "system", "content": system_content}]
        messages.append({"role": "user", "content": task_prompt})
        return messages

    def _build_workflow_context(self, iteration: int) -> str:
        """构建 Continuous Claude 风格的接力上下文"""
        notes = self._engine.read_shared_notes() if iteration > 1 else ""
        project_path = self._config.project_path or ""
        lines = [
            "## CONTINUOUS WORKFLOW CONTEXT",
            "This is part of a continuous development loop where work happens incrementally across multiple iterations.",
            "**Important**: You don't need to complete the entire goal in one iteration.",
            "Just make meaningful progress on ONE thing, then leave clear notes in SHARED_TASK_NOTES.md for the next iteration.",
            "Think of it as a relay race where you're passing the baton.",
            "",
        ]
        if project_path:
            lines.extend([
                f"## Project Root Directory",
                f"WORKDIR is set to: {project_path}",
                f"All file operations use paths relative to this root.",
                f"Example: write(path='SHARED_TASK_NOTES.md', content='...')  # auto-resolved to {project_path}",
                f"Example: read(path='src/main.py')  # relative to project root",
                "",
            ])
        lines.extend([
            "### SHARED_TASK_NOTES.md Protocol",
            "Before starting work, read SHARED_TASK_NOTES.md to see what was done last time and what's next.",
            "After completing your increment:",
            "1. Update SHARED_TASK_NOTES.md with: what you did, current status, what to do next",
            "2. Keep it concise and actionable — like a handoff note, not a full report",
            "3. Remove outdated information to keep it current",
            "",
            "### Completion Signal",
            'If the ENTIRE project goal is fully complete, output "DONE" on its own line.',
            "Only use this when absolutely certain — not after completing just one task.",
            "",
        ])
        if notes:
            lines.append("## Current State from SHARED_TASK_NOTES.md")
            lines.append(notes)

        return "\n".join(lines)

    def _create_worker(self, messages: List[Dict]) -> OpenAIChatWorker:
        """创建 ChatWorker"""
        llm_config = self._model_config_getter() if self._model_config_getter else {}
        session_messages = []
        
        # 定义 token 更新回调：每次内部 API 调用后实时更新到引擎
        def on_token_update(tokens: int):
            if self._engine:
                self._engine.add_tokens(tokens)
                # 更新进度显示
                self._emit_progress()
                # 检查是否已经超预算，如果超了立即取消
                reason = self._engine.check_budget()
                if reason:
                    self.log_signal.emit(f"⚠️ {reason}，正在停止...")
                    self._is_cancelled = True
                    if self._current_worker:
                        self._current_worker._is_cancelled = True

        worker = OpenAIChatWorker(
            messages=messages,
            session_messages=session_messages,
            llm_config=llm_config,
            tools=self._tools_schema or [],
            stream=True,
            tool_executor=self._tool_executor,
            permission_check_callback=self._permission_check_callback,
            permission_cache=self._permission_cache,
            compactor=self._compactor,
            token_update_callback=on_token_update,
        )

        # 只转发日志信号到运行卡显示
        worker.content_received.connect(lambda t: self.log_signal.emit(f"生成内容..."))
        worker.reasoning_content_received.connect(lambda t: self.log_signal.emit(f"思考中..."))
        worker.thinking_started.connect(lambda: self.log_signal.emit(f"开始推理"))
        worker.tool_call_started.connect(lambda tid, name, args, rid: self.log_signal.emit(f"调用工具: {name}"))
        worker.tool_result_received.connect(lambda tid, name, args, res: self.log_signal.emit(f"工具完成: {name}"))
        worker.error_occurred.connect(lambda e: self.log_signal.emit(f"错误: {e}"))

        return worker

    def _extract_usage_from_full_response(self):
        """从完整API响应中提取 token usage，放到 _current_worker._last_usage"""
        try:
            if not self._current_worker or not hasattr(self._current_worker, 'response'):
                return
            
            response = getattr(self._current_worker, 'response', None)
            if not response:
                return
                
            # 对于非流式响应，usage 在 response 对象上
            if hasattr(response, 'usage'):
                usage = response.usage
                if usage:
                    self._current_worker._last_usage = {
                        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(usage, "completion_tokens", 0),
                        "total_tokens": getattr(usage, "total_tokens", 0),
                    }
                    # 累加到 _accumulated_tokens
                    total = getattr(usage, "total_tokens", 0) or 0
                    if hasattr(self._current_worker, '_accumulated_tokens'):
                        self._current_worker._accumulated_tokens += total
                    return
            # 有些实现在 choices 里
            if hasattr(response, 'choices') and response.choices:
                first_choice = response.choices[0]
                if hasattr(first_choice, 'usage'):
                    usage = first_choice.usage
                    self._current_worker._last_usage = {
                        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(usage, "completion_tokens", 0),
                        "total_tokens": getattr(usage, "total_tokens", 0),
                    }
                    # 累加到 _accumulated_tokens
                    total = getattr(usage, "total_tokens", 0) or 0
                    if hasattr(self._current_worker, '_accumulated_tokens'):
                        self._current_worker._accumulated_tokens += total
                    return
        except Exception as e:
            logger.warning(f"[AutoLoop] Failed to extract usage from full response: {e}")
            pass
            
    def _get_token_usage(self) -> int:
        """获取本轮 token 使用量（包含所有内部工具迭代调用）"""
        try:
            if hasattr(self._current_worker, 'llm_config') and self._current_worker.llm_config:
                # 如果有累加后的总 token 数，优先使用（包含所有内部工具迭代调用）
                if hasattr(self._current_worker, '_accumulated_tokens'):
                    accumulated = getattr(self._current_worker, '_accumulated_tokens', 0)
                    if accumulated > 0:
                        return accumulated
                # 否则回退到使用最后一次 usage
                usage = getattr(self._current_worker, '_last_usage', None)
                if usage:
                    return (usage.get("prompt_tokens", 0) or 0) + (usage.get("completion_tokens", 0) or 0)
        except Exception:
            pass
        return 0

    def _extract_summary(self, response: str, iteration: int) -> str:
        """从响应中提取摘要"""
        lines = response.strip().split("\n")
        # 取前 3 行作为摘要
        summary_lines = [l for l in lines if l.strip() and not l.startswith("```")][:3]
        return " | ".join(summary_lines) if summary_lines else f"第{iteration}轮完成"

    def _emit_progress(self):
        """发射进度信号"""
        if self._engine:
            self.progress_updated.emit(self._engine.get_progress())
