# -*- coding: utf-8 -*-
"""
全局唯一托盘图标管理器（单例）
所有 ToolPopupDialog 共享同一个 QSystemTrayIcon，避免多个托盘图标。
"""
from PyQt5.QtCore import QObject
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication
from loguru import logger


class TrayManager(QObject):
    """全局唯一托盘图标管理器，管理所有聊天窗口的托盘行为"""

    _instance = None

    @classmethod
    def get_instance(cls) -> "TrayManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        if TrayManager._instance is not None:
            raise RuntimeError("TrayManager 是单例，请使用 get_instance() 获取")
        TrayManager._instance = self

        self._windows: list = []  # 已注册的 ToolPopupDialog 列表

        # 创建托盘图标
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setIcon(QIcon(":/icons/drifox.ico"))
        self._tray_icon.setToolTip("Drifox")

        # 创建右键菜单
        tray_menu = QMenu()
        show_action = QAction("显示窗口", tray_menu)
        show_action.triggered.connect(self._show_all_windows)
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        quit_action = QAction("退出", tray_menu)
        quit_action.triggered.connect(self._quit_application)
        tray_menu.addAction(quit_action)

        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.show()

        logger.info("TrayManager 初始化完成")

    def register_window(self, window) -> None:
        """注册一个窗口到托盘管理器"""
        if window not in self._windows:
            self._windows.append(window)
            logger.debug(f"窗口已注册到 TrayManager: {window.windowTitle()}")

    def unregister_window(self, window) -> None:
        """窗口销毁时注销"""
        if window in self._windows:
            self._windows.remove(window)
            logger.debug(f"窗口已从 TrayManager 注销: {window.windowTitle()}")

    def notify(self, title: str, message: str) -> None:
        """发送 Windows 通知"""
        if self._tray_icon.isVisible():
            self._tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon(1), 4000)

    def _show_all_windows(self) -> None:
        """显示所有已注册的窗口"""
        for w in list(self._windows):
            try:
                w.show()
                if w.isMinimized():
                    w.showNormal()
                w.activateWindow()
            except RuntimeError:
                # 窗口已被 C++ 销毁，清理引用
                self._windows = [x for x in self._windows if x is not w]

    def _quit_application(self) -> None:
        """退出应用：关闭所有窗口后退出"""
        for w in list(self._windows):
            try:
                if hasattr(w, "_is_closing"):
                    w._is_closing = True
                w.close()
            except RuntimeError:
                pass
        self._windows.clear()
        QApplication.instance().quit()
