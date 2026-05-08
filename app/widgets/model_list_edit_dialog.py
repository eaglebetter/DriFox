# -*- coding: utf-8 -*-
"""
极简模型列表编辑器
Enter 新增，Delete 删除，双击编辑，拖拽排序
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
)


class ModelListEditDialog(QDialog):
    """极简模型列表编辑器"""

    def __init__(self, models: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑模型列表")
        self.setMinimumWidth(380)
        self.setMinimumHeight(320)
        self._init_ui(models)

    def _init_ui(self, models):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # 提示行
        hint_label = QPushButton("双击编辑 · Enter 新增 · Delete 删除 · 拖拽排序")
        hint_label.setCursor(Qt.ArrowCursor)
        hint_label.setFlat(True)
        hint_label.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #666;
                font-size: 11px;
                text-align: left;
                padding: 0;
            }
        """)
        layout.addWidget(hint_label)

        # 列表
        self.listWidget = QListWidget()
        # 关闭内置交替行颜色，完全用 stylesheet 控制
        self.listWidget.setAlternatingRowColors(False)
        self.listWidget.setDragDropMode(QListWidget.InternalMove)
        self.listWidget.setDefaultDropAction(Qt.MoveAction)
        self.listWidget.setSelectionBehavior(QListWidget.SelectRows)
        self.listWidget.setEditTriggers(
            QListWidget.DoubleClicked | QListWidget.EditKeyPressed
        )
        self.listWidget.itemDoubleClicked.connect(self._start_edit)
        self.listWidget.addItems(models)
        layout.addWidget(self.listWidget)

        # 底部按钮
        bottom = QHBoxLayout()
        bottom.addStretch()

        cancelBtn = QPushButton("取消")
        cancelBtn.setFlat(True)
        cancelBtn.setFixedSize(60, 28)
        cancelBtn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #555;
                border-radius: 4px;
                color: #aaa;
                font-size: 12px;
            }
            QPushButton:hover {
                border-color: #888;
                color: #fff;
            }
        """)
        cancelBtn.clicked.connect(self.reject)
        bottom.addWidget(cancelBtn)

        okBtn = QPushButton("确定")
        okBtn.setFlat(True)
        okBtn.setFixedSize(60, 28)
        okBtn.setStyleSheet("""
            QPushButton {
                background: #0078d4;
                border: none;
                border-radius: 4px;
                color: #fff;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #1a8ae5;
            }
        """)
        okBtn.clicked.connect(self.accept)
        bottom.addWidget(okBtn)

        layout.addLayout(bottom)

        # 所有视觉样式完全由 stylesheet 控制，无内置交替行
        self.listWidget.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                font-size: 13px;
                outline: none;
            }
            /* 奇数行 */
            QListWidget::item:nth-child(odd) {
                background-color: #252525;
            }
            /* 偶数行 */
            QListWidget::item:nth-child(even) {
                background-color: #2a2a2a;
            }
            /* 悬停 */
            QListWidget::item:hover {
                background-color: #333333;
            }
            /* 选中 */
            QListWidget::item:selected {
                background-color: #264f78;
                color: #ffffff;
            }
            /* 悬停 + 选中 */
            QListWidget::item:selected:hover {
                background-color: #365f8f;
            }
        """)

        self.listWidget.setFocus()

    def _start_edit(self, item):
        """双击开始编辑"""
        self.listWidget.editItem(item)

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()

        if key in (Qt.Key_Return, Qt.Key_Enter) and not mods:
            self._add_new()
            return

        if key == Qt.Key_Delete:
            self._delete_selected()
            return

        if key == Qt.Key_Escape:
            self.reject()
            return

        super().keyPressEvent(event)

    def _add_new(self):
        """添加新项并立即编辑"""
        item = QListWidgetItem("新模型")
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.listWidget.addItem(item)
        self.listWidget.setCurrentItem(item)
        self.listWidget.editItem(item)

    def _delete_selected(self):
        """删除选中项"""
        row = self.listWidget.currentRow()
        if row >= 0:
            self.listWidget.takeItem(row)

    def get_models(self):
        return [self.listWidget.item(i).text() for i in range(self.listWidget.count())]
