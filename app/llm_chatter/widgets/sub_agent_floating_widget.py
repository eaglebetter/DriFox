# -*- coding: utf-8 -*-
"""
子智能体悬浮框组件 - 支持多任务并行和结构化日志
"""
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QTextEdit,
    QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCharFormat, QColor
from qfluentwidgets import CardWidget, SegmentedWidget, BodyLabel, PrimaryPushButton
from app.utils.utils import get_unified_font
import time


class SubTaskLogWidget(QFrame):
    """单个子任务的日志显示组件"""

    def __init__(self, task_id: str, agent_name: str, task_desc: str, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.agent_name = agent_name
        self.task_desc = task_desc
        self._start_time = time.time()
        self._step_count = 0
        self._tool_call_count = 0
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        # 任务状态行：状态 + 步骤 + 时间
        status_layout = QHBoxLayout()
        status_layout.setSpacing(4)

        self.status_icon = QLabel("⏳")
        self.status_icon.setFont(get_unified_font(12))
        status_layout.addWidget(self.status_icon)

        self.status_label = BodyLabel("执行中", self)
        self.status_label.setFont(get_unified_font(9, True))
        self.status_label.setStyleSheet("color: #FFA500;")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        self.step_label = BodyLabel("步骤 0", self)
        self.step_label.setFont(get_unified_font(9))
        self.step_label.setStyleSheet("color: #888;")
        status_layout.addWidget(self.step_label)

        self.time_label = BodyLabel("00:00", self)
        self.time_label.setFont(get_unified_font(9))
        self.time_label.setStyleSheet("color: #666;")
        status_layout.addWidget(self.time_label)

        layout.addLayout(status_layout)

        # 日志内容（紧凑）
        self.log_text = QTextEdit(self)
        self.log_text.setFont(get_unified_font(8))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #252526;
                color: #d4d4d4;
                border: none;
                border-radius: 3px;
                padding: 4px;
            }
        """)
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(80)
        layout.addWidget(self.log_text)

        # 初始化日志格式
        self._init_log_format()

    def _init_log_format(self):
        """初始化日志文本格式"""
        self._normal_fmt = QTextCharFormat()
        self._normal_fmt.setForeground(QColor("#d4d4d4"))

        self._step_fmt = QTextCharFormat()
        self._step_fmt.setForeground(QColor("#4EC9B0"))
        self._step_fmt.setFontWeight(QFont.Bold)

        self._tool_fmt = QTextCharFormat()
        self._tool_fmt.setForeground(QColor("#DCDCAA"))

        self._tool_success_fmt = QTextCharFormat()
        self._tool_success_fmt.setForeground(QColor("#6A9955"))

        self._tool_error_fmt = QTextCharFormat()
        self._tool_error_fmt.setForeground(QColor("#F14C4C"))

        self._result_fmt = QTextCharFormat()
        self._result_fmt.setForeground(QColor("#CE9178"))

        self._error_fmt = QTextCharFormat()
        self._error_fmt.setForeground(QColor("#F14C4C"))
        self._error_fmt.setFontWeight(QFont.Bold)

    def _append_log(self, text: str, fmt: QTextCharFormat = None):
        """追加日志（带格式）"""
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        if fmt:
            cursor.setCharFormat(fmt)
        cursor.insertText(text + "\n")
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()

    def _update_time(self):
        """更新时间显示"""
        elapsed = int(time.time() - self._start_time)
        mins = elapsed // 60
        secs = elapsed % 60
        self.time_label.setText(f"{mins:02d}:{secs:02d}")

    def _update_step(self):
        """更新步骤显示"""
        self.step_label.setText(f"步骤 {self._step_count}")

    def update_progress(self, message: str):
        """更新进度"""
        self._step_count += 1
        self._append_log(f"📌 {message}", self._step_fmt)
        self._update_step()
        self._update_time()

    def add_thinking(self, thinking: str):
        """添加思考内容"""
        if not thinking:
            return
        preview = thinking[:150] + "..." if len(thinking) > 150 else thinking
        self._append_log(f"💭 思考: {preview}", self._result_fmt)

    def add_ai_response(self, response: str):
        """添加 AI 回复"""
        if not response:
            return
        preview = response[:200] + "..." if len(response) > 200 else response
        self._append_log(f"🤖 AI: {preview}", self._normal_fmt)

    def add_tool_call(self, tool_name: str, args: dict = None):
        """添加工具调用"""
        self._tool_call_count += 1
        self._update_step()
        tool_info = f"🔧 工具: {tool_name}"
        if args:
            import json
            args_str = json.dumps(args, ensure_ascii=False, indent=2)[:80]
            self._append_log(f"{tool_info}\n   └ {args_str}", self._tool_fmt)
        else:
            self._append_log(tool_info, self._tool_fmt)

    def add_tool_result(self, tool_name: str, result: str, success: bool = True):
        """添加工具结果"""
        status = "✅" if success else "❌"
        result_preview = str(result)[:150] if result else ""
        if len(str(result)) > 150:
            result_preview += "..."
        fmt = self._tool_success_fmt if success else self._tool_error_fmt
        self._append_log(f"{status} {tool_name}: {result_preview}", fmt)

    def finish_task(self, result: str = None, success: bool = True):
        """完成任务"""
        elapsed = int(time.time() - self._start_time)
        mins = elapsed // 60
        secs = elapsed % 60

        if success:
            self.status_icon.setText("✅")
            self.status_label.setText("已完成")
            self.status_label.setStyleSheet("color: #4EC9B0;")
            self._append_log(f"\n✓ 任务完成 | 耗时 {mins:02d}:{secs:02d} | 工具调用 {self._tool_call_count} 次", self._step_fmt)
            if result:
                result_preview = result[:300] + "\n\n[...]" if len(result) > 300 else result
                self._append_log(f"📋 结果:\n{result_preview}", self._result_fmt)
        else:
            self.status_icon.setText("❌")
            self.status_label.setText("执行失败")
            self.status_label.setStyleSheet("color: #F14C4C;")
            error_msg = result if result else "执行失败"
            self._append_log(f"\n✗ 执行失败 | {error_msg[:100]}", self._error_fmt)

    def clear(self):
        """清空日志"""
        self.log_text.clear()
        self._step_count = 0
        self._tool_call_count = 0


class SubAgentFloatingWidget(CardWidget):
    """
    子智能体悬浮框 - 支持多任务并行显示
    
    使用 SegmentedWidget 切换不同任务的日志视图
    """

    closed = pyqtSignal()
    task_selected = pyqtSignal(str)  # 发出选中的任务ID

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks: Dict[str, SubTaskLogWidget] = {}  # task_id -> widget
        self._task_labels: Dict[str, str] = {}  # task_id -> label text
        self._active_task_id: str = None
        self._batch_started: bool = False  # 当前批次是否已开始
        self._timer: QTimer = None
        self._setup_ui()
        self._start_timer()

    def _setup_ui(self):
        self.setSizePolicy(1, 0)
        self.setMinimumHeight(280)
        self.setStyleSheet("""
            CardWidget {
                background-color: rgba(30, 30, 30, 240);
                border: 1px solid #9C27B0;
                border-radius: 8px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(6)

        # 顶部标题栏
        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel("🤖 子智能体", self)
        title.setFont(get_unified_font(11, True))
        title.setStyleSheet("color: #9C27B0;")
        header.addWidget(title)

        self.task_count_label = QLabel("0 个任务", self)
        self.task_count_label.setFont(get_unified_font(10))
        self.task_count_label.setStyleSheet("color: #888;")
        header.addWidget(self.task_count_label)

        header.addStretch()

        close_btn = QPushButton("✕", self)
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #757575;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #ffffff;
                background-color: #404040;
                border-radius: 3px;
            }
        """)
        close_btn.clicked.connect(self._on_close)
        header.addWidget(close_btn)

        main_layout.addLayout(header)

        # Segment 切换栏
        self.segment_widget = SegmentedWidget(self)
        self.segment_widget.currentItemChanged.connect(self._on_segment_changed)
        main_layout.addWidget(self.segment_widget)

        # 任务日志容器
        self.log_container = QFrame(self)
        self.log_container.setStyleSheet("background-color: transparent;")
        self.log_container_layout = QVBoxLayout(self.log_container)
        self.log_container_layout.setContentsMargins(0, 4, 0, 0)
        self.log_container_layout.setSpacing(4)
        main_layout.addWidget(self.log_container, 1)

        # 空状态提示
        self.empty_label = BodyLabel("暂无运行中的子智能体任务", self)
        self.empty_label.setFont(get_unified_font(10))
        self.empty_label.setStyleSheet("color: #666; padding: 20px;")
        self.empty_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.empty_label)

    def _start_timer(self):
        """启动定时器更新任务时间"""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_all_times)
        self._timer.start(1000)

    def _update_all_times(self):
        """更新所有任务的时间显示"""
        for task_widget in self._tasks.values():
            task_widget._update_time()

    def _on_segment_changed(self, task_id: str):
        """切换任务标签"""
        if task_id and task_id in self._tasks:
            self._show_task_log(task_id)
            self.task_selected.emit(task_id)

    def _show_task_log(self, task_id: str):
        """显示指定任务的日志"""
        if task_id not in self._tasks:
            return
        
        # 隐藏当前显示的任务
        if self._active_task_id and self._active_task_id in self._tasks:
            self._tasks[self._active_task_id].hide()
        
        # 显示选中的任务
        self._tasks[task_id].show()
        self.log_container_layout.addWidget(self._tasks[task_id])
        self._active_task_id = task_id

    def _on_close(self):
        self.setVisible(False)
        self._batch_started = False
        self.closed.emit()

    def add_task(self, task_id: str, agent_name: str, task_desc: str):
        """添加新任务"""
        # 创建任务日志组件（不自动显示启动消息，保持紧凑）
        task_widget = SubTaskLogWidget(task_id, agent_name, task_desc, self.log_container)

        self._tasks[task_id] = task_widget

        # 更新 Segment，标签显示任务序号
        task_index = len(self._tasks)
        self.segment_widget.addItem(task_id, f"任务{task_index}")
        self.segment_widget.setCurrentItem(task_id)

        # 更新计数
        self._update_task_count()

        # 显示日志
        self._show_task_log(task_id)
        self.setVisible(True)

    def update_progress(self, task_id: str, message: str):
        """更新指定任务的进度"""
        if task_id in self._tasks:
            self._tasks[task_id].update_progress(message)

    def add_thinking(self, task_id: str, thinking: str):
        """添加思考内容"""
        if task_id in self._tasks:
            self._tasks[task_id].add_thinking(thinking)

    def add_tool_call(self, task_id: str, tool_name: str, args: dict = None):
        """添加工具调用"""
        if task_id in self._tasks:
            self._tasks[task_id].add_tool_call(tool_name, args)

    def add_tool_result(self, task_id: str, tool_name: str, result: str, success: bool = True):
        """添加工具结果"""
        if task_id in self._tasks:
            self._tasks[task_id].add_tool_result(tool_name, result, success)

    def finish_task(self, task_id: str, result: str = None, success: bool = True):
        """完成任务"""
        if task_id in self._tasks:
            self._tasks[task_id].finish_task(result, success)

            # 更新 Segment 标签显示
            task_index = list(self._tasks.keys()).index(task_id) + 1
            status_text = "✓" if success else "✗"
            label = f"{status_text} 任务{task_index}"
            self._task_labels[task_id] = label
            self.segment_widget.setItemText(task_id, label)
            
            # 更新计数
            self._update_task_count()

        # 如果当前显示的是这个任务，切换到下一个
        if self._active_task_id == task_id:
            self._switch_to_next_active()
        
        # 检查是否所有任务都完成了
        self._check_all_finished()

    def _check_all_finished(self):
        """检查是否所有任务都完成了，如果是则隐藏面板"""
        if not self._tasks:
            return
        
        all_done = all(
            self._task_labels.get(tid, "").startswith(("✓", "✗"))
            for tid in self._tasks
        )
        
        if all_done:
            # 延迟 3 秒后隐藏
            QTimer.singleShot(3000, self.hide)

    def _switch_to_next_active(self):
        """切换到下一个活跃任务"""
        for task_id in self._tasks:
            label = self._task_labels.get(task_id, "")
            if not label.startswith("✓") and not label.startswith("✗"):
                self.segment_widget.setCurrentItem(task_id)
                return

        # 所有任务都完成了，显示第一个
        if self._tasks:
            first_id = list(self._tasks.keys())[0]
            self.segment_widget.setCurrentItem(first_id)

    def _update_task_count(self):
        """更新任务计数"""
        active = sum(
            1 for tid in self._tasks
            if not self._task_labels.get(tid, "").startswith(("✓", "✗"))
        )
        total = len(self._tasks)
        self.task_count_label.setText(f"{active} 个活跃 / {total} 个任务")

        # 显示/隐藏空状态
        if total > 0:
            self.empty_label.hide()
        else:
            self.empty_label.show()

    def remove_task(self, task_id: str):
        """移除任务"""
        if task_id in self._tasks:
            widget = self._tasks[task_id]
            widget.hide()
            self.log_container_layout.removeWidget(widget)
            widget.deleteLater()
            del self._tasks[task_id]

        # 移除 Segment
        self.segment_widget.removeItem(task_id)

        # 更新计数
        self._update_task_count()

        # 如果没有任务了，显示空状态
        if not self._tasks:
            self.empty_label.show()

    def clear(self):
        """清空所有任务"""
        for task_id in list(self._tasks.keys()):
            self.remove_task(task_id)
        self._active_task_id = None
        self._batch_started = False

    def clear_finished_tasks(self):
        """清空已完成的任务（用于新任务开始前清理旧状态）"""
        finished_ids = [
            tid for tid, label in self._task_labels.items()
            if label.startswith(("✓", "✗"))
        ]
        for tid in finished_ids:
            self.remove_task(tid)

    def set_opacity(self, opacity: float):
        """设置透明度，用于响应全局透明度变化"""
        alpha = int(240 * opacity)
        self.setStyleSheet(f"""
            CardWidget {{
                background-color: rgba(30, 30, 30, {alpha});
                border: 1px solid #9C27B0;
                border-radius: 8px;
            }}
        """)