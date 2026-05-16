# -*- coding: utf-8 -*-
import time

import orjson as json
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRectF
from PyQt5.QtGui import QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QWidget, QApplication,
)
from qfluentwidgets import SimpleCardWidget

from app.utils.utils import get_unified_font


class _RotatingIcon(QWidget):
    """用 QPainter 原地旋转 SVG，消除 QPixmap.transform 的 bounding-box 抖动"""

    def __init__(self, svg_path: str, size: int = 18, parent=None):
        super().__init__(parent)
        self._renderer = QSvgRenderer(svg_path)
        self._size = size
        self._angle = 0
        self.setFixedSize(size, size)
        # 预渲染一帧到 QPixmap，用于 QLabel 显示
        self._last_pixmap = QPixmap(size, size)
        self._last_pixmap.fill(Qt.transparent)

    def set_angle(self, degrees: float):
        self._angle = degrees
        self.update()
        self._redraw()

    def _redraw(self):
        self._last_pixmap.fill(Qt.transparent)
        p = QPainter(self._last_pixmap)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        cx, cy = self._size / 2, self._size / 2
        p.translate(cx, cy)
        p.rotate(self._angle)
        p.translate(-cx, -cy)
        self._renderer.render(p, QRectF(0, 0, self._size, self._size))
        p.end()

    def current_pixmap(self) -> QPixmap:
        return self._last_pixmap

    def paintEvent(self, event):
        p = QPainter(self)
        p.drawPixmap(0, 0, self._last_pixmap)
        p.end()


class ToolFloatingWidget(SimpleCardWidget):
    """工具执行悬浮框组件 - 当工具执行时间过长时显示"""

    cancelled = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._task_start_time = None
        self._is_running = False
        self._current_tool = None
        self._current_process = None
        self._rotation_angle = 0
        self._rotation_timer = QTimer(self)
        self._rotation_timer.timeout.connect(self._update_rotation)
        self._rotating = False
        self._svg_renderer = _RotatingIcon(":/icons/执行中.svg", size=18)
        self._setup_ui()

    def _setup_ui(self):
        self.setSizePolicy(1, 0)
        self.setFixedHeight(80)
        self.setStyleSheet("""
            CardWidget {
                background-color: rgba(33, 33, 38, 250);
                border: 1px solid #f59e0b;
                border-radius: 8px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 10, 16, 10)
        main_layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(10)

        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(22, 22)
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        # 初始显示静态 SVG
        self.icon_label.setPixmap(self._svg_renderer.current_pixmap())

        self.tool_name_label = QLabel("", self)
        self.tool_name_label.setFont(get_unified_font(10))
        self.tool_name_label.setStyleSheet(
            "color: #64b5f6; background-color: rgba(100, 181, 246, 0.1); padding: 2px 8px; border-radius: 4px;"
        )

        self.title_label = QLabel("正在执行工具", self)
        self.title_label.setFont(get_unified_font(11, True))
        self.title_label.setStyleSheet("color: #f59e0b;")

        header.addWidget(self.icon_label)
        header.addWidget(self.tool_name_label)
        header.addWidget(self.title_label)
        header.addStretch()

        self.cancel_btn = QPushButton("中止", self)
        self.cancel_btn.setFixedSize(50, 24)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e53935;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c62828;
            }
            QPushButton:disabled {
                background-color: #757575;
            }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel)
        header.addWidget(self.cancel_btn)

        main_layout.addLayout(header)

        self.task_label = QLabel("等待执行...", self)
        self.task_label.setFont(get_unified_font(10))
        self.task_label.setStyleSheet("color: #9e9e9e;")
        self.task_label.setWordWrap(True)
        self.task_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        main_layout.addWidget(self.task_label)

    # ── 旋转图标 ──────────────────────────────────────────

    def _start_rotation(self):
        if not self._rotating:
            self._rotating = True
            self._rotation_timer.start(30)  # 30ms ≈ 33fps，流畅旋转

    def _stop_rotation(self):
        self._rotating = False
        self._rotation_timer.stop()

    def _update_rotation(self):
        self._rotation_angle = (self._rotation_angle + 12) % 360
        self._svg_renderer.set_angle(self._rotation_angle)
        self.icon_label.setPixmap(self._svg_renderer.current_pixmap())

    def _on_close(self):
        self.setVisible(False)
        self.closed.emit()

    def _on_cancel(self):
        self._is_running = False
        self._stop_rotation()
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("已中止")
        self.title_label.setText("执行已中止")
        self.title_label.setStyleSheet("color: #ef5350;")
        self.cancelled.emit()

    def set_process(self, process):
        """设置当前进程以便中止"""
        self._current_process = process

    def start_tool(self, tool_name: str, args: dict = None):
        """开始执行工具"""
        self._task_start_time = time.time()
        self._is_running = True
        self._current_tool = tool_name
        self._current_process = None

        self.title_label.setText("正在执行工具")
        self.title_label.setStyleSheet("color: #f59e0b;")

        self._start_rotation()

        self.tool_name_label.setText(f" {tool_name} ")

        args_preview = ""
        if args:
            args_str = json.dumps(args).decode('utf-8')
            if len(args_str) > 60:
                args_preview = f"{args_str[:60]}..."
            else:
                args_preview = f"{args_str}"

        self.task_label.setText(f"⏳ {args_preview}")

        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("中止")

        self.setVisible(True)
        self.raise_()
        QApplication.processEvents()

    def _append_progress(self, text: str):
        self.task_label.setText(text)

    def update_progress(self, message: str):
        """更新进度"""
        import time

        elapsed = time.time() - self._task_start_time if self._task_start_time else 0

        if elapsed > 3:
            self.setVisible(True)

        self.task_label.setText(f"⏳ {message}")

    def add_tool_call(self, tool_name: str, args: dict = None):
        """添加工具调用"""
        import time

        elapsed = time.time() - self._task_start_time if self._task_start_time else 0

        if elapsed > 3:
            self.setVisible(True)

        self.tool_name_label.setText(f" {tool_name} ")

    def add_tool_result(self, result: str, success: bool = True):
        """添加工具结果"""
        import time

        elapsed = time.time() - self._task_start_time if self._task_start_time else 0

        if elapsed > 3:
            self.setVisible(True)

    def finish_tool(self, result: str = None, success: bool = True):
        """完成工具执行"""
        self._is_running = False
        self._current_process = None
        self._stop_rotation()

        # 清除旋转 pixmap，显示结果表情
        self.icon_label.setPixmap(QPixmap())
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setFont(get_unified_font(14))
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        self.icon_label.setText("✅" if success else "❌")

        if success:
            self.title_label.setText("执行完成")
            self.title_label.setStyleSheet("color: #66bb6a;")
            self.task_label.setText("✓ 工具执行成功")
        else:
            self.title_label.setText("执行失败")
            self.title_label.setStyleSheet("color: #ef5350;")
            error_msg = result if result else "执行失败"
            self.task_label.setText(f"✗ {error_msg[:50]}")

        self.cancel_btn.setVisible(False)

        self.setVisible(True)
        self.raise_()

        QTimer.singleShot(2000, self.hide)

    def is_cancelled(self) -> bool:
        """检查是否已被中止"""
        return not self._is_running

    def clear(self):
        """清空显示"""
        self._task_start_time = None
        self._is_running = False
        self._current_tool = None
        self._current_process = None
        self._stop_rotation()
        self._rotation_angle = 0
        self.setVisible(False)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setVisible(True)
        self.cancel_btn.setText("中止")
        self.icon_label.setPixmap(self._svg_renderer.current_pixmap())
        self.icon_label.setText("")
        self.icon_label.setFixedSize(22, 22)
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        self.title_label.setText("正在执行工具")
        self.title_label.setStyleSheet("color: #f59e0b;")

    def show_if_needed(self, elapsed: float):
        """根据耗时决定是否显示"""
        if elapsed > 3:
            self.setVisible(True)

    def set_opacity(self, opacity: float):
        """设置透明度，用于响应全局透明度变化"""
        alpha = int(250 * opacity)
        self.setStyleSheet(f"""
            CardWidget {{
                background-color: rgba(33, 33, 38, {alpha});
                border: 1px solid #f59e0b;
                border-radius: 8px;
            }}
        """)
