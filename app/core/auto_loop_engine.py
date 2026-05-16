# -*- coding: utf-8 -*-
"""
AutoLoop 循环引擎 — 管理循环状态、迭代追踪、完成信号检测、预算控制、共享笔记

两阶段设计：
1. PLANNING 阶段：拆解任务为步骤，写入 SHARED_TASK_NOTES.md
2. EXECUTING 阶段：按步骤执行，每步必须验证
"""
import time
from pathlib import Path
from typing import Optional, List

from loguru import logger

from app.core.auto_loop_config import AutoLoopConfig


class LoopState:
    IDLE = "idle"
    RUNNING = "running"
    PLANNING = "planning"   # 规划阶段：拆解任务
    EXECUTING = "executing" # 执行阶段：按步骤执行
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
        
        # 规划状态
        self._is_planning_phase = True  # 默认在规划阶段
        self._planning_count = 0        # 规划尝试次数
        self._current_step = 0          # 当前步骤编号（1-based）
        self._total_steps = 0           # 总步骤数
        self._step_verified = False      # 当前步骤是否已验证
        self._verification_failures = 0  # 连续验证失败次数

    # ========== 状态管理 ==========

    def reset(self):
        self.state = LoopState.IDLE
        self.iteration = 0
        self._completion_count = 0
        self._start_time = 0.0
        self._total_tokens = 0
        self._consecutive_failures = 0
        self._is_planning_phase = True
        self._planning_count = 0
        self._current_step = 0
        self._total_steps = 0
        self._step_verified = False
        self._verification_failures = 0

    def start(self):
        self.state = LoopState.PLANNING
        self._start_time = time.time()
        self._is_planning_phase = True
        logger.info("[AutoLoop] Engine started in PLANNING phase")

    def enter_execution_phase(self):
        """进入执行阶段"""
        self.state = LoopState.EXECUTING
        self._is_planning_phase = False
        self._current_step = 1
        logger.info("[AutoLoop] Entering EXECUTION phase, step 1")

    def stop(self):
        self.state = LoopState.STOPPED
        logger.info("[AutoLoop] Engine stopped by user")

    def is_planning_phase(self) -> bool:
        return self._is_planning_phase

    def is_executing_phase(self) -> bool:
        return not self._is_planning_phase

    # ========== 规划阶段管理 ==========

    def on_planning_attempt(self):
        """每次规划尝试调用"""
        self._planning_count += 1
        if self._planning_count > 5:
            logger.warning("[AutoLoop] Too many planning attempts, forcing execution")
            self.enter_execution_phase()

    def parse_steps_from_notes(self, notes: str) -> tuple[int, int]:
        """从笔记中解析当前步骤和总步骤数"""
        import re
        # 匹配 "- [步骤 N]" 或 "- [步骤 N]" 格式
        steps = re.findall(r'- \[[步骤Step]+\s*(\d+)\]', notes)
        if steps:
            nums = [int(s) for s in steps]
            return max(nums), len(nums)  # current_step, total_steps
        return 0, 0

    # ========== 执行阶段管理 ==========

    def advance_to_step(self, step_num: int):
        """前进到指定步骤"""
        self._current_step = step_num
        self._step_verified = False
        logger.info(f"[AutoLoop] Advanced to step {step_num}/{self._total_steps}")

    def verify_current_step(self, success: bool):
        """验证当前步骤结果"""
        if success:
            self._step_verified = True
            self._verification_failures = 0
        else:
            self._verification_failures += 1
            if self._verification_failures >= 3:
                logger.warning(f"[AutoLoop] Step {self._current_step} failed 3 times, skipping")
                self._step_verified = True  # 标记为已处理，避免卡住
                self._verification_failures = 0

    def is_task_completed(self) -> bool:
        """检查任务是否完成（所有步骤都已验证）"""
        if self._total_steps == 0:
            return False
        return self._step_verified and self._current_step > self._total_steps

    # ========== 完成检测 ==========

    def check_completion(self, response_text: str) -> bool:
        """检测响应中是否包含完成信号"""
        signal = self.config.completion_signal
        if not signal:
            return False
        if signal in response_text:
            # 在执行阶段，必须确保所有步骤都已完成
            if self.is_executing_phase() and not self.is_task_completed():
                logger.info(f"[AutoLoop] Received DONE but not all steps verified, continuing")
                return False
            self._completion_count += 1
            if self._completion_count >= self.config.completion_threshold:
                self.state = LoopState.COMPLETED
                logger.info(f"[AutoLoop] Completion signal detected ({self._completion_count} times)")
                return True
        else:
            self._completion_count = 0
        return False

    def check_planning_complete(self, response_text: str, notes: str) -> bool:
        """检测规划是否完成：必须包含 PLANNING_COMPLETE 且笔记有有效步骤"""
        if "PLANNING_COMPLETE" not in response_text.upper():
            return False
        current, total = self.parse_steps_from_notes(notes)
        if total == 0:
            logger.info("[AutoLoop] PLANNING_COMPLETE found but no steps in notes")
            return False
        self._total_steps = total
        self._current_step = 1
        return True

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
            "phase": "planning" if self._is_planning_phase else "executing",
            "current_step": self._current_step,
            "total_steps": self._total_steps,
        }

    @staticmethod
    def _format_time(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}时{m}分{s}秒"
        return f"{m}分{s}秒"
