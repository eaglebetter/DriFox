# -*- coding: utf-8 -*-
"""
AutoLoop Worker — 后台循环工作线程

两阶段任务执行循环：
1. 规划阶段：拆解任务为 N 个步骤，写入 SHARED_TASK_NOTES.md
2. 执行阶段：按步骤执行，每步必须验证

每个迭代创建一个 OpenAIChatWorker，等待其完成后检测完成信号，
更新共享笔记，继续下一轮或停止。

阶段强制机制：
- 规划阶段：tools 仅允许 scan_repo/glob/grep 和写笔记（限制写代码）
- 执行阶段：允许所有工具，但每步必须验证通过才能前进
"""
import re
import threading
import time
from typing import Dict, List, Optional, Any, Callable

from PyQt5.QtCore import QThread, pyqtSignal
from loguru import logger

from app.core.auto_loop_config import AutoLoopConfig
from app.core.auto_loop_engine import AutoLoopEngine, LoopState
from app.core.workers import OpenAIChatWorker


# ========== 规划阶段受限工具集 ==========
PLANNING_TOOLS = {
    # 扫描工具
    "scan_repo", "glob", "grep", "list", "read", "websearch", "webfetch"
    # 笔记写入工具
    "write",
}


class AutoLoopWorker(QThread):
    """AutoLoop 后台工作线程"""

    # === 进度信号 ===
    iteration_started = pyqtSignal(int, int)  # (current, max)
    iteration_completed = pyqtSignal(int, str)  # (iteration, summary)
    progress_updated = pyqtSignal(dict)  # progress dict
    loop_completed = pyqtSignal(str)  # 完成消息
    loop_error = pyqtSignal(str)  # 错误消息
    loop_stopped = pyqtSignal()  # 用户手动停止
    
    # === 阶段变更信号（用于运行卡 UI）===
    phase_changed = pyqtSignal(str)  # "planning" / "executing" / "completed"

    # === 迭代过程中的消息转发（用于日志显示）===
    log_signal = pyqtSignal(str)  # 日志消息

    # === Token 实时更新信号（直接更新运行卡 UI）===
    tokens_updated = pyqtSignal(int)  # 追加的 token 数量
    
    # === 消息日志列表信号（用于保存到会话）===
    messages_logged = pyqtSignal(list)  # 发送完整的消息日志列表

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config: Optional[AutoLoopConfig] = None
        self._model_config_getter: Optional[Callable[[], Dict]] = None
        self._tool_executor: Optional[Any] = None
        self._tools_schema: Optional[List[Dict]] = None
        self._all_tools_schema: Optional[List[Dict]] = None  # 保留完整工具集
        self._agent_system_prompt_getter: Optional[Callable[[str], str]] = None

        self._is_cancelled = False
        self._engine: Optional[AutoLoopEngine] = None
        self._current_worker: Optional[OpenAIChatWorker] = None

        # 执行阶段的步骤追踪
        self._last_step = 0  # 上次完成的步骤
        
        # 规划阶段标志：记录首次规划后的状态，防止模型一次性完成
        self._first_planning_done = False
        
        # 汇总的完整消息列表（从每个 ChatWorker 获取）
        self._all_messages: List[Dict] = []
        
        # Worker 完成事件（用于同步等待 finished_with_messages 信号）
        self._worker_done_event = threading.Event()

    def _configure_tools_for_phase(self, tools_schema: List[Dict]) -> List[Dict]:
        """根据当前阶段配置工具集"""
        if self._engine and self._engine.is_planning_phase():
            # 规划阶段：只允许受限工具
            allowed = set(PLANNING_TOOLS)
            filtered = [t for t in tools_schema if t.get("function", {}).get("name", "") in allowed]
            logger.info(f"[AutoLoop] Planning phase: restricting to {len(filtered)} tools")
            return filtered
        else:
            # 执行阶段：使用完整工具集
            return self._all_tools_schema or tools_schema

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
        self._all_tools_schema = tools_schema  # 保存完整工具集
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
        """主循环 — 两阶段：规划 → 执行"""
        if not self._config or not self._config.task_prompt:
            self.loop_error.emit("未设置任务描述")
            return

        self._is_cancelled = False
        self._engine = AutoLoopEngine(self._config)
        self._engine.start()
        self._last_step = 0
        self._first_planning_done = False
        
        # 清空消息列表
        self._all_messages = []
        
        # 发送阶段信号：规划中
        self.phase_changed.emit("planning")
        self.log_signal.emit("📋 进入规划阶段：拆解任务...")

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
            
            # 根据阶段获取对应的工具集
            current_tools = self._configure_tools_for_phase(self._all_tools_schema or self._tools_schema)

            # 创建并运行 worker
            try:
                # 重置完成事件和消息列表
                self._worker_finished_messages = []
                self._worker_done_event.clear()
                
                self._current_worker = self._create_worker(messages, current_tools)
                
                # 使用本地事件循环等待 worker 完成，保持事件循环运行以便信号转发
                from PyQt5.QtCore import QEventLoop
                loop = QEventLoop()
                self._current_worker.finished.connect(loop.quit)
                self._current_worker.start()
                loop.exec_()  # 等待 worker 完成，但保持事件循环处理信号，这样日志可以正常更新
                
                # 检查是否被取消（token 超限等）
                if self._is_cancelled:
                    self.log_signal.emit("⏹ 达到限制，AutoLoop 停止")
                    self.loop_stopped.emit()
                    return
                
                # 等待 finished_with_messages 信号（最多等待 30 秒）
                if not self._worker_done_event.wait(timeout=30):
                    logger.warning(f"[AutoLoop] Iteration {iteration}: timeout waiting for finished_with_messages")

                response = self._current_worker.full_response or ""
                self._extract_usage_from_full_response()
                real_usage = self._get_token_usage()
                if real_usage > 0:
                    token_usage = real_usage
                else:
                    token_usage = max(1, len(response) // 4)
                self._engine.add_tokens(token_usage)
                self._emit_progress()
                
                # 获取 ChatWorker 的完整消息并追加到列表
                if self._worker_finished_messages:
                    self._all_messages.extend(self._worker_finished_messages)
                    
                # 【新增】强制检查接力文档更新
                if not self._check_relay_doc_updated(iteration):
                    # 未更新接力文档，强制要求更新后才能继续
                    self.log_signal.emit("⚠️【强制】接力文档未更新！正在要求更新...")
                    
                    # 重新构建消息，注入强制更新提示
                    force_messages = self._build_messages(task_prompt, iteration, force_update=True)
                    
                    # 创建新的 worker 执行强制更新
                    self._worker_finished_messages = []
                    self._worker_done_event.clear()
                    self._current_worker = self._create_worker(force_messages, current_tools)
                    
                    from PyQt5.QtCore import QEventLoop
                    loop = QEventLoop()
                    self._current_worker.finished.connect(loop.quit)
                    self._current_worker.start()
                    loop.exec_()
                    
                    # 再次检查接力文档
                    if self._check_relay_doc_updated(iteration):
                        self.log_signal.emit("✅ 接力文档已更新，继续执行...")
                    else:
                        self.log_signal.emit("⚠️ 接力文档仍未更新，将继续强制要求")
                        # 允许继续（避免死循环），但会在下一轮继续检查
                    
                    self._emit_progress()
                    continue
            except Exception as e:
                logger.error(f"[AutoLoop] Worker error on iteration {iteration}: {e}")
                self.loop_error.emit(f"第{iteration}轮出错: {str(e)}")
                self._engine._consecutive_failures += 1
                if self._engine._consecutive_failures >= 3:
                    self.loop_error.emit("连续失败 3 次，已停止")
                    return
                self._emit_progress()
                continue

            # 生成摘要
            summary = self._extract_summary(response, iteration)
            self.iteration_completed.emit(iteration, summary)

            # ===== 阶段处理 =====
            
            if self._engine.is_planning_phase():
                # --- 规划阶段 ---
                notes = self._engine.read_shared_notes()
                
                # 检测规划是否完成
                planning_done = self._engine.check_planning_complete(response, notes)
                
                if planning_done:
                    self._first_planning_done = True
                    self._engine.enter_execution_phase()
                    current, total = self._engine.parse_steps_from_notes(notes)
                    self.log_signal.emit(f"✅ 规划完成！共 {total} 个步骤")
                    self.log_signal.emit(f"📋 开始执行阶段: {self._get_next_step_preview(notes, 1)}")
                    
                    # 发送阶段信号：执行中
                    self.phase_changed.emit("executing")
                    self._emit_progress()
                    continue
                else:
                    # 规划未完成，继续规划
                    self._engine.on_planning_attempt()
                    
                    # 检查：是否写了笔记但没输出 PLANNING_COMPLETE
                    if notes and "## 执行计划" in notes and "PLANNING_COMPLETE" not in response.upper():
                        # 模型写了计划但忘记输出信号，提醒它
                        self.log_signal.emit("📋 检测到已写入计划，请在回复末尾添加 PLANNING_COMPLETE")
                    
                    self.log_signal.emit("📋 继续规划...")
                    self._emit_progress()
                    continue
                    
            else:
                # --- 执行阶段 ---
                notes = self._engine.read_shared_notes()
                
                # 解析当前步骤
                current_step, total_steps = self._engine.parse_steps_from_notes(notes)
                if total_steps > 0:
                    self._engine._total_steps = total_steps
                    
                    # 检测步骤完成 - 必须在响应中找到步骤完成信号
                    step_completed = self._check_step_completed(response, notes, self._engine._current_step)
                    
                    if step_completed:
                        self._last_step = self._engine._current_step
                        self.log_signal.emit(f"✓ 步骤 {self._engine._current_step}/{total_steps} 完成")
                        
                        if self._engine._current_step >= total_steps:
                            # 所有步骤完成，输出 DONE
                            self.log_signal.emit("🎉 所有步骤完成！任务结束")
                            self.phase_changed.emit("completed")
                            self.loop_completed.emit("所有计划步骤已完成！🎉")
                            return
                        else:
                            # 前进到下一步
                            self._engine.advance_to_step(self._engine._current_step + 1)
                            self.log_signal.emit(f"📋 执行步骤 {self._engine._current_step}/{total_steps}: {self._get_next_step_preview(notes, self._engine._current_step)}")
                    else:
                        # 步骤未完成，可能需要继续执行或验证
                        # 检查是否有验证失败的情况
                        if "验证失败" in response or "failed" in response.lower():
                            self.log_signal.emit("⚠️ 检测到验证失败，模型应修复后重试")
                
                # 检查完成信号（可能在响应中直接输出 DONE）
                if self._engine.check_completion(response):
                    self.phase_changed.emit("completed")
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

    # ========== 内部辅助方法 ==========

    def _get_step_completion_keyword(self, notes: str, step_num: int) -> Optional[str]:
        """从笔记中提取步骤完成的关键词"""
        import re
        # 匹配 "[步骤 N] 描述" 并找下一行的关键词
        pattern = rf'- \[步骤\s*{step_num}\].*?(?=\n- \[步骤|\Z)'
        match = re.search(pattern, notes, re.DOTALL)
        if match:
            step_text = match.group(0)
            # 提取验证方式中冒号后的内容
            verify_match = re.search(r'验证方式[:：]\s*(.+)', step_text)
            if verify_match:
                return verify_match.group(1).strip()
            # 或者取完整描述
            return step_text.split('|')[1].strip() if '|' in step_text else step_text.strip()
        return None

    def _check_step_completed(self, response: str, notes: str, step_num: int) -> bool:
        """检测当前步骤是否完成
        
        完成条件（满足任一即可）：
        1. 响应中包含 "步骤 N 完成" / "step N complete" / "完成验证"
        2. 笔记中该步骤标记为完成（如 [x] 或 ✓）
        3. 响应末尾包含 DONE
        4. 笔记中有"步骤 N 结果"或"当前状态"更新
        """
        import re
        
        # 条件1：响应中明确提到步骤完成
        patterns = [
            rf'步骤\s*{step_num}\s*(完成|已验证|验证成功)',
            rf'step\s*{step_num}\s*(complete|verified|done)',
            rf'验证.*?成功|verify.*?success',
        ]
        for p in patterns:
            if re.search(p, response, re.IGNORECASE):
                return True
        
        # 条件2：笔记中该步骤已标记完成
        if notes:
            # 匹配 - [x] 步骤 N 或 - [✓] 步骤 N 格式
            pattern = rf'- \[(x|✓)\]\s*步骤\s*{step_num}'
            if re.search(pattern, notes, re.IGNORECASE):
                return True
            # 或者匹配 "步骤 N 结果" 段落在笔记中出现
            if re.search(rf'步骤\s*{step_num}\s+结果', notes):
                return True
            # 或者有"当前状态"包含步骤完成信息
            if re.search(rf'步骤\s*{step_num}.*完成', notes, re.DOTALL):
                return True
        
        # 条件3：响应末尾有 DONE
        if response.strip().endswith("DONE"):
            return True
        
        return False

    def _get_next_step_preview(self, notes: str, step_num: int) -> str:
        """获取下一步骤的预览文本"""
        import re
        pattern = rf'- \[步骤\s*{step_num}\].*?'
        match = re.search(pattern, notes)
        if match:
            step_text = match.group(0)
            # 移除 "- [步骤 N]" 前缀
            preview = re.sub(r'^-\s*\[步骤\s*\d+\]\s*', '', step_text)
            # 只取前 50 字符
            return preview[:60].strip() + ('...' if len(preview) > 60 else '')
        return f"步骤 {step_num}"

    def _check_relay_doc_updated(self, iteration: int) -> bool:
        """检查接力文档是否已更新
        
        Returns:
            True: 已更新，可以继续
            False: 未更新，需要强制要求更新
        """
        notes = self._engine.read_shared_notes() if self._engine else ""
        
        # 检查接力文档是否为空或几乎为空
        if not notes or len(notes.strip()) < 50:
            logger.warning(f"[AutoLoop] Iteration {iteration}: relay doc is empty or too short")
            return False
        
        # 检查规划阶段：必须有执行计划
        if self._engine.is_planning_phase():
            if "## 执行计划" not in notes and "- [步骤" not in notes:
                logger.warning(f"[AutoLoop] Iteration {iteration}: no execution plan in relay doc")
                return False
            return True
        
        # 执行阶段：检查当前步骤是否有结果记录
        current_step = self._engine._current_step if self._engine else 1
        total_steps = self._engine._total_steps if self._engine else 0
        
        if total_steps > 0:
            # 检查是否有"步骤 X 结果"段落
            result_pattern = rf'步骤\s*{current_step}\s+结果|## 步骤\s*{current_step}\s+结果'
            if not re.search(result_pattern, notes, re.IGNORECASE):
                # 也检查是否有"当前状态"更新
                if "## 当前状态" not in notes and "当前状态" not in notes:
                    logger.warning(f"[AutoLoop] Iteration {iteration}: no step {current_step} result recorded")
                    return False
        
        return True

    def _build_forced_update_prompt(self, iteration: int) -> str:
        """生成强制更新接力文档的提示"""
        current_step = self._engine._current_step if self._engine else 1
        total_steps = self._engine._total_steps if self._engine else 0
        is_planning = self._engine.is_planning_phase() if self._engine else True
        
        if is_planning:
            return f"""
## ⚠️ 【强制】接力文档未更新！

你（迭代 {iteration} 轮）尚未更新接力文档 `SHARED_TASK_NOTES.md`。

根据规则，你必须：
1. 使用 `write` 工具将完整的执行计划写入 SHARED_TASK_NOTES.md
2. 包含所有步骤的描述、目标文件、验证方式
3. 然后输出 `PLANNING_COMPLETE`

当前接力文档状态：
```
{self._engine.read_shared_notes()[:500] if self._engine else ""}...
```

请立即使用 `write` 工具更新接力文档，然后输出 `PLANNING_COMPLETE`。
"""
        else:
            return f"""
## ⚠️ 【强制】接力文档未更新！

你（迭代 {iteration} 轮）尚未更新接力文档 `SHARED_TASK_NOTES.md`。

根据规则，你必须：
1. 更新 SHARED_TASK_NOTES.md 中的"步骤 {current_step} 结果"章节
2. 记录本轮执行的改动、验证命令和结果
3. 然后才能继续下一步或输出 DONE

当前接力文档状态：
```
{self._engine.read_shared_notes()[:500] if self._engine else ""}...
```

请立即使用 `write` 工具更新接力文档（追加步骤结果），然后继续执行。
"""

    # ========== 内部辅助 ==========

    def _build_messages(self, task_prompt: str, iteration: int, force_update: bool = False) -> List[Dict]:
        """构建本轮对话消息 — 两阶段上下文注入
        
        Args:
            task_prompt: 原始任务提示
            iteration: 当前迭代轮次
            force_update: 是否强制要求更新接力文档
        """
        system_prompt = self._agent_system_prompt_getter("auto_loop") if self._agent_system_prompt_getter else ""

        # 根据阶段注入不同上下文
        workflow_context = self._build_workflow_context(iteration, force_update)
        system_content = system_prompt

        messages = [{"role": "system", "content": system_content}]
        messages.append({"role": "user", "content": task_prompt + "\n\n" + workflow_context})
        return messages

    def _build_workflow_context(self, iteration: int, force_update: bool = False) -> str:
        """根据当前阶段构建工作流上下文
        
        Args:
            iteration: 当前迭代轮次
            force_update: 是否强制要求更新接力文档
        """
        project_path = self._config.project_path or ""
        is_planning = self._engine.is_planning_phase() if self._engine else True
        
        lines = []
        
        # 【新增】强制更新提示
        if force_update:
            lines.append("## ⚠️ 【强制】接力文档未更新！\n")
            lines.append("你必须使用 `write` 工具更新 `SHARED_TASK_NOTES.md` 后才能继续。\n")
            lines.append("**不更新接力文档就继续是违规行为！**\n")
        
        if is_planning:
            # ========== 规划阶段上下文 ==========
            lines = [
                "## 🚀 PHASE 1: TASK PLANNING",
                "",
                "你正处于**任务规划阶段**。你的职责是将复杂任务拆解为可验证的步骤。",
                "",
                "### 规划流程",
                "1. **扫描项目**: 使用 `scan_repo`/`glob`/`grep` 了解项目结构",
                "2. **拆解任务**: 将任务分为 N 个可验证的子步骤",
                "3. **写入笔记**: 将计划写入 SHARED_TASK_NOTES.md",
                "4. **输出信号**: 在响应末尾输出 `PLANNING_COMPLETE` 表示规划完成",
                "",
                "### 步骤格式（必须严格遵循）",
                "```",
                "[步骤 1] <简短描述> | <目标文件> | <验证方式>",
                "[步骤 2] <简短描述> | <目标文件> | <验证方式>",
                "...",
                "```",
                "",
                "### 验证方式参考",
                "| 类型 | 示例 | 说明 |",
                "|------|------|------|",
                "| 测试 | `测试: pytest tests/` | 运行测试 |",
                "| Lint | `lint: flake8` | 代码检查 |",
                "| 检查 | `检查: 文件包含 xxx` | 内容验证 |",
                "| 运行 | `运行: python main.py` | 命令执行 |",
                "",
                "### SHARED_TASK_NOTES.md 模板",
                "```markdown",
                "# SHARED_TASK_NOTES",
                "",
                "## 任务概述",
                "<一句话描述要完成的目标>",
                "",
                "## 执行计划",
                "- [步骤 1] <描述> | <文件> | <验证方式>",
                "- [步骤 2] <描述> | <文件> | <验证方式>",
                "- [步骤 3] <描述> | <文件> | <验证方式>",
                "",
                "## 当前状态",
                "等待开始执行",
                "",
                "## 下一步",
                "执行步骤 1",
                "```",
                "",
                "### ⚠️ 重要规则",
                "- **不要在规划阶段执行代码改动**！先规划，后执行",
                "- 必须输出 `PLANNING_COMPLETE` 才能进入执行阶段",
                "- 每个步骤必须有明确的验证方式，否则无法确认完成",
                "- `## 任务概述` 和 `## 执行计划` 一旦写入，进入执行阶段后将被锁定保护，**禁止修改**，执行阶段只能更新 `## 当前状态` 和追加步骤结果",
            ]
        else:
            # ========== 执行阶段上下文 ==========
            current_step = self._engine._current_step if self._engine else 1
            total_steps = self._engine._total_steps if self._engine else 0
            notes = self._engine.read_shared_notes() if self._engine else ""
            
            lines = [
                "## ⚡ PHASE 2: EXECUTION LOOP",
                "",
                f"**当前进度**: 步骤 {current_step} / {total_steps}",
                "",
                "### 📋 文档保护规则（必须严格遵守！）",
                "",
                "✅ **允许修改**: `## 当前状态` 和 `## 下一步` 以及新增的 `步骤 X 结果` 章节",
                "❌ **禁止修改**: `## 任务概述` 和 `## 执行计划` 这两个章节一旦在规划阶段完成，**绝对不能修改或重写**，必须原样保留！",
                "❌ **禁止简化**: 不得将原详细的多步骤计划简化为少数步骤，必须保留所有原始步骤细节。",
                "",
                "### 执行规则（严格遵守）",
                "",
                "**每轮只做一件事，然后验证**。不要试图一次完成多个步骤。",
                "",
                "### 工作流程",
                "1. 读 `SHARED_TASK_NOTES.md` 确认当前步骤",
                "2. 读取相关目标文件",
                "3. 执行当前步骤（**只做一件事**）",
                "4. **必须运行验证命令**（不能跳过）",
                "5. 更新 `SHARED_TASK_NOTES.md`: **只追加/更新当前步骤结果和当前状态，不得改动执行计划部分**",
                "6. 判断：继续当前步骤 | 前进到下一步 | 输出 DONE",
                "",
                "### 验证失败处理",
                "- 验证失败 → 分析原因 → 修复 → 重试",
                "- 连续失败 3 次 → 记录问题 → 尝试降级方案或跳过",
                "- 验证成功 → 前进到下一步",
                "",
                "### 完成条件",
                "- 所有计划步骤都验证通过",
                "- 输出 `DONE`（独占一行）",
                "",
                "### 当前步骤详情",
            ]
            
            # 提取当前步骤信息
            if notes:
                import re
                pattern = rf'- \[步骤\s*{current_step}\].*?'
                match = re.search(pattern, notes)
                if match:
                    step_text = match.group(0)
                    lines.append(f"```")
                    lines.append(step_text)
                    lines.append("```")
                else:
                    lines.append(f"(未找到步骤 {current_step} 信息)")
            else:
                lines.append("(暂无笔记信息，请先读取 SHARED_TASK_NOTES.md)")

        if project_path:
            lines.extend([
                "",
                "## Project Root Directory",
                f"`WORKDIR`: {project_path}",
                "所有文件操作使用相对路径：",
                f"  - write(path='src/main.py', ...) → {project_path}/src/main.py",
                f"  - read(path='src/main.py')    → 读取 {project_path}/src/main.py",
            ])
        
        if not is_planning and notes:
            lines.extend([
                "",
                "## 当前 SHARED_TASK_NOTES.md 内容",
                "```",
                notes[:2000],  # 限制长度避免 token 浪费
                "```" if len(notes) <= 2000 else "...[已截断]",
            ])

        return "\n".join(lines)

    def _create_worker(self, messages: List[Dict], tools: List[Dict] = None) -> OpenAIChatWorker:
        """创建 ChatWorker"""
        llm_config = self._model_config_getter() if self._model_config_getter else {}
        session_messages = []
        
        # 用于接收 worker 完成的信号和数据
        self._worker_finished_messages: List[Dict] = []
        
        def on_worker_finished(msgs: list):
            self._worker_finished_messages = list(msgs) if msgs else []
            
            # 实时计算消息列表的 token 数并更新 UI
            if self._engine and msgs:
                from app.core.token_estimator import count_messages_tokens
                token_count = count_messages_tokens(msgs)
                self._engine.add_tokens(token_count)
                self.tokens_updated.emit(self._engine._total_tokens)
                
                # 检查是否超预算，超预算则取消
                reason = self._engine.check_budget()
                if reason:
                    self.log_signal.emit(f"⚠️ {reason}，正在停止...")
                    self._is_cancelled = True
                    if self._current_worker:
                        self._current_worker._is_cancelled = True
            
            self._worker_done_event.set()
        
        # 使用传入的 tools（已根据阶段过滤），如果没有则使用默认
        effective_tools = tools if tools is not None else (self._all_tools_schema or self._tools_schema or [])

        worker = OpenAIChatWorker(
            messages=messages,
            session_messages=session_messages,
            llm_config=llm_config,
            tools=effective_tools,
            stream=True,
            tool_executor=self._tool_executor,
            permission_check_callback=self._permission_check_callback,
            permission_cache=self._permission_cache,
            compactor=self._compactor,
        )
        
        # 连接完成信号，等待消息
        worker.finished_with_messages.connect(on_worker_finished)

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

    def _check_planning_complete(self, response: str) -> bool:
        """检测规划阶段是否完成（旧方法，保留兼容性）"""
        return "PLANNING_COMPLETE" in response.upper()
    
    def get_all_messages(self) -> List[Dict]:
        """获取所有消息（用于保存到会话）"""
        return self._all_messages.copy()
