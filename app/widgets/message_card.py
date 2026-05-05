# -*- coding: utf-8 -*-
import base64
import hashlib
import json
import math
import re
import urllib.parse
from functools import lru_cache
from datetime import datetime
from html import escape
from typing import List, Dict, Any, Optional

from loguru import logger

from PyQt5.QtCore import (
    Qt,
    QTimer,
    QTimerEvent,
    pyqtSignal,
    QUrl,
    QVariantAnimation,
    QEasingCurve,
)
from PyQt5.QtGui import (
    QWheelEvent,
    QPainter,
    QPen,
    QColor,
    QBrush,
    QLinearGradient,
    QPainterPath,
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QSizePolicy,
    QTextEdit,
)
from markdown import Markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer
from qfluentwidgets import (
    FluentIcon,
    ToolTipFilter,
    TransparentToolButton,
)
from qfluentwidgets.components.widgets.card_widget import (
    CardSeparator,
    SimpleCardWidget,
)

from app.utils.message_content import (
    append_text_block,
    content_to_markdown,
    content_to_text,
    ensure_content_blocks, make_tool_result_block,
)
from app.widgets.render_helpers import (
    render_tool_block,
)
from app.utils.utils import get_font_family_css, get_icon

# ======== Markdown 实例 ========
_md_instance = None
ACTION_COLOR_MAP = {
    "jump": "#FFA500",
    "create": "#9370DB",
    "generate": "#32CD32",
    "ask": "#FF6347",
    "view": "#4169E1",
}
DEFAULT_COLOR = "#888888"

# ======== 预编译的正则表达式（提升到模块级别，避免重复编译）=======
_CODE_BLOCK_PATTERN = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_CODE_BLOCK_WITH_LANG_PATTERN = re.compile(r"<pre><code(?:\s+class=\"([^\"]*)\")?>(.*?)</code></pre>", re.DOTALL)
_CONTEXT_LINK_PATTERN = re.compile(r"`*\[([^\[\]]+?)\]\(([^)\s]+)\)`*")
_CODE_BLOCK_CODE_PATTERN = re.compile(r"```[\w]*\n")
_CODE_BLOCK_END_PATTERN = re.compile(r"```\n")
_CODE_BLOCK_FINAL_PATTERN = re.compile(r"```")


def get_markdown_instance():
    global _md_instance
    if _md_instance is None:
        _md_instance = Markdown(
            extensions=["fenced_code", "nl2br", "tables"],
            output_format="html5",
            safe=False,
        )
    return _md_instance


def _unwrap_code_blocks_with_context_links(md_text: str) -> str:
    def replacer(match):
        lang_part = match.group(1) or ""
        code_content = match.group(2)
        if re.search(r"\[[^\[\]]+\]\([^)\s]+\)", code_content) and lang_part not in (
                "python"
        ):
            return code_content
        else:
            return (
                f"```{lang_part}\n{code_content}```"
                if lang_part
                else f"```\n{code_content}```"
            )

    return _CODE_BLOCK_PATTERN.sub(replacer, md_text)


def _strip_code_blocks(text: str) -> str:
    """
    移除 markdown 代码块标记和代码内容。
    思考框内不需要代码编辑框，直接显示纯文本。
    """
    # 匹配完整的代码块，包括内容
    text = re.sub(r"```[\s\S]*?```", "", text)
    # 移除剩余的反引号
    text = text.replace("`", "")
    # 将换行符替换为空格，让内容自然填充，避免多余空行
    text = text.replace("\r\n", " ").replace("\n", " ")
    # 合并多余空格
    text = re.sub(r" +", " ", text)
    return text.strip()


# ======== 核心逻辑：保留你的原始代码块样式 ========
def _wrap_code_blocks_with_copy_button_web(html: str) -> str:
    def replacer(match):
        lang = (match.group(1) or "").replace("language-", "").strip()
        code_content_raw = match.group(2) or ""
        # --- 优化后的代码块逻辑 ---
        try:
            copy_text = (
                code_content_raw.replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&amp;", "&")
                .replace("&#39;", "'")
                .replace("&quot;", '"')
            )
        except:
            copy_text = code_content_raw

        b64_copy = base64.b64encode(copy_text.encode("utf-8")).decode("ascii")

        lines = copy_text.splitlines() or [""]
        line_count = len(lines)

        # 高亮代码（获取 <pre> 内部 HTML）
        try:
            lexer = get_lexer_by_name(lang, stripall=False) if lang else TextLexer()
            formatter = HtmlFormatter(
                style="dracula",
                linenos=False,
                noclasses=True,
                cssclass="code-block",
                prestyles="margin:0; padding:0; background:transparent; font-family: Consolas, monospace; font-size:13px; color:#D4D4D4;",
            )
            highlighted = highlight(copy_text, lexer, formatter)
            # 提取 <pre> 内部内容
            pre_match = re.search(r"<pre[^>]*>(.*?)</pre>", highlighted, re.DOTALL)
            if pre_match:
                inner_code_html = pre_match.group(1)
            else:
                inner_code_html = escape(copy_text)
        except Exception:
            inner_code_html = escape(copy_text)

        # 生成行号（纯文本，每行一个数字）
        line_numbers_text = "\n".join(str(i + 1) for i in range(line_count))

        # 构建新的代码容器（行号固定 + 代码可横向滚动）
        code_block_html = f"""
        <div class="code-container">
            <div class="line-numbers">{escape(line_numbers_text)}</div>
            <div class="code-content">
                <pre>{inner_code_html}</pre>
            </div>
        </div>
        """

        return f'''
        <div style="
            position: relative;
            margin: 12px 0;
            background: rgba(30, 32, 40, 0.20);
            border: 1px solid rgba(58, 63, 71, 0.6);
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.18), 0 1px 3px rgba(0,0,0,0.2);
            backdrop-filter: blur(8px);
            font-family: Consolas, monospace;
            font-size: 13px;
        ">
            <!-- 顶部工具栏区域 -->
            <div style="
                display: flex; justify-content: space-between; align-items: center;
                padding: 6px 10px; height: 30px; background: rgba(28, 28, 36, 0.18);
                border-bottom: 1px solid rgba(45, 45, 57, 0.5); border-radius: 10px 10px 0 0;
            ">
                {f'<span style="color: #FFA500; font-size: 13px; font-weight: bold;">{lang}</span>' if lang else '<span style="color: #888;">Plain Text</span>'}
                <div style="display: flex; gap: 12px; align-items: center; padding-right: 4px;">
                    <button type="button" data-action="save_file" data-lang="{lang}" data-copy="{b64_copy}" class="code-btn" data-tooltip="保存本地文件" style="width: 30px; height: 30px; background: transparent; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 0; border-radius: 6px;">
                        <img src="qrc:/icons/导入.svg" style="width:22px; height:22px; pointer-events: none;" />
                    </button>
                    <button type="button" data-action="copy" data-copy="{b64_copy}" class="code-btn" data-tooltip="复制代码" style="width: 30px; height: 30px; background: transparent; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 0; border-radius: 6px;">
                        <img src="qrc:/icons/复制.svg" style="width:22px; height:22px; pointer-events: none;" />
                    </button>
                </div>
            </div>
            <!-- 可横向滚动的代码区域 -->
            <div style="
                padding: 8px 0 0 0;
                border-radius: 0 0 10px 10px;
            ">
                {code_block_html}
            </div>
        </div>
        '''

    return _CODE_BLOCK_WITH_LANG_PATTERN.sub(replacer, html)


def _sanitize_incomplete_markdown(md_text: str) -> str:
    if not md_text:
        return ""
    # 只处理 markdown 代码块的不完整情况
    # 不再删除尾随的 <，因为它可能是 HTML/工具标签的一部分
    if md_text.count("```") % 2 == 1:
        md_text += "\n```"
    return md_text


def _render_think_block(content: str, completed: bool = True) -> str:
    status_text = "💡 思考过程" if completed else "🧠 正在思考..."
    expanded = not completed

    max_preview = 40
    content_preview = content.strip().replace("\n", " ")[:max_preview]
    if len(content.strip().replace("\n", " ")) > max_preview:
        content_preview += "..."

    block_seed = f"{content}|{completed}"
    block_key = "think-" + hashlib.sha1(block_seed.encode("utf-8")).hexdigest()[:12]
    expanded_attr = "true" if expanded else "false"
    body_style = ' style="height:auto; opacity:1;"' if expanded else ""

    # 思考内容不需要渲染代码编辑框，移除代码块标记
    content = _strip_code_blocks(content)
    content = escape(content)

    return f"""<div class="cm-collapsible think-block" data-block-key="{block_key}" data-expanded="{expanded_attr}">
    <button type="button" class="cm-collapsible__summary think-block__summary" aria-expanded="{expanded_attr}">
        <span class="cm-collapsible__chevron" aria-hidden="true"></span>
        <span style="white-space: nowrap;">{status_text}</span>
        <span style="color: #666; font-size: 11px; font-weight: normal; margin-left: auto;">{escape(content_preview)}</span>
    </button>
    <div class="cm-collapsible__body"{body_style}>
        <div class="think-content loading" style="white-space: normal; word-break: break-word; line-height: 1.6;">{content}</div>
    </div>
</div>"""


def _inject_think_cards(md_text: str, completed: bool = True) -> str:
    """注入思考框HTML。

    关键逻辑：<think> 匹配到下一个 <think> 之前的最后一个 </think>，
    避免流式输出时多个 </think> 导致内容泄露。
    """
    parts = []
    i = 0
    while i < len(md_text):
        start_idx = md_text.find("<think>", i)
        if start_idx == -1:
            parts.append(md_text[i:])
            break
        parts.append(md_text[i:start_idx])

        think_start = start_idx + len("<think>")

        # 确定搜索边界：到下一个 <think> 或文本结尾
        next_think = md_text.find("<think>", think_start)
        search_end = next_think if next_think != -1 else len(md_text)

        # 在边界内查找最后一个 </think>（处理多个 </think> 的情况）
        end_idx = md_text.rfind("</think>", think_start, search_end)

        if end_idx != -1:
            content = md_text[think_start:end_idx]
            parts.append(_render_think_block(content, completed=True))
            i = end_idx + len("</think>")
        else:
            # 未闭合：内容截取到边界处，避免吞掉后续 <think>
            content = md_text[think_start:search_end]
            parts.append(_render_think_block(content, completed=False))
            i = search_end
    return "".join(parts)


def _render_tool_block_content(content: str) -> str:
    """
    渲染工具块内容为HTML。

    解析格式：
    <tool>
    name: xxx
    args: {JSON}  <- 可能跨行，需要正确处理嵌套 JSON
    result: xxx   <- 可能跨行
    success: true
    tool_call_id: xxx
    </tool>
    """
    from loguru import logger
    
    tool_name = ""
    tool_args_str = ""
    tool_result = ""
    tool_success = True
    tool_call_id = None

    content = content.strip()

    # ========== 解析 name ==========
    name_match = re.search(r"^name:\s*(.+?)\s*$", content, re.MULTILINE)
    if name_match:
        tool_name = name_match.group(1).strip()

    # ========== 解析 args（需要正确处理嵌套 JSON）==========
    args_start = content.find("args:")
    result_search_start = 0  # 默认值
    tool_args_str = ""
    
    if args_start != -1:
        brace_start = content.find("{", args_start)
        if brace_start != -1:
            depth = 0
            i = brace_start
            while i < len(content):
                c = content[i]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        tool_args_str = content[brace_start:i + 1]
                        result_search_start = i + 1
                        break
                i += 1
            if depth != 0:  # 循环结束但没找到匹配的 }
                # JSON 未正确闭合，回退到单行解析
                tool_args_str = ""
                # 尝试找到 args: 后的内容作为替代
                line_match = re.search(r"args:\s*(\{[^}]*\})", content)
                if line_match:
                    tool_args_str = line_match.group(1)
                    result_search_start = args_start + len(line_match.group(0))
        else:
            line = content[args_start:].split("\n")[0]
            tool_args_str = line[args_start + 5:].strip()
            result_search_start = args_start + len(line)

    # ========== 解析 success ==========
    success_match = re.search(r"^success:\s*(.+?)\s*$", content, re.MULTILINE)
    if success_match:
        tool_success = success_match.group(1).strip().lower() == "true"

    # ========== 解析 tool_call_id ==========
    id_match = re.search(r"^tool_call_id:\s*(.+?)\s*$", content, re.MULTILINE)
    if id_match:
        tool_call_id = id_match.group(1).strip()

    # ========== 解析 result ==========
    result_line_match = re.search(r"^result:\s*(.*)$", content[result_search_start:], re.MULTILINE)
    if result_line_match:
        result_content = result_line_match.group(1)
        remaining = content[result_search_start + result_line_match.end():]
        next_field_match = re.search(r"\n\w+:", remaining)
        if next_field_match:
            tool_result = (result_content + remaining[:next_field_match.start()]).strip()
        else:
            tool_result = result_content.strip()

    # ========== 解析 args JSON 为字典 ==========
    args_dict = {}
    if tool_args_str:
        try:
            args_dict = json.loads(tool_args_str)
            if not isinstance(args_dict, dict):
                args_dict = {}
        except json.JSONDecodeError:
            # JSON 解析失败，尝试使用正则提取参数
            args_dict = _extract_args_by_regex(tool_args_str)
    else:
        # 没有 args，尝试从整个 content 中提取参数
        args_dict = _extract_args_by_regex(content)

    return render_tool_block(
        tool_name, args_dict, tool_result, tool_success, collapsed=True,
        tool_call_id=tool_call_id
    )


def _extract_args_by_regex(content: str) -> dict:
    """
    当 JSON 解析失败时，使用正则表达式提取参数。
    处理包含大量转义字符和被截断的字符串的情况。
    """
    args = {}
    
    # 提取常见的字符串参数
    string_params = ["path", "oldString", "newString", "command", "url", "pattern", "query", "name"]
    
    for param in string_params:
        # 查找 "param": " 后面开始的位置
        pattern = rf'"{param}"\s*:\s*"'
        match = re.search(pattern, content)
        if match:
            start = match.end()
            # 从 start 开始，找到第一个未转义的引号 "
            i = start
            while i < len(content):
                if content[i] == '"':
                    # 找到结束引号
                    value = content[start:i]
                    # 清理截断标记
                    value = value.replace('\n... [内容已截断]', '').replace('... [内容已截断]', '')
                    # 解码转义字符
                    try:
                        args[param] = value.encode().decode('unicode_escape')
                    except:
                        args[param] = value
                    break
                elif content[i] == '\\':
                    # 转义字符，跳过下一个字符
                    i += 2
                else:
                    i += 1
    
    return args


def _inject_tool_blocks(md_text: str, completed: bool = True) -> str:
    """注入工具块HTML，类似think块"""
    if not md_text:
        return md_text

    parts = []
    i = 0
    while i < len(md_text):
        start_idx = md_text.find("<tool>", i)
        if start_idx == -1:
            parts.append(md_text[i:])
            break
        parts.append(md_text[i:start_idx])
        end_idx = md_text.find("</tool>", start_idx + len("<tool>"))
        if end_idx != -1:
            content = md_text[start_idx + len("<tool>"): end_idx]
            parts.append(_render_tool_block_content(content))
            i = end_idx + len("</tool>")
        else:
            parts.append(md_text[start_idx:])
            break
    return "".join(parts)


@lru_cache(maxsize=256)
def _render_markdown_to_html_cached(raw_md: str, reasoning: str) -> str:
    if reasoning:
        raw_md = _render_think_block(reasoning, completed=True) + raw_md

    safe_md = _sanitize_incomplete_markdown(raw_md)
    safe_md = _unwrap_code_blocks_with_context_links(safe_md)
    safe_md = _inject_context_links(safe_md)
    processed_md = _inject_think_cards(safe_md, True)
    processed_md = _inject_tool_blocks(processed_md, True)

    try:
        md = get_markdown_instance()
        md.reset()
        html_content = md.convert(processed_md)
        return _wrap_code_blocks_with_copy_button_web(html_content)
    except Exception:
        return f"<pre>{escape(raw_md)}</pre>"


# ======== 欢迎卡片随机 Tips ========
WELCOME_TIPS = [
    # ===== 文件与输入 =====
    "💡 拖拽文件到输入框即可快速分析",
    "💡 Shift+Enter 换行，Enter 发送消息",
    "💡 按 ↑/↓ 键可浏览历史输入记录",

    # ===== 会话管理 =====
    "💡 Ctrl+N 快速新建对话，Ctrl+L 清空当前会话",
    "💡 历史会话自动保存，关闭窗口也不丢失",
    "💡 长对话会自动启用「上下文压缩」优化 Token",

    # ===== 模型与参数 =====
    "💡 点击模型名称可快速切换大模型",
    "💡 模型参数影响回复风格（温度/最大Token），多试试找到你的风格",
    "💡 不同智能体擅长不同任务：Plan 规划、Build 构建、Explore 探索",

    # ===== 技能系统 =====
    "💡 输入 @ 可快速选择技能，触发 AI 专项能力",
    "💡 @brainstorming 集思广益，@writing-plans 制定计划",
    "💡 @git-commit 自动分析改动生成规范提交信息",
    "💡 @skill-creator 创建新的自定义技能扩展",
    "💡 @minimax-image-understanding 分析图片内容",

    # ===== 代码与文件 =====
    "💡 代码块右上角有复制和保存按钮，点击即可",
    "💡 工具执行结果可点击「查看差异」对比文件修改",
    "💡 工具悬浮框会显示正在执行的工具，点击可查看详情",

    # ===== 窗口与布局 =====
    "💡 右上角「新建窗口」按钮可创建并发会话，多任务同时进行",
    "💡 右上角「分支」按钮可复制当前会话到新窗口",
    "💡 右下角可展开历史会话卡片，点击继续历史对话",

    # ===== 高级功能 =====
    "💡 记忆管理让 AI 更懂你的偏好和习惯",
    "💡 点击上下文指示器可查看 Token 使用详情",
    "💡 子智能体可协助处理复杂任务，观察其工作过程",
]

# ======== 欢迎卡片欢迎语 ========
WELCOME_GREETINGS = [
    "你好！我是 Drifox 飘狐 🦊",
    "嗨！有什么我可以帮你的吗？",
    "欢迎回来！今天想聊点什么？",
    "你好！随时可以问我问题或让我帮忙处理任务",
    "嗨！准备好一起探索了吗？",
    "欢迎！需要帮忙分析什么吗？",
    "你好！可以帮你总结、分析、生成内容哦！",
    "Drifox 为你准备了最近的会话记录，点击即可继续之前的对话 👇",
    "欢迎使用 Drifox 飘狐！我是你的智能助手 🚀",
    "嗨！我是你的 AI 搭档，有问题尽管问 🤖",
]


def get_random_tip() -> str:
    """获取随机 Tips"""
    import random
    return random.choice(WELCOME_TIPS)


def get_random_greeting() -> str:
    """获取随机欢迎语"""
    import random
    return random.choice(WELCOME_GREETINGS)


_CONTEXT_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((ask|jump|create|generate|view|session)(?:\|([^)]*))?\)")


def _inject_context_links(md_text: str) -> str:
    """将 [文本](ask/jump/create/generate/view/session) 转换为胶囊样式的追问标签

    session 类型格式：[文本](session|session_id|last_time)
    last_time 如果为空则不显示
    """

    def replacer(match):
        content = match.group(1)
        action = match.group(2)
        extra = match.group(3) or ""

        if action == "session":
            # session 格式：session_id|last_time
            parts = extra.split("|")
            session_id = parts[0].strip() if parts else ""
            last_time = parts[1].strip() if len(parts) > 1 else ""

            # 如果有 last_time，追加显示
            if last_time:
                display_content = f'{content}<span class="session-time">{last_time}</span>'
            else:
                display_content = content

            attrs = f'data-type="session" data-session-id="{escape(session_id)}" data-action="session"'
            if last_time:
                attrs += f' data-last-time="{escape(last_time)}"'
            return f'<span class="context-tag session-tag" {attrs}>{display_content}</span>'

        return f'<span class="context-tag" data-type="{action}" data-content="{escape(content)}" data-action="{action}">{content}</span>'

    return _CONTEXT_LINK_PATTERN.sub(replacer, md_text)


# ======== WebViewer ========
class ConsoleMonitorPage(QWebEnginePage):
    codeActionRequested = pyqtSignal(str, str)
    contextActionRequested = pyqtSignal(str, str)
    heightReported = pyqtSignal(int)
    contentReady = pyqtSignal()
    toolDiffRequested = pyqtSignal(str)  # tool_call_id
    subAgentLogRequested = pyqtSignal(str)  # task_ids (comma-separated)
    saveFileRequested = pyqtSignal(str, str)  # code, lang

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        msg = message.strip()
        if msg == "pywebview_ready":
            self.contentReady.emit()
        elif msg.startswith("pywebview_height:"):
            try:
                self.heightReported.emit(int(float(msg.split(":")[1])))
            except:
                pass
        elif msg.startswith("pywebview_action:"):
            if "context|||" in msg:
                try:
                    parts = msg.split("|||")
                    self.contextActionRequested.emit(
                        urllib.parse.unquote(parts[1]), urllib.parse.unquote(parts[2])
                    )
                except:
                    pass
            elif "context_lost" in msg:
                self._handle_context_lost()
            elif "open_url:" in msg:
                try:
                    url_str = msg.split("open_url:", 1)[1]
                    from PyQt5.QtGui import QDesktopServices
                    from PyQt5.QtCore import QUrl

                    QDesktopServices.openUrl(QUrl(url_str))
                except:
                    pass
            elif "tool_diff:" in msg:
                # 处理工具差异对比请求
                try:
                    tool_call_id = msg.split("tool_diff:", 1)[1]
                    self.toolDiffRequested.emit(tool_call_id)
                except Exception:
                    pass
            elif "subagent_log:" in msg:
                # 处理子智能体日志查看请求
                try:
                    task_ids = msg.split("subagent_log:", 1)[1]
                    self.subAgentLogRequested.emit(task_ids)
                except Exception:
                    pass
            elif "save_file:" in msg:
                # 处理保存文件请求
                try:
                    parts = msg.split("save_file:", 1)[1]
                    # 格式: b64_code:lang
                    sub_parts = parts.rsplit(":", 1)
                    if len(sub_parts) == 2:
                        b64_code, lang = sub_parts
                        code = base64.b64decode(b64_code).decode("utf-8")
                        self.saveFileRequested.emit(code, lang)
                except Exception:
                    pass
            else:
                try:
                    p = msg.split(":")
                    self.codeActionRequested.emit(
                        base64.b64decode(p[2]).decode("utf-8"), p[1]
                    )
                except:
                    pass

    def _handle_context_lost(self):
        self.contentReady.emit()


class CodeWebViewer(QWebEngineView):
    contentHeightChanged = pyqtSignal(int)
    codeActionRequested = pyqtSignal(str, str)
    contextActionRequested = pyqtSignal(str, str)
    toolDiffRequested = pyqtSignal(str)  # tool_call_id
    subAgentLogRequested = pyqtSignal(str)  # task_ids (comma-separated)
    saveFileRequested = pyqtSignal(str, str)  # code, lang
    # WebEngine 上下文丢失信号
    contextLost = pyqtSignal()
    contextRestored = pyqtSignal()

    # WebEngine 最大尺寸限制，防止 GPU 内存溢出
    MAX_WIDTH = 1600
    MAX_HEIGHT = 2000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._markdown_text = ""
        self._streaming = True
        self._is_js_ready = False
        self._last_rendered_html = ""
        self._last_rendered_markdown = ""
        self._reasoning_content = ""  # DeepSeek thinking mode
        self._min_render_interval = 50
        self._height_report_pending = False
        self._context_lost = False  # 上下文丢失标志
        self._context_lost_count = 0  # 上下文丢失次数统计
        self._resize_debounce_timer = QTimer(self)
        self._resize_debounce_timer.setSingleShot(True)
        self._resize_debounce_timer.setInterval(100)
        self._resize_debounce_timer.timeout.connect(self._do_resize_check)
        # 性能优化：resize 锁，防止 resize 期间频繁报告高度
        self._resize_locked = False
        self._resize_unlock_timer = QTimer(self)
        self._resize_unlock_timer.setSingleShot(True)
        self._resize_unlock_timer.setInterval(150)  # resize 结束后 150ms 再报告高度
        self._resize_unlock_timer.timeout.connect(self._on_resize_unlock)

        # 1. 渲染定时器
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._perform_update)

        # 2. Resize 定时器 (修复 Crash 的关键：作为成员变量，随 self 销毁)
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(50)
        self._resize_timer.timeout.connect(self._safe_report_height)

        self._page = ConsoleMonitorPage(self)
        self.setPage(self._page)
        # 透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.page().setBackgroundColor(Qt.transparent)
        self.setContextMenuPolicy(Qt.NoContextMenu)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(40)

        self._page.codeActionRequested.connect(self.codeActionRequested.emit)
        self._page.contextActionRequested.connect(self.contextActionRequested.emit)
        self._page.heightReported.connect(self._on_height_reported)
        self._page.contentReady.connect(self._on_js_ready)
        self._page.toolDiffRequested.connect(self.toolDiffRequested.emit)
        self._page.subAgentLogRequested.connect(self.subAgentLogRequested.emit)
        self._page.saveFileRequested.connect(self.saveFileRequested.emit)

        self._load_skeleton()

    def _handle_context_lost(self):
        """JavaScript 报告上下文丢失"""
        if not self._context_lost:
            self._context_lost = True
            self._context_lost_count += 1
            self.contextLost.emit()
            # 尝试恢复上下文
            self._schedule_context_restore()

    def _schedule_context_restore(self):
        """延迟恢复 WebEngine 上下文"""
        QTimer.singleShot(500, self._try_restore_context)

    def _try_restore_context(self):
        """尝试恢复 WebEngine 上下文"""
        try:
            # 重新加载骨架 HTML
            self._is_js_ready = False
            self._load_skeleton()
            self._context_lost = False
            self.contextRestored.emit()
            # 重新渲染内容
            if self._markdown_text:
                self._schedule_render(immediate=True)
        except Exception as e:
            print(f"Context restore failed: {e}")

    def event(self, event):
        """拦截 WebEngine 事件"""
        # 处理上下文丢失
        if event.type() == QTimerEvent and hasattr(self, '_context_lost_timer'):
            pass
        return super().event(event)

    def setFixedSize(self, *args, **kwargs):
        """限制最大尺寸，防止 GPU 内存溢出"""
        # 计算安全尺寸
        w = args[0] if len(args) > 0 else kwargs.get('width', self.MAX_WIDTH)
        h = args[1] if len(args) > 1 else kwargs.get('height', self.MAX_HEIGHT)

        # 限制最大尺寸
        safe_w = min(w, self.MAX_WIDTH) if isinstance(w, int) else w
        safe_h = min(h, self.MAX_HEIGHT) if isinstance(h, int) else h

        super().setFixedSize(safe_w, safe_h)

    def resize(self, *args, **kwargs):
        """限制 resize 尺寸，防止过大导致 GPU 内存溢出"""
        w = args[0] if len(args) > 0 else kwargs.get('width', self.MAX_WIDTH)
        h = args[1] if len(args) > 1 else kwargs.get('height', self.MAX_HEIGHT)

        # 限制最大尺寸
        safe_w = min(w, self.MAX_WIDTH) if isinstance(w, int) else w
        safe_h = min(h, self.MAX_HEIGHT) if isinstance(h, int) else h

        super().resize(safe_w, safe_h)

    def _install_dialog_filter(self):
        """安装事件过滤器，监听对话框显示"""
        from PyQt5.QtWidgets import QApplication

        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        # 监听对话框显示/激活事件
        event_type = event.type()
        if event_type == 24 or event_type == 9:  # QEvent.Show = 24, QEvent.FocusIn = 9
            obj_class = obj.__class__.__name__
            popup_keywords = [
                "Dialog",
                "Popup",
                "Flyout",
                "InfoBar",
                "Toast",
                "ComboBox",
                "Menu",
                "ToolTip",
            ]
            if any(kw in obj_class for kw in popup_keywords):
                # 降低当前WebView及其父组件的层级
                self.lower()
                parent = self.parent()
                while parent:
                    parent.lower()
                    # 找到 MessageCard 或聊天容器为止
                    if (
                            hasattr(parent, "chat_layout")
                            or parent.__class__.__name__ == "MessageCard"
                    ):
                        break
                    parent = parent.parent()
                # 同时将弹窗提升到最顶层
                if hasattr(obj, "raise_"):
                    obj.raise_()
        return super().eventFilter(obj, event)

    def lower_for_popup(self):
        """降低控件层级，让弹出窗口可以显示在前面"""
        self.lower()
        # 降低父级
        parent_card = self.parent()
        if parent_card:
            parent_card.lower()

    # 安全的高度上报函数
    def _safe_report_height(self):
        try:
            # 再次检查 page 是否存在，避免 C++ 对象已删除错误
            if self.page():
                self._height_report_pending = False
                self.page().runJavaScript("reportHeight();")
        except RuntimeError:
            # 捕获可能的 "wrapped C/C++ object has been deleted"
            pass

    def _do_resize_check(self):
        # 如果处于 resize 锁定状态，跳过 height 报告
        if self._resize_locked:
            return
        try:
            if self.page():
                self.page().runJavaScript("reportHeight();")
        except RuntimeError:
            pass

    def _on_resize_unlock(self):
        """resize 结束后触发高度报告"""
        self._resize_locked = False
        self._do_resize_check()

    def _on_height_reported(self, h):
        self._height_report_pending = False
        final_h = h + 2
        if abs(self.height() - final_h) > 2:
            self.contentHeightChanged.emit(final_h)

    def _on_js_ready(self):
        self._is_js_ready = True
        if self._markdown_text:
            self._schedule_render(immediate=True)

    def _load_skeleton(self):
        # 获取系统字体
        font_family = "Segoe UI, sans-serif"
        try:
            from app.utils.config import Settings
            settings = Settings.get_instance()
            font_family = settings.llm_font_family.value
            if not font_family:
                font_family = settings.canvas_font_selected.value or "Segoe UI, sans-serif"
        except Exception:
            pass

        tag_css = []
        for act, col in ACTION_COLOR_MAP.items():
            tag_css.append(
                f'.context-tag[data-type="{act}"] {{ background: {col}15; border-color: {col}60; color: {col}; }}'
            )
            tag_css.append(
                f'.context-tag[data-type="{act}"]:hover {{ background: {col}30; border-color: {col}; }}'
            )

        cdn_libs = """
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        """

        scrollbar_css = """
            ::-webkit-scrollbar { width: 10px; height: 10px; }
            ::-webkit-scrollbar-track { background: #252526; border-radius: 5px; }
            ::-webkit-scrollbar-thumb { background: #454545; border-radius: 5px; border: 1px solid #3c3c3c; }
            ::-webkit-scrollbar-thumb:hover { background: #5a5a5a; }
        """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            {cdn_libs}
            <style>
                :root {{
                    --bg: transparent;
                    --panel: #121722;
                    --panel-elevated: #171d2a;
                    --panel-soft: #1d2533;
                    --border: #253044;
                    --border-strong: #32425e;
                    --text: #e8edf7;
                    --text-secondary: #b2bfd6;
                    --text-muted: #7f8ca3;
                    --accent: #66c6ff;
                    --accent-warm: #ffb65c;
                    --code-bg: rgba(15, 20, 29, 0.85);
                    --code-toolbar: rgba(28, 28, 36, 0.7);
                    --code-border: #2a3447;
                    --success: #5fd18c;
                    --danger: #ff7b7b;
                }}
                html {{ overflow: hidden; }}
                body {{
                    background: var(--bg) !important;
                    color: var(--text);
                    font-family: "{font_family}", "Segoe UI", sans-serif; font-size: 14px; line-height: 1.5;
                    margin: 0; 
                    padding: 6px 14px; 
                    overflow: hidden;
                }}
                {scrollbar_css}

                #content-placeholder {{ color: var(--text); }}
                #content-placeholder * {{ color: inherit; }}
                h1, h2, h3, h4, h5, h6 {{ color: #FFFFFF !important; font-weight: 700; letter-spacing: 0.01em; }}
                h1 {{ font-size: 1.45em; margin: 12px 0 8px; }}
                h2 {{ font-size: 1.25em; margin: 10px 0 6px; }}
                h3 {{ font-size: 1.1em; margin: 8px 0 4px; }}
                p {{ margin: 8px 0; color: var(--text-secondary); }}
                a {{ color: var(--accent) !important; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                ul, ol {{ margin: 8px 0; padding-left: 24px; }}
                li {{ margin: 4px 0; color: var(--text-secondary); }}
                strong {{ color: #FFFFFF !important; font-weight: 600; }}
                em {{ color: #c4cedd !important; font-style: italic; }}
                code:not(.code-content *):not(pre code) {{ 
                    background: rgba(102, 198, 255, 0.12) !important; 
                    color: #9bddff !important;
                    padding: 2px 6px; 
                    border-radius: 5px; 
                    font-family: Consolas, monospace;
                }}
                hr {{ border: none; border-top: 1px solid var(--border); margin: 14px 0; }}

                /* 优化：移除首尾元素的边距，彻底消除多余空白 */
                #content-placeholder > :first-child {{ margin-top: 0 !important; }}
                #content-placeholder > :last-child {{ margin-bottom: 0 !important; }}

                /* 优化：紧凑的段落间距 */
                p {{ margin: 8px 0; }}

                table:not(.code-table) {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 10px 0;
                    background: rgba(30, 32, 40, 0.30);
                    border: 1px solid rgba(58, 63, 71, 0.5);
                    border-radius: 10px;
                    overflow: hidden;
                    border: 1px solid var(--border);
                }}
                table:not(.code-table) th {{
                    background: rgba(50, 66, 94, 0.35);
                    padding: 8px 12px;
                    text-align: left;
                    font-weight: 600;
                    color: #fff !important;
                    border-bottom: 1px solid var(--border-strong);
                }}
                table:not(.code-table) td {{
                    padding: 8px 12px;
                    border-bottom: 1px solid rgba(37, 48, 68, 0.8);
                    color: var(--text-secondary) !important;
                }}
                table:not(.code-table) tr:nth-child(even) {{ background: rgba(29, 37, 51, 0.35); }}
                table:not(.code-table) tr:hover {{ background: rgba(38, 50, 69, 0.6); }}

                .context-tag {{
                    display: inline-block;
                    padding: 2px 8px;
                    margin: 0 2px;
                    border: 1px solid transparent;
                    border-radius: 999px;
                    font-size: 12px;
                    font-weight: 700;
                    cursor: pointer;
                    transition: 0.18s ease;
                    vertical-align: middle;
                }}
                {"".join(tag_css)}

                /* session 历史会话标签样式 */
                .session-tag {{
                    background: rgba(100, 198, 255, 0.12);
                    border-color: rgba(100, 198, 255, 0.5);
                    color: #66c6ff;
                    margin: 4px 4px;
                    min-width: 120px;
                }}
                .session-tag:hover {{
                    background: rgba(100, 198, 255, 0.25);
                    border-color: rgba(100, 198, 255, 0.8);
                }}
                /* session 时间显示在标题下方 */
                .session-tag .session-time {{
                    display: block;
                    font-size: 10px;
                    font-weight: normal;
                    opacity: 0.6;
                    margin-top: 4px;
                    color: #88d4ff;
                }}

                /* Markdown 表格样式 */
                .session-table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 8px 0;
                }}
                .session-table th, .session-table td {{
                    border: 1px solid rgba(100, 198, 255, 0.3);
                    padding: 8px 12px;
                    text-align: left;
                }}
                .session-table th {{
                    background: rgba(100, 198, 255, 0.1);
                    color: #66c6ff;
                    font-weight: 600;
                }}
                .session-table td {{
                    background: rgba(30, 40, 60, 0.5);
                    vertical-align: middle;
                }}
                .session-table tr:hover td {{
                    background: rgba(100, 198, 255, 0.08);
                }}

                /* 代码块通用样式 */
                .code-table {{ width: 100%; border-collapse: collapse; }}
                .code-table td {{ padding: 0; vertical-align: top; }}
                .lineno {{ width: 32px; text-align: right; padding-right: 8px !important; color: #606060; border-right: 1px solid #404040; user-select: none; font-size: 12px; line-height: 1.5; }}
                /* 优化后的代码块布局：行号固定，代码可横向滚动 */
                .code-container {{
                    display: flex;
                    overflow-x: auto;
                    overflow-y: hidden;
                    background: rgba(20, 25, 35, 0.7);
                    font-family: Consolas, monospace;
                    font-size: 13px;
                    line-height: 1.5;
                    padding: 0 10px 8px 0;
                    margin: 0;
                }}
                .line-numbers {{
                    flex: 0 0 auto;
                    text-align: right;
                    padding-right: 12px;
                    color: #5b6578;
                    border-right: 1px solid var(--code-border);
                    user-select: none; /* 关键：禁止复制行号 */
                    white-space: pre;
                    min-width: 32px;
                    overflow: hidden;
                }}
                .code-content {{
                    flex: 1;
                    overflow-x: auto;
                    overflow-y: hidden;
                    padding-left: 12px;
                }}
                .code-content pre {{
                    margin: 0 !important;
                    white-space: pre;
                    word-wrap: normal;
                    overflow: visible;
                    background: transparent !important;
                    font-family: Consolas, monospace !important;
                    font-size: 13px !important;
                    line-height: 1.5 !important;
                }}
                .code-line {{ padding-left: 12px !important; white-space: pre; font-family: Consolas, monospace; }}

                .code-btn:hover {{ background: rgba(255,255,255,0.08) !important; }}

                .cm-collapsible {{
                    overflow: hidden;
                    transform: translateZ(0);
                    backface-visibility: hidden;
                }}
                .cm-collapsible__summary {{
                    width: 100%;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    background: transparent;
                    border: none;
                    text-align: left;
                    cursor: pointer;
                    outline: none;
                    -webkit-tap-highlight-color: transparent;
                }}
                .cm-collapsible__summary:focus-visible {{
                    box-shadow: inset 0 0 0 1px rgba(102, 198, 255, 0.28);
                }}
                .cm-collapsible__chevron {{
                    flex: 0 0 auto;
                    width: 8px;
                    height: 8px;
                    border-right: 1.5px solid currentColor;
                    border-bottom: 1.5px solid currentColor;
                    transform: rotate(45deg);
                    transform-origin: center;
                    transition: transform 180ms ease;
                    margin-left: 2px;
                    opacity: 0.85;
                }}
                .cm-collapsible[data-expanded="true"] .cm-collapsible__chevron {{
                    transform: rotate(225deg);
                }}
                .cm-collapsible__body {{
                    height: 0;
                    opacity: 0;
                    overflow: hidden;
                    will-change: height, opacity;
                    transition: height 250ms cubic-bezier(0.4, 0, 0.2, 1), opacity 200ms ease;
                }}
                .cm-collapsible[data-expanded="true"] .cm-collapsible__body {{
                    opacity: 1;
                }}

                .think-block {{
                    margin: 8px 0;
                    background: rgba(30, 32, 40, 0.28);
                    border: 1px solid var(--border);
                    border-radius: 10px;
                    transition: border-color 220ms ease;
                }}
                .think-block[data-expanded="true"] {{
                    border-color: rgba(102, 198, 255, 0.4);
                }}
                .think-block__summary {{
                    padding: 8px 12px;
                    color: var(--text-secondary);
                    font-weight: 600;
                }}
                .think-content {{
                    padding: 10px 12px;
                    border-top: 1px solid var(--border);
                    background: rgba(30, 32, 40, 0.18);
                    color: var(--text-muted) !important;
                    font-style: italic;
                    font-size: 13px;
                    line-height: 1.6;
                }}
                /* 思考内容加载骨架屏动画 */
                .think-content.loading {{
                    background-image: linear-gradient(
                        90deg,
                        rgba(30, 32, 40, 0.18) 25%,
                        rgba(40, 44, 55, 0.28) 50%,
                        rgba(30, 32, 40, 0.18) 75%
                    );
                    background-size: 200% 100%;
                    animation: think-shimmer 1.5s ease-in-out infinite;
                }}
                @keyframes think-shimmer {{
                    0% {{ background-position: 200% 0; }}
                    100% {{ background-position: -200% 0; }}
                }}

                .tool-block {{
                    margin: 8px 0;
                    background: rgba(30, 32, 40, 0.28);
                    border: 1px solid var(--border);
                    border-radius: 10px;
                    box-shadow: none;
                    transition: border-color 220ms ease;
                }}
                .tool-block[data-expanded="true"] {{
                    border-color: rgba(95, 209, 140, 0.5);
                }}
                .tool-block__summary {{
                    padding: 8px 12px;
                    color: var(--accent);
                    font-weight: 600;
                    font-size: 13px;
                    white-space: normal;
                }}
                .tool-expanded-content {{
                    padding: 0;
                }}
                .tool-params-section,
                .tool-result-section {{
                    padding: 0;
                }}
                .tool-section-label {{
                    color: #888;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 8px 12px 4px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                .args-table {{
                    display: flex;
                    flex-direction: column;
                    gap: 0;
                    margin: 0;
                }}
                .args-row {{
                    display: flex;
                    align-items: flex-start;
                    padding: 6px 12px;
                    border-bottom: 1px solid rgba(58, 63, 71, 0.4);
                    font-size: 12px;
                }}
                .args-row:last-child {{
                    border-bottom: none;
                }}
                .args-row.empty {{
                    color: #666;
                    font-style: italic;
                    padding: 8px 12px;
                }}
                .args-key {{
                    flex: 0 0 auto;
                    min-width: 80px;
                    max-width: 120px;
                    color: #9C9C9C;
                    font-weight: 500;
                    margin-right: 12px;
                    word-break: break-word;
                }}
                .args-row.result-success {{
                    border-top: 1px solid rgba(95, 209, 140, 0.3);
                    background: rgba(95, 209, 140, 0.05);
                }}
                .args-row.result-fail {{
                    border-top: 1px solid rgba(244, 67, 54, 0.3);
                    background: rgba(244, 67, 54, 0.05);
                }}
                .args-value {{
                    flex: 1 1 auto;
                    color: #d4d4d4;
                    word-break: break-all;
                    font-family: Consolas, monospace;
                    font-size: 11px;
                }}
                .result-content {{
                    padding: 6px 12px 10px;
                    color: #d4d4d4;
                    font-size: 12px;
                    line-height: 1.5;
                    word-break: break-word;
                    font-family: Consolas, monospace;
                    max-height: 400px;
                    overflow-y: auto;
                }}
                .result-empty {{
                    padding: 6px 12px 10px;
                    color: #666;
                    font-style: italic;
                    font-size: 12px;
                }}
                .tool-content {{
                    padding: 10px 12px;
                    border-top: 1px solid var(--border);
                    background: rgba(18, 24, 35, 0.25);
                }}
                .tool-content pre {{
                    margin: 0;
                    color: #d8b68d;
                    font-size: 12px;
                    font-family: Consolas, monospace;
                    white-space: pre-wrap;
                    word-break: break-word;
                }}

                blockquote {{
                    border-left: 3px solid var(--accent-warm);
                    background: rgba(255,182,92,0.08);
                    margin: 10px 0;
                    padding: 8px 12px;
                    border-radius: 0 10px 10px 0;
                    color: var(--text-secondary) !important;
                }}
            </style>
        </head>
        <body>
            <div id="content-placeholder"></div>
            <script>
                const collapsibleState = new Map();

                function syncExpandedAttrs(block, expanded) {{
                    block.dataset.expanded = expanded ? 'true' : 'false';
                    const summary = block.querySelector('.cm-collapsible__summary');
                    if (summary) summary.setAttribute('aria-expanded', expanded ? 'true' : 'false');
                    const key = block.dataset.blockKey;
                    if (key) collapsibleState.set(key, expanded);
                }}

                function animateCollapsible(block, expand) {{
                    const body = block.querySelector('.cm-collapsible__body');
                    if (!body) return;

                    const ANIM_DURATION = 220;
                    const startTime = performance.now();
                    const startHeight = body.getBoundingClientRect().height;
                    const startOpacity = expand ? 0 : 1;
                    const endHeight = expand ? body.scrollHeight : 0;
                    const endOpacity = expand ? 1 : 0;

                    // 立即更新展开状态
                    syncExpandedAttrs(block, expand);

                    // 阻止 CSS transition 干扰
                    body.style.transition = 'none';
                    body.style.height = startHeight + 'px';
                    body.style.opacity = startOpacity;

                    // 强制重绘
                    void body.offsetHeight;

                    // 取消之前的动画
                    if (window._collapsibleAnimId) {{
                        cancelAnimationFrame(window._collapsibleAnimId);
                    }}

                    function tick(now) {{
                        const elapsed = now - startTime;
                        const progress = Math.min(elapsed / ANIM_DURATION, 1);
                        // 使用 easeOutQuad 缓动
                        const eased = 1 - (1 - progress) * (1 - progress);

                        const currentHeight = startHeight + (endHeight - startHeight) * eased;
                        const currentOpacity = startOpacity + (endOpacity - startOpacity) * eased;

                        body.style.height = currentHeight + 'px';
                        body.style.opacity = currentOpacity;

                        if (progress < 1) {{
                            window._collapsibleAnimId = requestAnimationFrame(tick);
                        }} else {{
                            // 动画结束
                            body.style.height = expand ? 'auto' : '0px';
                            body.style.opacity = endOpacity;
                            // 动画结束后只报告一次高度
                            setTimeout(() => reportHeight(), 0);
                        }}
                    }}

                    window._collapsibleAnimId = requestAnimationFrame(tick);
                }}

                function restoreCollapsibleStates(root) {{
                    root.querySelectorAll('.cm-collapsible').forEach(block => {{
                        const key = block.dataset.blockKey;
                        const expanded = key && collapsibleState.has(key)
                            ? collapsibleState.get(key)
                            : block.dataset.expanded === 'true';
                        const body = block.querySelector('.cm-collapsible__body');
                        syncExpandedAttrs(block, !!expanded);
                        if (body) {{
                            body.style.transition = 'none';
                            if (expanded) {{
                                body.style.height = 'auto';
                                body.style.opacity = '1';
                            }} else {{
                                body.style.height = '0px';
                                body.style.opacity = '0';
                            }}
                            body.offsetHeight;
                            body.style.transition = '';
                        }}
                    }});
                }}

                function updateContent(newHtml) {{
                    const container = document.getElementById('content-placeholder');
                    if (container.innerHTML !== newHtml) {{
                        // 记录当前展开状态的思考块
                        const expandedStates = new Map();
                        container.querySelectorAll('.think-block').forEach(block => {{
                            expandedStates.set(block.dataset.blockKey, block.dataset.expanded === 'true');
                        }});

                        container.innerHTML = newHtml;

                        // 恢复展开状态并移除骨架屏动画
                        container.querySelectorAll('.think-content').forEach(content => {{
                            content.classList.remove('loading');
                        }});

                        restoreCollapsibleStates(container);

                        // 恢复展开状态
                        container.querySelectorAll('.think-block').forEach(block => {{
                            const savedState = expandedStates.get(block.dataset.blockKey);
                            if (savedState !== undefined) {{
                                block.dataset.expanded = savedState ? 'true' : 'false';
                                const body = block.querySelector('.cm-collapsible__body');
                                if (body) {{
                                    body.style.height = savedState ? 'auto' : '0px';
                                    body.style.opacity = savedState ? '1' : '0';
                                }}
                            }}
                        }});

                        if (window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise();
                        reportHeight();
                    }}
                }}
                function reportHeight() {{
                    const h = document.documentElement.getBoundingClientRect().height;
                    console.log('pywebview_height:' + h);
                }}
                document.addEventListener('click', e => {{
                    const btn = e.target.closest('button[data-action]');
                    if (btn) {{
                        const act = btn.getAttribute('data-action');
                        const b64 = btn.getAttribute('data-copy');
                        const lang = btn.getAttribute('data-lang') || '';
                        if (act === 'copy' && navigator.clipboard) navigator.clipboard.writeText(atob(b64));
                        console.log('pywebview_action:' + act + ':' + b64 + ':' + lang);
                        return;
                    }}
                    const summary = e.target.closest('.cm-collapsible__summary');
                    if (summary) {{
                        const block = summary.closest('.cm-collapsible');
                        if (block) {{
                            animateCollapsible(block, block.dataset.expanded !== 'true');
                        }}
                        return;
                    }}
                    const tag = e.target.closest('.context-tag');
                    if (tag) {{
                        var tagType = tag.getAttribute('data-type') || tag.getAttribute('data-action') || '';
                        var sessionId = tag.getAttribute('data-session-id') || '';
                        var tagContent = sessionId || tag.getAttribute('data-content') || tag.getAttribute('data-title') || '';
                        e.stopPropagation();
                        e.preventDefault();
                        console.log('pywebview_action:context|||' + tagContent + '|||' + tagType);
                        return;
                    }}
                    const link = e.target.closest('a');
                    if (link) {{
                        console.log('pywebview_action:link_found:' + link.href);
                    }}
                    if (link && link.href) {{
                        e.preventDefault();
                        console.log('pywebview_action:open_url:' + link.href);
                    }}
                }});
                document.addEventListener('DOMContentLoaded', () => {{
                    console.log('pywebview_ready');
                    reportHeight();
                    new ResizeObserver(() => requestAnimationFrame(reportHeight)).observe(document.body);
                }});
                window.addEventListener('load', () => {{
                    reportHeight();
                }});
                window.addEventListener('webglcontextlost', (e) => {{
                    e.preventDefault();
                    console.log('pywebview_action:context_lost');
                }}, false);
                window.addEventListener('webglcontextrestored', () => {{
                    console.log('pywebview_ready');
                    reportHeight();
                }}, false);
                window.pywebview = {{ reportHeight: reportHeight }};

                // 工具差异对比请求函数
                window._requestToolDiff = function(toolCallId) {{
                    console.log('pywebview_action:tool_diff:' + toolCallId);
                }};

                // 子智能体日志查看请求函数
                window._requestSubAgentLog = function(taskIds) {{
                    console.log('pywebview_action:subagent_log:' + taskIds);
                }};
            </script>
        </body>
        </html>
        """
        self.setHtml(html, QUrl(""))

    def append_chunk(self, text: str):
        if not text:
            return

        self._markdown_text += text

        if not self._is_js_ready:
            return
        if self._streaming and len(text) > 3:
            self._schedule_render(immediate=True)
        else:
            self._schedule_render()

    def _render_markdown_to_html(self, raw_md: str) -> str:
        if not self._streaming:
            return _render_markdown_to_html_cached(
                raw_md,
                getattr(self, "_reasoning_content", "") or "",
            )

        # DeepSeek thinking mode: 注入 reasoning_content 作为思考块
        reasoning = getattr(self, '_reasoning_content', '') or ''
        if reasoning:
            think_html = _render_think_block(reasoning, completed=True)
            raw_md = think_html + raw_md

        safe_md = _sanitize_incomplete_markdown(raw_md)
        safe_md = _unwrap_code_blocks_with_context_links(safe_md)
        safe_md = _inject_context_links(safe_md)
        processed_md = _inject_think_cards(safe_md, self._streaming is False)
        processed_md = _inject_tool_blocks(processed_md, self._streaming is False)

        try:
            md = get_markdown_instance()
            md.reset()
            html_content = md.convert(processed_md)
            return _wrap_code_blocks_with_copy_button_web(html_content)
        except Exception:
            return f"<pre>{escape(raw_md)}</pre>"

    def _schedule_render(self, immediate: bool = False):
        if not self._is_js_ready:
            return
        if immediate:
            if self._render_timer.isActive():
                self._render_timer.stop()
            self._perform_update()
            return
        interval = self._min_render_interval if self._streaming else 40
        if self._render_timer.isActive():
            return
        self._render_timer.start(interval)

    def _perform_update(self):
        try:
            if not self.page():
                return
            if self._markdown_text == self._last_rendered_markdown:
                if not self._height_report_pending:
                    self._height_report_pending = True
                    self._resize_timer.start()
                return

            html_content = self._render_markdown_to_html(self._markdown_text)
            self._last_rendered_markdown = self._markdown_text
            if html_content == self._last_rendered_html:
                if not self._height_report_pending:
                    self._height_report_pending = True
                    self._resize_timer.start()
                return

            self._last_rendered_html = html_content
            self._height_report_pending = True
            js_code = f"updateContent({json.dumps(html_content, ensure_ascii=False)});"
            self.page().runJavaScript(js_code)
        except RuntimeError:
            pass

    def finish_streaming(self):
        self._streaming = False
        self._schedule_render(immediate=True)

    def get_plain_text(self) -> str:
        return self._markdown_text

    def get_html(self) -> str:
        return self._markdown_text

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._streaming:
            return

        # 性能优化：使用 resize 锁，阻止 resize 期间频繁报告高度
        if not self._resize_locked:
            self._resize_locked = True
            self._resize_unlock_timer.stop()
            self._resize_unlock_timer.start()

    def wheelEvent(self, event: QWheelEvent):
        # 获取滚动条（向上找 QScrollArea）
        scroll_area = self.parent().parent.chat_scroll_area
        if scroll_area:
            vbar = scroll_area.verticalScrollBar()
            if vbar and vbar.minimum() != vbar.maximum():
                # 让外部 ScrollArea 滚动
                delta = event.angleDelta().y()
                vbar.setValue(vbar.value() - delta // 2)
                event.accept()  # 标记事件已处理
                return

        super().wheelEvent(event)

    def deleteLater(self):
        if self._render_timer.isActive():
            self._render_timer.stop()
        if self._resize_timer.isActive():
            self._resize_timer.stop()
        if self._resize_debounce_timer.isActive():
            self._resize_debounce_timer.stop()
        if self._resize_unlock_timer.isActive():
            self._resize_unlock_timer.stop()
        if self.page():
            self.page().deleteLater()
        super().deleteLater()


class PlainTextViewer(QWidget):
    contentHeightChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self._init_ui()
        # 性能优化：添加 resize 防抖定时器
        self._resize_debounce_timer = QTimer(self)
        self._resize_debounce_timer.setSingleShot(True)
        self._resize_debounce_timer.setInterval(50)  # 50ms 防抖
        self._resize_debounce_timer.timeout.connect(self._do_resize_update)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(0)

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.text_edit.setFrameShape(QTextEdit.NoFrame)
        font_css = get_font_family_css()
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                {font_css}
                color: #F5F7FB;
                font-size: 14px;
                line-height: 1.5;
                selection-background-color: rgba(102, 198, 255, 0.28);
            }}
        """)
        layout.addWidget(self.text_edit)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(40)

    def append_chunk(self, text: str):
        self._text += text
        self.text_edit.setPlainText(self._text)
        # 设置文档宽度以确保正确计算换行
        vp_width = self.text_edit.viewport().width()
        if vp_width > 0:
            self.text_edit.document().setTextWidth(vp_width)
        QTimer.singleShot(100, self._update_height)

    def finish_streaming(self):
        QTimer.singleShot(100, self._update_height)

    def get_plain_text(self) -> str:
        return self._text

    def set_text(self, text: str):
        self._text = text
        self.text_edit.setPlainText(text)
        # 设置文档宽度以确保正确计算换行
        vp_width = self.text_edit.viewport().width()
        if vp_width > 0:
            self.text_edit.document().setTextWidth(vp_width)
        QTimer.singleShot(500, self._update_height)

    def _update_height(self):
        """强制 QTextEdit 重新布局后再计算高度"""
        # 先让 QTextEdit 重新布局
        self.text_edit.update()
        self.text_edit.document().markContentsDirty(0, self.text_edit.document().characterCount())

        # 强制更新几何信息
        self.text_edit.ensurePolished()

        doc = self.text_edit.document()
        h = int(doc.size().height()) + 16  # padding

        h = max(40, h)

        if abs(self.height() - h) > 2:
            self.setFixedHeight(h)
            self.contentHeightChanged.emit(h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 性能优化：使用防抖定时器，避免每次 resize 都触发高度计算
        self._resize_debounce_timer.stop()
        self._resize_debounce_timer.start()

    def _do_resize_update(self):
        """防抖后执行高度更新"""
        self._update_height()

    def update_height(self):
        """公开方法，用于外部触发高度重算（跳过防抖，直接更新）"""
        self._resize_debounce_timer.stop()  # 取消待执行的防抖
        self._update_height()


class MessageCard(SimpleCardWidget):
    heightChanged = pyqtSignal(int)
    deleteRequested = pyqtSignal()
    undoRequested = pyqtSignal()
    actionRequested = pyqtSignal(str, str)
    contextActionRequested = pyqtSignal(str, str)
    optionSelected = pyqtSignal(dict)
    interventionRequested = pyqtSignal(dict)
    toolDiffRequested = pyqtSignal(str)  # tool_call_id
    subAgentLogRequested = pyqtSignal(str)  # task_ids (comma-separated)
    cardDiffRequested = pyqtSignal(int)  # message_index（消息在 session.messages 中的索引）
    saveFileRequested = pyqtSignal(str, str)  # code, lang

    def __init__(
            self,
            role: str,
            timestamp: str = None,
            parent=None,
            tag_params: dict = None,
            error: bool = False,
            reasoning_content: str = "",
    ):
        super().__init__(parent)
        self.parent = parent
        self.role = role
        self.context_tags = tag_params or {}
        self.timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")
        self.error = error
        self._interactive_options: List[dict] = []
        self._content_data: Any = [] if role == "assistant" else ""
        self._streaming = False
        self._round_index: Optional[int] = None  # 用于卡片差异功能
        self._message_index: Optional[int] = None  # 用于卡片差异和撤销功能：消息在 session.messages 中的索引
        self._reasoning_content = reasoning_content
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._update_anim)
        self._pulse_phase = 0.0
        self._height_anim = QVariantAnimation(self)
        self._height_anim.setDuration(180)
        self._height_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._height_anim.valueChanged.connect(self._apply_viewer_height)
        self._height_anim.stateChanged.connect(self._on_height_anim_state_changed)
        self._is_height_animating = False  # 动画期间抑制重复报告
        # 禁用 Python 端的动画，依赖 JS 动画控制高度
        self._height_anim.setDuration(0)  # 设置为0相当于禁用插值
        self._target_viewer_height = 40
        self._last_applied_viewer_height = 40
        self._theme = self._build_theme(role, error)
        self._base_bg = self._theme["bg"]
        self._base_border = self._theme["border"]
        # 性能优化：缓存上次宽度值，避免不必要的更新
        self._last_synced_width = 0
        self._resize_preview_mode = False
        self._resize_preview_height = 0
        self._options_were_visible_before_resize = False
        # WebEngine 上下文恢复标志
        self._webengine_needs_restore = False
        self._setup_ui()

    def _build_theme(self, role: str, error: bool = False) -> Dict[str, str]:
        themes = {
            "assistant": {
                "avatar": "AI",
                "title": "Drifox",
                "subtitle": "Assistant",
                "bg": "rgba(45, 30, 20, 150)",
                "border": "none",
                "accent": "#D35400",
                "text": "#FFD4B8",
                "muted": "#8FA4C2",
                "side": "left",
            },
            "welcome": {
                "avatar": "DX",
                "title": "Drifox",
                "subtitle": "AI Copilot",
                "bg": "rgba(45, 30, 20, 150)",
                "border": "none",
                "accent": "#D35400",
                "text": "#FFD4B8",
                "muted": "#95A4BC",
                "side": "left",
            },
            "user": {
                "avatar": "你",
                "title": "你",
                "subtitle": "Prompt",
                "bg": "rgba(27,42,67,150)",
                "border": "none",
                "accent": "#9FC3FF",
                "text": "#F4F7FD",
                "muted": "#B4C2D9",
                "side": "right",
            },
        }
        theme = dict(themes.get(role, themes["assistant"]))
        if error:
            theme["bg"] = "#2A1F1F"
            theme["border"] = "#A94444"
            theme["accent"] = "#FF7B7B"
        return theme

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)
        top = QHBoxLayout()
        top.setSpacing(10)

        av = QLabel(self)
        if self.role in ("welcome", "assistant"):
            # 品牌图标头像
            av_icon = get_icon("drifox")
            pixmap = av_icon.pixmap(28, 28)
            av.setPixmap(pixmap)
            av.setFixedSize(30, 30)
            av.setAlignment(Qt.AlignCenter)
        else:
            # user 和其他：圆形文字头像
            av.setText(self._theme["avatar"])
            font_css = get_font_family_css()
            av.setStyleSheet(
                f"""
                QLabel {{
                    {font_css} font-size: 12px;
                    color: #FFFFFF;
                    font-weight: 700;
                    background: {self._theme["accent"]};
                    border: 1px solid rgba(255,255,255,0.12);
                    border-radius: 15px;
                }}
                """
            )
            av.setFixedSize(30, 30)
            av.setAlignment(Qt.AlignCenter)

        title_wrap = QWidget(self)
        title_layout = QVBoxLayout(title_wrap)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(1)

        font_css = get_font_family_css()
        nm_l = QLabel(self._theme["title"], self)
        nm_l.setStyleSheet(
            f"{font_css} font-size:14px;color:{self._theme['text']};font-weight:700;"
        )
        sub_l = QLabel(self._theme["subtitle"], self)
        sub_l.setStyleSheet(
            f"{font_css} font-size:11px;color:{self._theme['muted']};font-weight:500;letter-spacing:0.02em;"
        )
        title_layout.addWidget(nm_l)
        title_layout.addWidget(sub_l)

        top.addWidget(av)
        top.addWidget(title_wrap)
        if self.role != "user":
            ts = QLabel(self.timestamp, self)
            ts.setStyleSheet(
                f"""
                QLabel {{
                    font-size: 11px;
                    color: {self._theme["muted"]};
                    background: rgba(255,255,255,0.03);
                    border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 9px;
                    padding: 2px 8px;
                }}
                """
            )
            top.addWidget(ts)
        top.addStretch()

        btns = QWidget(self)
        bl = QHBoxLayout(btns)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(4)
        specs = []
        if self.role == "assistant":
            specs = [
                (
                    get_icon("差异对比"),
                    "文档差异对比",
                    lambda: self._emit_card_diff_requested(),
                ),
                (
                    get_icon("复制"),
                    "复制",
                    lambda: self.actionRequested.emit(self.get_plain_text(), "copy"),
                ),
            ]
        elif self.role == "user":
            specs = [
                (
                    get_icon("复制"),
                    "复制",
                    lambda: self.actionRequested.emit(self.get_plain_text(), "copy"),
                ),
                (get_icon("撤销"), "撤销到这里", self.undoRequested.emit),
                (FluentIcon.DELETE, "删除", self.deleteRequested.emit),
            ]
        for ic, tp, cb in specs:
            b = TransparentToolButton(ic, self)
            b.setToolTip(tp)
            b.clicked.connect(cb)
            b.setFixedSize(32, 32)
            b.installEventFilter(ToolTipFilter(b))
            bl.addWidget(b)
        top.addWidget(btns)
        main.addLayout(top)
        main.addWidget(CardSeparator(self))

        if self.role == "user":
            self.viewer = PlainTextViewer(self)
            self.viewer.contentHeightChanged.connect(self._update_height)
            main.addWidget(self.viewer)
        else:
            self.viewer = CodeWebViewer(self)
            self.viewer.codeActionRequested.connect(self.actionRequested.emit)
            self.viewer.contextActionRequested.connect(self.contextActionRequested.emit)
            self.viewer.contentHeightChanged.connect(self._update_height)
            self.viewer.toolDiffRequested.connect(self.toolDiffRequested.emit)
            self.viewer.subAgentLogRequested.connect(self.subAgentLogRequested.emit)
            self.viewer.saveFileRequested.connect(self.saveFileRequested.emit)
            # WebEngine 上下文丢失处理
            self.viewer.contextLost.connect(self._on_webengine_context_lost)
            self.viewer.contextRestored.connect(self._on_webengine_context_restored)
            main.addWidget(self.viewer)
            self.resize_placeholder = QFrame(self)
            self.resize_placeholder.setVisible(False)
            self.resize_placeholder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.resize_placeholder.setStyleSheet(
                """
                QFrame {
                    background: rgba(255,255,255,0.035);
                    border: 1px dashed rgba(255,255,255,0.08);
                    border-radius: 12px;
                }
                """
            )
            main.addWidget(self.resize_placeholder)

        self.options_widget = QWidget(self)
        self.options_layout = QVBoxLayout(self.options_widget)
        self.options_layout.setContentsMargins(0, 8, 0, 0)
        self.options_layout.setSpacing(8)
        self.options_widget.setVisible(False)
        main.addWidget(self.options_widget)

        main.addWidget(CardSeparator(self))
        self.setStyleSheet(
            f"""
            CardWidget {{
                background-color: {self._theme["bg"]};
                border: 1px solid {self._theme["border"]};
                border-radius: 16px;
            }}
            """
        )

    def start_streaming_anim(self):
        if self._streaming:
            return
        self._streaming = True
        self._pulse_phase = 0.0
        try:
            self._anim_timer.start(80)
        except RuntimeError:
            return
        self.update()

    def _update_anim(self):
        self._pulse_phase = (self._pulse_phase + 0.25) % (math.pi * 2)
        self.update()

    def _apply_card_style(self, border: str = None, bg: str = None):
        self.setStyleSheet(
            f"""
            CardWidget {{
                background-color: {bg or self._base_bg};
                border: 1px solid {border or self._base_border};
                border-radius: 16px;
            }}
            """
        )

    def stop_streaming_anim(self):
        self._streaming = False
        try:
            self._anim_timer.stop()
        except RuntimeError:
            return
        self._apply_card_style()
        self.update()

    def _on_webengine_context_lost(self):
        """WebEngine 上下文丢失时显示恢复提示"""
        # 设置卡片为错误状态样式
        self._apply_card_style(border="#A94444")
        # 标记需要恢复
        self._webengine_needs_restore = True

    def _on_webengine_context_restored(self):
        """WebEngine 上下文恢复后恢复正常样式"""
        self._apply_card_style()
        self._webengine_needs_restore = False
        # 重新同步宽度
        self.sync_width(force=True)

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        radius = 16

        accent = QColor(self._theme["accent"])
        accent.setAlpha(95 if self.role == "user" else 75)
        stripe_width = 4
        stripe_x = w - stripe_width - 2 if self._theme.get("side") == "right" else 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(accent)
        painter.drawRoundedRect(stripe_x, 10, stripe_width, max(18, h - 20), 3, 3)

        if not self._streaming:
            return

        path = QPainterPath()
        path.addRoundedRect(1, 1, w - 2, h - 2, radius, radius)
        painter.setClipPath(path)

        gradient = QLinearGradient(0, 0, w, h)
        if self.role == "assistant":
            rainbow = [
                QColor("#63D8FF"),
                QColor("#7FA8FF"),
                QColor("#A98BFF"),
                QColor("#FF92C2"),
                QColor("#FFB86B"),
                QColor("#7BE3A1"),
            ]
            shift = int((self._pulse_phase / (math.pi * 2)) * len(rainbow))
            rainbow = rainbow[shift:] + rainbow[:shift]
            positions = [0.0, 0.2, 0.4, 0.62, 0.82, 1.0]
            for pos, color in zip(positions, rainbow):
                c = QColor(color)
                c.setAlpha(175)
                gradient.setColorAt(pos, c)
        else:
            pulse = QColor(self._theme["accent"])
            glow_alpha = 90 + int(45 * (math.sin(self._pulse_phase) + 1) / 2)
            pulse.setAlpha(glow_alpha)
            gradient.setColorAt(0.0, pulse.lighter(120))
            gradient.setColorAt(0.5, pulse)
            gradient.setColorAt(1.0, pulse.darker(130))

        pen = QPen(gradient, 3)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.NoBrush))
        painter.drawRoundedRect(1, 1, w - 2, h - 2, radius, radius)

        highlight = QColor(self._theme["accent"])
        highlight.setAlpha(24)
        painter.fillRect(0, 0, w, 4, highlight)

    def set_error_state(self, is_error: bool):
        self.error = is_error
        if is_error:
            bd, bg = "#ff4d4d", "#2a1f1f"
        else:
            bd, bg = self._base_border, self._base_bg
        self._apply_card_style(border=bd, bg=bg)

    def _emit_card_diff_requested(self):
        """发射卡片差异请求信号"""
        if self._round_index is not None:
            self.cardDiffRequested.emit(self._round_index)

    def _update_height(self, h):
        target_height = max(40, h)
        current_height = self.viewer.height() or self.viewer.minimumHeight() or 40
        self._target_viewer_height = target_height

        # 关键优化：高度变化完全由 CSS transition 驱动
        # PyQt 只设置最终值，不做 QVariantAnimation 插值动画
        # 因为 CSS transition 已经提供了平滑动画
        if self._streaming or abs(target_height - current_height) < 10:
            if self._height_anim.state() == QVariantAnimation.Running:
                self._height_anim.stop()
            self._apply_viewer_height(target_height)
            return

        # 停止任何正在进行的动画，直接跳到目标值
        # CSS transition 会负责平滑过渡
        self._height_anim.stop()
        self._apply_viewer_height(target_height)

    def _on_height_anim_state_changed(self, state):
        self._is_height_animating = (state == QVariantAnimation.Running)
        # 动画结束时触发一次高度变化信号，让父容器更新
        if state == QVariantAnimation.Stopped:
            self.heightChanged.emit(self._last_applied_viewer_height)
            layout = self.layout()
            if layout:
                layout.invalidate()

    def _apply_viewer_height(self, value):
        height = max(40, int(value))
        if height == self._last_applied_viewer_height:
            return
        self._last_applied_viewer_height = height
        self.viewer.setFixedHeight(height)
        self.heightChanged.emit(height)
        # 简化：直接触发布局更新，不再区分动画状态

    def sync_width(self, force: bool = False):
        """同步卡片宽度

        Args:
            force: 是否强制更新，即使宽度没变化
        """
        parent = self.parentWidget()
        if not parent:
            return
        parent_width = parent.width()
        if self.role == "welcome":
            horizontal_margin = 20
        elif self.role == "user":
            horizontal_margin = 120
        else:
            horizontal_margin = 72

        target_width = max(320, parent_width - horizontal_margin)

        # 性能优化：只有宽度真正变化时才更新
        if not force and target_width == self._last_synced_width:
            return

        self._last_synced_width = target_width
        if self.minimumWidth() != target_width or self.maximumWidth() != target_width:
            self.blockSignals(True)
            self.setMinimumWidth(target_width)
            self.setMaximumWidth(target_width)
            self.blockSignals(False)

        # 宽度同步后触发 viewer 高度重算（用于 user 卡片的 PlainTextViewer）
        if not self._resize_preview_mode and hasattr(self.viewer, 'update_height'):
            self.viewer.update_height()

    def set_resize_preview_mode(self, enabled: bool):
        """在窗口 resize 期间切换到轻量占位模式，减少复杂子控件重绘。

        只有使用 CodeWebViewer 的卡片需要 placeholder 优化，
        PlainTextViewer（user 卡片）weight 很轻，不需要。
        """
        if enabled == self._resize_preview_mode:
            return

        self._resize_preview_mode = enabled

        # user 卡片使用 PlainTextViewer，weight 很轻，不需要 placeholder
        if self.role == "user":
            return

        if enabled:
            viewer_height = max(self.viewer.height(), self.viewer.minimumHeight(), 40)
            options_height = self.options_widget.sizeHint().height() if self.options_widget.isVisible() else 0
            self._resize_preview_height = max(40, viewer_height + options_height)
            self.resize_placeholder.setFixedHeight(self._resize_preview_height)
            self.resize_placeholder.show()
            self.viewer.setUpdatesEnabled(False)
            self.viewer.hide()
            self._options_were_visible_before_resize = self.options_widget.isVisible()
            if self._options_were_visible_before_resize:
                self.options_widget.setUpdatesEnabled(False)
                self.options_widget.hide()
            return

        self.viewer.show()
        self.viewer.setUpdatesEnabled(True)
        if self._options_were_visible_before_resize:
            self.options_widget.show()
            self.options_widget.setUpdatesEnabled(True)
        self.resize_placeholder.hide()
        self.resize_placeholder.setFixedHeight(0)
        self._resize_preview_height = 0
        self._options_were_visible_before_resize = False

        if hasattr(self.viewer, "update_height"):
            self.viewer.update_height()

    def wheelEvent(self, event: QWheelEvent):
        try:
            scroll_area = self.parent.chat_scroll_area
            if scroll_area:
                vbar = scroll_area.verticalScrollBar()
                if (
                        vbar
                        and vbar.minimum() != vbar.maximum()
                        and event.angleDelta().y() != 0
                ):
                    vbar.setValue(vbar.value() - event.angleDelta().y() // 2)
                    event.accept()
                    return
        except:
            pass
        super().wheelEvent(event)

    def update_content(self, txt):
        if self.role == "assistant" and not self._streaming:
            self.start_streaming_anim()
        if isinstance(txt, list):
            self.set_content(txt)
            return
        self.append_text(txt)

    def set_content(self, content: Any):
        if self.role == "assistant":
            self._content_data = ensure_content_blocks(content)
            rendered = content_to_markdown(self._content_data)
        else:
            self._content_data = str(content or "")
            rendered = self._content_data

        if hasattr(self.viewer, "_markdown_text"):
            self.viewer._markdown_text = rendered
            self.viewer._schedule_render(immediate=True)
        elif hasattr(self.viewer, "set_text"):
            self.viewer.set_text(rendered)

    def append_text(self, text: str):
        if self.role == "assistant":
            self._content_data = append_text_block(self._content_data, text)
            rendered = content_to_markdown(self._content_data)
            self.viewer._markdown_text = rendered
            self.viewer._schedule_render(immediate=False)
            return

        self._content_data = str(self._content_data or "") + str(text or "")
        self.viewer.append_chunk(str(text or ""))

    def append_tool_result(
            self,
            tool_name: str,
            arguments: Dict[str, Any] = None,
            result: Any = None,
            success: bool = True,
            tool_call_id: str = None,
    ):
        self._content_data.append(
            make_tool_result_block(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                success=success,
                tool_call_id=tool_call_id,
            )
        )
        self.viewer._markdown_text = content_to_markdown(self._content_data)
        self.viewer._schedule_render(immediate=True)

    def get_plain_text(self) -> str:
        if self.role == "assistant":
            return content_to_text(self._content_data, include_tool_results=True)
        return str(self._content_data or "")

    def run_js(self, js_code: str):
        """运行 JavaScript 代码"""
        try:
            if self.viewer and hasattr(self.viewer, "page"):
                self.viewer.page().runJavaScript(js_code)
        except RuntimeError:
            pass

    def set_reasoning_content(self, content: str):
        """设置思考内容（用于 DeepSeek 思考模式）"""
        self._reasoning_content = content
        if content and hasattr(self.viewer, "_markdown_text"):
            # 刷新渲染以显示思考内容
            self.viewer._schedule_render(immediate=True)

    def set_html_direct(self, html: str):
        """直接设置 HTML，绕过打字机效果"""
        try:
            if self.viewer:
                self.viewer._markdown_text = html
                self.viewer._streaming = False
                self.viewer._perform_update()
        except RuntimeError:
            pass

    def append_reasoning(self, text: str):
        """追加思考内容（流式模式）"""
        if not hasattr(self.viewer, '_reasoning_content'):
            return
        self._reasoning_content = (self._reasoning_content or '') + text
        self.viewer._reasoning_content = self._reasoning_content
        # 触发渲染更新
        self.viewer._schedule_render(immediate=True)

    def add_interactive_option(self, option: Dict[str, Any]):
        """添加交互选项"""
        self._interactive_options.append(option)

        option_widget = QWidget(self.options_widget)
        option_layout = QHBoxLayout(option_widget)
        option_layout.setContentsMargins(0, 0, 0, 0)
        option_layout.setSpacing(8)

        label = QLabel(f"• {option.get('label', '选项')}", self)
        label.setStyleSheet(f"color: #4a9eff; {get_font_family_css()} font-size: 13px; cursor: pointer;")
        label.setCursor(Qt.PointingHandCursor)
        label.option_data = option
        label.mousePressEvent = lambda e, opt=option: self._on_option_clicked(opt)

        option_layout.addWidget(label)
        option_layout.addStretch()

        self.options_layout.addWidget(option_widget)
        self.options_widget.setVisible(True)

    def add_interactive_options(self, options: List[Dict[str, Any]]):
        """批量添加交互选项"""
        if not options:
            return

        title_label = QLabel("👉 请选择：", self)
        title_label.setStyleSheet(f"color: #888; {get_font_family_css()} font-size: 12px; margin-top: 8px;")
        self.options_layout.addWidget(title_label)

        for option in options:
            self.add_interactive_option(option)

    def _on_option_clicked(self, option: Dict[str, Any]):
        """选项被点击"""
        self.optionSelected.emit(option)

    def set_intervention_mode(self, enabled: bool):
        """设置人工干预模式"""
        if enabled:
            self.interventionRequested.emit(
                {"card_id": id(self), "message": "请求人工干预"}
            )

    def finish_streaming(self):
        try:
            self.viewer.finish_streaming()
        except RuntimeError:
            pass
        self.stop_streaming_anim()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 宽度同步由外层聊天窗口统一调度，避免卡片自身 resize 再次触发全量重算

    def closeEvent(self, e):
        try:
            self._anim_timer.stop()
        except RuntimeError:
            pass
        try:
            self._height_anim.stop()
        except RuntimeError:
            pass
        if hasattr(self.viewer, "deleteLater"):
            try:
                self.viewer.deleteLater()
            except RuntimeError:
                pass
        super().closeEvent(e)


def create_welcome_card(
        parent=None, agent_name: str = "", agent_description: str = "",
        recent_sessions: list = None, top_by_count: list = None
) -> MessageCard:
    """创建欢迎卡片

    Args:
        parent: 父控件
        agent_name: 当前智能体名称
        agent_description: 智能体描述
        recent_sessions: 最近的历史会话列表，每项包含 title, last_time, session_id, message_count
        top_by_count: 消息最多的会话列表，每项包含 title, last_time, session_id, message_count
    """
    agent_tendency = ""
    if agent_name:
        agent_tendency = f"""
---

### 🤖 当前智能体：{agent_name}

{agent_description}

"""

    # 随机选择欢迎语和 Tips
    greeting = get_random_greeting()
    tip = get_random_tip()

    # 构建历史会话链接（两列表格：最近会话 | 最多消息）
    history_section = ""
    if recent_sessions or top_by_count:
        # 生成表格 HTML（使用纯 HTML 确保胶囊样式正确显示）
        table_rows = ""
        for i in range(3):
            # 左边：最近会话
            recent = recent_sessions[i] if recent_sessions and i < len(recent_sessions) else None
            # 右边：消息最多
            top = top_by_count[i] if top_by_count and i < len(top_by_count) else None

            if recent:
                title = escape(recent.get("title", "未命名会话"))
                session_id = escape(recent.get("session_id", ""))
                last_time = escape(recent.get("last_time", ""))
                left_cell = f'<span class="context-tag session-tag" data-type="session" data-session-id="{session_id}" data-action="session">{title}<span class="session-time">{last_time}</span></span>'
            else:
                left_cell = "-"

            if top:
                title = escape(top.get("title", "未命名会话"))
                session_id = escape(top.get("session_id", ""))
                msg_count = top.get("message_count", 0)
                right_cell = f'<span class="context-tag session-tag" data-type="session" data-session-id="{session_id}" data-action="session">{title}<span class="session-time">{msg_count}条消息</span></span>'
            else:
                right_cell = "-"

            table_rows += f'<tr><td>{left_cell}</td><td>{right_cell}</td></tr>'

        history_section = f"""
<table class="session-table">
<tr><th>最近会话</th><th>最活跃会话</th></tr>
{table_rows}
</table>
"""

    welcome_md = f"""### 👋 {greeting}

---

**{tip}**

{history_section}
"""

    card = MessageCard(role="welcome", timestamp="就绪", parent=parent)
    card.update_content(welcome_md)
    card.finish_streaming()
    return card
