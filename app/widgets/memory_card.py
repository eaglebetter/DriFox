# -*- coding: utf-8 -*-
"""
记忆管理卡片 - 重构为 3 Tab 结构
1. 条目记忆 - 列表 + 搜索 + 编辑
2. 项目笔记 - Markdown 编辑器
3. 关键文档 - 列表 + 拖拽添加
"""
import os
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidgetItem,
    QFileDialog,
    QMenu,
    QAction,
    QTextEdit,
)
from PyQt5.QtGui import QDropEvent, QDragEnterEvent, QDragMoveEvent
from loguru import logger
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
    TextEdit,
)
from qfluentwidgets.components.widgets.card_widget import CardSeparator

from app.utils.utils import get_font_family_css


# Tab 标识
TAB_ENTRY_MEMORIES = "entries"
TAB_PROJECT_NOTES = "notes"
TAB_KEY_DOCUMENTS = "docs"


class DocDropListWidget(ListWidget):
    """支持拖拽文件的列表控件"""
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._is_drag_over = False

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._is_drag_over = True
            self.update()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._is_drag_over = False
        self.update()

    def dropEvent(self, event: QDropEvent):
        self._is_drag_over = False
        self.update()

        file_paths = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                # 文件和文件夹都接受
                if path and (os.path.isfile(path) or os.path.isdir(path)):
                    file_paths.append(path)

        if file_paths:
            self.files_dropped.emit(file_paths)


class EntryMemoryItemWidget(QWidget):
    """条目记忆项组件"""

    deleted = pyqtSignal(str)  # memory_id
    toggled = pyqtSignal(str, bool)
    edited = pyqtSignal(str, str)  # memory_id, new_content

    def __init__(
        self,
        memory_id: str,
        content: str,
        enabled: bool = True,
        source: str = "manual",
        parent=None,
    ):
        super().__init__(parent)
        self.memory_id = memory_id
        self._content = content
        self._editing = False
        self._init_ui(enabled, source)

    def _init_ui(self, enabled, source):
        self.setFixedHeight(50)
        self.setSizePolicy(1, 0)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(4)

        # 内容区域
        self.text_widget = QWidget(self)
        self.text_widget.setSizePolicy(1, 0)
        text_layout = QVBoxLayout(self.text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        self.content_label = BodyLabel(self._content, self.text_widget)
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet(
            f"padding: 2px 4px 0 4px; {get_font_family_css()} font-size: 12px;"
        )
        text_layout.addWidget(self.content_label)

        self.meta_label = BodyLabel(f"source={source}", self.text_widget)
        self.meta_label.setStyleSheet(
            f"padding: 0 4px 2px 4px; color: #8c99ad; {get_font_family_css()} font-size: 10px;"
        )
        text_layout.addWidget(self.meta_label)

        main_layout.addWidget(self.text_widget, 1)

        # 编辑输入框（初始隐藏）
        self.edit_widget = QWidget(self)
        self.edit_widget.setSizePolicy(1, 0)
        self.edit_widget.setVisible(False)
        edit_layout = QVBoxLayout(self.edit_widget)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(2)

        self.edit_line = LineEdit(self.edit_widget)
        self.edit_line.setText(self._content)
        self.edit_line.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(50, 50, 50, 200);
                border: 1px solid rgba(14, 99, 156, 200);
                color: #e0e0e0;
                padding: 2px 6px;
                border-radius: 3px;
                {get_font_family_css()} font-size: 12px;
            }}
        """)
        self.edit_line.returnPressed.connect(self._finish_edit)
        self.edit_line.setFixedHeight(24)
        edit_layout.addWidget(self.edit_line)

        main_layout.addWidget(self.edit_widget, 1)

        # 操作按钮
        self.edit_btn = TransparentToolButton(FluentIcon.EDIT, self)
        self.edit_btn.setToolTip("编辑")
        self.edit_btn.clicked.connect(self._start_edit)

        self.delete_btn = TransparentToolButton(FluentIcon.DELETE, self)
        self.delete_btn.setToolTip("删除")
        self.delete_btn.clicked.connect(lambda: self.deleted.emit(self.memory_id))

        self.switch = SwitchButton(self)
        self.switch.setChecked(enabled)
        self.switch.setOnText("")
        self.switch.setOffText("")
        self.switch.checkedChanged.connect(
            lambda checked: self.toggled.emit(self.memory_id, checked)
        )
        self.switch.setFixedWidth(40)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(2)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.switch)

        main_layout.addLayout(btn_layout)

    def _start_edit(self):
        """开始编辑"""
        self._editing = True
        self.text_widget.setVisible(False)
        self.edit_widget.setVisible(True)
        self.edit_line.setFocus()
        self.edit_line.selectAll()

    def _finish_edit(self):
        """完成编辑"""
        new_content = self.edit_line.text().strip()
        if new_content and new_content != self._content:
            self.edited.emit(self.memory_id, new_content)
            self._content = new_content
            self.content_label.setText(new_content)
        self._cancel_edit()

    def _cancel_edit(self):
        """取消编辑"""
        self._editing = False
        self.text_widget.setVisible(True)
        self.edit_widget.setVisible(False)
        self.edit_line.setText(self._content)


class KeyDocumentItemWidget(QWidget):
    """关键文档项组件"""

    removed = pyqtSignal(str)  # doc_id
    open_file = pyqtSignal(str)  # file_path
    open_folder = pyqtSignal(str)  # folder_path

    def __init__(
        self,
        doc_id: str,
        file_name: str,
        file_path: str,
        added_by: str = "manual",
        parent=None,
    ):
        super().__init__(parent)
        self.doc_id = doc_id
        self.file_path = file_path
        self._init_ui(file_name, added_by)

    def _init_ui(self, file_name, added_by):
        self.setFixedHeight(44)
        self.setSizePolicy(1, 0)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(4)

        # 文件图标 + 名称
        icon_label = BodyLabel("📄", self)
        icon_label.setStyleSheet(f"font-size: 16px; padding: 0 4px;")

        name_label = BodyLabel(file_name, self)
        name_label.setWordWrap(True)
        name_label.setSizePolicy(1, 0)
        name_label.setStyleSheet(
            f"{get_font_family_css()} font-size: 12px; padding: 0 4px;"
        )

        main_layout.addWidget(icon_label)
        main_layout.addWidget(name_label, 1)

        # 来源标签
        by_label = BodyLabel(f"[{added_by}]", self)
        by_label.setStyleSheet(
            f"color: #8c99ad; {get_font_family_css()} font-size: 10px; padding: 0 4px;"
        )
        main_layout.addWidget(by_label)

        # 操作按钮
        self.open_btn = TransparentToolButton(FluentIcon.FOLDER, self)
        self.open_btn.setToolTip("打开所在文件夹")
        self.open_btn.clicked.connect(lambda: self.open_folder.emit(self.file_path))

        self.remove_btn = TransparentToolButton(FluentIcon.DELETE, self)
        self.remove_btn.setToolTip("移除")
        self.remove_btn.clicked.connect(lambda: self.removed.emit(self.doc_id))

        main_layout.addWidget(self.open_btn)
        main_layout.addWidget(self.remove_btn)


class DropZoneWidget(QWidget):
    """拖拽区域组件"""

    files_dropped = pyqtSignal(list)  # file_paths

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setMinimumHeight(60)
        self.setMaximumHeight(80)
        self.setAcceptDrops(True)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(37, 37, 38, 150);
                border: 2px dashed rgba(62, 62, 66, 200);
                border-radius: 6px;
                {get_font_family_css()}
            }}
            QWidget:hover {{
                border-color: rgba(14, 99, 156, 200);
                background-color: rgba(50, 50, 55, 150);
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        icon_label = BodyLabel("📁", self)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 20px;")
        layout.addWidget(icon_label)

        label = BodyLabel("拖拽文件到此处 或 点击选择文件", self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            f"color: #8c99ad; {get_font_family_css()} font-size: 11px;"
        )
        layout.addWidget(label)

        self._is_drag_over = False

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._is_drag_over = True
            self.update()

    def dragLeaveEvent(self, event):
        self._is_drag_over = False
        self.update()

    def dropEvent(self, event: QDropEvent):
        self._is_drag_over = False
        self.update()

        file_paths = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path and os.path.isfile(path):
                    file_paths.append(path)

        if file_paths:
            self.files_dropped.emit(file_paths)

    def mousePressEvent(self, event):
        """点击打开文件选择对话框"""
        if event.button() == Qt.LeftButton:
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "选择关键文档",
                "",
                "所有文件 (*.*);;文本文件 (*.txt *.md);;代码文件 (*.py *.js *.ts)"
            )
            if files:
                self.files_dropped.emit(files)


class MemoryCardContent(QWidget):
    """记忆卡片内容区域 - 3 Tab 结构"""

    memorySaved = pyqtSignal(list)
    projectNoteChanged = pyqtSignal(str, str)  # project, content

    def __init__(self, memory_manager, parent=None):
        super().__init__(parent)
        self._memory_manager = memory_manager
        self._current_project = "默认项目"
        self._current_tab = TAB_ENTRY_MEMORIES
        self._init_ui()

    def _get_memory_manager(self):
        """获取 memory_manager"""
        if self._memory_manager:
            return self._memory_manager
        parent = self.parent()
        while parent:
            if hasattr(parent, '_memory_manager'):
                return parent._memory_manager
            parent = parent.parent()
        return None

    def set_project(self, project: str):
        """设置当前项目"""
        if self._current_project != project:
            self._current_project = project
        # 强制刷新项目笔记和关键文档
        self._load_project_note()
        self._load_key_documents()

    def _init_ui(self):
        self.setStyleSheet(f"""
            QWidget {{
                background: transparent;
            }}
            QListWidget {{
                background-color: rgba(37, 37, 38, 180);
                border: 1px solid rgba(62, 62, 66, 150);
                color: #e0e0e0;
                border-radius: 6px;
            }}
            QListWidget::item {{
                padding: 0;
                border-bottom: 1px solid rgba(62, 62, 66, 80);
            }}
            QListWidget::item:selected {{
                background-color: rgba(9, 71, 113, 150);
            }}
            BodyLabel {{
                color: #e0e0e0;
                {get_font_family_css()}
            }}
            QTextEdit, QPlainTextEdit {{
                background-color: rgba(37, 37, 38, 180);
                border: 1px solid rgba(62, 62, 66, 150);
                color: #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                {get_font_family_css()} font-size: 12px;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)

        # Tab 切换
        self.tab_widget = SegmentedWidget(self)
        self.tab_widget.addItem(TAB_ENTRY_MEMORIES, "条目记忆")
        self.tab_widget.addItem(TAB_PROJECT_NOTES, "项目笔记")
        self.tab_widget.addItem(TAB_KEY_DOCUMENTS, "关键文档")
        self.tab_widget.setCurrentItem(TAB_ENTRY_MEMORIES)
        self.tab_widget.currentItemChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.tab_widget)

        # 内容区域容器
        self.content_stack = QWidget(self)
        stack_layout = QVBoxLayout(self.content_stack)
        stack_layout.setContentsMargins(0, 0, 0, 0)
        stack_layout.setSpacing(0)

        # Tab 1: 条目记忆
        self._tab_entries = self._create_entries_tab()
        stack_layout.addWidget(self._tab_entries)

        # Tab 2: 项目笔记
        self._tab_notes = self._create_notes_tab()
        self._tab_notes.setVisible(False)
        stack_layout.addWidget(self._tab_notes)

        # Tab 3: 关键文档
        self._tab_docs = self._create_docs_tab()
        self._tab_docs.setVisible(False)
        stack_layout.addWidget(self._tab_docs)

        main_layout.addWidget(self.content_stack, 1)

    def _create_entries_tab(self) -> QWidget:
        """创建条目记忆 Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 搜索框
        self.search_edit = LineEdit(self)
        self.search_edit.setFixedHeight(28)
        self.search_edit.setPlaceholderText("🔍 搜索条目记忆...")
        self.search_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(37, 37, 38, 180);
                border: 1px solid rgba(62, 62, 66, 150);
                color: #e0e0e0;
                padding: 4px 8px;
                border-radius: 4px;
                {get_font_family_css()} font-size: 12px;
            }}
        """)
        self.search_edit.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.search_edit)

        # 记忆列表
        self.entries_list = ListWidget(self)
        self.entries_list.setStyleSheet(f"""
            QListWidget {{
                background-color: rgba(37, 37, 38, 180);
                border: 1px solid rgba(62, 62, 66, 150);
                color: #e0e0e0;
                border-radius: 6px;
                {get_font_family_css()}
            }}
            QListWidget::item {{
                padding: 0;
                border-bottom: 1px solid rgba(62, 62, 66, 80);
            }}
        """)
        layout.addWidget(self.entries_list, 1)

        # 添加区域
        add_layout = QHBoxLayout()
        add_layout.setSpacing(6)
        self.entry_input = LineEdit(self)
        self.entry_input.setFixedHeight(28)
        self.entry_input.setPlaceholderText("添加新的条目记忆...")
        self.entry_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(37, 37, 38, 180);
                border: 1px solid rgba(62, 62, 66, 150);
                color: #e0e0e0;
                padding: 4px 8px;
                border-radius: 4px;
                {get_font_family_css()} font-size: 12px;
            }}
        """)
        self.entry_add_btn = PrimaryPushButton("添加", self)
        self.entry_add_btn.setFixedSize(50, 28)
        self.entry_add_btn.setStyleSheet("""
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
        self.entry_add_btn.clicked.connect(self._add_entry)
        self.entry_input.returnPressed.connect(self._add_entry)
        add_layout.addWidget(self.entry_input, 1)
        add_layout.addWidget(self.entry_add_btn)
        layout.addLayout(add_layout)

        return widget

    def _create_notes_tab(self) -> QWidget:
        """创建项目笔记 Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 项目名标签
        self.project_name_label = BodyLabel(f"项目: {self._current_project}", self)
        self.project_name_label.setStyleSheet(
            f"color: #8c99ad; {get_font_family_css()} font-size: 11px; padding: 0 4px;"
        )
        layout.addWidget(self.project_name_label)

        # Markdown 编辑器
        self.notes_editor = TextEdit(self)
        self.notes_editor.setPlaceholderText("在此记录项目笔记，支持 Markdown 格式...")
        layout.addWidget(self.notes_editor, 1)

        # 保存按钮
        self.notes_save_btn = PrimaryPushButton("保存笔记", self)
        self.notes_save_btn.setFixedHeight(28)
        self.notes_save_btn.setStyleSheet("""
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
        self.notes_save_btn.clicked.connect(self._save_project_note)
        layout.addWidget(self.notes_save_btn)

        return widget

    def _create_docs_tab(self) -> QWidget:
        """创建关键文档 Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 文档列表（支持拖拽）
        self.docs_list = DocDropListWidget(self)  # 使用支持拖拽的列表
        self.docs_list.setStyleSheet(f"""
            QListWidget {{
                background-color: rgba(37, 37, 38, 180);
                border: 2px dashed rgba(62, 62, 66, 200);
                color: #e0e0e0;
                border-radius: 6px;
                {get_font_family_css()}
            }}
            QListWidget::item {{
                padding: 0;
                border-bottom: 1px solid rgba(62, 62, 66, 80);
            }}
        """)
        self.docs_list.files_dropped.connect(self._on_files_dropped)
        layout.addWidget(self.docs_list, 1)

        # 添加按钮（仅按钮）
        add_btn_layout = QHBoxLayout()
        add_btn_layout.setSpacing(6)
        
        self.add_doc_btn = PrimaryPushButton("📁 添加文件", self)
        self.add_doc_btn.setFixedHeight(28)
        self.add_doc_btn.setStyleSheet("""
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
        self.add_doc_btn.clicked.connect(self._on_add_file_clicked)
        
        add_btn_layout.addWidget(self.add_doc_btn)
        add_btn_layout.addStretch()
        layout.addLayout(add_btn_layout)

        return widget

    def _on_add_file_clicked(self):
        """点击添加文件按钮"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择关键文档",
            "",
            "所有文件 (*.*)"
        )
        if files:
            self._on_files_dropped(files)

    def _on_tab_changed(self, tab_key: str):
        """切换 Tab"""
        self._current_tab = tab_key

        self._tab_entries.setVisible(tab_key == TAB_ENTRY_MEMORIES)
        self._tab_notes.setVisible(tab_key == TAB_PROJECT_NOTES)
        self._tab_docs.setVisible(tab_key == TAB_KEY_DOCUMENTS)

        self._refresh_current_tab()

    def _refresh_current_tab(self):
        """刷新当前 Tab 的内容"""
        if self._current_tab == TAB_ENTRY_MEMORIES:
            self._load_entries()
        elif self._current_tab == TAB_PROJECT_NOTES:
            self._load_project_note()
        elif self._current_tab == TAB_KEY_DOCUMENTS:
            self._load_key_documents()

    # ==================== 条目记忆操作 ====================

    def _load_entries(self, query: str = ""):
        """加载条目记忆"""
        self.entries_list.clear()
        memory_mgr = self._get_memory_manager()
        if not memory_mgr:
            return

        entries = memory_mgr.get_entry_memories(query)
        for entry in entries:
            memory_id = entry.get("id", "")
            content = entry.get("content", "")
            enabled = entry.get("enabled", True)
            source = entry.get("source", "manual")

            item = QListWidgetItem()
            item.setSizeHint(self._get_entry_item_size())
            widget = EntryMemoryItemWidget(memory_id, content, enabled, source)
            widget.deleted.connect(self._delete_entry)
            widget.toggled.connect(self._toggle_entry)
            widget.edited.connect(self._edit_entry)
            self.entries_list.addItem(item)
            self.entries_list.setItemWidget(item, widget)

    def _get_entry_item_size(self):
        from PyQt5.QtCore import QSize
        width = self.entries_list.size().width()
        if width <= 0:
            width = 400
        return QSize(width, 50)

    def _on_search_changed(self, text: str):
        """搜索变化"""
        self._load_entries(text)

    def _add_entry(self):
        """添加条目"""
        content = self.entry_input.text().strip()
        if not content:
            return

        memory_mgr = self._get_memory_manager()
        if memory_mgr:
            memory_mgr.add_entry_memory(content)

        self.entry_input.clear()
        self._load_entries(self.search_edit.text())

    def _delete_entry(self, memory_id: str):
        """删除条目"""
        memory_mgr = self._get_memory_manager()
        if memory_mgr:
            memory_mgr.delete_entry_memory(memory_id)
        self._load_entries(self.search_edit.text())

    def _toggle_entry(self, memory_id: str, enabled: bool):
        """切换条目"""
        memory_mgr = self._get_memory_manager()
        if memory_mgr:
            memory_mgr.toggle_entry_memory(memory_id, enabled)

    def _edit_entry(self, memory_id: str, content: str):
        """编辑条目"""
        memory_mgr = self._get_memory_manager()
        if memory_mgr:
            memory_mgr.update_entry_memory(memory_id, content)

    # ==================== 项目笔记操作 ====================

    def _load_project_note(self):
        """加载项目笔记"""
        memory_mgr = self._get_memory_manager()
        if not memory_mgr:
            return

        self.project_name_label.setText(f"项目: {self._current_project}")
        note = memory_mgr.get_project_note(self._current_project)
        content = note.get("content", "") if note else ""
        self.notes_editor.setPlainText(content)

    def _save_project_note(self):
        """保存项目笔记"""
        memory_mgr = self._get_memory_manager()
        if memory_mgr:
            content = self.notes_editor.toPlainText()
            memory_mgr.save_project_note(self._current_project, content)
            self.projectNoteChanged.emit(self._current_project, content)

    # ==================== 关键文档操作 ====================

    def _load_key_documents(self):
        """加载关键文档"""
        self.docs_list.clear()
        memory_mgr = self._get_memory_manager()
        if not memory_mgr:
            return

        docs = memory_mgr.get_key_documents(self._current_project)
        for doc in docs:
            doc_id = doc.get("id", "")
            file_name = doc.get("file_name", "")
            file_path = doc.get("file_path", "")
            added_by = doc.get("added_by", "manual")

            item = QListWidgetItem()
            item.setSizeHint(self._get_doc_item_size())
            widget = KeyDocumentItemWidget(doc_id, file_name, file_path, added_by)
            widget.removed.connect(self._remove_key_document)
            widget.open_folder.connect(self._open_folder)
            self.docs_list.addItem(item)
            self.docs_list.setItemWidget(item, widget)

    def _get_doc_item_size(self):
        from PyQt5.QtCore import QSize
        width = self.docs_list.size().width()
        if width <= 0:
            width = 400
        return QSize(width, 44)

    def _on_files_dropped(self, file_paths: list):
        """处理文件拖拽/选择"""
        memory_mgr = self._get_memory_manager()
        if not memory_mgr:
            return

        for path in file_paths:
            memory_mgr.add_key_document(self._current_project, path, "manual")

        self._load_key_documents()

    def _remove_key_document(self, doc_id: str):
        """移除关键文档"""
        memory_mgr = self._get_memory_manager()
        if memory_mgr:
            memory_mgr.remove_key_document(doc_id)
        self._load_key_documents()

    def _open_folder(self, path: str):
        """打开文件或文件夹"""
        import subprocess
        import os
        try:
            # 优先判断路径类型
            if os.path.isdir(path):
                # 文件夹：直接打开
                os.startfile(path) if os.name == 'nt' else subprocess.Popen(['xdg-open', path])
            elif os.path.isfile(path):
                # 文件：直接打开
                os.startfile(path) if os.name == 'nt' else subprocess.Popen(['open', path])
            else:
                # 路径不存在，尝试打开父目录
                folder = os.path.dirname(path)
                if folder and os.path.exists(folder):
                    subprocess.Popen(['explorer', '/select,', path])
        except Exception as e:
            from loguru import logger
            logger.error(f"Failed to open: {e}")

    def refresh(self):
        """刷新所有数据"""
        self._refresh_current_tab()

    def refresh_from_db(self):
        """刷新所有数据（兼容旧接口）"""
        self._refresh_current_tab()