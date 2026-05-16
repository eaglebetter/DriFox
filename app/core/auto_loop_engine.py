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
        self._verified_steps: set[int] = set()  # 已验证通过的步骤集合
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
        self._verified_steps = set()
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
        """从笔记中解析当前步骤和总步骤数
        
        支持格式：
        - [ ] [步骤 1] xxx   (未完成)
        - [x] [步骤 1] xxx   (已完成)
        - [步骤 1] xxx
        """
        import re
        # 匹配各种格式的步骤号：
        patterns = [
            r'- \[.?\]?\s*\[步骤\s*(\d+)\]',  # - [ ] [步骤 1] 或 - [x] [步骤 1] 或 - [步骤 1]
            r'- \[.?\]?\s*步骤\s*(\d+)',        # - [ ] 步骤 1 或 - [x] 步骤 1
            r'- \[x\]\s*\[步骤\s*(\d+)\]',     # - [x] [步骤 1]
            r'\\[步骤\s*(\d+)\\]',              # [步骤 1]
        ]
        steps = []
        for pattern in patterns:
            matches = re.findall(pattern, notes, re.IGNORECASE)
            if matches:
                steps = [int(m) for m in matches]
                break
        if steps:
            return max(steps), len(steps)
        return 0, 0

    def parse_current_and_next_step(self, notes: str) -> tuple[int, int, int]:
        """从笔记中解析当前步骤、已勾选完成的最大步骤、总步骤数
        
        Returns:
            (current_step, max_verified_step, total_steps)
            - current_step: 下一个要执行的步骤（已完成的最后一个+1）
            - max_verified_step: 已勾选 [x] 的最大步骤号
            - total_steps: 总步骤数
        """
        import re
        # 匹配所有步骤号（包括 [ ] 和 [x]）
        all_step_pattern = r'- \[.?\]?\s*\[步骤\s*(\d+)\]'
        all_steps = re.findall(all_step_pattern, notes, re.IGNORECASE)
        if not all_steps:
            all_steps = re.findall(r'- \[.?\]?\s*步骤\s*(\d+)', notes, re.IGNORECASE)
        
        total_steps = len(all_steps)
        max_step_num = max([int(s) for s in all_steps]) if all_steps else 0
        
        # 解析已勾选的步骤
        verified_steps = self.parse_checked_steps_from_notes(notes)
        max_verified = max(verified_steps) if verified_steps else 0
        
        # 当前应该执行的步骤 = 已完成的最后一个 + 1
        current_step = max_verified + 1
        
        return current_step, max_verified, total_steps

    def parse_checked_steps_from_notes(self, notes: str) -> set[int]:
        """从笔记中解析已勾选完成的步骤 [x]
        
        支持格式：
        - - [x] [步骤 1] xxx
        - - [x] 步骤 1 xxx
        """
        import re
        # 匹配已勾选完成的步骤
        patterns = [
            r'- \[x\]\s*\[步骤\s*(\d+)\]',   # - [x] [步骤 1]
            r'- \[x\]\s*步骤\s*(\d+)',        # - [x] 步骤 1
            r'- \[x\]\s*\[Step\s*(\d+)\]',   # - [x] [Step 1]
        ]
        checked = set()
        for pattern in patterns:
            for match in re.finditer(pattern, notes, re.IGNORECASE):
                checked.add(int(match.group(1)))
        return checked

    def get_verified_steps(self) -> set[int]:
        """获取已验证通过的步骤集合"""
        return self._verified_steps

    def sync_verified_steps_from_notes(self, notes: str):
        """从笔记同步已勾选步骤到缓存"""
        self._verified_steps = self.parse_checked_steps_from_notes(notes)
        logger.info(f"[AutoLoop] Synced {len(self._verified_steps)} verified steps from notes")

    def is_current_step_verified(self) -> bool:
        """检查当前步骤是否已验证通过"""
        return self._current_step in self._verified_steps

    def get_incremental_summary(self) -> str:
        """生成增量执行进度总结，告诉模型哪些已完成，只需要处理当前步骤"""
        if self._is_planning_phase:
            return ""
        
        verified = sorted(self._verified_steps)
        total = self._total_steps
        current = self._current_step
        remaining = [s for s in range(1, total + 1) if s not in self._verified_steps]
        
        summary = [
            "\n\n📊 **增量执行进度总结**",
            f"- ✅ 已验证完成：{verified if verified else '无'}",
            f"- 🔄 当前需要处理：步骤 {current}",
            f"- ⏭️ 未开始：{remaining if remaining else '无'}",
            "",
            "⚠️ 强制要求：",
            f"- 你只需要处理**当前步骤 {current}**",
            "- 已完成步骤不需要重复验证或修改",
            "- **每轮结束必须追加**本轮操作记录到 SHARED_TASK_NOTES.md",
            "- 禁止覆盖原始执行计划，只能在文档末尾追加结果记录",
            "",
        ]
        return "\n".join(summary)

    def get_current_system_time(self) -> str:
        """获取当前系统时间字符串，用于注入prompt"""
        import time
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    def get_stage_constraint(self) -> str:
        """获取当前阶段的强制约束提示（注入到prompt最开头）"""
        current_time = self.get_current_system_time()
        
        if self._is_planning_phase:
            return f"""
🕒 当前系统时间：{current_time}

🔒 【当前阶段强制约束 - 规划阶段】
你现在 **ONLY 只允许** 做任务拆解和方案设计。
**ABSOLUTELY 禁止** 写任何实现代码，禁止使用 edit/bash/delete 工具修改代码文件！

你的任务：
1. 扫描项目理解现状
2. 将任务拆解为步骤，每个步骤格式：
   - [ ] [步骤 N] <描述> | <文件> | <验证方式>
     ✅ 需求验证：<这个步骤必须满足什么需求？输出什么结果？>
3. 将完整计划写入 SHARED_TASK_NOTES.md
4. 输出 PLANNING_COMPLETE
5. STOP！到此为止

记住：你现在只规划，不实现。代码一根都不能写！
""".strip()
        else:
            # 执行阶段
            current = self._current_step
            total = self._total_steps
            return f"""
🕒 当前系统时间：{current_time}

🔒 【当前阶段强制约束 - 执行阶段】
你现在 **ONLY 只允许** 处理 **当前步骤 {current}/{total}**。
**ABSOLUTELY 禁止** 提前执行后续步骤，禁止一次性做完多个步骤！

你必须严格遵循：
1. 读取 SHARED_TASK_NOTES.md 确认当前步骤要求和需求验证点
2. 只完成当前这一个步骤，不要碰后续步骤
3. 按照步骤要求运行验证（必须真的运行验证命令，不能假设成功）
4. 验证必须通过两层检查：
   ① 基础验证：代码能跑通吗？语法/编译/测试通过吗？
   ② 需求验证：功能真的满足原始需求吗？每个验证点都通过吗？
5. 两层验证都通过后，在 SHARED_TASK_NOTES.md 中将当前步骤改为 `[x]`
6. 在文档末尾**追加**本轮操作记录（包括改动文件、验证命令、验证结果）
7. STOP！到此为止，等待下一轮

记住：一次只做一个步骤，做完就停。已完成步骤不需要重复处理。
""".strip()

    # ========== 执行阶段管理 ==========

    def advance_to_step(self, step_num: int):
        """前进到指定步骤"""
        self._current_step = step_num
        self._step_verified = False
        logger.info(f"[AutoLoop] Advanced to step {step_num}/{self._total_steps}")

    def verify_current_step(self, success: bool):
        """验证当前步骤结果"""
        if success:
            self._verified_steps.add(self._current_step)
            self._step_verified = True
            self._verification_failures = 0
        else:
            self._verification_failures += 1
            if self._verification_failures >= 3:
                logger.warning(f"[AutoLoop] Step {self._current_step} failed 3 times, skipping")
                # 跳过仍标记为已处理，避免卡住
                self._verified_steps.add(self._current_step)
                self._verification_failures = 0

    def is_task_completed(self) -> bool:
        """检查任务是否完成（所有步骤都已验证）"""
        if self._total_steps == 0:
            return False
        # 所有步骤都在已验证集合中才算完成
        all_steps = set(range(1, self._total_steps + 1))
        return self._verified_steps == all_steps

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

    def get_round_log_path(self, iteration: int) -> Optional[Path]:
        """获取当前轮次的独立日志文件路径（round_001.md 格式）"""
        if not self.config.project_path:
            return None
        project_dir = Path(self.config.project_path)
        logs_dir = project_dir / self.config.logs_dir
        logs_dir.mkdir(parents=True, exist_ok=True)
        # 格式: round_001.md → 自然排序
        return logs_dir / f"round_{iteration:03d}.md"

    def write_round_log(self, iteration: int, content: str) -> bool:
        """写入当前轮次的完整日志到独立文件"""
        path = self.get_round_log_path(iteration)
        if not path:
            return False
        try:
            path.write_text(content, encoding="utf-8")
            logger.info(f"[AutoLoop] Wrote round {iteration} log to {path}")
            return True
        except Exception as e:
            logger.warning(f"[AutoLoop] Failed to write round log: {e}")
            return False

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
