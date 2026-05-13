# -*- coding: utf-8 -*-
"""Hook 管理设置卡片"""

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QMenu
from qfluentwidgets import (
    ExpandSettingCard,
    PushButton,
    FluentIcon,
    SwitchButton,
    MessageBoxBase,
    LineEdit,
    ComboBox,
    PrimaryPushButton,
    BodyLabel,
    VerticalSeparator,
    CheckBox,
)
from app.utils.design_tokens import ItemStyles
from app.utils.utils import get_app_data_dir
import json
from pathlib import Path


class HookItem(QWidget):
    """单个 Hook 条目"""
    removed = pyqtSignal(int)  # 发送 hook 索引
    toggled = pyqtSignal(int, bool)  # 索引, 启用状态
    
    def __init__(self, event_name: str, hook_data: dict, index: int, parent=None):
        super().__init__(parent=parent)
        self.event_name = event_name
        self.hook_data = hook_data
        self.index = index
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet("background-color: transparent;")
        self.hBoxLayout = QHBoxLayout(self)
        
        # 命令显示（截断到 50 字符）
        command = self.hook_data.get("command", self.hook_data.get("url", ""))
        display_cmd = command[:50] + ("..." if len(command) > 50 else "")
        self.commandLabel = QLabel(display_cmd, self)
        self.commandLabel.setObjectName("titleLabel")
        self.commandLabel.setStyleSheet("font-size: 13px;")
        
        # Matcher 标签
        matcher = self.hook_data.get("matcher", "")
        if matcher:
            self.matcherLabel = QLabel(matcher, self)
            self.matcherLabel.setStyleSheet(
                "background-color: #E0E0E0; color: #666; font-size: 11px; padding: 2px 6px; border-radius: 4px;"
            )
        else:
            self.matcherLabel = QLabel("")
        
        # 启用开关
        self.switch = SwitchButton(self)
        self.switch.setChecked(self.hook_data.get("enabled", True))
        
        self.setFixedHeight(40)
        self.hBoxLayout.setContentsMargins(48, 0, 16, 0)
        self.hBoxLayout.addWidget(self.commandLabel, 1)
        self.hBoxLayout.addWidget(self.matcherLabel, 0)
        self.hBoxLayout.addSpacing(12)
        self.hBoxLayout.addWidget(self.switch, 0, Qt.AlignRight)
        self.hBoxLayout.setAlignment(Qt.AlignVCenter)
        
        self.switch.checkedChanged.connect(lambda checked: self.toggled.emit(self.index, checked))
        
        # 右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
    
    def _show_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("删除", lambda: self.removed.emit(self.index))
        menu.exec_(self.mapToGlobal(pos))


class AddHookDialog(MessageBoxBase):
    """添加 Hook 对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.titleLabel = BodyLabel("添加 Hook", self)
        self.resize(400, 360)
        
        # 事件选择
        self.eventLabel = QLabel("事件:", self)
        self.eventCombo = ComboBox(self)
        self.eventCombo.addItems([
            "SessionStart", "PreUserMessage", "PostUserMessage",
            "PreAssistantMessage", "PostAssistantMessage",
            "PreToolUse", "PostToolUse"
        ])
        
        # 类型选择
        self.typeLabel = QLabel("类型:", self)
        self.typeCombo = ComboBox(self)
        self.typeCombo.addItems(["command", "http", "python"])
        
        # 命令输入
        self.commandLabel = QLabel("命令/URL/函数:", self)
        self.commandEdit = LineEdit(self)
        
        # Matcher 输入
        self.matcherLabel = QLabel("Matcher (可选):", self)
        self.matcherEdit = LineEdit(self)
        self.matcherEdit.setPlaceholderText("如: tool:bash 或 .*帮助.*")
        
        # 启用复选框
        self.enabledCheck = CheckBox("启用", self)
        self.enabledCheck.setChecked(True)
        
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(4)
        self.viewLayout.addWidget(self.eventLabel)
        self.viewLayout.addWidget(self.eventCombo)
        self.viewLayout.addWidget(self.typeLabel)
        self.viewLayout.addWidget(self.typeCombo)
        self.viewLayout.addWidget(self.commandLabel)
        self.viewLayout.addWidget(self.commandEdit)
        self.viewLayout.addWidget(self.matcherLabel)
        self.viewLayout.addWidget(self.matcherEdit)
        self.viewLayout.addSpacing(8)
        self.viewLayout.addWidget(self.enabledCheck)
        
        # 设置弹窗按钮
        self.yesButton = PrimaryPushButton("添加", self)
        self.cancelButton = PushButton("取消", self)
        self.yesButton.clicked.connect(self._on_yes)
        self.cancelButton.clicked.connect(self.reject)
    
class AddHookDialog(MessageBoxBase):
    """保留的旧版弹窗对话框 - 暂时保留以兼容"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.titleLabel = BodyLabel("添加 Hook（弹窗模式）", self)
        self.resize(400, 360)
        self.eventLabel = QLabel("事件:", self)
        self.eventCombo = ComboBox(self)
        self.eventCombo.addItems([
            "SessionStart", "PreUserMessage", "PostUserMessage",
            "PreAssistantMessage", "PostAssistantMessage",
            "PreToolUse", "PostToolUse"
        ])
        self.typeLabel = QLabel("类型:", self)
        self.typeCombo = ComboBox(self)
        self.typeCombo.addItems(["command", "http", "python"])
        self.commandLabel = QLabel("命令:", self)
        self.commandEdit = LineEdit(self)
        self.matcherLabel = QLabel("Matcher (可选):", self)
        self.matcherEdit = LineEdit(self)
        self.matcherEdit.setPlaceholderText("如: tool:bash 或 .*帮助.*")
        self.enabledCheck = CheckBox("启用", self)
        self.enabledCheck.setChecked(True)
        
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(4)
        self.viewLayout.addWidget(self.eventLabel)
        self.viewLayout.addWidget(self.eventCombo)
        self.viewLayout.addWidget(self.typeLabel)
        self.viewLayout.addWidget(self.typeCombo)
        self.viewLayout.addWidget(self.commandLabel)
        self.viewLayout.addWidget(self.commandEdit)
        self.viewLayout.addWidget(self.matcherLabel)
        self.viewLayout.addWidget(self.matcherEdit)
        self.viewLayout.addSpacing(8)
        self.viewLayout.addWidget(self.enabledCheck)
        
        self.yesButton = PrimaryPushButton("添加", self)
        self.cancelButton = PushButton("取消", self)
        self.yesButton.clicked.connect(self._on_yes)
        self.cancelButton.clicked.connect(self.reject)
    
    def _on_yes(self):
        event = self.eventCombo.currentText()
        command = self.commandEdit.text().strip()
        if not event or not command:
            return
        self.accept()
    
    def get_values(self):
        return {
            "event": self.eventCombo.currentText(),
            "type": self.typeCombo.currentText(),
            "command": self.commandEdit.text().strip(),
            "matcher": self.matcherEdit.text().strip(),
            "enabled": self.enabledCheck.isChecked()
        }


class HookEditCard(QWidget):
    """
    Hook 编辑卡片（卡片形态）
    类似 ProviderEditCard，放在 BaseSettingsCard 中使用
    """
    
    saved = pyqtSignal(dict)
    closed = pyqtSignal()
    
    def __init__(self, hook_data: dict = None, parent=None):
        super().__init__(parent=parent)
        self._hook_data = hook_data or {}
        self._is_new = hook_data is None
        self._setup_ui()
        if not self._is_new:
            self._load_data()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 8, 16, 8)
        
        layout.addWidget(BodyLabel("事件:"))
        self.eventCombo = ComboBox(self)
        self.eventCombo.addItems([
            "SessionStart", "PreUserMessage", "PostUserMessage",
            "PreAssistantMessage", "PostAssistantMessage",
            "PreToolUse", "PostToolUse"
        ])
        layout.addWidget(self.eventCombo)
        
        layout.addWidget(BodyLabel("类型:"))
        self.typeCombo = ComboBox(self)
        self.typeCombo.addItems(["command", "http", "python"])
        layout.addWidget(self.typeCombo)
        
        layout.addWidget(BodyLabel("命令:"))
        self.commandEdit = LineEdit(self)
        self.commandEdit.setPlaceholderText('如: echo "Hello" 或 python script.py')
        layout.addWidget(self.commandEdit)
        
        layout.addWidget(BodyLabel("Matcher (可选):"))
        self.matcherEdit = LineEdit(self)
        self.matcherEdit.setPlaceholderText("如: tool:bash 或 .*帮助.*")
        layout.addWidget(self.matcherEdit)
        
        self.enabledCheck = CheckBox("添加后启用", self)
        self.enabledCheck.setChecked(True)
        layout.addWidget(self.enabledCheck)
        layout.addStretch(1)
    
    def _load_data(self):
        d = self._hook_data
        hook_type = d.get("type", "command")
        for i in range(self.typeCombo.count()):
            if self.typeCombo.itemText(i) == hook_type:
                self.typeCombo.setCurrentIndex(i)
                break
        self.commandEdit.setText(d.get("command", d.get("url", "")))
        self.enabledCheck.setChecked(d.get("enabled", True))
    
    def get_values(self) -> dict:
        return {
            "event": self.eventCombo.currentText(),
            "type": self.typeCombo.currentText(),
            "command": self.commandEdit.text().strip(),
            "matcher": self.matcherEdit.text().strip(),
            "enabled": self.enabledCheck.isChecked(),
        }
    
    def _on_save(self):
        values = self.get_values()
        if not values["event"] or not values["command"]:
            return
        self.saved.emit(values)
    
    def get_title(self) -> str:
        if self._is_new:
            return "➕ 添加 Hook"
        return "✏️ 编辑 Hook"


class HookListSettingCard(ExpandSettingCard):
    """Hook 管理设置卡片"""
    
    hooksChanged = pyqtSignal()
    showAddHookCard = pyqtSignal()  # 显示添加 Hook 卡片
    showEditHookCard = pyqtSignal(dict)  # 显示编辑 Hook 卡片
    
    def __init__(self, icon: QIcon, title: str, content: str = None, parent=None, home=None,
                 hook_manager=None):
        self.home = home
        self._hook_manager = hook_manager
        super().__init__(icon, title, content, parent)
        self.title = title
        self.hooks_config_file = get_app_data_dir() / "hooks" / "hooks.json"
        self._load_hooks()
        self._setup_ui()
    
    def _load_hooks(self):
        """从配置文件加载 hooks"""
        self.all_hooks = {}
        if self.hooks_config_file.exists():
            try:
                with open(self.hooks_config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.all_hooks = config.get("hooks", {})
            except Exception as e:
                print(f"加载 hooks 配置失败: {e}")
    
    def _save_hooks(self):
        """保存 hooks 到配置文件，并同步到 HookManager"""
        self.hooks_config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.hooks_config_file, 'w', encoding='utf-8') as f:
            json.dump({"hooks": self.all_hooks}, f, indent=2, ensure_ascii=False)
        
        # 同步到 HookManager（热重载）
        if self._hook_manager:
            self._hook_manager.reload_global_hooks(str(self.hooks_config_file))
            logger = __import__('logging').getLogger('hook_setting_card')
            logger.info(f"[HookSettingCard] Synced hooks to HookManager")
    
    def _setup_ui(self):
        self.viewLayout.setSpacing(0)
        self.viewLayout.setAlignment(Qt.AlignTop)
        self.viewLayout.setContentsMargins(8, 0, 8, 0)
        
        # 按钮移到卡片头部（类似 SkillListSettingCard）
        self.addButton = PushButton("添加", self, FluentIcon.ADD)
        self.refreshButton = PushButton("刷新", self, FluentIcon.SYNC)
        
        self.addButton.clicked.connect(self.showAddHookCard.emit)
        self.refreshButton.clicked.connect(self._refresh)
        
        self.addWidget(self.addButton)
        self.addWidget(self.refreshButton)
        
        # 事件分组
        self._render_hooks()
    
    def _render_hooks(self):
        """渲染所有 hooks"""
        if not self.all_hooks:
            empty_label = QLabel("暂无 Hooks，点击「+ 添加」创建", self.view)
            empty_label.setStyleSheet("color: #888; padding: 16px; font-size: 12px;")
            empty_label.setAlignment(Qt.AlignCenter)
            self.viewLayout.addWidget(empty_label)
            return
        
        for event_name, rules in self.all_hooks.items():
            if not rules:
                continue
            
            # 事件标题
            header = QLabel(f"Event: {event_name}", self.view)
            header.setStyleSheet(
                "background-color: #F0F0F0; color: #333; font-weight: bold; "
                "padding: 6px 48px; font-size: 12px;"
            )
            self.viewLayout.addWidget(header)
            
            # Hook 条目
            for rule_index, rule in enumerate(rules):
                hooks = rule.get("hooks", [])
                for hook_index, hook in enumerate(hooks):
                    item = HookItem(event_name, hook, hook_index, self.view)
                    # 使用闭包捕获正确的变量值
                    item.removed.connect(
                        lambda idx, en=event_name, ri=rule_index: self._remove_hook(en, ri, idx)
                    )
                    item.toggled.connect(
                        lambda idx, enabled, en=event_name, ri=rule_index, hi=hook_index: self._toggle_hook(en, ri, hi, enabled)
                    )
                    self.viewLayout.addWidget(item)
    
    def _add_hook(self, event: str, command: str, matcher: str = "", hook_type: str = "command", enabled: bool = True):
        """添加新 hook"""
        if event not in self.all_hooks:
            self.all_hooks[event] = []
        
        hook_data = {
            "type": hook_type,
            "command": command,
            "enabled": enabled
        }
        
        new_rule = {"hooks": [hook_data]}
        if matcher:
            new_rule["matcher"] = matcher
        
        self.all_hooks[event].append(new_rule)
        self._save_hooks()
        self._refresh()
        self.hooksChanged.emit()
    
    def _remove_hook(self, event: str, rule_index: int, hook_index: int):
        """删除 hook"""
        if event in self.all_hooks:
            rules = self.all_hooks[event]
            if rule_index < len(rules):
                hooks = rules[rule_index].get("hooks", [])
                if hook_index < len(hooks):
                    hooks.pop(hook_index)
                    # 如果规则没有 hooks 了，移除规则
                    if not hooks:
                        rules.pop(rule_index)
                    # 如果事件没有规则了，移除事件
                    if not rules:
                        del self.all_hooks[event]
                    self._save_hooks()
                    self._refresh()
                    self.hooksChanged.emit()
    
    def _toggle_hook(self, event: str, rule_index: int, hook_index: int, enabled: bool):
        """切换 hook 启用状态"""
        if event in self.all_hooks:
            rules = self.all_hooks[event]
            if rule_index < len(rules):
                hooks = rules[rule_index].get("hooks", [])
                if hook_index < len(hooks):
                    hooks[hook_index]["enabled"] = enabled
                    self._save_hooks()
                    self.hooksChanged.emit()
    
    def _refresh(self):
        """刷新 hook 列表"""
        self._load_hooks()
        # 移除 viewLayout 中的所有 widgets
        for i in reversed(range(self.viewLayout.count())):
            item = self.viewLayout.itemAt(i)
            widget = item.widget()
            if widget:
                self.viewLayout.removeItem(item)
                widget.deleteLater()
        # 重新渲染
        self._render_hooks()
        # 调整展开区域高度
        self._adjustViewSize()