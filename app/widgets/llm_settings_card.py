# -*- coding: utf-8 -*-
"""
大模型设置卡片 - 垂直列表布局，高度不够滚动
现已迁移到 SystemCardFrame 基类，获得统一头部布局和固定边框
"""

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QVBoxLayout,
)
from loguru import logger

from app.widgets.system_card_frame import SystemCardFrame
from app.widgets.provider_setting_card import ProviderListSettingCard


class NoWheelFontComboBox(QFontComboBox):
    """禁用滚轮切换的字体下拉框"""

    def wheelEvent(self, event):
        event.ignore()

from qfluentwidgets import (
    StrongBodyLabel,
    SwitchSettingCard,
    OptionsSettingCard,
    FluentIcon, SettingCard, PrimaryPushButton,
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
        pass

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
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.error(
                title="检查更新失败",
                content=msg,
                position=InfoBarPosition.BOTTOM,
                duration=3000,
                parent=self.parent_widget,
            ).show()
        except Exception as e:
            print(f"_on_error error: {e}")


class LLMSettingsCard(SystemCardFrame):
    """大模型设置卡片 - 固定边框 + 垂直列表布局"""

    closed = pyqtSignal()
    configChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_icon("⚙️")
        self.set_title_text("系统设置")
        self.setFixedHeight(350)

        self.cfg = Settings.get_instance()
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._perform_save)

        self._setup_content()

    def _setup_content(self):
        content_layout = self.content_layout
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
                self.fontCombo.setSizeAdjustPolicy(QFontComboBox.SizeAdjustPolicy.AdjustToContents)
                self._apply_font_combo_style()
                current_font = cfg.llm_font_family.value
                self.fontCombo.setCurrentFont(QFont(current_font))
                self.fontCombo.currentFontChanged.connect(self._on_font_changed)

                self.hBoxLayout.addWidget(self.fontCombo)
                self.hBoxLayout.addSpacing(16)

            def _apply_font_combo_style(self):
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

                palette = view.palette()
                palette.setColor(view.backgroundRole(), QColor(42, 42, 46))
                view.setPalette(palette)
                view.setAutoFillBackground(True)
                self.fontCombo.view().setTextElideMode(Qt.ElideRight)

            def _on_font_changed(self, font):
                self.cfg.set(self.cfg.llm_font_family, font.family(), save=True)
                self.cfg.save()
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
        from app.api import (
            stop_llm_api_service,
            is_service_running,
            get_llm_api_service,
        )

        if self.cfg.llm_api_enabled.value and is_service_running():
            stop_llm_api_service()
            service = get_llm_api_service()
            service.port = port
            service.start(background=True)
        if hasattr(self, "llmApiEnabledCard"):
            self.llmApiEnabledCard.setContent(f"http://localhost:{port}/docs")

    def show(self):
        if hasattr(self, 'llmProviderCard'):
            self.llmProviderCard._refresh_items()
        super().show()

    def set_opacity(self, opacity: float):
        """设置透明度（保留接口，暂不实现动态透明度）"""
        pass