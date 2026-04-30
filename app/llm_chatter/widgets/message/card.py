# -*- coding: utf-8 -*-
"""消息卡片组件"""
import math
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional

from PyQt5.QtCore import Qt, QTimer, QVariantAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QLinearGradient, QPainterPath, QWheelEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import (
    FluentIcon,
    ToolTipFilter,
    TransparentToolButton,
    CardWidget,
    CaptionLabel,
)
from qfluentwidgets.components.widgets.card_widget import CardSeparator

from app.llm_chatter.widgets.message.viewer import CodeWebViewer, PlainTextViewer
from app.llm_chatter.widgets.context_selector import ContextRegistry
from app.utils.utils import get_font_family_css, get_icon


class TagWidget(CardWidget):
    """标签组件"""
    closed = pyqtSignal(str)
    doubleClicked = pyqtSignal(str)

    def __init__(self, key: str, text: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.setFixedHeight(24)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        l = QHBoxLayout(self)
        l.setContentsMargins(6, 0, 6, 0)
        l.addWidget(CaptionLabel(text, self))

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.doubleClicked.emit(self.key)
        super().mouseDoubleClickEvent(e)


class MessageCard(CardWidget):
    """消息卡片组件"""
    deleteRequested = pyqtSignal()
    undoRequested = pyqtSignal()
    actionRequested = pyqtSignal(str, str)
    contextActionRequested = pyqtSignal(str, str)
    optionSelected = pyqtSignal(dict)
    interventionRequested = pyqtSignal(dict)
    toolDiffRequested = pyqtSignal(str)  # tool_call_id
    cardDiffRequested = pyqtSignal(int)  # round_index
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
        self._round_index: Optional[int] = None
        self._reasoning_content = reasoning_content
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._update_anim)
        self._pulse_phase = 0.0
        self._height_anim = QVariantAnimation(self)
        self._height_anim.setDuration(180)
        self._height_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._height_anim.valueChanged.connect(self._apply_viewer_height)
        self._target_viewer_height = 40
        self._last_applied_viewer_height = 40
        self._theme = self._build_theme(role, error)
        self._base_bg = self._theme["bg"]
        self._base_border = self._theme["border"]
        self._last_synced_width = 0
        self._resize_anim_locked = False
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
        from app.llm_chatter.utils.message_content import ensure_content_blocks, content_to_markdown
        
        main = QVBoxLayout(self)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)
        top = QHBoxLayout()
        top.setSpacing(10)

        av = QLabel(self)
        if self.role in ("welcome", "assistant"):
            av_icon = get_icon("drifox")
            pixmap = av_icon.pixmap(28, 28)
            av.setPixmap(pixmap)
            av.setFixedSize(30, 30)
            av.setAlignment(Qt.AlignCenter)
        else:
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

        if self.role == "user" and self.context_tags:
            tg_c = QWidget(self)
            tl = QHBoxLayout(tg_c)
            tl.setContentsMargins(0, 0, 0, 0)
            tl.setSpacing(4)
            for k, (n, _, _, _) in self.context_tags.items():
                t = TagWidget(k, n)
                t.doubleClicked.connect(lambda k=k, t=t: self._on_link_click(k, t))
                tl.addWidget(t)
            tl.addStretch()
            main.addWidget(tg_c)
            main.addWidget(CardSeparator(self))

        if self.role in ("user", "welcome"):
            self.viewer = PlainTextViewer(self)
            self.viewer.contentHeightChanged.connect(self._update_height)
        else:
            self.viewer = CodeWebViewer(self)
            self.viewer.codeActionRequested.connect(self.actionRequested.emit)
            self.viewer.contextActionRequested.connect(self.contextActionRequested.emit)
            self.viewer.contentHeightChanged.connect(self._update_height)
            self.viewer.toolDiffRequested.connect(self.toolDiffRequested.emit)
            self.viewer.saveFileRequested.connect(self.saveFileRequested.emit)
            self.viewer.contextLost.connect(self._on_webengine_context_lost)
            self.viewer.contextRestored.connect(self._on_webengine_context_restored)
        main.addWidget(self.viewer)

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
        self._apply_card_style(border="#A94444")
        self._webengine_needs_restore = True

    def _on_webengine_context_restored(self):
        self._apply_card_style()
        self._webengine_needs_restore = False
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

    def _on_link_click(self, k, t):
        if ContextRegistry and k in self.context_tags:
            try:
                exe = self.parent.homepage.context_register.get_executor(k)
                if exe:
                    exe(self.context_tags[k][2], t)
            except:
                pass

    def _emit_card_diff_requested(self):
        if self._round_index is not None:
            self.cardDiffRequested.emit(self._round_index)

    def _update_height(self, h):
        target_height = max(40, h)
        current_height = self.viewer.height() or self.viewer.minimumHeight() or 40
        self._target_viewer_height = target_height

        if self._streaming or abs(target_height - current_height) < 10:
            if self._height_anim.state() == QVariantAnimation.Running:
                self._height_anim.stop()
            self._apply_viewer_height(target_height)
            return

        self._height_anim.stop()
        self._height_anim.setStartValue(current_height)
        self._height_anim.setEndValue(target_height)
        self._height_anim.start()

    def _apply_viewer_height(self, value):
        height = max(40, int(value))
        if height == self._last_applied_viewer_height:
            return
        self._last_applied_viewer_height = height
        self.viewer.setFixedHeight(height)
        self.updateGeometry()
        parent = self.parentWidget()
        if parent:
            parent.updateGeometry()

    def sync_width(self, force: bool = False):
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
        
        if not force and target_width == self._last_synced_width:
            return
        
        self._last_synced_width = target_width
        if self.minimumWidth() != target_width or self.maximumWidth() != target_width:
            self.blockSignals(True)
            self.setMinimumWidth(target_width)
            self.setMaximumWidth(target_width)
            self.blockSignals(False)

    def wheelEvent(self, event: QWheelEvent):
        try:
            scroll_area = self.parent.chat_scroll_area
            if scroll_area:
                vbar = scroll_area.verticalScrollBar()
                if vbar and vbar.minimum() != vbar.maximum() and event.angleDelta().y() != 0:
                    vbar.setValue(vbar.value() - event.angleDelta().y() // 2)
                    event.accept()
                    return
        except:
            pass
        super().wheelEvent(event)

    def update_content(self, txt):
        from app.llm_chatter.utils.message_content import ensure_content_blocks, content_to_markdown
        
        if self.role == "assistant" and not self._streaming:
            self.start_streaming_anim()
        if isinstance(txt, list):
            self.set_content(txt)
            return
        self.append_text(txt)

    def set_content(self, content: Any):
        from app.llm_chatter.utils.message_content import ensure_content_blocks, content_to_markdown
        
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
        from app.llm_chatter.utils.message_content import append_text_block, content_to_markdown
        
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
        from app.llm_chatter.utils.message_content import make_tool_result_block, content_to_markdown
        
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
        from app.llm_chatter.utils.message_content import content_to_text
        if self.role == "assistant":
            return content_to_text(self._content_data, include_tool_results=True)
        return str(self._content_data or "")

    def run_js(self, js_code: str):
        try:
            if self.viewer and hasattr(self.viewer, "page"):
                self.viewer.page().runJavaScript(js_code)
        except RuntimeError:
            pass

    def set_reasoning_content(self, content: str):
        self._reasoning_content = content
        if content and hasattr(self.viewer, "_markdown_text"):
            self.viewer._schedule_render(immediate=True)

    def set_html_direct(self, html: str):
        try:
            if self.viewer:
                self.viewer._markdown_text = html
                self.viewer._streaming = False
                self.viewer._perform_update()
        except RuntimeError:
            pass

    def append_reasoning(self, text: str):
        if not hasattr(self.viewer, '_reasoning_content'):
            return
        self._reasoning_content = (self._reasoning_content or '') + text
        self.viewer._reasoning_content = self._reasoning_content
        self.viewer._schedule_render(immediate=True)

    def add_interactive_option(self, option: Dict[str, Any]):
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
        if not options:
            return

        title_label = QLabel("👉 请选择：", self)
        title_label.setStyleSheet(f"color: #888; {get_font_family_css()} font-size: 12px; margin-top: 8px;")
        self.options_layout.addWidget(title_label)

        for option in options:
            self.add_interactive_option(option)

    def _on_option_clicked(self, option: Dict[str, Any]):
        self.optionSelected.emit(option)

    def set_intervention_mode(self, enabled: bool):
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
        if not self._resize_anim_locked:
            self._resize_anim_locked = True
            QTimer.singleShot(50, self._unlock_resize_and_sync)
    
    def _unlock_resize_and_sync(self):
        self._resize_anim_locked = False
        self.sync_width(force=True)

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


def create_welcome_card(
    parent=None, agent_name: str = "", agent_description: str = ""
) -> MessageCard:
    """创建欢迎卡片"""
    agent_tendency = ""
    if agent_name:
        agent_tendency = f"""
---

### 🤖 当前智能体：{agent_name}

{agent_description}

"""

    welcome_md = f"""\
### 👋 你好！我是 Drifox 飘狐

---
*如需切换智能体，请在输入框右下角下拉菜单中选择。*

{agent_tendency}
"""

    card = MessageCard(role="welcome", timestamp="就绪", parent=parent)
    card.update_content(welcome_md)
    card.finish_streaming()
    return card
