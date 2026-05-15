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

    # === 迭代过程中的消息转发（用于在聊天区显示）===
    content_received = pyqtSignal(str)
    reasoning_content_received = pyqtSignal(str)
    thinking_started = pyqtSignal()
    tool_call_started = pyqtSignal(str, str, dict, str)
    tool_result_received = pyqtSignal(str, str, dict, object)
    error_occurred = pyqtSignal(str)

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
            compactor: Any = None,
    ):
        """配置 worker（应在 start() 前调用）"""
        self._config = config
        self._model_config_getter = model_config_getter
        self._tool_executor = tool_executor
        self._tools_schema = tools_schema
        self._agent_system_prompt_getter = agent_system_prompt_getter
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
                self._current_worker.start()
                self._current_worker.wait()  # 阻塞等待 worker 结束

                response = self._current_worker.full_response or ""
                # 近似 token 统计：按字符数 / 4 估算
                token_usage = max(1, len(response) // 4)
                self._engine.add_tokens(token_usage)
            except Exception as e:
                logger.error(f"[AutoLoop] Worker error on iteration {iteration}: {e}")
                self.error_occurred.emit(f"第{iteration}轮出错: {str(e)}")
                self._engine._consecutive_failures += 1
                if self._engine._consecutive_failures >= 3:
                    self.loop_error.emit("连续失败 3 次，已停止")
                    return
                continue

            # 生成摘要
            summary = self._extract_summary(response, iteration)
            self.iteration_completed.emit(iteration, summary)

            # 更新共享笔记（agent 可能自己更新了，这里也保留一份系统级备份）
            notes = self._build_notes(iteration, summary, response)
            self._engine.update_shared_notes(notes)

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
        """构建本轮对话消息 — 注入共享笔记实现接力"""
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
        lines = [
            "## CONTINUOUS WORKFLOW CONTEXT",
            "This is part of a continuous development loop where work happens incrementally across multiple iterations.",
            "**Important**: You don't need to complete the entire goal in one iteration.",
            "Just make meaningful progress on ONE thing, then leave clear notes in SHARED_TASK_NOTES.md for the next iteration.",
            "Think of it as a relay race where you're passing the baton.",
            "",
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
        ]
        if notes:
            lines.append("## Current State from SHARED_TASK_NOTES.md")
            lines.append(notes)

        return "\n".join(lines)

    def _create_worker(self, messages: List[Dict]) -> OpenAIChatWorker:
        """创建 ChatWorker"""
        llm_config = self._model_config_getter() if self._model_config_getter else {}
        session_messages = []

        worker = OpenAIChatWorker(
            messages=messages,
            session_messages=session_messages,
            llm_config=llm_config,
            tools=self._tools_schema or [],
            stream=True,
            tool_executor=self._tool_executor,
            compactor=self._compactor,
        )

        # 转发信号到主线程
        worker.content_received.connect(self.content_received.emit)
        worker.reasoning_content_received.connect(self.reasoning_content_received.emit)
        worker.thinking_started.connect(self.thinking_started.emit)
        worker.tool_call_started.connect(self.tool_call_started.emit)
        worker.tool_result_received.connect(self.tool_result_received.emit)
        worker.error_occurred.connect(self.error_occurred.emit)

        return worker

    def _get_token_usage(self) -> int:
        """获取本轮 token 使用量"""
        try:
            if hasattr(self._current_worker, 'llm_config') and self._current_worker.llm_config:
                # 部分 worker 会记录 usage
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

    def _build_notes(self, iteration: int, summary: str, full_response: str) -> str:
        """构建共享笔记内容"""
        return (
            f"# AutoLoop Shared Notes\n\n"
            f"## Iteration {iteration}\n"
            f"摘要: {summary}\n\n"
            f"---\n"
            f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Total iterations so far: {iteration}\n"
        )

    def _emit_progress(self):
        """发射进度信号"""
        if self._engine:
            self.progress_updated.emit(self._engine.get_progress())
