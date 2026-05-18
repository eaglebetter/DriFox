# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout
from qfluentwidgets import SimpleCardWidget, FluentIcon, TransparentToolButton

from app.utils.design_tokens import Colors
from app.utils.utils import get_unified_font


class TodoFloatingWidget(SimpleCardWidget):
    """TODO 悬浮框组件"""

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._todo_list = []
        self._setup_ui()

    def _setup_ui(self):
        self.setSizePolicy(1, 0)
        self._apply_style()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 10, 14, 10)
        main_layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(10)

        title_icon = QLabel("📋", self)
        title_icon.setFont(get_unified_font(14))

        title = QLabel("待办事项", self)
        title.setFont(get_unified_font(11, True))
        title.setStyleSheet(f"color: {Colors.REALTIME_TEXT};")

        self.progress_label = QLabel("", self)
        self.progress_label.setFont(get_unified_font(10, True))
        self.progress_label.setStyleSheet(f"color: {Colors.REALTIME_ACCENT}; font-weight: bold;")

        header.addWidget(title_icon)
        header.addWidget(title)
        header.addWidget(self.progress_label)
        header.addStretch()

        self.close_btn = TransparentToolButton(FluentIcon.CLOSE)
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self._on_close)
        header.addWidget(self.close_btn)

        self.content_label = QLabel("暂无待办", self)
        self.content_label.setFont(get_unified_font(10))
        self.content_label.setStyleSheet(f"color: {Colors.REALTIME_TEXT_SECONDARY};")
        self.content_label.setWordWrap(True)
        self.content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.content_label.setAlignment(Qt.AlignTop)

        main_layout.addLayout(header)
        main_layout.addWidget(self.content_label, 1)

    def _apply_style(self):
        Colors.refresh()
        self.setStyleSheet(f"""
            CardWidget {{
                background-color: {Colors.REALTIME_BG};
                border: 1px solid {Colors.REALTIME_BORDER};
                border-radius: 10px;
            }}
        """)

    def refresh_style(self):
        """响应主题切换"""
        self._apply_style()
        # 刷新标题颜色
        title_label = self.findChild(QLabel, "")
        for child in self.findChildren(QLabel):
            text = child.text()
            if text == "待办事项":
                child.setStyleSheet(f"color: {Colors.REALTIME_TEXT};")
            elif child == self.progress_label:
                # 进度标签颜色由 update_todos 控制，不在这里刷新
                pass
            elif child == self.content_label:
                # 内容颜色由 update_todos 控制，不在这里刷新
                pass
        # 如果有数据，重新渲染
        if self._todo_list:
            self.update_todos(self._todo_list)

    def _on_close(self):
        self.setVisible(False)
        self.closed.emit()

    def update_todos(self, todos):
        """更新 TODO 列表显示（不自行控制可见性，由调用方决定）"""
        self._todo_list = todos or []

        if not self._todo_list:
            self.setVisible(False)
            return

        lines = []
        completed = 0
        in_progress = 0
        for todo in self._todo_list:
            status = todo.get("status", "")
            content = todo.get("content", "")
            priority = todo.get("priority", "medium")

            if status == "completed":
                completed += 1
                status_icon = "✓"
            elif status == "in_progress":
                in_progress += 1
                status_icon = "▶"
            else:
                status_icon = "○"

            priority_colors = {"high": Colors.REALTIME_ERROR, "medium": Colors.REALTIME_ACCENT_WARM, "low": Colors.REALTIME_SUCCESS}
            priority_color = priority_colors.get(priority, Colors.REALTIME_ACCENT_WARM)

            priority_labels = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            priority_icon = priority_labels.get(priority, "🟡")

            if status == "completed":
                content_style = f"color: {Colors.REALTIME_TEXT_SECONDARY}; text-decoration: line-through;"
            elif status == "in_progress":
                content_style = f"color: {Colors.REALTIME_ACCENT}; font-weight: bold;"
            else:
                content_style = f"color: {Colors.REALTIME_TEXT};"

            lines.append(
                f'<span style="color: {Colors.REALTIME_ACCENT}; font-weight: bold;">{status_icon}</span> '
                f'<span style="color: {priority_color};">{priority_icon}</span> '
                f'<span style="{content_style}">{content}</span>'
            )

        total = len(self._todo_list)
        done_count = completed + in_progress
        if done_count == total and done_count > 0:
            if in_progress > 0:
                progress_text = f"⏳ {in_progress}进行中 + {completed}完成"
                self.progress_label.setStyleSheet(f"color: {Colors.REALTIME_ACCENT}; font-weight: bold;")
            else:
                progress_text = f"🎉 {completed}/{total} 全部完成"
                self.progress_label.setStyleSheet(f"color: {Colors.REALTIME_SUCCESS}; font-weight: bold;")
        else:
            progress_text = f"{completed}完成/{in_progress}进行中/{total}"
            self.progress_label.setStyleSheet(f"color: {Colors.REALTIME_ACCENT}; font-weight: bold;")

        self.progress_label.setText(progress_text)
        self.content_label.setText("<br>".join(lines))

    def clear(self):
        """清空 TODO 显示"""
        self._todo_list = []
        self.setVisible(False)

    def set_opacity(self, opacity: float):
        """设置透明度，用于响应全局透明度变化"""
        Colors.refresh()
        # 从 REALTIME_BG 提取 alpha 并替换
        bg = Colors.REALTIME_BG
        if bg.startswith("rgba("):
            alpha = int(opacity * 255)
            bg = bg.rsplit(",", 1)[0] + f", {alpha})"
        self.setStyleSheet(f"""
            CardWidget {{
                background-color: {bg};
                border: 1px solid {Colors.REALTIME_BORDER};
                border-radius: 10px;
            }}
        """)
