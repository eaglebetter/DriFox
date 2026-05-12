# -*- coding: utf-8 -*-
import asyncio

import httpx
import orjson as json
import os
import re
import socket
import sys
from pathlib import Path

import psutil
import requests
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont

from app.utils.config import Settings

try:
    from pypinyin import pinyin, Style
except ImportError:
    pinyin = None

from app.utils.icon_name_map import ICON_NAME_TO_FILE

# ANSI 颜色代码映射
ANSI_COLOR_MAP = {
    "30": "#000000",  # 黑色
    "31": "#ff0000",  # 红色
    "32": "#00ff00",  # 绿色
    "33": "#ffff00",  # 黄色
    "34": "#0000ff",  # 蓝色
    "35": "#ff00ff",  # 紫色
    "36": "#00ffff",  # 青色
    "37": "#ffffff",  # 白色
    "90": "#808080",  # 亮黑
    "91": "#ff5555",  # 亮红
    "92": "#50fa7b",  # 亮绿
    "93": "#f1fa8c",  # 亮黄
    "94": "#8be9fd",  # 亮蓝
    "95": "#ff79c6",  # 亮紫
    "96": "#8be9fd",  # 亮青
    "97": "#ffffff",  # 亮白
}
_ICON_CACHE = {}  # 缓存图标名 → QIcon 实例


def get_app_data_dir() -> Path:
    """获取应用数据目录（跨平台兼容）
    
    开发环境: 当前目录/.drifox
    PyInstaller打包: 应用支持目录/.drifox（可写）
    macOS .app: ~/Library/Application Support/Drifox/.drifox
    """
    # 开发环境
    if not hasattr(sys, '_MEIPASS') and not getattr(sys, 'frozen', False):
        return Path('.drifox')
    
    # macOS .app: 使用 Application Support（用户可写）
    if sys.platform == 'darwin':
        from AppKit import NSApplicationSupportDirectory, NSUserDomainMask, NSFileManager
        paths = NSFileManager.defaultManager().URLsForDirectory_inDomains_(
            NSApplicationSupportDirectory, NSUserDomainMask
        )
        if paths:
            # paths[0].path 是 ObjC native-selector，用 fileSystemRepresentation() 转 bytes 再解码
            app_support_path = paths[0].fileSystemRepresentation().decode('utf-8')
            app_support = Path(app_support_path) / 'Drifox'
            app_support.mkdir(parents=True, exist_ok=True)
            return app_support / '.drifox'
    
    # Windows/Linux 或其他平台
    if hasattr(sys, '_MEIPASS'):
        # 使用 MEIPASS 的同级的可写目录
        return Path(sys._MEIPASS).parent / '.drifox'
    
    # Fallback
    return Path.home() / '.drifox'

def get_pinyin_search_keys(text):
    """生成拼音全拼和首字母缩写"""
    if not pinyin or not text:
        return ""
    # 提取首字母 (Style.FIRST_LETTER)
    first_letters = "".join([i[0][0] for i in pinyin(text, style=Style.FIRST_LETTER)])
    # 提取全拼 (Style.NORMAL)
    full_pinyin = "".join([i[0] for i in pinyin(text, style=Style.NORMAL)])
    return f"{first_letters} {full_pinyin} {text}".lower()


def kill_proc_tree(pid):
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        parent.kill()
        psutil.wait_procs(children + [parent], timeout=5)
    except psutil.NoSuchProcess:
        pass


# 预编译 ANSI 处理正则表达式
_ANSI_CURSOR_PATTERN = re.compile(r"\x1b\[[0-9;]*[ABCDHfJKmnsu]")
_ANSI_COLOR_PATTERN = re.compile(r"\x1b\[([0-9;]*)m")
_ANSI_RESET_PATTERN = re.compile(r"\x1b\[0m")
_ANSI_REMAINS_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def ansi_to_html(text):
    """
    将 ANSI 颜色代码转换为 HTML span 标签
    """
    if not text:
        return ""

    # 移除光标控制序列（如 \x1b[2K）
    text = _ANSI_CURSOR_PATTERN.sub("", text)

    # 处理颜色代码
    def replace_ansi(match):
        codes = match.group(1).split(";")
        color = None
        bold = False

        for code in codes:
            if code in ANSI_COLOR_MAP:
                color = ANSI_COLOR_MAP[code]
            elif code == "1":
                bold = True

        if color:
            style = f"color: {color};"
            if bold:
                style += " font-weight: bold;"
            return f'<span style="{style}">'
        elif bold:
            return '<span style="font-weight: bold;">'
        else:
            return "<span>"

    # 替换 ANSI 开始序列 \x1b[...m
    text = _ANSI_COLOR_PATTERN.sub(replace_ansi, text)

    # 替换 ANSI 结束序列 \x1b[0m 为 </span>
    text = _ANSI_RESET_PATTERN.sub("</span>", text)

    # 处理剩余的 ANSI 序列（清理）
    text = _ANSI_REMAINS_PATTERN.sub("", text)

    # 转换换行符
    text = text.replace("\n", "<br>")

    return text


def ansi_to_rich_text(text):
    """
    将 ANSI 转换为 Qt Rich Text（备用方案）
    """
    return f"<pre style='font-family: Consolas, monospace;'>{ansi_to_html(text)}</pre>"


def resource_path(relative_path) -> str:
    """获取打包后资源文件的绝对路径"""
    if hasattr(sys, "_MEIPASS"):
        # 如果是打包后的环境
        base_path = sys._MEIPASS
    else:
        # 开发环境，直接使用当前路径
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def get_port_node(port):
    """安全获取端口所属节点，兼容 property 和 method"""
    node = port.node
    return node() if callable(node) else node


def get_icon(icon_name: str) -> QIcon:
    """
    从 Qt 资源系统加载图标（高性能、无磁盘 I/O）

    Args:
        icon_name: 图标名（不含扩展名），如 "copy"

    Returns:
        QIcon 实例
    """
    if icon_name in _ICON_CACHE:
        return _ICON_CACHE[icon_name]

    # 1. 从映射表中找真实文件名
    filename = ICON_NAME_TO_FILE.get(icon_name)
    if filename:
        resource_path = f":/icons/{filename}"
        icon = QIcon(resource_path)
        # 可选：再做一次 null 检查（虽然理论上不会错）
        if not icon.isNull():
            _ICON_CACHE[icon_name] = icon
            return icon

    # 2. fallback 到 FluentIcon
    try:
        from qfluentwidgets import FluentIcon

        icon = FluentIcon.APPLICATION.icon()
        _ICON_CACHE[icon_name] = icon
        return icon
    except Exception:
        pass

    # 3. 最终 fallback
    return QIcon()


def get_canvas_font(size=10, bold=False):
    try:
        font_family = Settings.get_instance().llm_font_family.value
    except Exception:
        try:
            font_family = Settings.get_instance().canvas_font_selected.value
        except Exception:
            font_family = "Segoe UI"

    font = QFont(font_family, size)
    if bold:
        font.setBold(True)
    return font


def get_unified_font(size=10, bold=False):
    """Get font with unified font family configured by user"""
    try:
        font_family = Settings.get_instance().llm_font_family.value
    except Exception:
        try:
            font_family = Settings.get_instance().canvas_font_selected.value
        except Exception:
            font_family = "Segoe UI"
    font = QFont(font_family, size)
    if bold:
        font.setBold(True)
    return font


def get_font_family_css() -> str:
    """获取 CSS font-family 字符串，用于 stylesheet 中保持字体统一"""
    try:
        font_family = Settings.get_instance().llm_font_family.value
    except Exception:
        try:
            font_family = Settings.get_instance().canvas_font_selected.value
        except Exception:
            font_family = "Segoe UI"
    return f"font-family: '{font_family}';"


def str_to_bool(value):
    """可靠的布尔值转换"""
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes", "on")


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def serialize_for_json(obj, large_list_threshold=1000):
    """递归将对象转换为 JSON 可序列化格式"""
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif hasattr(obj, "serialize") and callable(getattr(obj, "serialize")):
        try:
            return obj.serialize()
        except:
            return str(obj)
    else:
        # 其他类型：尝试转为字符串
        try:
            json.dumps(obj)  # 测试是否可序列化
            return obj
        except (TypeError, ValueError):
            return None


def deserialize_from_json(obj):
    if isinstance(obj, dict):
        return {k: deserialize_from_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deserialize_from_json(v) for v in obj]
    else:
        return obj


class DownloadThread(QThread):
    progress_signal = pyqtSignal(int)  # 进度信号
    finished_signal = pyqtSignal(str)  # 完成信号（返回文件路径）
    error_signal = pyqtSignal(str)  # 错误信号
    canceled_signal = pyqtSignal()  # 取消信号（新增）

    def __init__(self, url, file_path, token):
        super().__init__()
        self.url = url
        self.file_path = file_path
        self.headers = {"Authorization": token} if token else {}
        self.is_canceled = False  # 取消标志位
        self.session = requests.Session()  # 使用 Session 以便关闭连接

    def run(self):
        try:
            response = self.session.get(self.url, headers=self.headers, stream=True, timeout=10)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(self.file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if self.is_canceled:  # 每次读取前检查取消标志
                        f.close()
                        os.remove(self.file_path)  # 删除不完整文件
                        self.canceled_signal.emit()
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            self.progress_signal.emit(progress)

            self.finished_signal.emit(self.file_path)
        except Exception as e:
            if not self.is_canceled:  # 非取消情况才触发错误信号
                self.error_signal.emit(str(e))
        finally:
            self.session.close()  # 确保释放网络资源


class AsyncUpdateChecker(QThread):
    finished = pyqtSignal(object)  # 返回 latest_release 或 None
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.repo = parent.repo
        self.platform = parent.platform
        self.token = parent.token

    async def fetch_github(self):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        headers = headers | {"Authorization": f"token {self.token}"} if self.token else headers
        url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                print("GitHub API 响应:", resp.json())
                return resp.json()
            else:
                print("GitHub API 响应:", resp.text)
                self.error.emit(f"GitHub API 请求失败：{resp.status_code}")
                return None

    async def fetch_gitee(self):
        headers = {"Authorization": self.token} if self.token else {}
        url = f"https://gitee.com/api/v5/repos/{self.repo}/releases/latest"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            else:
                self.error.emit(f"Gitee API 请求失败：{resp.status_code}")
                return None

    async def fetch_gitcode(self):
        headers = {"Authorization": self.token} if self.token else {}
        url = f"https://gitcode.com/api/v5/repos/{self.repo}/releases/latest"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            else:
                self.error.emit(f"Gitcode API 请求失败：{resp.status_code}")
                return None

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            if self.platform == "github":
                result = loop.run_until_complete(self.fetch_github())
            elif self.platform == "gitee":
                result = loop.run_until_complete(self.fetch_gitee())
            elif self.platform == "gitcode":
                result = loop.run_until_complete(self.fetch_gitcode())
            else:
                result = None
                self.error.emit("不支持的平台")
        except Exception as e:
            self.error.emit(str(e))
            result = None
        finally:
            self.finished.emit(result)
