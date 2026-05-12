import os
import subprocess
import tempfile

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QApplication, QProgressDialog, QHBoxLayout
from qfluentwidgets import (
    InfoBar,
    InfoBarPosition,
    InfoBarIcon,
    PrimaryPushButton,
    MessageBox,
)

from app.utils.config import Settings
from app.utils.utils import AsyncUpdateChecker, DownloadThread


class UpdateChecker(QWidget):
    """优化后的更新检查器：保留 InfoBar 交互，适配 Inno Setup EXE"""
    finished = pyqtSignal(object)  # 供外部监听检查结果
    error = pyqtSignal(str)  # 供外部监听错误

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.cfg = Settings.get_instance()

        # --- 修复报错：初始化 AsyncUpdateChecker 依赖的属性 ---
        self.platform = self.cfg.patch_platform.value
        self.repo = self.cfg.github_repo.value
        self.token = self.cfg.github_token.value
        self.current_version = self.cfg.current_version
        # -----------------------------------------------

        self.progress_dialog = None
        self.download_thread = None
        self.installer_path = None

    def check_update(self):
        """检查更新入口"""
        self.async_checker = AsyncUpdateChecker(self)
        self.async_checker.finished.connect(self._on_check_finished)
        self.async_checker.error.connect(
            lambda msg: self.create_errorbar("检查更新失败", msg)
        )
        self.async_checker.start()

    def _forward_error(self, msg):
        """转发错误给外部监听者"""
        self.error.emit(msg)
        self.create_errorbar("检查更新失败", msg)

    def _on_check_finished(self, latest_release):
        """异步请求完成回调"""
        # 通知外部监听者
        self.finished.emit(latest_release)
        if latest_release:
            latest_version = latest_release.get("tag_name", "").lstrip("v")
            if self._compare_versions(latest_version, self.current_version) > 0:
                self._show_update_infobar(latest_release)
            else:
                # 仅在手动触发时提示“已是最新”
                pass

    def _show_update_infobar(self, latest_release):
        """保持原有的 InfoBar 交互方式，并增加查看详情按钮"""
        latest_version = latest_release.get("tag_name", "未知")
        update_notes = latest_release.get("body", "无更新说明")
        html_url = latest_release.get("html_url", "").strip()  # 获取发布页面URL

        info_bar = InfoBar(
            icon=InfoBarIcon.INFORMATION,
            title=f"发现新版本 {latest_version}",
            content=f"",
            orient=Qt.Vertical,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=-1,
            parent=self.parent or self,
        )

        # 创建按钮容器（水平布局）
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        from qfluentwidgets import PushButton  # 普通按钮用于次要操作

        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)
        button_layout.addStretch(1)  # 左侧弹性空间，使按钮右对齐

        # 立即更新按钮（主操作）
        update_button = PrimaryPushButton("立即更新")
        update_button.setFixedWidth(80)
        update_button.clicked.connect(
            lambda: self._on_update_confirmed(latest_release, info_bar)
        )

        # 查看详情按钮（次要操作）
        view_button = PushButton("查看详情")
        view_button.setFixedWidth(80)
        if html_url:
            view_button.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(html_url))
            )
        else:
            view_button.setEnabled(False)  # 无有效URL时禁用按钮

        # 添加按钮到容器
        button_layout.addWidget(update_button)
        button_layout.addWidget(view_button)

        # 将按钮容器添加到InfoBar布局
        info_bar.widgetLayout.addWidget(button_container, 0, Qt.AlignRight)

        info_bar.show()

    def _on_update_confirmed(self, latest_release, info_bar):
        """用户点击 InfoBar 上的按钮后触发"""
        info_bar.close()
        self._start_download(latest_release)

    def _start_download(self, latest_release):
        """根据平台寻找安装文件并下载"""
        import platform
        update_url = None
        exe_name = f"Update_{latest_release['tag_name']}.exe"

        # 获取当前系统平台
        system = platform.system().lower()

        # 遍历 Release 资产定位安装文件
        for asset in latest_release.get("assets", []):
            asset_name = asset["name"].lower()
            if system == "darwin" and asset_name.endswith(".dmg"):
                # macOS 下载 dmg
                update_url = asset["browser_download_url"]
                exe_name = asset["name"]
                break
            elif system == "windows" and asset_name.endswith(".exe"):
                # Windows 下载 exe
                update_url = asset["browser_download_url"]
                exe_name = asset["name"]
                break
            elif asset_name.endswith(".exe"):
                # 其他平台优先使用 exe
                update_url = asset["browser_download_url"]
                exe_name = asset["name"]
                break

        if not update_url:
            self.create_errorbar("未找到安装程序", "请前往 Release 手动下载")
            return

        # 下载到临时目录
        self.installer_path = os.path.join(tempfile.gettempdir(), exe_name)

        # 显示下载进度对话框
        self.progress_dialog = QProgressDialog(
            "正在下载新版本...", "取消", 0, 100, self.parent or self
        )
        self.progress_dialog.setWindowTitle("软件更新")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.canceled.connect(self._cancel_download)

        self.download_thread = DownloadThread(
            update_url, self.installer_path, self.token
        )
        self.download_thread.progress_signal.connect(self.progress_dialog.setValue)
        self.download_thread.finished_signal.connect(self._handle_download_finished)
        self.download_thread.error_signal.connect(self._handle_download_error)
        self.download_thread.start()

    def _handle_download_finished(self):
        """下载完成：不再执行解压和 BAT，直接运行 EXE"""
        if self.progress_dialog:
            self.progress_dialog.close()

        # 专业软件的最后确认：询问是否关闭程序并安装
        title = "下载完成"
        content = "安装包已准备就绪，是否立即关闭程序并升级？"
        msg_box = MessageBox(title, content, self.parent or self)
        msg_box.yesButton.setText(self.tr("现在安装"))
        msg_box.cancelButton.setText(self.tr("稍后手动安装"))

        if msg_box.exec():
            self._run_installer()

    def _run_installer(self):
        """启动 Inno Setup 安装向导"""
        try:
            subprocess.Popen(
                [self.installer_path],
                shell=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS,
            )

            # 立即关闭主程序
            QApplication.quit()
            os._exit(0)
        except Exception as e:
            self.create_errorbar("启动失败", str(e))

    def _cancel_download(self):
        if self.download_thread:
            self.download_thread.is_canceled = True
            self.download_thread = None

    def _handle_download_error(self, error_msg):
        if self.progress_dialog:
            self.progress_dialog.close()
        self.create_errorbar("下载失败", error_msg)

    def create_errorbar(self, title, content):
        InfoBar.error(
            title,
            content,
            position=InfoBarPosition.TOP_RIGHT,
            duration=5000,
            parent=self.parent or self,
        )

    def _compare_versions(self, v1, v2):
        """
        改进的版本比对：支持 v0.3.5 > v0.3.5-beta
        规则：如果数字部分相同，有后缀的（预发布版）小于无后缀的（正式版）
        """
        import re

        def split_version(v):
            # 提取前面的数字部分和后面的后缀部分
            # 如 "0.3.5-beta" -> ([0, 3, 5], "-beta")
            match = re.match(r"^v?([\d.]+)(.*)", v.strip().lower())
            if not match:
                return [], ""
            nums = [int(x) for x in match.group(1).split(".") if x]
            suffix = match.group(2)
            return nums, suffix

        try:
            p1_nums, p1_suffix = split_version(v1)
            p2_nums, p2_suffix = split_version(v2)

            # 1. 首先比较数字部分 [0, 3, 5]
            if p1_nums != p2_nums:
                return (p1_nums > p2_nums) - (p1_nums < p2_nums)

            # 2. 如果数字相同，检查后缀
            # 原则：无后缀 > 有后缀 (正式版 > 预览版)
            if not p1_suffix and p2_suffix:
                return 1
            if p1_suffix and not p2_suffix:
                return -1

            # 3. 如果都有后缀，按字母序比较 (如 beta < rc)
            return (p1_suffix > p2_suffix) - (p1_suffix < p2_suffix)

        except Exception:
            # 后备方案：纯字符串比较
            return (v1 > v2) - (v1 < v2)
