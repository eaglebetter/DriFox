# -*- coding: utf-8 -*-
"""
大模型设置卡片 - 垂直列表布局，高度不够滚动
"""

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QFontComboBox,
)
from loguru import logger

from app.utils.design_tokens import CardStyles
from app.widgets.provider_setting_card import ProviderListSettingCard


class NoWheelFontComboBox(QFontComboBox):
    """禁用滚轮切换的字体下拉框"""

    def wheelEvent(self, event):
        # 忽略滚轮事件，防止悬浮时滚轮切换字体
        event.ignore()

from qfluentwidgets import (
    StrongBodyLabel,
    SwitchSettingCard,
    OptionsSettingCard,
    FluentIcon, SimpleCardWidget, SettingCard, PrimaryPushButton,
)

from app.utils.config import Settings
from app.utils.utils import get_icon, get_unified_font


class ManualUpdateCard(SettingCard):
    def __init__(self, title, content, parent_widget, parent=None):
        super().__init__(FluentIcon.SYNC, title, content, parent)
        self.parent_widget = parent_widget

        self.updateBtn = PrimaryPushButton("检查更新", self)
        self.updateBtn.setFixedWidth(100)
        self.updateBtn.clicked.connect(self._on_check_update)
        self.hBoxLayout.addWidget(self.updateBtn, 0, Qt.AlignRight)

    def _on_check_update(self):
        from app.update_checker import UpdateChecker

        self.updateBtn.setText("检查中...")
        self.updateBtn.setEnabled(False)

        checker = UpdateChecker(self.parent_widget)
        checker.finished.connect(self._on_check_finished)
        checker.finished.connect(self._on_check_finished_final)
        checker.error.connect(self._on_error)
        checker.check_update()

    def _on_check_finished(self, latest_release):
        pass  # UpdateChecker 内部已处理

    def _on_check_finished_final(self, latest_release):
        self.updateBtn.setText("检查更新")
        self.updateBtn.setEnabled(True)

    def _on_error(self, msg):
        self.updateBtn.setText("检查更新")
        self.updateBtn.setEnabled(True)
        logger.error(msg)

    def _on_error(self, msg):
        try:
            self.updateBtn.setText("检查更新")
            self.updateBtn.setEnabled(True)
            from qfluentwidgets import InfoBar, InfoBarPosition, InfoBarIcon
            InfoBar.error(
                icon=InfoBarIcon.WARNING,
                title="检查更新失败",
                content=msg,
                position=InfoBarPosition.BOTTOM,
                duration=3000,
                parent=self.parent_widget,
            ).show()
        except Exception as e:
            print(f"_on_error error: {e}")


class LLMSettingsCard(SimpleCardWidget):
    """大模型设置卡片 - 垂直列表布局"""

    closed = pyqtSignal()
    configChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cfg = Settings.get_instance()
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._perform_save)

        self._setup_ui()

    def _setup_ui(self):
        self.setSizePolicy(1, 0)  # 水平方向可扩展
        self.setFixedHeight(350)  # 固定高度，超出滚动
        self.setStyleSheet(CardStyles.card())

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(4)

        # 头部
        header = QHBoxLayout()
        header.setSpacing(8)

        icon_label = QLabel("⚙️", self)
        icon_label.setFont(get_unified_font(12))

        title_label = StrongBodyLabel("系统设置", self)
        title_label.setFont(get_unified_font(11, True))
        title_label.setStyleSheet(CardStyles.title_label())

        header.addWidget(icon_label)
        header.addWidget(title_label)
        header.addStretch()

        # 关闭按钮
        self.close_btn = QLabel("✕", self)
        self.close_btn.setFont(get_unified_font(11))
        self.close_btn.setStyleSheet(CardStyles.close_button())
        self.close_btn.mousePressEvent = lambda e: self._on_close()
        header.addWidget(self.close_btn)

        main_layout.addLayout(header)

        # 内容区域 - 使用 ScrollArea
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
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
        """)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 4, 0, 4)
        content_layout.setSpacing(6)

        self.llmProviderCard = ProviderListSettingCard(
            icon=get_icon("大模型"),
            configItem=self.cfg.llm_saved_providers,
            defaultProviderItem=self.cfg.llm_selected_model,
            title="已保存的服务商",
            content="管理已配置的大模型服务商",
            parent=self,
            home=self,
        )
        content_layout.addWidget(self.llmProviderCard)

        # 启用技能
        from app.widgets.list_setting_card import SkillListSettingCard

        self.llmSkillsCard = SkillListSettingCard(
            icon=get_icon("智能体"),
            configItem=self.cfg.llm_enabled_skills,
            title="启用技能",
            content="选择要注入的技能",
            parent=self,
            home=self,
        )
        content_layout.addWidget(self.llmSkillsCard)

        # Hooks 管理
        from app.widgets.hook_setting_card import HookListSettingCard
        
        hook_manager = getattr(self.parent(), 'backend', None)
        if hook_manager:
            hook_manager = hook_manager.hook_manager

        self.hookListCard = HookListSettingCard(
            icon=get_icon("hooks"),
            title="Hooks 管理",
            content="管理全局 Hooks",
            parent=self,
            home=self,
            hook_manager=hook_manager,
        )
        content_layout.addWidget(self.hookListCard)

        # 全局字体设置
        self._setup_font_card()
        content_layout.addWidget(self.llmFontCard)

        # 智能体完成通知
        self.llmNotifyCard = SwitchSettingCard(
            get_icon("提示"),
            "智能体完成通知",
            "窗口不在前台时发送通知",
            configItem=self.cfg.llm_notify_enabled,
            parent=self,
        )
        content_layout.addWidget(self.llmNotifyCard)

        # 通知提示音
        self.llmSoundCard = OptionsSettingCard(
            self.cfg.llm_notify_sound,
            get_icon("提示"),
            "通知提示音",
            "选择提示音",
            texts=["默认", "短提示音", "无"],
            parent=self,
        )
        content_layout.addWidget(self.llmSoundCard)

        # 分隔标签
        sep_label = StrongBodyLabel("版本更新", self)
        sep_label.setFont(get_unified_font(10, True))
        sep_label.setStyleSheet("color: #888; padding: 4px 0;")
        content_layout.addWidget(sep_label)

        # 自动检查更新
        self.autoUpdateCard = SwitchSettingCard(
            get_icon("提示"),
            "自动检查更新",
            "启动时自动检测新版本",
            configItem=self.cfg.auto_check_update,
            parent=self,
        )
        content_layout.addWidget(self.autoUpdateCard)

        self.manualUpdateCard = ManualUpdateCard(
            "手动检查更新",
            "点击按钮检查是否有新版本",
            self.parent(),
            self.parent(),
        )
        content_layout.addWidget(self.manualUpdateCard)

        content_layout.addStretch(1)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll, 1)

        # 连接信号
        self.llmProviderCard.providerChanged.connect(self._on_config_changed)
        self.llmSkillsCard.skillsChanged.connect(self._on_config_changed)
        self.cfg.llm_notify_enabled.valueChanged.connect(self._on_config_changed)
        self.llmSoundCard.optionChanged.connect(self._on_config_changed)
        self.cfg.llm_font_family.valueChanged.connect(self._on_config_changed)
        self.cfg.llm_api_enabled.valueChanged.connect(self._on_llm_api_enabled_changed)
        self.cfg.llm_api_port.valueChanged.connect(self._on_llm_api_port_changed)

    def _setup_font_card(self):
        """创建字体设置卡片"""
        from qfluentwidgets import SettingCard

        class FontSettingCard(SettingCard):
            def __init__(self, title, content, cfg, parent=None):
                super().__init__(FluentIcon.FONT, title, content, parent)
                self.cfg = cfg
                self._parent = parent

                self.fontCombo = NoWheelFontComboBox()
                # 设置下拉框向左延伸，框右边对齐
                self.fontCombo.setSizeAdjustPolicy(QFontComboBox.SizeAdjustPolicy.AdjustToContents)
                self._apply_font_combo_style()
                # 设置当前字体
                current_font = cfg.llm_font_family.value
                self.fontCombo.setCurrentFont(QFont(current_font))
                self.fontCombo.currentFontChanged.connect(self._on_font_changed)

                self.hBoxLayout.addWidget(self.fontCombo)
                self.hBoxLayout.addSpacing(16)

            def _apply_font_combo_style(self):
                """应用字体下拉框样式"""
                view = self.fontCombo.view()

                self.fontCombo.setStyleSheet("""
                    QFontComboBox {
                        color: #e8e8e8;
                        background-color: #2a2a2e;
                        border: 1px solid #4a4a4e;
                        border-radius: 5px;
                        padding: 5px 12px 5px 10px;
                        min-height: 28px;
                    }
                    QFontComboBox:hover {
                        border: 1px solid #0078d4;
                        background-color: #333338;
                    }
                    QFontComboBox:focus {
                        border: 1px solid #0078d4;
                    }
                    QFontComboBox::drop-down {
                        border: none;
                        width: 20px;
                        subcontrol-origin: padding;
                        subcontrol-position: right center;
                    }
                    QFontComboBox::down-arrow {
                        image: none;
                        border-left: 5px solid transparent;
                        border-right: 5px solid transparent;
                        border-top: 5px solid #888888;
                        width: 0px;
                        height: 0px;
                        margin-right: 4px;
                    }
                    QFontComboBox::down-arrow:hover {
                        border-top-color: #0078d4;
                    }
                """)
                
                # 设置下拉视图样式（包含滚动条）
                view.setStyleSheet("""
                    QAbstractItemView {
                        color: #e8e8e8;
                        background-color: #2a2a2e;
                        border: 1px solid #4a4a4e;
                        border-radius: 6px;
                        padding: 4px;
                        outline: none;
                        show-decoration-selected: 1;
                    }
                    QAbstractItemView::item {
                        padding: 6px 14px 6px 12px;
                        min-height: 36px;
                        border-radius: 3px;
                    }
                    QAbstractItemView::item:hover {
                        background-color: #3a3a3e;
                    }
                    QAbstractItemView::item:selected {
                        background-color: #0078d4;
                        color: white;
                    }
                    QScrollBar:vertical {
                        background: #2a2a2e;
                        border: none;
                        width: 14px;
                        margin: 4px 2px 4px 2px;
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        height: 0px;
                    }
                    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                        background: none;
                    }
                """)

                # 通过 palette 强制设置背景色
                palette = view.palette()
                palette.setColor(view.backgroundRole(), QColor(42, 42, 46))
                view.setPalette(palette)
                view.setAutoFillBackground(True)

                # 下拉框右边与点击框右边对齐，向左延伸
                self.fontCombo.view().setTextElideMode(Qt.ElideRight)

            def _on_font_changed(self, font):
                self.cfg.set(self.cfg.llm_font_family, font.family(), save=True)
                self.cfg.save()
                # 通知父级配置变化
                if self._parent and hasattr(self._parent, "_on_config_changed"):
                    self._parent._on_config_changed()

        self.llmFontCard = FontSettingCard(
            "全局字体",
            "设置界面显示字体",
            self.cfg,
            self,
        )

    def _setup_port_card(self):
        """创建端口设置卡片"""
        from qfluentwidgets import SettingCard, SpinBox
        from qfluentwidgets import FluentIcon

        class PortSettingCard(SettingCard):
            def __init__(self, title, content, cfg, parent=None):
                super().__init__(FluentIcon.INFO, title, content, parent)
                self.cfg = cfg

                self.spinBox = SpinBox()
                self.spinBox.setFixedWidth(100)
                self.spinBox.setRange(1024, 65535)
                self.spinBox.setValue(cfg.llm_api_port.value)
                self.spinBox.valueChanged.connect(self._on_value_changed)

                self.hBoxLayout.addWidget(self.spinBox)
                self.hBoxLayout.addSpacing(16)

            def _on_value_changed(self, value):
                self.cfg.set(self.cfg.llm_api_port, value, save=True)
                # 更新 API 服务开关卡片的描述
                parent = self.parent()
                while parent and not hasattr(parent, "llmApiEnabledCard"):
                    parent = parent.parent()
                if parent and hasattr(parent, "llmApiEnabledCard"):
                    parent.llmApiEnabledCard.setContent(
                        f"http://localhost:{value}/docs"
                    )

        self.llmApiPortCard = PortSettingCard(
            "API 端口",
            "设置 API 服务端口（1024-65535）",
            self.cfg,
            self,
        )

    def _on_close(self):
        self.setVisible(False)
        self.closed.emit()

    def _on_config_changed(self):
        self.configChanged.emit()
        self._save_timer.start()

    def _perform_save(self):
        try:
            self.cfg.save_config()
        except Exception as e:
            print(f"保存配置失败: {e}")

    def _on_llm_api_enabled_changed(self, enabled):
        """API 服务开关变化时启动/停止服务"""
        from app.api import (
            stop_llm_api_service,
            is_service_running,
            get_llm_api_service,
        )

        if enabled:
            if not is_service_running():
                service = get_llm_api_service()
                service.port = self.cfg.llm_api_port.value
                service.start(background=True)
        else:
            if is_service_running():
                stop_llm_api_service()
        self._on_config_changed()

    def _on_llm_api_port_changed(self, port):
        """端口变化时，如果服务正在运行则重启服务"""
        from app.api import (
            stop_llm_api_service,
            is_service_running,
            get_llm_api_service,
        )

        if self.cfg.llm_api_enabled.value and is_service_running():
            # 停止旧服务
            stop_llm_api_service()
            # 用新端口启动服务
            service = get_llm_api_service()
            service.port = port
            service.start(background=True)
        # 更新 API 服务开关卡片的描述
        if hasattr(self, "llmApiEnabledCard"):
            self.llmApiEnabledCard.setContent(f"http://localhost:{port}/docs")

    def show(self):
        # 刷新服务商列表
        if hasattr(self, 'llmProviderCard'):
            self.llmProviderCard._refresh_items()
        self.setVisible(True)
        self.raise_()

    def hide(self):
        self.setVisible(False)

    def set_opacity(self, opacity: float):
        """设置透明度，用于响应全局透明度变化"""
        alpha = int(250 * opacity)
        self.setStyleSheet(CardStyles.card(alpha))
