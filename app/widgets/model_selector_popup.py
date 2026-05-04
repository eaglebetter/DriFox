# -*- coding: utf-8 -*-
"""
扁平式模型选择上拉框 - 类似 OpenCode 风格
展示所有已配置服务商的模型，服务商作为小标题，下面是模型列表
"""
from typing import List, Tuple, Dict, Any

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QLineEdit,
    QApplication,
    QDialog,
    QPushButton,
)
from qfluentwidgets import FluentIcon, TransparentToolButton
from app.widgets.provider_setting_card import ProviderIconWidget

from app.utils.utils import get_font_family_css, get_icon


class ProviderHeader(QWidget):
    """服务商标题行"""

    def __init__(self, provider_name: str, parent=None):
        super().__init__(parent)
        self.provider_name = provider_name
        self.setFixedHeight(36)
        self.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 8, 0)
        layout.setSpacing(8)

        # 服务商图标
        self.icon_widget = ProviderIconWidget(provider_name, 20)
        layout.addWidget(self.icon_widget)

        # 服务商名称
        self.name_label = QLabel(provider_name, self)
        self.name_label.setStyleSheet(f"color: #e0e0e0; {get_font_family_css()} font-size: 12px; font-weight: bold;")
        layout.addWidget(self.name_label)

        layout.addStretch(1)


class ModelItem(QWidget):
    """单个模型项 - 可点击"""
    clicked = pyqtSignal(str, str)  # provider_name, model_name

    def __init__(self, provider_name: str, model_name: str, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.provider_name = provider_name
        self.model_name = model_name
        self.is_active = is_active
        self.setFixedHeight(34)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(30, 0, 12, 0)
        layout.setSpacing(8)

        # 选中状态指示点
        self.dot = QLabel("●", self)
        self.dot.setStyleSheet(
            f"color: #0078d4; {get_font_family_css()} font-size: 10px;" if self.is_active else f"color: transparent; {get_font_family_css()} font-size: 10px;"
        )
        self.dot.setFixedWidth(14)
        layout.addWidget(self.dot)

        # 模型名
        self.name_label = QLabel(self.model_name, self)
        if self.is_active:
            self.name_label.setStyleSheet(f"color: #ffffff; font-weight: bold; {get_font_family_css()} font-size: 13px;")
        else:
            self.name_label.setStyleSheet(f"color: #cccccc; {get_font_family_css()} font-size: 13px;")
        layout.addWidget(self.name_label, 1)

    def set_active(self, active: bool):
        self.is_active = active
        self.dot.setStyleSheet(
            f"color: #0078d4; {get_font_family_css()} font-size: 10px;" if active else f"color: transparent; {get_font_family_css()} font-size: 10px;"
        )
        if active:
            self.name_label.setStyleSheet(f"color: #ffffff; font-weight: bold; {get_font_family_css()} font-size: 13px;")
        else:
            self.name_label.setStyleSheet(f"color: #cccccc; {get_font_family_css()} font-size: 13px;")

    def mousePressEvent(self, event):
        self.clicked.emit(self.provider_name, self.model_name)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        if not self.is_active:
            self.name_label.setStyleSheet(f"color: #ffffff; {get_font_family_css()} font-size: 13px;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.is_active:
            self.name_label.setStyleSheet(f"color: #cccccc; {get_font_family_css()} font-size: 13px;")
        super().leaveEvent(event)


class ModelSelectorPopup(QWidget):
    """扁平式模型选择弹窗"""
    modelSelected = pyqtSignal(str, str)  # provider_name, model_name
    addProviderClicked = pyqtSignal()  # 添加服务商
    configureProviderClicked = pyqtSignal()  # 配置服务商

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.parent_widget = parent

        # 数据
        self._provider_models: List[Tuple[str, List[str]]] = []  # [(provider, [models])]
        self._current_provider: str = ""
        self._current_model: str = ""
        self._model_widgets: List[ModelItem] = []
        self._all_model_items: List[Tuple[ModelItem, str, str]] = []  # (widget, provider, model)

        self._setup_ui()

    def _setup_ui(self):
        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("popupFrame")
        self.main_frame.setStyleSheet("""
            QFrame#popupFrame {
                background-color: #2d2d2d;
                border: 1px solid #444444;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self.main_frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        # 搜索框 + 操作按钮区域
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(4)

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("搜索模型...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 6px 10px;
                selection-background-color: #0078d4;
                selection-color: #ffffff;
                {get_font_family_css()} font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: #0078d4;
                background-color: #404040;
            }}
            QLineEdit::placeholder {{
                color: #888888;
            }}
            QLineEdit::text {{
                background-color: transparent;
            }}
            /* 清除按钮样式 */
            QLineEdit QToolButton {{
                background-color: transparent;
                border: none;
                padding: 2px;
            }}
            QLineEdit QToolButton:hover {{
                background-color: #555555;
                border-radius: 3px;
            }}
            QLineEdit QToolButton:pressed {{
                background-color: #666666;
            }}
        """)
        self.search_edit.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_edit, 1)

        # 添加服务商按钮
        self.add_provider_btn = TransparentToolButton(FluentIcon.ADD, self)
        self.add_provider_btn.setFixedSize(28, 28)
        self.add_provider_btn.setToolTip("添加服务商")
        self.add_provider_btn.clicked.connect(lambda: self.addProviderClicked.emit())
        search_layout.addWidget(self.add_provider_btn)

        # 配置服务商按钮
        self.config_provider_btn = TransparentToolButton(get_icon("配置管理"), self)
        self.config_provider_btn.setFixedSize(28, 28)
        self.config_provider_btn.setToolTip("配置服务商")
        self.config_provider_btn.clicked.connect(lambda: self.configureProviderClicked.emit())
        search_layout.addWidget(self.config_provider_btn)

        layout.addLayout(search_layout)

        # 分隔线
        separator = QFrame(self)
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #3d3d3d; max-height: 1px; margin: 6px 0;")
        layout.addWidget(separator)

        # 滚动区域
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
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
                margin: 4px;
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
        """)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        # 底部弹性空间，让内容靠上
        self.content_layout.addStretch(1)

        self.scroll_area.setWidget(self.content_widget)
        self.scroll_area.setMinimumHeight(50)
        layout.addWidget(self.scroll_area, 1)

        # 整体窗口布局
        window_layout = QVBoxLayout(self)
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.addWidget(self.main_frame)

    def set_providers_data(
        self,
        provider_models: List[Tuple[str, List[str], bool]],  # (provider, [models], is_current_provider)
        current_provider: str,
        current_model: str,
    ):
        """设置服务商和模型数据"""
        self._current_provider = current_provider
        self._current_model = current_model
        self._provider_models = [(p, m) for p, m, _ in provider_models]
        self._model_widgets.clear()
        self._all_model_items.clear()

        # 清空内容区域（保留最后的 stretch）
        while self.content_layout.count() > 0:
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        search_text = self.search_edit.text().strip().lower()

        for provider_name, models, is_current_provider in provider_models:
            # 过滤
            if search_text:
                filtered_models = [m for m in models if search_text in m.lower()]
                if not filtered_models:
                    continue
            else:
                filtered_models = models

            # 服务商标题
            header = ProviderHeader(provider_name, self)
            self.content_layout.addWidget(header)

            # 模型列表
            for model_name in filtered_models:
                is_active = (
                    provider_name == current_provider and model_name == current_model
                )
                item = ModelItem(provider_name, model_name, is_active, self)
                item.clicked.connect(self._on_model_clicked)
                self.content_layout.addWidget(item)
                self._model_widgets.append(item)
                self._all_model_items.append((item, provider_name, model_name))

        # 如果没有匹配的模型
        if not self._all_model_items and search_text:
            no_result = QLabel(f"未找到匹配 \"{search_text}\" 的模型", self)
            no_result.setAlignment(Qt.AlignCenter)
            no_result.setStyleSheet(f"color: #888888; {get_font_family_css()} font-size: 12px; padding: 20px;")
            self.content_layout.addWidget(no_result)

        # 底部弹性空间
        self.content_layout.addStretch(1)

        # 隐藏时 adjustSize 不生效，改用显式 resize
        self.main_frame.layout().activate()
        QApplication.processEvents()
        content_size = self.main_frame.sizeHint()
        self.resize(content_size.width(), content_size.height())

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def _on_search_changed(self, text: str):
        """搜索文本变化时刷新列表"""
        # 重新构建 provider_models 数据（从保存的原始数据重建）
        # 需要重新获取 is_current_provider 信息
        provider_models_with_flag = []
        for prov, models in self._provider_models:
            is_cur = prov == self._current_provider
            provider_models_with_flag.append((prov, models, is_cur))

        self.set_providers_data(
            provider_models_with_flag,
            self._current_provider,
            self._current_model,
        )

    def _on_model_clicked(self, provider_name: str, model_name: str):
        """模型被点击"""
        self.modelSelected.emit(provider_name, model_name)
        self.close()

    def show_at(self, reference_widget: QWidget):
        """在参考控件上方显示弹窗（向上展开）"""
        # 先显示以激活布局计算
        self.show()
        QApplication.processEvents()

        # 获取内容实际需要的尺寸
        content_size = self.content_widget.sizeHint()
        content_width = max(content_size.width(), 350)  # 最小宽度确保能显示完整名称
        scroll_area_height = content_size.height() + 20  # 搜索框+边距

        # 设置合理的最大尺寸
        screen = QApplication.primaryScreen()
        if screen:
            screen_geom = screen.availableGeometry()
            max_width = max(min(450, screen_geom.width() - 40), content_width)
            max_height = min(500, screen_geom.height() - 120)
        else:
            max_width = max(450, content_width)
            max_height = 500

        self.setMaximumSize(max_width, max_height)

        # 使用内容尺寸 resize（宽高各缩小1/3）
        new_width = max_width * 2 // 3
        new_height = min(scroll_area_height, 500) * 2 // 3
        self.resize(new_width, new_height)

        btn_rect = reference_widget.rect()
        btn_global_pos = reference_widget.mapToGlobal(btn_rect.topLeft())

        popup_width = min(self.width(), self.maximumWidth())
        popup_height = min(self.height(), self.maximumHeight())

        # 水平位置：左对齐到按钮左边缘
        x = btn_global_pos.x()

        # 垂直位置：在按钮上方展开
        y = btn_global_pos.y() - popup_height

        if screen:
            # 水平边界检查
            if x < screen_geom.left():
                x = screen_geom.left() + 10
            if x + popup_width > screen_geom.right():
                x = screen_geom.right() - popup_width - 10
            # 如果上方空间不够，显示在下方
            if y < screen_geom.top():
                y = btn_global_pos.y() + btn_rect.height()

        self.move(x, y)
        self.show()
        self.raise_()
        self.search_edit.setFocus()
        self.search_edit.selectAll()


class ProviderConfigListDialog(QDialog):
    """配置服务商弹窗 - 展示已配置的服务商列表"""

    def __init__(self, providers: Dict[str, Dict[str, Any]], current_provider: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("配置服务商")
        self.setMinimumSize(420, 350)
        self.setMaximumSize(520, 600)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        self.setModal(True)
        self._providers = providers
        self._current_provider = current_provider
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #cccccc;
                background: transparent;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title = QLabel("已配置的服务商")
        title.setStyleSheet(f"color: #ffffff; font-size: 16px; font-weight: bold; {get_font_family_css()}")
        layout.addWidget(title)

        # 提示文字
        hint = QLabel("点击编辑按钮可修改服务商配置，点击删除按钮可移除服务商。")
        hint.setStyleSheet(f"color: #888888; font-size: 12px; {get_font_family_css()}")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # 分隔线
        sep = QFrame(self)
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #3d3d3d; max-height: 1px;")
        layout.addWidget(sep)

        # 滚动区域
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
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
                margin: 4px;
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
        """)

        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        if not self._providers:
            empty_label = QLabel("暂无已配置的服务商，请点击「添加」按钮添加。")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet(f"color: #888888; {get_font_family_css()} font-size: 13px; padding: 30px;")
            content_layout.addWidget(empty_label)
        else:
            for provider_name, config in self._providers.items():
                provider_widget = self._create_provider_item(provider_name, config)
                content_layout.addWidget(provider_widget)

        content_layout.addStretch(1)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)

        # 关闭按钮
        close_btn_layout = QHBoxLayout()
        close_btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setFixedSize(100, 36)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #3d3d3d;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 6px;
                {get_font_family_css()} font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #4d4d4d;
                color: #ffffff;
            }}
        """)
        close_btn.clicked.connect(self.accept)
        close_btn_layout.addWidget(close_btn)
        layout.addLayout(close_btn_layout)

    def _create_provider_item(self, provider_name: str, config: Dict[str, Any]) -> QWidget:
        """创建一个服务商配置项"""
        widget = QWidget()
        widget.setFixedHeight(48)
        is_current = provider_name == self._current_provider
        widget.setStyleSheet(f"""
            QWidget#provider_item_{provider_name} {{
                background-color: {'#383838' if is_current else '#333333'};
                border-radius: 6px;
                border: {'1px solid #0078d4' if is_current else '1px solid transparent'};
            }}
            QWidget#provider_item_{provider_name}:hover {{
                background-color: #3d3d3d;
            }}
        """)
        widget.setObjectName(f"provider_item_{provider_name}")

        hlayout = QHBoxLayout(widget)
        hlayout.setContentsMargins(12, 4, 8, 4)
        hlayout.setSpacing(8)

        # 服务商图标
        icon_widget = ProviderIconWidget(provider_name, 24)
        hlayout.addWidget(icon_widget)

        # 服务商名称 + 模型名称
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)

        name_label = QLabel(provider_name)
        name_label.setStyleSheet(f"color: #ffffff; {get_font_family_css()} font-size: 13px; font-weight: bold; background: transparent;")
        info_layout.addWidget(name_label)

        model_name = config.get("模型名称", "")
        model_label = QLabel(f"模型: {model_name}" if model_name else "未设置模型")
        model_label.setStyleSheet(f"color: #888888; {get_font_family_css()} font-size: 11px; background: transparent;")
        info_layout.addWidget(model_label)

        hlayout.addLayout(info_layout, 1)

        if is_current:
            current_tag = QLabel("当前")
            current_tag.setStyleSheet(f"""
                QLabel {{
                    color: #0078d4;
                    {get_font_family_css()} font-size: 11px;
                    font-weight: bold;
                    background: rgba(0, 120, 212, 0.15);
                    border: 1px solid rgba(0, 120, 212, 0.3);
                    border-radius: 4px;
                    padding: 2px 6px;
                }}
            """)
            hlayout.addWidget(current_tag)

        return widget
