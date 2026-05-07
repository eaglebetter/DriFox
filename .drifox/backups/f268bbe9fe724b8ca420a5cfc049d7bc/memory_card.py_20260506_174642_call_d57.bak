# -*- coding: utf-8 -*-
"""
记忆管理卡片 - 复刻 memory_manager.py 弹窗完整样式
"""
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidgetItem,
)
from qfluentwidgets import (
    BodyLabel,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SwitchButton,
    FluentIcon,
    TransparentToolButton,
    ListWidget,
    SegmentedWidget,
)
from qfluentwidgets.components.widgets.card_widget import CardSeparator, SimpleCardWidget

from app.utils.utils import get_font_family_css

MEMORY_CATEGORIES_WIDGET = {
    "agent_identity": "【智能体自身身份记忆】",
    "user_identity": "【用户身份记忆】",
    "task_preference": "【用户任务偏好】",
    "task_taboos": "【任务忌讳】",
    "key_knowledge": "【关键事实】",
}

MEMORY_CATEGORY_SHORT_NAMES = {
    "agent_identity": "智能体",
    "user_identity": "用户",
    "task_preference": "偏好",
    "task_taboos": "忌讳",
    "key_knowledge": "知识",
}


class MemoryItemWidget(QWidget):
    """记忆项显示组件 - 和弹窗一致"""

    deleted = pyqtSignal(int)
    toggled = pyqtSignal(int, bool)

    def __init__(
        self,
        item_id: int,
        content: str,
        enabled: bool = True,
        meta_text: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.item_id = item_id
        self.content = content
        self.meta_text = meta_text
        self._init_ui(enabled)

    def _init_ui(self, enabled):
        self.setFixedHeight(60)
        self.setSizePolicy(1, 0)  # 水平扩展，垂直固定

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(0)

        text_wrap = QWidget(self)
        text_wrap.setSizePolicy(1, 0)  # 水平扩展，垂直固定
        text_layout = QVBoxLayout(text_wrap)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        self.label = BodyLabel(self.content, self)
        self.label.setWordWrap(True)
        self.label.setStyleSheet(f"padding: 2px 8px 0 8px; {get_font_family_css()} font-size: 12px;")
        text_layout.addWidget(self.label)

        if self.meta_text:
            self.meta_label = BodyLabel(self.meta_text, self)
            self.meta_label.setWordWrap(True)
            self.meta_label.setStyleSheet(
                f"padding: 0 8px 2px 8px; color: #8c99ad; {get_font_family_css()} font-size: 10px;"
            )
            text_layout.addWidget(self.meta_label)

        main_layout.addWidget(text_wrap, 1)
        main_layout.addWidget(CardSeparator())

        self.switch = SwitchButton(self)
        self.switch.setChecked(enabled)
        self.switch.setOnText("")
        self.switch.setOffText("")
        self.switch.checkedChanged.connect(
            lambda checked: self.toggled.emit(self.item_id, checked)
        )
        main_layout.addWidget(self.switch)

        main_layout.addWidget(CardSeparator())
        self.delete_btn = TransparentToolButton(FluentIcon.DELETE, self)
        self.delete_btn.clicked.connect(lambda: self.deleted.emit(self.item_id))
        main_layout.addWidget(self.delete_btn)


class MemoryCardContent(QWidget):
    """记忆卡片内容区域 - 完整复刻 MemoryManagerDialog 样式和功能"""

    memorySaved = pyqtSignal(list)

    def __init__(self, memory_manager, parent=None):
        super().__init__(parent)
        self._memory_manager = memory_manager  # 初始引用
        self._memories = []
        self._current_category = "agent_identity"
        self._init_ui()

    def _get_memory_manager(self):
        """获取 memory_manager，优先使用注入的，否则从父窗口获取"""
        if self._memory_manager:
            return self._memory_manager
        # 尝试从父窗口获取
        parent = self.parent()
        while parent:
            if hasattr(parent, '_memory_manager'):
                return parent._memory_manager
            parent = parent.parent()
        return None

    def _init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background: transparent;
            }
            QListWidget {
                background-color: rgba(37, 37, 38, 180);
                border: 1px solid rgba(62, 62, 66, 150);
                color: #e0e0e0;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 0;
            }
            QListWidget::item:selected {
                background-color: rgba(9, 71, 113, 150);
            }
            BodyLabel {
                color: #e0e0e0;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)

        # 分类切换 - 使用 SegmentedWidget，紧凑设计
        self.segmented_widget = SegmentedWidget(self)
        segment_keys = list(MEMORY_CATEGORIES_WIDGET.keys())
        for k in segment_keys:
            self.segmented_widget.addItem(k, MEMORY_CATEGORY_SHORT_NAMES[k])
        self.segmented_widget.setCurrentItem(segment_keys[0])
        self.segmented_widget.currentItemChanged.connect(self._on_category_changed)
        main_layout.addWidget(self.segmented_widget)

        # 统计标签
        self.category_count_label = BodyLabel(self)
        self.category_count_label.setStyleSheet(
            f"color: #8c99ad; {get_font_family_css()} font-size: 11px; padding: 2px 4px;"
        )
        main_layout.addWidget(self.category_count_label)

        # 记忆列表
        self.list_widget = ListWidget(self)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: rgba(37, 37, 38, 180);
                border: 1px solid rgba(62, 62, 66, 150);
                color: #e0e0e0;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 0;
                border-bottom: 1px solid rgba(62, 62, 66, 80);
            }
            QListWidget::item:selected {
                background-color: rgba(9, 71, 113, 150);
            }
        """)
        main_layout.addWidget(self.list_widget, 1)

        # 添加区域 - 紧凑设计
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)
        self.input_edit = LineEdit(self)
        self.input_edit.setFixedHeight(28)
        self.input_edit.setPlaceholderText("添加新的记忆...")
        self.input_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(37, 37, 38, 180);
                border: 1px solid rgba(62, 62, 66, 150);
                color: #e0e0e0;
                padding: 4px 8px;
                border-radius: 4px;
                {get_font_family_css()} font-size: 12px;
            }}
        """)
        self.add_btn = PrimaryPushButton("添加", self)
        self.add_btn.setFixedSize(50, 28)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)
        self.add_btn.clicked.connect(self._add_memory)
        self.input_edit.returnPressed.connect(self._add_memory)
        input_layout.addWidget(self.input_edit, 1)
        input_layout.addWidget(self.add_btn)
        main_layout.addLayout(input_layout)

        # 操作按钮行 - 紧凑设计
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        select_all_btn = PushButton("全部启用", self)
        select_all_btn.setFixedHeight(26)
        select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(14, 99, 156, 180);
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)
        select_all_btn.clicked.connect(self._select_all)

        deselect_all_btn = PushButton("全部关闭", self)
        deselect_all_btn.setFixedHeight(26)
        deselect_all_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(14, 99, 156, 180);
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)
        deselect_all_btn.clicked.connect(self._deselect_all)

        clear_disabled_btn = PushButton("删除未选", self)
        clear_disabled_btn.setFixedHeight(26)
        clear_disabled_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(196, 43, 28, 180);
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #d43d2a;
            }
        """)
        clear_disabled_btn.clicked.connect(self._clear_disabled)

        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(deselect_all_btn)
        btn_layout.addWidget(clear_disabled_btn)
        btn_layout.addStretch()

        # 保存按钮
        self.save_btn = PrimaryPushButton("保存", self)
        self.save_btn.setFixedHeight(26)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)
        self.save_btn.clicked.connect(self._save_memories)
        btn_layout.addWidget(self.save_btn)

        main_layout.addLayout(btn_layout)

    def _on_category_changed(self, key: str):
        """切换分类"""
        if key in MEMORY_CATEGORIES_WIDGET:
            self._current_category = key
            self._load_memories()

    def _update_category_count_label(self):
        """更新分类统计"""
        category_memories = {k: [] for k in MEMORY_CATEGORIES_WIDGET}

        for mem in self._memories:
            if isinstance(mem, dict):
                cat = mem.get("category", "task_preference")
                if cat in category_memories:
                    category_memories[cat].append(mem)

        counts = {k: len(v) for k, v in category_memories.items()}
        total = sum(counts.values())
        current_count = counts.get(self._current_category, 0)

        from app.core.memory_manager import MEMORY_CATEGORY_LIMITS

        limit = MEMORY_CATEGORY_LIMITS.get(self._current_category, 20)
        self.category_count_label.setText(f"{current_count}/{limit} | 总: {total}")

    def _load_memories(self):
        """加载记忆数据"""
        self.list_widget.clear()

        # 获取 memory_manager（只在首次加载或刷新时从数据库读取）
        memory_mgr = self._get_memory_manager()
        if not self._memories and memory_mgr:
            # 首次加载或数据为空时，从数据库读取
            all_memories = memory_mgr.get_user_memories()
            if all_memories:
                self._memories = list(all_memories)
            else:
                self._memories = []
        elif not self._memories:
            self._memories = []

        # 按分类组织记忆（使用本地 _memories，不再从数据库读取）
        category_memories = {k: [] for k in MEMORY_CATEGORIES_WIDGET}

        for mem_idx, mem in enumerate(self._memories):
            if isinstance(mem, dict):
                content = mem.get("content", "")
                enabled = mem.get("enabled", True)
                source = mem.get("source", "manual")
                confidence = mem.get("confidence", 0.8)
                hit_count = mem.get("hit_count", 0)
                last_used = mem.get("last_used_at", "")
                category = mem.get("category", "task_preference")
                meta_parts = [f"source={source}", f"conf={confidence:.2f}"]
                if hit_count > 0:
                    meta_parts.append(f"hits={hit_count}")
                if last_used:
                    days_ago = ""
                    try:
                        from datetime import datetime as dt

                        used_date = dt.strptime(last_used, "%Y-%m-%d %H:%M:%S")
                        days = (dt.now() - used_date).days
                        if days == 0:
                            days_ago = "today"
                        elif days == 1:
                            days_ago = "1d"
                        else:
                            days_ago = f"{days}d"
                        meta_parts.append(f"used={days_ago}")
                    except Exception:
                        pass
                meta_text = " | ".join(meta_parts)
            else:
                content = str(mem)
                enabled = True
                meta_text = "source=legacy"
                category = "task_preference"

            if category not in MEMORY_CATEGORIES_WIDGET:
                category = "task_preference"

            category_memories[category].append((mem_idx, content, enabled, meta_text))

        # 显示当前分类的记忆
        current_memories = category_memories.get(self._current_category, [])

        for display_idx, (mem_idx, content, enabled, meta_text) in enumerate(current_memories):
            item = QListWidgetItem()
            item.setSizeHint(self._get_item_size())
            widget = MemoryItemWidget(display_idx, content, enabled, meta_text)
            widget.deleted.connect(self._delete_item)
            widget.toggled.connect(self._toggle_item)
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

        self._update_category_count_label()

    def _get_item_size(self):
        """获取列表项大小"""
        from PyQt5.QtCore import QSize
        width = self.list_widget.size().width()
        if width <= 0:
            width = 400  # 默认宽度
        return QSize(width, 60)

    def _get_memory_index_from_item_id(self, item_id: int) -> int:
        """根据 item_id (显示索引) 找到真实的 memory 索引"""
        category_memories = {k: [] for k in MEMORY_CATEGORIES_WIDGET}

        for mem_idx, mem in enumerate(self._memories):
            if isinstance(mem, dict):
                category = mem.get("category", "task_preference")
            else:
                category = "task_preference"
            if category not in MEMORY_CATEGORIES_WIDGET:
                category = "task_preference"
            category_memories[category].append(mem_idx)

        current_category_indices = category_memories.get(self._current_category, [])
        if 0 <= item_id < len(current_category_indices):
            return current_category_indices[item_id]
        return -1

    def _add_memory(self):
        """添加记忆（只添加到本地缓存，不立即保存）"""
        content = self.input_edit.text().strip()
        if not content:
            return

        new_entry = {
            "content": content,
            "enabled": True,
            "confidence": 0.8,
            "source": "manual",
            "last_used_at": "",
            "conflict_group": "",
            "category": self._current_category,
        }

        if isinstance(self._memories, list):
            self._memories.append(new_entry)

        self.input_edit.clear()
        self._load_memories()

    def _delete_item(self, item_id: int):
        """删除记忆（只从本地缓存删除，不立即保存）"""
        mem_idx = self._get_memory_index_from_item_id(item_id)
        if 0 <= mem_idx < len(self._memories):
            deleted_content = self._memories[mem_idx].get("content", "")[:30]
            self._memories.pop(mem_idx)
            self._load_memories()

    def _toggle_item(self, item_id: int, enabled: bool):
        """切换启用状态（只更新本地缓存，不立即保存）"""
        mem_idx = self._get_memory_index_from_item_id(item_id)
        if 0 <= mem_idx < len(self._memories):
            if isinstance(self._memories[mem_idx], dict):
                self._memories[mem_idx]["enabled"] = enabled
            else:
                self._memories[mem_idx] = {
                    "content": str(self._memories[mem_idx]),
                    "enabled": enabled,
                }
            # 只更新卡片状态，不保存
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                widget = self.list_widget.itemWidget(item)
                if widget and widget.item_id == item_id:
                    widget.switch.setChecked(enabled)
                    break

    def _select_all(self):
        """全部启用（只更新本地缓存，不立即保存）"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget:
                widget.switch.setChecked(True)
                mem_idx = self._get_memory_index_from_item_id(widget.item_id)
                if 0 <= mem_idx < len(self._memories):
                    self._memories[mem_idx]["enabled"] = True

    def _deselect_all(self):
        """全部关闭（只更新本地缓存，不立即保存）"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget:
                widget.switch.setChecked(False)
                mem_idx = self._get_memory_index_from_item_id(widget.item_id)
                if 0 <= mem_idx < len(self._memories):
                    self._memories[mem_idx]["enabled"] = False

    def _clear_disabled(self):
        """删除未启用（只更新本地缓存，不立即保存）"""
        enabled_memories = []
        for mem in self._memories:
            if isinstance(mem, dict):
                if mem.get("enabled", True):
                    enabled_memories.append(mem)
            else:
                enabled_memories.append(
                    {"content": str(mem), "enabled": True, "category": "task_preference"}
                )

        self._memories = enabled_memories
        self._load_memories()

        self._load_memories()

    def _save_memories(self):
        """保存记忆"""
        memory_mgr = self._get_memory_manager()
        if memory_mgr:
            memory_mgr.update_user_memories(self._memories)
        self.memorySaved.emit(self._memories)

    def load_memories(self):
        """外部调用刷新数据"""
        self._load_memories()

    def get_memories(self) -> list:
        return self._memories