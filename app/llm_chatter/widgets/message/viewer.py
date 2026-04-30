# -*- coding: utf-8 -*-
"""消息查看器 - WebViewer 和文本查看器"""
import base64
import json
import re
import urllib.parse
from html import escape
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PyQt5.QtCore import QUrl

from app.utils.utils import get_font_family_css


# ==================== Console Monitor Page ====================

class ConsoleMonitorPage(QWebEnginePage):
    """控制台监控页面"""
    codeActionRequested = pyqtSignal(str, str)
    contextActionRequested = pyqtSignal(str, str)
    heightReported = pyqtSignal(int)
    contentReady = pyqtSignal()
    toolDiffRequested = pyqtSignal(str)  # tool_call_id
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
                    QDesktopServices.openUrl(QUrl(url_str))
                except:
                    pass
            elif "tool_diff:" in msg:
                try:
                    tool_call_id = msg.split("tool_diff:", 1)[1]
                    self.toolDiffRequested.emit(tool_call_id)
                except Exception:
                    pass
            elif "save_file:" in msg:
                try:
                    parts = msg.split("save_file:", 1)[1]
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


# ==================== Code Web Viewer ====================

class CodeWebViewer(QWebEngineView):
    """代码 Web 查看器"""
    contentHeightChanged = pyqtSignal(int)
    codeActionRequested = pyqtSignal(str, str)
    contextActionRequested = pyqtSignal(str, str)
    toolDiffRequested = pyqtSignal(str)  # tool_call_id
    saveFileRequested = pyqtSignal(str, str)  # code, lang
    contextLost = pyqtSignal()
    contextRestored = pyqtSignal()

    MAX_WIDTH = 1600
    MAX_HEIGHT = 2000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._markdown_text = ""
        self._streaming = True
        self._is_js_ready = False
        self._last_rendered_html = ""
        self._last_rendered_markdown = ""
        self._reasoning_content = ""
        self._min_render_interval = 50
        self._height_report_pending = False
        self._context_lost = False
        self._context_lost_count = 0
        
        # 定时器
        self._resize_debounce_timer = QTimer(self)
        self._resize_debounce_timer.setSingleShot(True)
        self._resize_debounce_timer.setInterval(100)
        self._resize_debounce_timer.timeout.connect(self._do_resize_check)
        
        self._resize_locked = False
        self._resize_unlock_timer = QTimer(self)
        self._resize_unlock_timer.setSingleShot(True)
        self._resize_unlock_timer.setInterval(150)
        self._resize_unlock_timer.timeout.connect(self._on_resize_unlock)
        
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._perform_update)
        
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(50)
        self._resize_timer.timeout.connect(self._safe_report_height)

        self._page = ConsoleMonitorPage(self)
        self.setPage(self._page)
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
        self._page.saveFileRequested.connect(self.saveFileRequested.emit)

        self._load_skeleton()

    def _handle_context_lost(self):
        if not self._context_lost:
            self._context_lost = True
            self._context_lost_count += 1
            self.contextLost.emit()
            self._schedule_context_restore()

    def _schedule_context_restore(self):
        QTimer.singleShot(500, self._try_restore_context)

    def _try_restore_context(self):
        try:
            if self._context_lost:
                self._context_lost = False
                self.contextRestored.emit()
                self._is_js_ready = False
                self._load_skeleton()
        except Exception:
            pass

    def _install_dialog_filter(self):
        from PyQt5.QtCore import QEvent
        from PyQt5.QtWidgets import QInputDialog, QFileDialog
        
        old_event = self.event
        
        def new_event(event):
            if event.type() == QEvent.Type.KeyPress:
                return True
            return old_event(event)
        
        self.event = new_event

    def _load_skeleton(self):
        font_css = get_font_family_css()
        skeleton = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{font_css}
body {{
    margin: 0; padding: 0; background: transparent; font-family: inherit;
    font-size: 14px; line-height: 1.6; color: #E0E0E0;
}}
#content-placeholder {{ min-height: 40px; }}
</style>
</head>
<body>
<div id="content-placeholder"></div>
<script>
function updateContent(html) {{
    var ph = document.getElementById('content-placeholder');
    if (ph) {{
        ph.innerHTML = html;
        window.scrollTo(0, 0);
        var h = document.body.scrollHeight;
        if (window.pywebview !== undefined) {{
            window.pywebview.height = h;
            window.pywebview.api.resize(h);
        }}
    }}
}}
function getScrollHeight() {{ return document.body.scrollHeight; }}
function getContentHeight() {{ 
    var ph = document.getElementById('content-placeholder');
    return ph ? ph.offsetHeight : 0;
}}
function reportHeight() {{
    var h = document.body.scrollHeight;
    console.log('pywebview_height:' + h);
}}
document.addEventListener('DOMContentLoaded', function() {{
    console.log('pywebview_ready');
    window.pywebviewReady = true;
}});
document.addEventListener('click', function(e) {{
    var target = e.target;
    if (target.tagName === 'BUTTON' || target.tagName === 'A') {{
        var action = target.getAttribute('data-action');
        if (action) {{
            if (action === 'copy') {{
                var copyData = target.getAttribute('data-copy');
                if (copyData) {{
                    navigator.clipboard.writeText(atob(copyData));
                    console.log('pywebview_action:copy:' + btoa('复制成功'));
                }}
            }} else if (action === 'insert') {{
                console.log('pywebview_action:insert:' + btoa(target.getAttribute('data-code') || ''));
            }} else if (action === 'create') {{
                console.log('pywebview_action:create:' + btoa(target.getAttribute('data-code') || ''));
            }}
        }}
        var href = target.getAttribute('href');
        if (href && href !== '#') {{
            console.log('pywebview_action:open_url:' + href);
            e.preventDefault();
        }}
    }}
    var contextTag = target.closest('.context-tag');
    if (contextTag) {{
        var t = contextTag.getAttribute('data-type');
        var c = contextTag.getAttribute('data-content');
        var a = contextTag.getAttribute('data-action');
        if (t && c) {{
            console.log('pywebview_action:context|||' + c + '||' + a);
        }}
        e.preventDefault();
    }}
}});
window.addEventListener('error', function(e) {{
    if (e.message.includes('pywebview')) return;
    console.log('js_error:' + e.message);
}});
</script>
</body>
</html>"""
        self.setHtml(skeleton)

    def _on_js_ready(self):
        self._is_js_ready = True
        if self._markdown_text:
            self._schedule_render(immediate=True)

    def _safe_report_height(self):
        try:
            h = self.page().runJavaScript("getContentHeight()")
            if isinstance(h, (int, float)) and h > 0:
                h = min(int(h), self.MAX_HEIGHT)
                if abs(self.height() - h) > 2:
                    self.setFixedHeight(h)
                    self.contentHeightChanged.emit(h)
        except Exception:
            pass
        self._height_report_pending = False

    def _on_height_reported(self, h):
        if h <= 0 or h > self.MAX_HEIGHT:
            return
        if abs(self.height() - h) > 2:
            self.setFixedHeight(h)
            self.contentHeightChanged.emit(h)

    def _do_resize_check(self):
        try:
            js = "getScrollHeight()"
            h = self.page().runJavaScript(js)
            if isinstance(h, (int, float)) and h > 0:
                h = min(int(h), self.MAX_HEIGHT)
                if abs(self.height() - h) > 2:
                    self.setFixedHeight(h)
                    self.contentHeightChanged.emit(h)
        except Exception:
            pass

    def _on_resize_unlock(self):
        self._resize_locked = False

    def _schedule_render(self, immediate=False):
        if immediate:
            self._render_timer.setInterval(10)
        else:
            interval = self._min_render_interval if self._streaming else 40
            self._render_timer.setInterval(interval)
        if self._render_timer.isActive():
            return
        self._render_timer.start(interval if not immediate else 10)

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

    def _render_markdown_to_html(self, md_text: str) -> str:
        from app.llm_chatter.widgets.message.renderer import (
            render_markdown,
            unwrap_code_blocks_with_context_links,
            _inject_context_links,
        )
        from markdown import Markdown
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import get_lexer_by_name, TextLexer
        from app.llm_chatter.widgets.render_helpers import render_tool_block
        
        md_text = unwrap_code_blocks_with_context_links(md_text)
        
        # 处理 <think> 标签
        md_text = self._inject_think_blocks(md_text)
        
        # 处理工具标签
        md_text = self._inject_tool_blocks(md_text)
        
        # 渲染 Markdown
        md = Markdown(extensions=["fenced_code", "nl2br", "tables"], output_format="html5", safe=False)
        html = md.convert(md_text)
        
        # 处理代码块
        html = self._wrap_code_blocks_with_copy_button_web(html)
        
        # 注入上下文链接
        html = _inject_context_links(html)
        
        # 注入工具块
        html = self._inject_tool_block_components(html)
        
        return self._build_full_html(html)

    def _build_full_html(self, content: str) -> str:
        from app.llm_chatter.widgets.message.style import MARKDOWN_CSS
        from app.llm_chatter.widgets.render_helpers import get_card_css
        
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{MARKDOWN_CSS}
{get_card_css()}
</style>
</head>
<body>
<div id="content-placeholder">{content}</div>
</body>
</html>"""

    def _wrap_code_blocks_with_copy_button_web(self, html: str) -> str:
        pattern = re.compile(r"<pre><code(?:\s+class=\"([^\"]*)\")?>(.*?)</code></pre>", re.DOTALL)
        
        def replacer(match):
            lang = (match.group(1) or "").replace("language-", "").strip()
            code_content_raw = match.group(2) or ""
            
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
                pre_match = re.search(r"<pre[^>]*>(.*?)</pre>", highlighted, re.DOTALL)
                if pre_match:
                    inner_code_html = pre_match.group(1)
                else:
                    inner_code_html = escape(copy_text)
            except Exception:
                inner_code_html = escape(copy_text)

            line_numbers_text = "\n".join(str(i + 1) for i in range(line_count))

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
                background: rgba(30, 32, 40, 0.85);
                border: 1px solid rgba(58, 63, 71, 0.6);
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.18), 0 1px 3px rgba(0,0,0,0.2);
                backdrop-filter: blur(8px);
                font-family: Consolas, monospace;
                font-size: 13px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; height: 30px; background: rgba(28, 28, 36, 0.75); border-bottom: 1px solid rgba(45, 45, 57, 0.5); border-radius: 10px 10px 0 0;">
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
                <div style="padding: 8px 0 0 0; border-radius: 0 0 10px 10px;">
                    {code_block_html}
                </div>
            </div>
            '''

        return pattern.sub(replacer, html)

    def _inject_think_blocks(self, md_text: str) -> str:
        if not md_text:
            return md_text
            
        parts = []
        i = 0
        while i < len(md_text):
            start_idx = md_text.find("<think>", i)
            if start_idx == -1:
                parts.append(md_text[i:])
                break
            parts.append(md_text[i:start_idx])
            think_start = start_idx + len("<think>")
            next_think = md_text.find("<think>", think_start)
            search_end = next_think if next_think != -1 else len(md_text)
            end_idx = md_text.rfind("</think>", think_start, search_end)
            
            if end_idx != -1:
                content = md_text[think_start:end_idx]
                parts.append(f"<think>{content}</think>")
                i = end_idx + len("</think>")
            else:
                parts.append(md_text[start_idx:])
                break
        return "".join(parts)

    def _inject_tool_blocks(self, md_text: str) -> str:
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
                content = md_text[start_idx + len("<tool>"):end_idx]
                parts.append(f"<toolcall>{content}</toolcall>")
                i = end_idx + len("</tool>")
            else:
                parts.append(md_text[start_idx:])
                break
        return "".join(parts)

    def _inject_tool_block_components(self, html: str) -> str:
        from app.llm_chatter.widgets.render_helpers import render_tool_block
        import json
        
        def replace_tool(match):
            content = match.group(1)
            tool_name, arguments, result, success, tool_call_id = self._parse_tool_content(content)
            
            args_dict = {}
            if arguments:
                try:
                    args_dict = json.loads(arguments)
                except:
                    pass
                    
            return render_tool_block(
                tool_name or "unknown",
                args_dict,
                result or "",
                success if success is not None else True,
                tool_call_id=tool_call_id
            )
            
        return re.sub(r'<toolcall>(.*?)</toolcall>', replace_tool, html, flags=re.DOTALL)

    def _parse_tool_content(self, content: str):
        tool_name = None
        arguments = None
        result = None
        success = None
        tool_call_id = None
        
        for line in content.split('\n'):
            if line.startswith('name:'):
                tool_name = line[5:].strip()
            elif line.startswith('arguments:'):
                arguments = line[10:].strip()
            elif line.startswith('result:'):
                result = line[8:].strip()
            elif line.startswith('success:'):
                success = line[9:].strip().lower() == 'true'
            elif line.startswith('tool_call_id:'):
                tool_call_id = line[13:].strip()
                
        return tool_name, arguments, result, success, tool_call_id

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
        if not self._resize_locked:
            self._resize_locked = True
            self._resize_unlock_timer.stop()
            self._resize_unlock_timer.start()

    def wheelEvent(self, event):
        from PyQt5.QtGui import QWheelEvent
        scroll_area = self.parent().parent.chat_scroll_area
        if scroll_area:
            vbar = scroll_area.verticalScrollBar()
            if vbar and vbar.minimum() != vbar.maximum():
                delta = event.angleDelta().y()
                vbar.setValue(vbar.value() - delta // 2)
                event.accept()
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


# ==================== Plain Text Viewer ====================

class PlainTextViewer(QWidget):
    """纯文本查看器"""
    contentHeightChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self._init_ui()

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
        vp_width = self.text_edit.viewport().width()
        if vp_width > 0:
            self.text_edit.document().setTextWidth(vp_width)
        QTimer.singleShot(100, self._update_height)

    def _update_height(self):
        self.text_edit.update()
        self.text_edit.document().markContentsDirty(0, self.text_edit.document().characterCount())
        self.text_edit.ensurePolished()
        doc = self.text_edit.document()
        h = int(doc.size().height()) + 16
        h = max(40, h)
        if abs(self.height() - h) > 2:
            self.setFixedHeight(h)
            self.contentHeightChanged.emit(h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_height()
