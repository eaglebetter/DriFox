# -*- coding: utf-8 -*-
"""
AutoLoop 循环引擎 — 管理循环状态、迭代追踪、完成信号检测、预算控制、共享笔记
"""
import time
from pathlib import Path
from typing import Optional

from loguru import logger

from app.core.auto_loop_config import AutoLoopConfig


class LoopState:
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    ERROR = "error"


class AutoLoopEngine:
    """核心循环引擎，不依赖 Qt，纯逻辑层"""

    def __init__(self, config: Optional[AutoLoopConfig] = None):
        self.config = config or AutoLoopConfig()
        self.state = LoopState.IDLE
        self.iteration = 0
        self._completion_count = 0
        self._start_time = 0.0
        self._total_tokens = 0
        self._consecutive_failures = 0

    # ========== 状态管理 ==========

    def reset(self):
        self.state = LoopState.IDLE
        self.iteration = 0
        self._completion_count = 0
        self._start_time = 0.0
        self._total_tokens = 0
        self._consecutive_failures = 0

    def start(self):
        self.state = LoopState.RUNNING
        self._start_time = time.time()
        logger.info("[AutoLoop] Engine started")

    def stop(self):
        self.state = LoopState.STOPPED
        logger.info("[AutoLoop] Engine stopped by user")

    # ========== 完成检测 ==========

    def check_completion(self, response_text: str) -> bool:
        """检测响应中是否包含完成信号"""
        signal = self.config.completion_signal
        if not signal:
            return False
        if signal in response_text:
            self._completion_count += 1
            if self._completion_count >= self.config.completion_threshold:
                self.state = LoopState.COMPLETED
                logger.info(f"[AutoLoop] Completion signal detected ({self._completion_count} times)")
                return True
        else:
            self._completion_count = 0
        return False

    # ========== 预算检查 ==========

    def check_budget(self) -> Optional[str]:
        """检查是否超预算，返回 None=正常，str=停止原因"""
        elapsed = time.time() - self._start_time
        elapsed_min = elapsed / 60

        if self.config.max_duration_minutes > 0 and elapsed_min >= self.config.max_duration_minutes:
            reason = f"超时: 已运行 {elapsed_min:.1f} 分钟，上限 {self.config.max_duration_minutes} 分钟"
            logger.warning(f"[AutoLoop] {reason}")
            return reason

        if self.config.max_tokens > 0 and self._total_tokens >= self.config.max_tokens:
            reason = f"Token 超限: 已用 {self._total_tokens}，上限 {self.config.max_tokens}"
            logger.warning(f"[AutoLoop] {reason}")
            return reason

        return None

    def add_tokens(self, tokens: int):
        self._total_tokens += tokens

    # ========== 共享笔记 ==========

    def get_notes_path(self) -> Optional[Path]:
        if not self.config.project_path:
            return None
        return Path(self.config.project_path) / self.config.notes_file

    def read_shared_notes(self) -> str:
        path = self.get_notes_path()
        if not path or not path.exists():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"[AutoLoop] Failed to read notes: {e}")
            return ""

    def update_shared_notes(self, notes_text: str):
        """更新共享笔记文件"""
        path = self.get_notes_path()
        if not path:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(notes_text, encoding="utf-8")
        except Exception as e:
            logger.warning(f"[AutoLoop] Failed to write notes: {e}")

    # ========== 获取进度信息 ==========

    def get_progress(self) -> dict:
        """获取当前进度信息，用于 UI 更新"""
        elapsed = time.time() - self._start_time
        return {
            "iteration": self.iteration,
            "max_iterations": self.config.max_iterations,
            "elapsed_seconds": int(elapsed),
            "elapsed_str": self._format_time(elapsed),
            "total_tokens": self._total_tokens,
            "max_tokens": self.config.max_tokens,
            "state": self.state,
        }

    @staticmethod
    def _format_time(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}时{m}分{s}秒"
        return f"{m}分{s}秒"
