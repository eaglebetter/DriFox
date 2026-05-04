# -*- coding: utf-8 -*-
"""
通用设置卡片基类 - 统一的设计语言
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
)
from qfluentwidgets import CardWidget, StrongBodyLabel, TransparentToolButton
from app.utils.utils import get_unified_font, get_icon


class BaseSettingsCard(CardWidget):
    """通用设置卡片基类"""

    closed = pyqtSignal()
    tabChanged = pyqtSignal(str)  # 标签切换信号

    def __init__(self, title: str, icon: str = "⚙️", parent=None):
        super().__init__(parent)
        self._title = title
        self._icon = icon
        self._current_tab = "main"  # 支持标签切换
        self._setup_base_ui()

    def _setup_base_ui(self):
        self.setSizePolicy(1, 0)  # 水平方向可扩展
        self.setFixedHeight(180)  # 固定高度，超出滚动
        self.setStyleSheet("""
            CardWidget {
                background-color: rgba(33, 33, 38, 250);
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(4)

        # 头部
        header = QHBoxLayout()
        header.setSpacing(8)

        self.icon_label = QLabel(self._icon, self)
        self.icon_label.setFont(get_unified_font(12))

        self.title_label = StrongBodyLabel(self._title, self)
        self.title_label.setFont(get_unified_font(11, True))
        self.title_label.setStyleSheet("color: #f59e0b;")

        header.addWidget(self.icon_label)
        header.addWidget(self.title_label)

        # 标签切换按钮容器
        self._tab_buttons_container = QHBoxLayout()
        self._tab_buttons_container.setSpacing(4)
        header.addLayout(self._tab_buttons_container)

        header.addStretch()

        # 额外按钮容器
        self._extra_buttons_container = QHBoxLayout()
        self._extra_buttons_container.setSpacing(4)
        header.addLayout(self._extra_buttons_container)

        # 关闭按钮
        self.close_btn = QLabel("✕", self)
        self.close_btn.setFont(get_unified_font(11))
        self.close_btn.setStyleSheet("color: #888888; cursor: pointer; padding: 4px;")
        self.close_btn.mousePressEvent = lambda e: self._on_close()
        header.addWidget(self.close_btn)

        main_layout.addLayout(header)

        # 内容区域 - 使用 ScrollArea
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
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
                width: 12px;
                margin: 4px 4px 4px 4px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #888888;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 4, 0, 4)
        self.content_layout.setSpacing(6)

        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area, 1)

    def _on_tab_clicked(self, tab_id: str):
        """标签点击处理"""
        if self._current_tab != tab_id:
            self._current_tab = tab_id
            self._update_tab_styles()
            self.tabChanged.emit(tab_id)

    def _on_close(self):
        self.setVisible(False)
        self.closed.emit()

    def show(self):
        self.setVisible(True)
        self.raise_()

    def hide(self):
        self.setVisible(False)

    def set_opacity(self, opacity: float):
        """设置透明度，用于响应全局透明度变化"""
        alpha = int(250 * opacity)
        self.setStyleSheet(f"""
            CardWidget {{
                background-color: rgba(33, 33, 38, {alpha});
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }}
        """)

    def set_extra_button_handler(self, handler):
        """
        设置额外的按钮处理器，用于添加自定义按钮

        Args:
            handler: 可调用的函数，点击按钮时触发
        """
        from qfluentwidgets import TransparentToolButton

        # 移除已有按钮
        while self._extra_buttons_container.count():
            item = self._extra_buttons_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加导入按钮
        import_btn = TransparentToolButton(get_icon("导入"), self)
        import_btn.setToolTip("导入会话")
        import_btn.setFixedSize(24, 24)
        import_btn.clicked.connect(handler)
        self._extra_buttons_container.addWidget(import_btn)

    def setup_tabs(self, tabs: list, default_tab: str = None):
        """
        设置标签切换按钮

        Args:
            tabs: 标签列表，每项为 (tab_id: str, tab_name: str)
            default_tab: 默认选中的标签
        """
        from qfluentwidgets import TransparentToolButton

        # 清除现有标签按钮
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
            btn.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.5);
                    font-size: 11px;
                    padding: 3px 8px;
                    border-radius: 4px;
                    cursor: pointer;
                }
                QLabel:hover {
                    color: rgba(255, 255, 255, 0.8);
                    background-color: rgba(255, 255, 255, 0.1);
                }
            """)
            btn.setCursor(Qt.PointingHandCursor)
            btn.mousePressEvent = lambda e, tid=tab_id: self._on_tab_clicked(tid)
            self._tab_buttons_container.addWidget(btn)
            self._tab_buttons[tab_id] = btn

        # 更新样式
        self._update_tab_styles()

    def _on_tab_clicked(self, tab_id: str):
        """标签点击处理"""
        if self._current_tab != tab_id:
            self._current_tab = tab_id
            self._update_tab_styles()
            self.tabChanged.emit(tab_id)

    def _update_tab_styles(self):
        """更新标签样式"""
        for tab_id, btn in self._tab_buttons.items():
            if tab_id == self._current_tab:
                btn.setStyleSheet("""
                    QLabel {
                        color: #fff;
                        font-size: 11px;
                        font-weight: bold;
                        padding: 3px 8px;
                        border-radius: 4px;
                        background-color: rgba(102, 198, 255, 0.3);
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QLabel {
                        color: rgba(255, 255, 255, 0.5);
                        font-size: 11px;
                        padding: 3px 8px;
                        border-radius: 4px;
                        cursor: pointer;
                    }
                    QLabel:hover {
                        color: rgba(255, 255, 255, 0.8);
                        background-color: rgba(255, 255, 255, 0.1);
                    }
                """)
