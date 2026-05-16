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
        self._suppress_visible = False  # 被系统卡片压制，工具调用期间不自行显示
        self._rotation_angle = 0
        self._rotation_timer = QTimer(self)
        self._rotation_timer.timeout.connect(self._update_rotation)
        self._rotating = False
        self._svg_renderer = _RotatingIcon(":/icons/执行中.svg", size=18)
        self._setup_ui()

    def _setup_ui(self):
        self.setSizePolicy(1, 0)
        self.setFixedHeight(80)
        self._update_style(False)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(8)

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
            "color: #90caf9; background-color: rgba(144, 202, 249, 0.15); padding: 2px 8px; border-radius: 6px;"
        )

        self.title_label = QLabel("正在执行工具", self)
        self.title_label.setFont(get_unified_font(11, True))
        self.title_label.setStyleSheet("color: #ffb74d;")

        header.addWidget(self.icon_label)
        header.addWidget(self.tool_name_label)
        header.addWidget(self.title_label)
        header.addStretch()

        self.cancel_btn = QPushButton("中止", self)
        self.cancel_btn.setFixedSize(52, 26)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setFont(get_unified_font(9, True))
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 83, 80, 0.9);
                color: white;
                border: 1px solid rgba(239, 83, 80, 0.3);
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(239, 83, 80, 1);
                border: 1px solid rgba(239, 83, 80, 0.6);
            }
            QPushButton:disabled {
                background-color: rgba(117, 117, 117, 0.6);
                border: 1px solid rgba(117, 117, 117, 0.3);
            }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel)
        header.addWidget(self.cancel_btn)

        main_layout.addLayout(header)

        self.task_label = QLabel("等待执行...", self)
        self.task_label.setFont(get_unified_font(10))
        self.task_label.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
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
        self._update_style(False)
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
        self.title_label.setStyleSheet("color: #ffb74d;")
        self._update_style(None)

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
        self.cancel_btn.setVisible(True)

        self.setVisible(True)  # 正常流程直接显示，压制逻辑在 start_tool 之前处理
        self.raise_()
        QApplication.processEvents()

    def _append_progress(self, text: str):
        self.task_label.setText(text)

    def show_when_ready(self):
        """根据经过时间决定是否显示（供外部在适当时机调用）"""
        if self._suppress_visible:
            return
        self.setVisible(True)

    def update_progress(self, message: str):
        """更新进度"""
        self.task_label.setText(f"⏳ {message}")

    def add_tool_call(self, tool_name: str, args: dict = None):
        """添加工具调用"""
        self.tool_name_label.setText(f" {tool_name} ")

    def add_tool_result(self, result: str, success: bool = True):
        """添加工具结果"""
        pass

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

        self._update_style(success)

        if success:
            self.title_label.setText("执行完成")
            self.title_label.setStyleSheet("color: #81c784;")
            self.task_label.setText("✓ 工具执行成功")
        else:
            self.title_label.setText("执行失败")
            self.title_label.setStyleSheet("color: #ef5350;")
            error_msg = result if result else "执行失败"
            self.task_label.setText(f"✗ {error_msg[:50]}")

        self.cancel_btn.setVisible(False)

        self.show_when_ready()  # 统一由 show_when_ready 控制显示时机
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
        self.title_label.setStyleSheet("color: #ffb74d;")
        self._update_style(None)

    def show_if_needed(self, elapsed: float):
        """根据耗时决定是否显示（不考虑压制状态）"""
        if elapsed > 3:
            self.setVisible(True)

    def show_when_ready(self):
        """统一控制显示时机（考虑压制状态）"""
        if not self._suppress_visible:
            self.setVisible(True)

    def set_suppress_visible(self, suppress: bool):
        """设置是否压制显示（系统卡片打开时调用）"""
        self._suppress_visible = suppress
        if suppress:
            self.setVisible(False)
        else:
            # 解除压制，若工具仍在运行则重新显示
            if self._is_running:
                self.setVisible(True)

    def _update_style(self, success: bool = None):
        """更新卡片样式，根据状态改变边框颜色"""
        if success is None:
            # 运行中
            border_color = "#ffb74d"
        elif success:
            # 成功
            border_color = "#81c784"
        else:
            # 失败
            border_color = "#ef5350"

        self.setStyleSheet(f"""
            CardWidget {{
                background-color: rgba(22, 30, 45, 240);
                border: 1px solid {border_color};
                border-radius: 10px;
            }}
        """)

    def set_opacity(self, opacity: float):
        """设置透明度，用于响应全局透明度变化"""
        alpha = int(240 * opacity)
        # 根据当前状态保持边框颜色
        if self._is_running:
            border_color = "#ffb74d"
        elif self.title_label.text() == "执行完成":
            border_color = "#81c784"
        else:
            border_color = "#ef5350"
        self.setStyleSheet(f"""
            CardWidget {{
                background-color: rgba(22, 30, 45, {alpha});
                border: 1px solid {border_color};
                border-radius: 10px;
            }}
        """)
