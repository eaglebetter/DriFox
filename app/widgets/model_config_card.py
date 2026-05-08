# -*- coding: utf-8 -*-
"""
模型配置卡片 - 优化布局，有变化自动保存
"""
import webbrowser

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import (
    BodyLabel,
    LineEdit,
    Slider,
    SpinBox,
    SwitchButton,
    PasswordLineEdit,
    ComboBox, )

from app.constants import (
    PARAM_UI_MAP,
    PARAM_RANGE_MAP,
)
from app.widgets.searchable_editable_combobox import SearchableEditableComboBox


class ModelConfigCard(QWidget):
    """模型配置卡片内容 - 有变化自动保存"""

    configApplied = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = {}
        self.current_provider = ""
        self._widgets = {}
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(300)
        self._save_timer.timeout.connect(self._do_save)
        self._setup_ui()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(4, 0, 4, 0)
        self.layout.setSpacing(3)  # 恢复行间距

    def _clear_layout(self, layout):
        """递归清理 layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def set_config(self, title: str, config: dict):
        self.config = config.copy()
        self.current_provider = title

        self._clear_layout(self.layout)
        self._widgets.clear()

        # 补充缺失的思考相关字段（向后兼容旧配置）
        if "启用思考" not in self.config:
            self.config["启用思考"] = True  # 默认开启
        if "思考等级" not in self.config:
            self.config["思考等级"] = "high"  # 默认普通思考

        # 仅显示参数配置（温度、上下文长度等），不显示连接/模型字段
        skip_keys = ["模型名称", "API_URL", "API_KEY", "认证方式", "获取地址", "模型列表", "选择模型"]
        # 显示名称映射（存储字段名 -> UI显示名）
        display_name_map = {
            "最大Token": "上下文长度",
        }
        
        # 分离普通参数和思考相关参数
        normal_params = []
        thinking_params = []
        for key, value in self.config.items():
            if key in skip_keys:
                continue
            if key in ["启用思考", "思考等级"]:
                thinking_params.append((key, value))
            else:
                normal_params.append((key, value))
        
        # 先显示普通参数
        for key, value in normal_params:
            self._add_param_row(key, value, display_name_map)
        
        # 添加分隔线和思考分组
        if thinking_params:
            separator = QLabel("", self)
            separator.setStyleSheet("border-bottom: 1px solid #3a3a3a; margin: 8px 0;")
            self.layout.addWidget(separator)
            
            thinking_header = QLabel("🔮 思考模式", self)
            thinking_header.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 4px;")
            self.layout.addWidget(thinking_header)
            
            for key, value in thinking_params:
                self._add_param_row(key, value, display_name_map)
                
    def _add_param_row(self, key, value, display_name_map):
        """添加一行参数配置"""
        ui_type = self._infer_ui_type(key, value)
        widget = self._create_widget(key, ui_type, value)
        display_name = display_name_map.get(key, key)
        label = BodyLabel(f"{display_name}：", self)
        
        # 思考相关参数样式微调
        if key in ["启用思考", "思考等级"]:
            label.setStyleSheet("color: #aaa;")
        
        hlayout = QHBoxLayout()
        hlayout.setContentsMargins(0, 2, 0, 2)  # 紧凑间距
        hlayout.setSpacing(12)
        hlayout.addWidget(label, 0)
        hlayout.addWidget(widget, 1)
        self.layout.addLayout(hlayout)
        self._widgets[key] = (label, widget)
        
        # 特殊处理：填充 combobox 选项
        if ui_type == "combobox":
            self._setup_combobox_options(key, widget, value)
    
    def _setup_combobox_options(self, key: str, widget, current_value):
        """为下拉框设置选项列表"""
        if key == "思考等级":
            options = ["low", "medium", "high", "max"]
            widget.blockSignals(True)  # 阻断信号，避免设置时触发保存
            widget.addItems(options)
            if current_value in options:
                widget.setCurrentText(current_value)
            widget.blockSignals(False)

    def _infer_ui_type(self, key: str, value) -> str:
        key_lower = key.lower()
        if key in PARAM_UI_MAP:
            return PARAM_UI_MAP[key]
        # 排除最大Token和上下文长度，避免被误判为password
        if "key" in key_lower or ("token" in key_lower and key not in ["最大Token", "上下文长度"]):
            return "password"
        if isinstance(value, (int, float)):
            if 0 <= value <= 1 or 0 <= value <= 2:
                return "slider"
            else:
                return "spinbox"
        return "line"

    def _create_widget(self, key, ui_type: str, value):
        if ui_type == "password":
            widget = PasswordLineEdit(self)
            widget.blockSignals(True)  # 阻断信号
            widget.setText(str(value) if value else "")
            widget.blockSignals(False)
            widget.setMinimumWidth(280)  # 统一宽度
            widget.textChanged.connect(lambda: self._on_field_changed())
            return widget
        elif ui_type == "slider":
            range_info = PARAM_RANGE_MAP.get(
                key, {"min": 0.0, "max": 1.0, "step": 0.01, "type": "float"}
            )
            min_val = range_info["min"]
            max_val = range_info["max"]
            step = range_info["step"]
            is_float = range_info["type"] == "float"
            current = float(value) if value not in (None, "") else min_val
            scale = 1 / step
            slider_min = int(min_val * scale)
            slider_max = int(max_val * scale)
            slider_value = int(round(current * scale))

            container = QWidget(self)
            container.setFixedHeight(28)  # 固定高度，避免占用过大空间
            hlayout = QHBoxLayout(container)
            hlayout.setContentsMargins(0, 0, 0, 0)

            slider = Slider(Qt.Horizontal, self)
            slider.setRange(slider_min, slider_max)
            slider.blockSignals(True)  # 阻断信号
            slider.setValue(slider_value)
            slider.blockSignals(False)
            slider.setMinimumHeight(22)
            slider.valueChanged.connect(lambda: self._on_field_changed())

            display_value = current if is_float else int(current)
            label = BodyLabel(
                f"{display_value:.2f}" if is_float else str(int(display_value)), self
            )
            label.setFixedWidth(60)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            def _update_label(v):
                logical_val = v / scale
                if not is_float:
                    logical_val = int(logical_val)
                fmt_val = f"{logical_val:.2f}" if is_float else str(logical_val)
                label.setText(fmt_val)

            slider.valueChanged.connect(_update_label)

            hlayout.addWidget(slider, 1)
            hlayout.addWidget(label)

            container.slider = slider
            container.label = label
            container.range_info = range_info
            container.scale = scale

            return container
        elif ui_type == "checkbox":
            widget = SwitchButton(self)
            widget._onText = widget.tr("开启")
            widget._offText = widget.tr("关闭")
            checked = False
            if isinstance(value, bool):
                checked = value
            elif isinstance(value, str):
                checked = value.lower() in ("true", "1", "yes", "on")
            elif isinstance(value, (int, float)):
                checked = bool(value)
            widget.blockSignals(True)  # 阻断信号，避免初始化时触发保存
            widget.setChecked(checked)
            widget.blockSignals(False)
            widget.checkedChanged.connect(lambda: self._on_field_changed())
            return widget
        elif ui_type == "switch":
            # 开关类型（和 checkbox 一样使用 SwitchButton）
            widget = SwitchButton(self)
            widget._onText = widget.tr("开启")
            widget._offText = widget.tr("关闭")
            checked = False
            if isinstance(value, bool):
                checked = value
            elif isinstance(value, str):
                checked = value.lower() in ("true", "1", "yes", "on")
            elif isinstance(value, (int, float)):
                checked = bool(value)
            widget.blockSignals(True)  # 阻断信号，避免初始化时触发保存
            widget.setChecked(checked)
            widget.blockSignals(False)
            widget.checkedChanged.connect(lambda: self._on_field_changed())
            return widget
        elif ui_type == "combobox":
            # 下拉框类型（用于思考等级等选项）
            widget = ComboBox(self)
            widget.setMinimumWidth(120)
            widget.blockSignals(True)  # 阻断信号
            if hasattr(widget, 'currentTextChanged'):
                # 先设置选项再设置当前值
                pass
            widget.blockSignals(False)
            widget.currentTextChanged.connect(lambda: self._on_field_changed())
            return widget
        elif ui_type == "spinbox":
            widget = SpinBox()
            val = int(value) if value else 2048
            # 从 PARAM_RANGE_MAP 获取范围配置，默认为无限范围
            range_info = PARAM_RANGE_MAP.get(key, {"min": 1, "max": 99999999})
            widget.setRange(range_info["min"], range_info["max"])
            widget.blockSignals(True)  # 阻断信号
            widget.setValue(val)
            widget.blockSignals(False)
            widget.setMinimumWidth(280)  # 统一宽度
            widget.valueChanged.connect(lambda: self._on_field_changed())
            return widget
        else:
            widget = LineEdit(self)
            widget.setMinimumWidth(280)  # 统一宽度
            widget.blockSignals(True)  # 阻断信号
            widget.setText(str(value) if value else "")
            widget.blockSignals(False)
            widget.textChanged.connect(lambda: self._on_field_changed())
            return widget

    def _on_field_changed(self):
        """字段变化时触发保存"""
        self._save_timer.start()

    def _do_save(self):
        """执行保存"""
        config = self.get_config()
        self.configApplied.emit(config)

    def get_config(self) -> dict:
        result = self.config.copy()
        for key, (label, widget) in self._widgets.items():
            actual_key = "模型名称" if key == "选择模型" else key

            if isinstance(widget, LineEdit):
                result[actual_key] = widget.text().strip()
            elif isinstance(widget, ComboBox):
                result[actual_key] = widget.currentText()
            elif isinstance(widget, SearchableEditableComboBox):
                text = (
                    widget.text().strip()
                    if callable(getattr(widget, "text", None))
                    else ""
                )
                if text:
                    result[actual_key] = text
                else:
                    result[actual_key] = (
                        widget.currentText() if hasattr(widget, "currentText") else ""
                    )
            elif hasattr(widget, "slider"):
                logical_value = widget.slider.value() / widget.scale
                range_info = getattr(widget, "range_info", {})
                if range_info.get("type") == "int":
                    result[actual_key] = int(round(logical_value))
                else:
                    result[actual_key] = float(logical_value)
            elif isinstance(widget, SpinBox):
                result[actual_key] = widget.value()
            elif hasattr(widget, "isChecked"):
                result[actual_key] = widget.isChecked()
            else:
                result[actual_key] = ""
        return result

    def _on_get_api_key(self, url: str):
        webbrowser.open(url)
