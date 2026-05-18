# -*- coding: utf-8 -*-
"""
MCP Server 配置卡片

列表卡片 + 编辑卡片，参考 ProviderListSettingCard / ProviderEditCard 模式：
- MCPListSettingCard: 展示服务器列表，含添加/编辑/删除/启停
- MCPEditCard: 编辑/添加服务器的表单卡片（承载在 BaseSettingsCard 中）
"""

import json

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QPlainTextEdit,
)
from loguru import logger
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ExpandSettingCard,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    PushButton,
    StrongBodyLabel,
    SwitchButton,
    ToolButton,
)

from app.utils.config import Settings
from app.utils.design_tokens import Colors
from app.utils.utils import get_icon, get_font_family_css


# ═══════════════════════════════════════════════════════════
# MCPEditCard — 添加/编辑 MCP Server 的表单卡片
# ═══════════════════════════════════════════════════════════

class MCPEditCard(QWidget):
    """MCP Server 编辑卡片 — 承载在 BaseSettingsCard 中"""

    saved = pyqtSignal(dict)   # 保存成功，发出 server_data dict
    closed = pyqtSignal()      # 取消/关闭

    def __init__(self, server_data: dict = None, parent=None):
        super().__init__(parent)
        self._server_data = server_data or {}
        self._is_edit = bool(server_data)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"""
            QWidget {{
                background: transparent;
            }}
            QLineEdit {{
                background-color: rgba(61, 61, 61, 180);
                color: #ffffff;
                border: 1px solid rgba(85, 85, 85, 150);
                border-radius: 4px;
                padding: 4px 8px;
                {get_font_family_css()}
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: rgba(0, 120, 212, 200);
            }}
            QComboBox {{
                background-color: rgba(61, 61, 61, 180);
                color: #ffffff;
                border: 1px solid rgba(85, 85, 85, 150);
                border-radius: 4px;
                padding: 4px 8px;
                {get_font_family_css()}
                font-size: 12px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #2a2a2e;
                color: #ffffff;
                selection-background-color: #0078d4;
            }}
            QPlainTextEdit {{
                background-color: rgba(61, 61, 61, 180);
                color: #ffffff;
                border: 1px solid rgba(85, 85, 85, 150);
                border-radius: 4px;
                padding: 4px 8px;
                {get_font_family_css()}
                font-size: 12px;
            }}
            QPlainTextEdit:focus {{
                border-color: rgba(0, 120, 212, 200);
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 2, 4, 2)
        main_layout.setSpacing(6)

        # ── 名称 ──
        name_row = QHBoxLayout()
        name_label = BodyLabel("名称:")
        name_label.setFixedWidth(70)
        name_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        name_row.addWidget(name_label)
        self.nameEdit = QLineEdit()
        self.nameEdit.setPlaceholderText("例如: github, filesystem, my-api")
        if self._is_edit:
            self.nameEdit.setText(self._server_data.get("name", ""))
            self.nameEdit.setReadOnly(True)
        name_row.addWidget(self.nameEdit, 1)
        main_layout.addLayout(name_row)

        # ── 类型 ──
        type_row = QHBoxLayout()
        type_label = BodyLabel("类型:")
        type_label.setFixedWidth(70)
        type_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        type_row.addWidget(type_label)
        self.typeCombo = QComboBox()
        self.typeCombo.addItems(["stdio", "sse", "http"])
        self.typeCombo.setCurrentText(self._server_data.get("type", "stdio"))
        self.typeCombo.currentTextChanged.connect(self._on_type_changed)
        type_row.addWidget(self.typeCombo, 1)
        main_layout.addLayout(type_row)

        # ── Command（stdio） ──
        cmd_row = QHBoxLayout()
        cmd_label = BodyLabel("Command:")
        cmd_label.setFixedWidth(70)
        cmd_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        cmd_row.addWidget(cmd_label)
        self.commandEdit = QLineEdit()
        self.commandEdit.setPlaceholderText("例如: npx")
        self.commandEdit.setText(self._server_data.get("command", ""))
        cmd_row.addWidget(self.commandEdit, 1)
        main_layout.addLayout(cmd_row)

        # ── Args（stdio） ──
        args_row = QHBoxLayout()
        args_label = BodyLabel("Args:")
        args_label.setFixedWidth(70)
        args_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        args_row.addWidget(args_label)
        self.argsEdit = QLineEdit()
        self.argsEdit.setPlaceholderText("例如: -y @modelcontextprotocol/server-filesystem /path")
        saved_args = self._server_data.get("args", [])
        if isinstance(saved_args, list):
            self.argsEdit.setText(" ".join(saved_args))
        args_row.addWidget(self.argsEdit, 1)
        main_layout.addLayout(args_row)

        # ── URL（sse/http） ──
        url_row = QHBoxLayout()
        url_label = BodyLabel("URL:")
        url_label.setFixedWidth(70)
        url_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        url_row.addWidget(url_label)
        self.urlEdit = QLineEdit()
        self.urlEdit.setPlaceholderText("例如: https://api.example.com/mcp")
        self.urlEdit.setText(self._server_data.get("url", ""))
        url_row.addWidget(self.urlEdit, 1)
        main_layout.addLayout(url_row)

        # ── Headers（sse/http） ──
        headers_row = QHBoxLayout()
        headers_label = BodyLabel("Headers:")
        headers_label.setFixedWidth(70)
        headers_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        headers_row.addWidget(headers_label)
        self.headersEdit = QPlainTextEdit()
        self.headersEdit.setMaximumHeight(60)
        self.headersEdit.setPlaceholderText('可选 JSON，例如: {"Authorization": "Bearer xxx"}')
        saved_headers = self._server_data.get("headers")
        if saved_headers and isinstance(saved_headers, dict):
            self.headersEdit.setPlainText(json.dumps(saved_headers, indent=2, ensure_ascii=False))
        headers_row.addWidget(self.headersEdit, 1)
        main_layout.addLayout(headers_row)

        # ── 环境变量（stdio） ──
        env_row = QHBoxLayout()
        env_label = BodyLabel("环境变量:")
        env_label.setFixedWidth(70)
        env_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        env_row.addWidget(env_label)
        self.envEdit = QPlainTextEdit()
        self.envEdit.setMaximumHeight(60)
        self.envEdit.setPlaceholderText('可选 JSON，例如: {"API_KEY": "xxx"}')
        saved_env = self._server_data.get("env")
        if saved_env and isinstance(saved_env, dict):
            self.envEdit.setPlainText(json.dumps(saved_env, indent=2, ensure_ascii=False))
        env_row.addWidget(self.envEdit, 1)
        main_layout.addLayout(env_row)

        # 初始显隐
        self._on_type_changed(self.typeCombo.currentText())

    def _on_type_changed(self, server_type: str):
        is_stdio = server_type == "stdio"
        # 找到对应的 label 和 input 行，控制可见性
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if not item or not item.layout():
                continue
            row = item.layout()
            # 检查行中的控件
            for j in range(row.count()):
                w = row.itemAt(j).widget()
                if w is self.commandEdit:
                    w.setVisible(is_stdio)
                    # 对应的 label
                    label_w = row.itemAt(0).widget()
                    if label_w:
                        label_w.setVisible(is_stdio)
                elif w is self.argsEdit:
                    w.setVisible(is_stdio)
                    label_w = row.itemAt(0).widget()
                    if label_w:
                        label_w.setVisible(is_stdio)
                elif w is self.urlEdit:
                    w.setVisible(not is_stdio)
                    label_w = row.itemAt(0).widget()
                    if label_w:
                        label_w.setVisible(not is_stdio)
                elif w is self.headersEdit:
                    w.setVisible(not is_stdio)
                    label_w = row.itemAt(0).widget()
                    if label_w:
                        label_w.setVisible(not is_stdio)
                elif w is self.envEdit:
                    w.setVisible(is_stdio)
                    label_w = row.itemAt(0).widget()
                    if label_w:
                        label_w.setVisible(is_stdio)

    def _on_save(self):
        """保存"""
        name = self.nameEdit.text().strip()
        if not name:
            InfoBar.warning("提示", "请输入服务器名称", parent=self.window(),
                            duration=2000, position=InfoBarPosition.BOTTOM)
            return

        server_type = self.typeCombo.currentText()
        server_data = {
            "name": name,
            "type": server_type,
            "enabled": self._server_data.get("enabled", True),
        }

        if server_type == "stdio":
            cmd = self.commandEdit.text().strip()
            if not cmd:
                InfoBar.warning("提示", "请输入 Command", parent=self.window(),
                                duration=2000, position=InfoBarPosition.BOTTOM)
                return
            server_data["command"] = cmd
            args_text = self.argsEdit.text().strip()
            server_data["args"] = args_text.split() if args_text else []

            env_text = self.envEdit.toPlainText().strip()
            if env_text:
                try:
                    server_data["env"] = json.loads(env_text)
                except json.JSONDecodeError as e:
                    InfoBar.warning("提示", f"环境变量 JSON 格式错误: {e}", parent=self.window(),
                                    duration=3000, position=InfoBarPosition.BOTTOM)
                    return
        else:
            url = self.urlEdit.text().strip()
            if not url:
                InfoBar.warning("提示", "请输入 URL", parent=self.window(),
                                duration=2000, position=InfoBarPosition.BOTTOM)
                return
            server_data["url"] = url
            headers_text = self.headersEdit.toPlainText().strip()
            if headers_text:
                try:
                    server_data["headers"] = json.loads(headers_text)
                except json.JSONDecodeError as e:
                    InfoBar.warning("提示", f"Headers JSON 格式错误: {e}", parent=self.window(),
                                    duration=3000, position=InfoBarPosition.BOTTOM)
                    return

        self.saved.emit(server_data)


# ═══════════════════════════════════════════════════════════
# MCPServerRow — 列表中的单行
# ═══════════════════════════════════════════════════════════

class MCPServerRow(CardWidget):
    """单行 MCP Server 显示"""

    removeRequested = pyqtSignal(str)
    editRequested = pyqtSignal(str)
    enabledChanged = pyqtSignal(str, bool)

    def __init__(self, server_data: dict, parent=None):
        super().__init__(parent)
        self._name = server_data.get("name", "")
        self._setup_ui(server_data)

    def _setup_ui(self, data: dict):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        server_type = data.get("type", "stdio")
        type_colors = {"stdio": "#2196F3", "sse": "#FF9800", "http": "#4CAF50"}
        color = type_colors.get(server_type, "#999")

        # 类型标签
        type_label = QLabel(server_type.upper())
        type_label.setStyleSheet(
            f"background-color: {color}22; color: {color}; "
            f"font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: bold;"
        )
        type_label.setFixedWidth(55)
        type_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(type_label)

        # 名称
        name_label = StrongBodyLabel(data.get("name", ""))
        name_label.setFixedWidth(100)
        layout.addWidget(name_label)

        # 描述
        if server_type == "stdio":
            desc = f"{data.get('command', '')} {' '.join(data.get('args', []))}".strip()
        else:
            desc = data.get("url", "")
        desc_label = QLabel(desc[:50] + "..." if len(desc) > 50 else desc)
        desc_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(desc_label, 1)

        # 启用开关
        self.switch = SwitchButton()
        self.switch.setChecked(data.get("enabled", True))
        self.switch.setOnText("")
        self.switch.setOffText("")
        self.switch.setFixedWidth(50)
        self.switch.checkedChanged.connect(lambda v: self.enabledChanged.emit(self._name, v))
        layout.addWidget(self.switch)

        # 编辑按钮
        edit_btn = ToolButton(FluentIcon.EDIT)
        edit_btn.setFixedSize(28, 28)
        edit_btn.setStyleSheet("background-color: transparent; border-radius: 4px;")
        edit_btn.clicked.connect(lambda: self.editRequested.emit(self._name))
        layout.addWidget(edit_btn)

        # 删除按钮
        del_btn = ToolButton(FluentIcon.CLOSE)
        del_btn.setFixedSize(28, 28)
        del_btn.setStyleSheet("background-color: transparent; border-radius: 4px;")
        del_btn.clicked.connect(lambda: self.removeRequested.emit(self._name))
        layout.addWidget(del_btn)


# ═══════════════════════════════════════════════════════════
# MCPListSettingCard — MCP Server 列表设置卡片
# ═══════════════════════════════════════════════════════════

class MCPListSettingCard(ExpandSettingCard):
    """MCP Server 管理设置卡片"""

    serversChanged = pyqtSignal()
    showAddCard = pyqtSignal()               # 显示添加卡片
    showEditCard = pyqtSignal(str, dict)     # 显示编辑卡片

    def __init__(self, icon, title: str, content: str = None, parent=None):
        self.cfg = Settings.get_instance()
        super().__init__(icon, title, content, parent)
        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        self.viewLayout.setSpacing(2)
        self.viewLayout.setAlignment(Qt.AlignTop)
        self.viewLayout.setContentsMargins(8, 0, 8, 0)
        self.view.setStyleSheet("background-color: transparent;")

        # 全局开关
        self.globalSwitch = SwitchButton()
        self.globalSwitch.setChecked(self.cfg.mcp_enabled.value)
        self.globalSwitch.setOnText("")
        self.globalSwitch.setOffText("")
        self.globalSwitch.checkedChanged.connect(self._on_global_switch)
        self.addWidget(self.globalSwitch)

        # 添加按钮
        self.addButton = PushButton("添加服务器", self, FluentIcon.ADD)
        self.addButton.clicked.connect(self.showAddCard.emit)
        self.addWidget(self.addButton)

        # 调整按钮位置到标题栏（与 ProviderListSettingCard 一致）
        self._update_button_position()

    def _update_button_position(self):
        """将添加按钮移到关闭按钮旁边"""
        card = self.card
        if hasattr(card, 'hBoxLayout'):
            self.card.hBoxLayout.removeWidget(self.addButton)
            for i in range(card.hBoxLayout.count()):
                item = card.hBoxLayout.itemAt(i)
                if item.widget() == card.expandButton:
                    card.hBoxLayout.removeItem(card.hBoxLayout.itemAt(i - 1))
                    card.hBoxLayout.insertWidget(i - 1, self.addButton, 0, Qt.AlignRight)
                    card.hBoxLayout.insertSpacing(i, 4)
                    break

    def _on_global_switch(self, enabled: bool):
        self.cfg.set(self.cfg.mcp_enabled, enabled, save=True)
        self.serversChanged.emit()

    def _refresh(self):
        """刷新服务器列表"""
        while self.viewLayout.count():
            item = self.viewLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        servers = self.cfg.mcp_servers.value
        if not servers:
            empty_label = QLabel("暂无 MCP 服务器，点击「添加服务器」创建", self.view)
            empty_label.setStyleSheet("color: #888; padding: 16px; font-size: 12px;")
            empty_label.setAlignment(Qt.AlignCenter)
            self.viewLayout.addWidget(empty_label)
            return

        for server_data in servers:
            row = MCPServerRow(server_data, self.view)
            row.removeRequested.connect(self._on_remove_server)
            row.editRequested.connect(self._show_edit_dialog)
            row.enabledChanged.connect(self._on_enabled_changed)
            self.viewLayout.addWidget(row)

        # 更新数量统计
        count = len(servers)
        enabled_count = sum(1 for s in servers if s.get("enabled", True))
        self.setCount(f"{enabled_count}/{count}")

    def setCount(self, text: str):
        """更新卡片数量统计"""
        # 在标题区域显示数量（类似 ProviderListSettingCard）
        card = self.card
        if hasattr(card, 'contentLabel'):
            card.contentLabel.setText(text)

    def _save_servers(self, servers: list):
        """保存服务器配置"""
        self.cfg.set(self.cfg.mcp_servers, servers, save=True)
        self._refresh()
        self.serversChanged.emit()

    def _on_remove_server(self, name: str):
        from qfluentwidgets import Dialog
        title = "确定要删除这个 MCP 服务器吗?"
        content = f'删除 "{name}" 后将不再出现在列表中。'
        w = Dialog(title, content, self.window())
        w.yesSignal.connect(lambda: self._do_remove(name))
        w.exec_()

    def _do_remove(self, name: str):
        servers = list(self.cfg.mcp_servers.value or [])
        servers = [s for s in servers if s.get("name") != name]
        self._save_servers(servers)

    def _show_edit_dialog(self, name: str):
        servers = list(self.cfg.mcp_servers.value or [])
        server_data = next((s for s in servers if s.get("name") == name), None)
        if server_data:
            self.showEditCard.emit(name, server_data)

    def _on_enabled_changed(self, name: str, enabled: bool):
        servers = list(self.cfg.mcp_servers.value or [])
        for s in servers:
            if s.get("name") == name:
                s["enabled"] = enabled
                break
        self.cfg.set(self.cfg.mcp_servers, servers, save=True)
        self.serversChanged.emit()

    # ── 供外部调用的添加/更新方法 ──

    def add_server(self, server_data: dict):
        """添加服务器"""
        servers = list(self.cfg.mcp_servers.value or [])
        name = server_data.get("name", "")
        if any(s.get("name") == name for s in servers):
            InfoBar.warning(
                title="名称重复",
                content=f"MCP Server '{name}' 已存在",
                position=InfoBarPosition.BOTTOM,
                duration=3000,
                parent=self.window(),
            )
            return False
        servers.append(server_data)
        self._save_servers(servers)
        return True

    def update_server(self, name: str, server_data: dict):
        """更新服务器"""
        servers = list(self.cfg.mcp_servers.value or [])
        for i, s in enumerate(servers):
            if s.get("name") == name:
                servers[i] = server_data
                break
        self._save_servers(servers)
