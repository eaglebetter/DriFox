# -*- coding: utf-8 -*-
"""
AnimatedCardFrame — QFrame 基类 + paintEvent 彩虹渐变边框 + 头部标准布局

所有系统设置卡片都应继承此类，以获得统一的视觉语言：
- 彩虹渐变边框（动画旋转）
- 标准头部（图标 + 标题 + 标签/统计 + 关闭按钮）
- ScrollArea 内容区
"""

import time
from PyQt5.QtCore import Qt, QVariantAnimation, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QLinearGradient, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
)
from qfluentwidgets import (
    StrongBodyLabel, TransparentToolButton, FluentIcon, PrimaryToolButton)

from app.utils.design_tokens import TabStyles
from app.utils.utils import get_unified_font, get_icon


class AnimatedCardFrame(QFrame):
    """带彩虹边框动画的系统卡片基类"""

    closed = pyqtSignal()
    tabChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hue_offset = 0.0
        self._anim_started = False

        # 彩虹边框动画（3秒一圈）
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(3000)
        self._anim.setStartValue(0)
        self._anim.setEndValue(360)
        self._anim.setLoopCount(-1)
        self._anim.valueChanged.connect(self._on_hue_changed)

        self._build_base_ui()

    # ── UI 构建 ──────────────────────────────────────────

    def _build_base_ui(self):
        self.setSizePolicy(1, 0)
        self.setFixedHeight(180)
        self._apply_base_style()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 5, 6, 5)
        main_layout.setSpacing(4)

        # ── 头部 ──
        self._header_layout = QHBoxLayout()
        self._header_layout.setSpacing(4)

        self.icon_label = QLabel(self)
        self.icon_label.setFont(get_unified_font(11))

        self.title_label = StrongBodyLabel(self)
        self.title_label.setFont(get_unified_font(10, True))
        self.title_label.setStyleSheet("color: #C9A85C;")

        self._header_layout.addWidget(self.icon_label)
        self._header_layout.addWidget(self.title_label)

        # 数量统计
        self._count_label = QLabel("", self)
        self._count_label.setFont(get_unified_font(10))
        self._count_label.setStyleSheet("color: rgba(255,255,255,0.5); padding-left: 2px;")
        self._count_label.setVisible(False)
        self._header_layout.addWidget(self._count_label)

        # 标签按钮容器
        self._tab_buttons_container = QHBoxLayout()
        self._tab_buttons_container.setSpacing(4)
        self._header_layout.addLayout(self._tab_buttons_container)

        self._header_layout.addStretch()

        # 额外按钮容器
        self._extra_buttons_container = QHBoxLayout()
        self._extra_buttons_container.setSpacing(4)
        self._header_layout.addLayout(self._extra_buttons_container)

        # 关闭按钮
        self.close_btn = TransparentToolButton(FluentIcon.CLOSE)
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.mousePressEvent = lambda e: self._on_close()
        self._header_layout.addWidget(self.close_btn)

        main_layout.addLayout(self._header_layout)

        # ── 内容区 ──
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(self._scroll_style())
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(self.content_widget)
        self._content_layout.setContentsMargins(4, 2, 4, 2)
        self._content_layout.setSpacing(4)

        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area, 1)

    @property
    def content_layout(self):
        return self._content_layout

    # ── 样式 ──────────────────────────────────────────

    def _apply_base_style(self):
        self.setStyleSheet("""
            AnimatedCardFrame {
                background: rgba(22, 30, 45, 230);
                border-radius: 12px;
            }
        """)

    @staticmethod
    def _scroll_style() -> str:
        return """
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 10px;
                margin: 4px 2px 4px 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.18);
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,0.3);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """

    # ── 彩虹边框动画 ────────────────────────────────────

    def _on_hue_changed(self, value: float):
        self._hue_offset = value
        self.update()

    def paintEvent(self, event):
        """绘制彩虹渐变边框"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        hue = int(self._hue_offset) % 360
        colors = [
            (0.00, QColor.fromHsv(hue, 200, 200, 140)),
            (0.25, QColor.fromHsv((hue + 72) % 360, 200, 200, 140)),
            (0.50, QColor.fromHsv((hue + 144) % 360, 200, 200, 140)),
            (0.75, QColor.fromHsv((hue + 216) % 360, 200, 200, 140)),
            (1.00, QColor.fromHsv((hue + 288) % 360, 200, 200, 140)),
        ]
        for pos, color in colors:
            gradient.setColorAt(pos, color)

        painter.setPen(QPen(QBrush(gradient), 2))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 11, 11)
        painter.end()

    # ── 公开控制 ───────────────────────────────────────

    def start_animation(self):
        if not self._anim_started:
            self._anim_started = True
            self._anim.start()

    def stop_animation(self):
        if self._anim_started:
            self._anim_started = False
            self._anim.stop()
            self._hue_offset = 0
            self.update()

    def set_icon(self, icon: str):
        """设置头部图标（emoji 或 FluentIcon）"""
        self.icon_label.setText(icon)

    def set_title_text(self, text: str):
        """设置头部标题文字"""
        self.title_label.setText(text)

    def set_count(self, count: int, limit: int = None):
        """设置标题右侧统计"""
        if limit and limit > 0:
            self._count_label.setText(f"({count}/{limit})")
        elif count > 0:
            self._count_label.setText(f"({count})")
        else:
            self._count_label.setText("")
        self._count_label.setVisible(count > 0 or (limit and limit > 0))

    def set_count_label(self, text: str):
        """设置标题右侧统计文本（自定义格式）"""
        self._count_label.setText(f"({text})" if text else "")
        self._count_label.setVisible(bool(text))

    def setup_tabs(self, tabs: list, default_tab: str = None):
        """设置标签切换按钮"""
        while self._tab_buttons_container.count():
            item = self._tab_buttons_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._tabs = tabs
        self._default_tab = default_tab or (tabs[0][0] if tabs else None)
        self._current_tab = self._default_tab
        self._tab_buttons = {}

        for tab_id, tab_name in tabs:
            btn = QLabel(f" {tab_name} ", self)
            btn.setFont(get_unified_font(11))
            btn.setStyleSheet(TabStyles.inactive())
            btn.setCursor(Qt.PointingHandCursor)
            btn.mousePressEvent = lambda e, tid=tab_id: self._on_tab_clicked(tid)
            self._tab_buttons_container.addWidget(btn)
            self._tab_buttons[tab_id] = btn

        self._update_tab_styles()

    def _on_tab_clicked(self, tab_id: str):
        if self._current_tab != tab_id:
            self._current_tab = tab_id
            self._update_tab_styles()
            self.tabChanged.emit(tab_id)

    def _update_tab_styles(self):
        for tab_id, btn in self._tab_buttons.items():
            btn.setStyleSheet(TabStyles.active() if tab_id == self._current_tab else TabStyles.inactive())
            btn.setFont(get_unified_font(11))

    def set_extra_button_handler(self, handler):
        """添加额外按钮到标题栏（默认：导入按钮）"""
        while self._extra_buttons_container.count():
            item = self._extra_buttons_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        btn = TransparentToolButton(get_icon("导入"), self)
        btn.setToolTip("导入会话")
        btn.clicked.connect(handler)
        self._extra_buttons_container.addWidget(btn)

    def set_save_button_handler(self, handler):
        """在标题栏添加保存按钮"""
        while self._extra_buttons_container.count():
            item = self._extra_buttons_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        btn = PrimaryToolButton(FluentIcon.SAVE, self)
        btn.setFixedSize(30, 30)
        btn.clicked.connect(handler)
        self._extra_buttons_container.addWidget(btn)

    # ── 生命周期 ──────────────────────────────────────

    def _on_close(self):
        self.setVisible(False)
        self.closed.emit()

    def show(self):
        self.setVisible(True)
        self.raise_()
        if not self._anim_started:
            self.start_animation()

    def hide(self):
        self.setVisible(False)

    def set_opacity(self, opacity: float):
        """设置透明度（保留，用于全局透明度变化）"""
        # 暂不支持透明度动态调整边框颜色，按需扩展
        pass