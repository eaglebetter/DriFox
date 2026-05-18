# -*- coding: utf-8 -*-
"""
MCP Server 配置卡片

列表卡片 + 编辑卡片，参考 ProviderListSettingCard / ProviderEditCard 模式：
- MCPListSettingCard: 展示服务器列表，含添加/编辑/删除/启停
- MCPEditCard: 编辑/添加服务器的表单卡片（承载在 BaseSettingsCard 中）
"""

import json

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
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
    PushButton,
    StrongBodyLabel,
    SwitchButton,
    ToolButton,
)

from app.utils.config import Settings
from app.utils.design_tokens import Colors, Sizes, ButtonStyles, SwitchStyles
from app.utils.utils import get_icon, get_font_family_css
from app.widgets.searchable_editable_combobox import SearchableEditableComboBox


# ═══════════════════════════════════════════════════════════
# 共用表单样式
# ═══════════════════════════════════════════════════════════

EDIT_CARD_STYLE = f"""
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
QLineEdit::placeholder {{
    color: rgba(255, 255, 255, 0.35);
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
"""


def _make_row(label_text: str, widget: QWidget, label_width: int = 70) -> QHBoxLayout:
    """构造一行：右对齐标签 + 输入控件"""
    row = QHBoxLayout()
    row.setSpacing(8)
    label = BodyLabel(label_text)
    label.setFixedWidth(label_width)
    label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    row.addWidget(label)
    row.addWidget(widget, 1)
    return row, label


class _ElidedLabel(QLabel):
    """自动根据可用宽度省略文本的 QLabel"""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._full_text = text

    def setText(self, text: str):
        self._full_text = text
        self._update_elided()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided()

    def _update_elided(self):
        fm = self.fontMetrics()
        elided = fm.elidedText(self._full_text, Qt.ElideRight, self.width())
        super().setText(elided)


# ═══════════════════════════════════════════════════════════
# MCPEditCard — 添加/编辑 MCP Server 的表单卡片
# ═══════════════════════════════════════════════════════════

class MCPEditCard(QWidget):
    """MCP Server 编辑卡片 — 承载在 BaseSettingsCard 中"""

    saved = pyqtSignal(dict)
    closed = pyqtSignal()

    def __init__(self, server_data: dict = None, parent=None):
        super().__init__(parent)
        self._server_data = server_data or {}
        self._is_edit = bool(server_data)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(EDIT_CARD_STYLE)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 2, 4, 2)
        main_layout.setSpacing(6)

        # ── 名称 ──
        self.nameEdit = QLineEdit()
        self.nameEdit.setPlaceholderText("例如: github, filesystem, my-api")
        if self._is_edit:
            self.nameEdit.setText(self._server_data.get("name", ""))
            self.nameEdit.setReadOnly(True)
        row, _ = _make_row("名称:", self.nameEdit)
        main_layout.addLayout(row)

        # ── 类型 ──
        self.typeCombo = SearchableEditableComboBox()
        self.typeCombo.addItems(["stdio", "sse", "http"])
        self.typeCombo.setCurrentText(self._server_data.get("type", "stdio"))
        self.typeCombo.currentTextChanged.connect(self._on_type_changed)
        row, _ = _make_row("类型:", self.typeCombo)
        main_layout.addLayout(row)

        # ── Command（stdio） ──
        self.commandEdit = QLineEdit()
        self.commandEdit.setPlaceholderText("例如: npx")
        self.commandEdit.setText(self._server_data.get("command", ""))
        self._cmd_row, self._cmd_label = _make_row("Command:", self.commandEdit)
        main_layout.addLayout(self._cmd_row)

        # ── Args（stdio） ──
        self.argsEdit = QLineEdit()
        self.argsEdit.setPlaceholderText("例如: -y @modelcontextprotocol/server-filesystem /path")
        saved_args = self._server_data.get("args", [])
        if isinstance(saved_args, list):
            self.argsEdit.setText(" ".join(saved_args))
        self._args_row, self._args_label = _make_row("Args:", self.argsEdit)
        main_layout.addLayout(self._args_row)

        # ── URL（sse/http） ──
        self.urlEdit = QLineEdit()
        self.urlEdit.setPlaceholderText("例如: https://api.example.com/mcp")
        self.urlEdit.setText(self._server_data.get("url", ""))
        self._url_row, self._url_label = _make_row("URL:", self.urlEdit)
        main_layout.addLayout(self._url_row)

        # ── Headers（sse/http） ──
        self.headersEdit = QPlainTextEdit()
        self.headersEdit.setMaximumHeight(60)
        self.headersEdit.setPlaceholderText('可选 JSON，例如: {"Authorization": "Bearer xxx"}')
        saved_headers = self._server_data.get("headers")
        if saved_headers and isinstance(saved_headers, dict):
            self.headersEdit.setPlainText(json.dumps(saved_headers, indent=2, ensure_ascii=False))
        self._headers_row, self._headers_label = _make_row("Headers:", self.headersEdit)
        main_layout.addLayout(self._headers_row)

        # ── 环境变量（stdio） ──
        self.envEdit = QPlainTextEdit()
        self.envEdit.setMaximumHeight(60)
        self.envEdit.setPlaceholderText('可选 JSON，例如: {"API_KEY": "xxx"}')
        saved_env = self._server_data.get("env")
        if saved_env and isinstance(saved_env, dict):
            self.envEdit.setPlainText(json.dumps(saved_env, indent=2, ensure_ascii=False))
        self._env_row, self._env_label = _make_row("环境变量:", self.envEdit)
        main_layout.addLayout(self._env_row)

        # 初始显隐
        self._on_type_changed(self.typeCombo.currentText())

    def _on_type_changed(self, server_type: str):
        is_stdio = server_type == "stdio"
        for w in (self._cmd_label, self.commandEdit):
            w.setVisible(is_stdio)
        for w in (self._args_label, self.argsEdit):
            w.setVisible(is_stdio)
        for w in (self._url_label, self.urlEdit):
            w.setVisible(not is_stdio)
        for w in (self._headers_label, self.headersEdit):
            w.setVisible(not is_stdio)
        for w in (self._env_label, self.envEdit):
            w.setVisible(is_stdio)

    def _on_save(self):
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

        type_label = QLabel(server_type.upper())
        type_label.setStyleSheet(
            f"background-color: {color}22; color: {color}; "
            f"font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: bold;"
        )
        type_label.setFixedWidth(55)
        type_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(type_label)

        name_label = StrongBodyLabel(data.get("name", ""))
        name_label.setFixedWidth(100)
        layout.addWidget(name_label)

        if server_type == "stdio":
            desc = f"{data.get('command', '')} {' '.join(data.get('args', []))}".strip()
        else:
            desc = data.get("url", "")
        desc_label = _ElidedLabel(desc)
        desc_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        desc_label.setMinimumWidth(40)
        layout.addWidget(desc_label, 1)

        self.switch = SwitchButton()
        SwitchStyles.configure(self.switch)
        self.switch.setChecked(data.get("enabled", True))
        self.switch.checkedChanged.connect(lambda v: self.enabledChanged.emit(self._name, v))
        layout.addWidget(self.switch)

        edit_btn = ToolButton(FluentIcon.EDIT)
        edit_btn.setFixedSize(Sizes.TOOL_BUTTON_SZ)
        edit_btn.setStyleSheet(ButtonStyles.tool_button())
        edit_btn.clicked.connect(lambda: self.editRequested.emit(self._name))
        layout.addWidget(edit_btn)

        del_btn = ToolButton(FluentIcon.CLOSE)
        del_btn.setFixedSize(Sizes.TOOL_BUTTON_SZ)
        del_btn.setStyleSheet(ButtonStyles.tool_button())
        del_btn.clicked.connect(lambda: self.removeRequested.emit(self._name))
        layout.addWidget(del_btn)


# ═══════════════════════════════════════════════════════════
# MCPListSettingCard — MCP Server 列表设置卡片
# ═══════════════════════════════════════════════════════════

class MCPListSettingCard(ExpandSettingCard):
    """MCP Server 管理设置卡片"""

    serversChanged = pyqtSignal()
    showAddCard = pyqtSignal()
    showEditCard = pyqtSignal(str, dict)

    # 内部信号（从后台线程桥接到主线程 UI 更新）
    _hotConnectResult = pyqtSignal(str, bool)

    def __init__(self, icon, title: str, content: str = None, parent=None):
        self.cfg = Settings.get_instance()
        super().__init__(icon, title, content, parent)
        self._setup_ui()
        self._refresh()

        # 连接信号（主线程处理 UI）
        self._hotConnectResult.connect(self._on_hot_connect_result)

    def _get_mcp_manager(self):
        from app.tools.mcp_tools import MCPClientManager
        return MCPClientManager.get_instance()

    def _setup_ui(self):
        self.viewLayout.setSpacing(2)
        self.viewLayout.setAlignment(Qt.AlignTop)
        self.viewLayout.setContentsMargins(8, 0, 8, 0)
        self.view.setStyleSheet("background-color: transparent;")

        self.addButton = PushButton("添加", self, FluentIcon.ADD)
        self.addButton.clicked.connect(self.showAddCard.emit)
        self.addWidget(self.addButton)

        self.globalSwitch = SwitchButton()
        self.globalSwitch.setChecked(self.cfg.mcp_enabled.value)
        SwitchStyles.configure(self.globalSwitch)
        self.globalSwitch.checkedChanged.connect(self._on_global_switch)
        self.addWidget(self.globalSwitch)

        self._update_button_position()

    def _update_button_position(self):
        """将 addButton + globalSwitch 移到卡片头部 expandButton 左侧"""
        card = self.card
        if not hasattr(card, 'hBoxLayout'):
            return
        # 先从原始位置移除
        card.hBoxLayout.removeWidget(self.addButton)
        card.hBoxLayout.removeWidget(self.globalSwitch)
        # 找到 expandButton 位置，在其前面插入
        for i in range(card.hBoxLayout.count()):
            item = card.hBoxLayout.itemAt(i)
            if item.widget() == card.expandButton:
                card.hBoxLayout.removeItem(card.hBoxLayout.itemAt(i - 1))
                card.hBoxLayout.insertWidget(i - 1, self.globalSwitch, 0, Qt.AlignRight)
                card.hBoxLayout.insertSpacing(i - 1, 4)
                card.hBoxLayout.insertWidget(i - 1, self.addButton, 0, Qt.AlignRight)
                card.hBoxLayout.insertSpacing(i - 1, 4)
                card.hBoxLayout.insertSpacing(i + 3, 4)
                break

    # ── 热更新操作（全部后台，不阻塞 UI）────────────

    def _hot_connect(self, name: str, config: dict):
        """后台连接单个服务器（不阻塞 UI）"""
        mgr = self._get_mcp_manager()
        if not self.cfg.mcp_enabled.value:
            return

        def on_done(n, success):
            self._hotConnectResult.emit(n, success)

        mgr.connect_server_background(name, config, on_done=on_done)

    def _on_hot_connect_result(self, name: str, success: bool):
        """连接结果回调（主线程，可安全操作 UI）"""
        self.serversChanged.emit()

    def _hot_disconnect(self, name: str):
        """后台断开单个服务器"""
        mgr = self._get_mcp_manager()
        mgr.disconnect_server_background(name)

    def _hot_disconnect_all(self):
        """后台断开所有服务器"""
        mgr = self._get_mcp_manager()
        mgr.disconnect_all_background()
        logger.info("[MCP] 后台断开所有服务器中...")

    # ── 全局开关 ──────────────────────────────────────

    def _on_global_switch(self, enabled: bool):
        self.cfg.set(self.cfg.mcp_enabled, enabled, save=True)
        if enabled:
            servers = self.cfg.mcp_servers.value or []
            for s in servers:
                if s.get("enabled", True):
                    self._hot_connect(s.get("name", ""), s)
        else:
            self._hot_disconnect_all()
        self.serversChanged.emit()

    # ── 列表刷新 ──────────────────────────────────────

    def _refresh(self):
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

        count = len(servers)
        enabled_count = sum(1 for s in servers if s.get("enabled", True))
        self.setCount(f"{enabled_count}/{count}")

    def setCount(self, text: str):
        card = self.card
        if hasattr(card, 'contentLabel'):
            card.contentLabel.setText(text)

    def _save_servers(self, servers: list):
        self.cfg.set(self.cfg.mcp_servers, servers, save=True)
        self._refresh()
        self.serversChanged.emit()

    def _on_remove_server(self, name: str):
        from qfluentwidgets import Dialog
        w = Dialog("确定要删除这个 MCP 服务器吗?", f'删除 "{name}" 后将不再出现在列表中。', self.window())
        w.yesSignal.connect(lambda: self._do_remove(name))
        w.exec_()

    def _do_remove(self, name: str):
        # 热断开
        self._hot_disconnect(name)
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

        # 热连接/断开
        if enabled and self.cfg.mcp_enabled.value:
            server_data = next((s for s in servers if s.get("name") == name), {})
            self._hot_connect(name, server_data)
        else:
            self._hot_disconnect(name)

        self.serversChanged.emit()

    # ── 供外部调用的添加/更新方法 ──────────────────────

    def add_server(self, server_data: dict):
        servers = list(self.cfg.mcp_servers.value or [])
        name = server_data.get("name", "")
        if any(s.get("name") == name for s in servers):
            InfoBar.warning(title="名称重复", content=f"MCP Server '{name}' 已存在",
                            position=InfoBarPosition.BOTTOM, duration=3000, parent=self.window())
            return False
        servers.append(server_data)
        self._save_servers(servers)
        # 热连接
        if server_data.get("enabled", True) and self.cfg.mcp_enabled.value:
            self._hot_connect(name, server_data)
        return True

    def update_server(self, name: str, server_data: dict):
        servers = list(self.cfg.mcp_servers.value or [])
        for i, s in enumerate(servers):
            if s.get("name") == name:
                servers[i] = server_data
                break
        self._save_servers(servers)
        # 先断开旧连接，再重新连接
        self._hot_disconnect(name)
        if server_data.get("enabled", True) and self.cfg.mcp_enabled.value:
            self._hot_connect(name, server_data)
