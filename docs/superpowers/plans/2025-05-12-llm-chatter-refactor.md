# LLM Chatter 重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 LLM Chatter 模块从强耦合系统拆出后进行分层解耦，消除冗余代码，提升性能

**Architecture:** 
- 事件总线（EventBus）解耦模块间回调
- 上下文管理器（ContextManager）隔离 Token 计算和历史压缩
- 交互控制器（InteractionController）管理状态机
- MessageCard 拆分为 renderer/content/style 三层

**Tech Stack:** Python 3.8+, PyQt5, asyncio

---

## 文件结构

```
app/llm_chatter/
├── core/
│   ├── __init__.py
│   ├── event_bus.py         # 新增：事件总线
│   ├── context_manager.py  # 新增：上下文管理
│   ├── session_store.py     # 新增：会话持久化
│   ├── chat_engine.py       # 修改：简化，仅保留核心接口
│   ├── tool_executor.py     # 修改：接入 EventBus
│   ├── agent.py             # 保持
│   └── memory_manager.py    # 保持
├── widgets/
│   ├── message/             # 新增目录
│   │   ├── __init__.py
│   │   ├── card.py          # 从 message_card.py 提取
│   │   ├── renderer.py      # 从 message_card.py 提取
│   │   ├── content.py       # 从 message_card.py 提取
│   │   └── style.py         # 从 message_card.py 提取
│   ├── interaction/         # 新增目录
│   │   ├── __init__.py
│   │   ├── controller.py    # 新增：交互控制器
│   │   └── state.py         # 新增：状态定义
│   ├── floating/           # 新增目录
│   │   ├── __init__.py
│   │   ├── base.py         # 从各 floating_widget 提取
│   │   ├── tool.py         # 修改
│   │   ├── todo.py         # 修改
│   │   ├── question.py     # 修改
│   │   └── agent.py        # 修改
│   ├── __init__.py
│   └── [其他组件保持]
└── main_widget.py          # 修改：大幅精简
```

---

## Phase 1: 基础设施

### Task 1: 创建 EventBus

**Files:**
- Create: `app/llm_chatter/core/event_bus.py`
- Modify: `app/llm_chatter/core/__init__.py`

- [ ] **Step 1: 创建 event_bus.py**

```python
# app/llm_chatter/core/event_bus.py
# -*- coding: utf-8 -*-
"""事件总线 - 解耦模块间通信"""
from typing import Any, Callable, Dict, List
from loguru import logger


class EventBus:
    """事件总线，替代直接回调，解耦模块间通信"""
    
    CONTENT_RECEIVED = "content_received"
    REASONING_CONTENT_RECEIVED = "reasoning_content_received"
    STREAM_STARTED = "stream_started"
    STREAM_FINISHED = "stream_finished"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_SYNC_REQUESTED = "tool_call_sync_requested"
    TOOL_RESULT_RECEIVED = "tool_result_received"
    MESSAGES_UPDATED = "messages_updated"
    ERROR = "error"
    USER_MESSAGE_ADDED = "user_message_added"
    SKILL_REQUESTED = "skill_requested"
    SHELL_COMMAND_REQUESTED = "shell_command_requested"
    QUESTION_ASKED = "question_asked"
    AGENT_SWITCHED = "agent_switched"
    TASK_STATE_CHANGED = "task_state_changed"
    PERMISSION_APPROVAL_REQUESTED = "permission_approval_requested"
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._event_history: List[tuple] = []  # 用于调试
        self._max_history = 100
        
    def on(self, event_type: str, handler: Callable) -> None:
        """订阅事件"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            
    def off(self, event_type: str, handler: Callable) -> None:
        """退订事件"""
        if event_type in self._handlers:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
                
    def emit(self, event_type: str, *args, **kwargs) -> None:
        """发布事件"""
        # 记录历史
        self._event_history.append((event_type, args, kwargs))
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
            
        # 分发事件
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Event handler error: {event_type}")
                
    def clear(self, event_type: str = None) -> None:
        """清除事件订阅"""
        if event_type:
            self._handlers.pop(event_type, None)
        else:
            self._handlers.clear()
            
    def get_subscribers(self, event_type: str) -> List[Callable]:
        """获取事件订阅者（用于调试）"""
        return list(self._handlers.get(event_type, []))
```

- [ ] **Step 2: 更新 core/__init__.py**

```python
# 添加到 app/llm_chatter/core/__init__.py
from .event_bus import EventBus
```

- [ ] **Step 3: 验证**

Run: `python -c "from app.llm_chatter.core import EventBus; eb = EventBus(); print('EventBus created')"`
Expected: `EventBus created`

- [ ] **Step 4: Commit**

```bash
git add app/llm_chatter/core/event_bus.py app/llm_chatter/core/__init__.py
git commit -m "feat(core): add EventBus for decoupled module communication"
```

---

### Task 2: 创建 ContextManager

**Files:**
- Create: `app/llm_chatter/core/context_manager.py`
- Modify: `app/llm_chatter/core/__init__.py`

- [ ] **Step 1: 从 chat_engine.py 提取上下文逻辑**

首先查看 chat_engine.py 中的上下文相关方法：

```bash
grep -n "def _" app/llm_chatter/core/chat_engine.py | head -30
```

- [ ] **Step 2: 创建 context_manager.py**

```python
# app/llm_chatter/core/context_manager.py
# -*- coding: utf-8 -*-
"""上下文管理器 - Token 预算、历史压缩、消息组装"""
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime
from loguru import logger

from app.llm_chatter.utils.token_estimator import count_messages_tokens
from app.llm_chatter.utils.message_content import content_to_text

MAX_HISTORY_SNIPPET_CHARS = 1200
RECENT_HISTORY_MIN_MESSAGES = 6


class ContextManager:
    """上下文管理：Token 预算、历史压缩、消息组装"""
    
    def __init__(self, budget_tokens: int = 120000):
        self._budget_tokens = budget_tokens
        self._soft_limit = int(budget_tokens * 0.75)
        self._target_limit = int(budget_tokens * 0.65)
        
    def set_budget(self, budget_tokens: int) -> None:
        """设置 Token 预算"""
        self._budget_tokens = budget_tokens
        self._soft_limit = int(budget_tokens * 0.75)
        self._target_limit = int(budget_tokens * 0.65)
        
    def build_messages(
        self,
        session,
        memory_context: str = "",
        system_prompt: str = "",
    ) -> List[Dict[str, Any]]:
        """构建发送给 LLM 的消息列表"""
        messages = []
        
        # 1. 系统消息
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if memory_context:
            messages.append({"role": "system", "content": memory_context})
            
        # 2. 历史消息
        history_messages = session.get_messages()
        messages.extend(history_messages)
        
        return messages
        
    def count_tokens(self, messages: List[Dict]) -> int:
        """计算消息列表的 token 总数"""
        return count_messages_tokens(messages)
        
    def should_compact(self, messages: List[Dict]) -> bool:
        """检查是否需要压缩"""
        total = self.count_tokens(messages)
        return total > self._soft_limit
        
    def get_compaction_needed(self, messages: List[Dict]) -> bool:
        """是否需要触发压缩"""
        return self.count_tokens(messages) > self._soft_limit
        
    def compact(
        self,
        messages: List[Dict],
        keep_tail: int = 6,
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        压缩历史消息
        
        Returns:
            (压缩后的消息, 压缩元数据)
        """
        if not messages:
            return [], {"active": False}
            
        # 保留最近 N 条消息
        tail_messages = messages[-keep_tail:] if len(messages) > keep_tail else messages
        compacted = messages[:-keep_tail] if len(messages) > keep_tail else []
        
        # 构建摘要
        summary_msg = {
            "role": "system",
            "content": f"[{len(compacted)} 条历史消息已压缩]"
        }
        
        result = [summary_msg] + tail_messages
        meta = {
            "active": True,
            "original_count": len(messages),
            "compacted_count": len(compacted),
            "kept_count": len(tail_messages),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        return result, meta
```

- [ ] **Step 3: 更新 core/__init__.py**

```python
# 添加到 app/llm_chatter/core/__init__.py
from .context_manager import ContextManager
```

- [ ] **Step 4: Commit**

```bash
git add app/llm_chatter/core/context_manager.py
git commit -m "feat(core): add ContextManager for token budget and message compaction"
```

---

### Task 3: 创建 InteractionController

**Files:**
- Create: `app/llm_chatter/widgets/interaction/state.py`
- Create: `app/llm_chatter/widgets/interaction/controller.py`
- Modify: `app/llm_chatter/widgets/__init__.py`

- [ ] **Step 1: 创建 interaction/state.py**

```python
# app/llm_chatter/widgets/interaction/state.py
# -*- coding: utf-8 -*-
"""交互状态定义"""
from enum import Enum


class InteractionState(Enum):
    """交互状态枚举"""
    IDLE = "idle"
    STREAMING = "streaming"
    WAITING_PERMISSION = "waiting_permission"
    WAITING_QUESTION = "waiting_question"
    PAUSED = "paused"


class StreamState:
    """流式响应状态"""
    
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.is_streaming = False
        self.tool_call_depth = 0
        self.pending_tool_calls = 0
        self.first_tool_result = True
        self.tool_cancelled_by_user = False
        self.cancelled_tool_call_id = None
        
    def start_stream(self):
        self.is_streaming = True
        
    def stop_stream(self):
        self.is_streaming = False
```

- [ ] **Step 2: 创建 interaction/controller.py**

```python
# app/llm_chatter/widgets/interaction/controller.py
# -*- coding: utf-8 -*-
"""交互控制器 - 管理 Agent 切换、权限确认、状态同步"""
from typing import Optional, Dict, Any, Callable
from loguru import logger

from app.llm_chatter.widgets.interaction.state import InteractionState, StreamState


class InteractionController:
    """交互状态机：管理 Agent 切换、权限确认、状态同步"""
    
    def __init__(self, event_bus):
        self._event_bus = event_bus
        self._state = InteractionState.IDLE
        self._stream_state = StreamState()
        self._current_agent = "plan"
        self._permission_queue = []
        self._question_tool_call_id = None
        
        # 注册事件监听
        self._event_bus.on("stream_started", self._on_stream_started)
        self._event_bus.on("stream_finished", self._on_stream_finished)
        self._event_bus.on("tool_call_started", self._on_tool_call_started)
        self._event_bus.on("tool_result_received", self._on_tool_result_received)
        
    @property
    def state(self) -> InteractionState:
        return self._state
        
    @property
    def stream_state(self) -> StreamState:
        return self._stream_state
        
    @property
    def current_agent(self) -> str:
        return self._current_agent
        
    def set_agent(self, agent: str):
        """设置当前 Agent"""
        if agent != self._current_agent:
            self._current_agent = agent
            self._event_bus.emit("agent_switched", agent)
            
    def start_stream(self):
        """开始流式响应"""
        self._state = InteractionState.STREAMING
        self._stream_state.start_stream()
        self._event_bus.emit("stream_started")
        
    def stop_stream(self):
        """停止流式响应"""
        self._state = InteractionState.IDLE
        self._stream_state.stop_stream()
        self._event_bus.emit("stream_finished")
        
    def request_permission(self, tool_call_id: str, details: Dict):
        """请求权限"""
        self._state = InteractionState.WAITING_PERMISSION
        self._permission_queue.append((tool_call_id, details))
        
    def confirm_permission(self):
        """确认权限"""
        if self._permission_queue:
            tool_call_id, _ = self._permission_queue.pop(0)
            self._state = InteractionState.STREAMING if self._stream_state.is_streaming else InteractionState.IDLE
            self._event_bus.emit("permission_confirmed", tool_call_id)
            
    def cancel_permission(self):
        """取消权限"""
        if self._permission_queue:
            tool_call_id, _ = self._permission_queue.pop(0)
            self._stream_state.tool_cancelled_by_user = True
            self._stream_state.cancelled_tool_call_id = tool_call_id
            self._state = InteractionState.IDLE
            
    def _on_stream_started(self):
        self._stream_state.start_stream()
        
    def _on_stream_finished(self):
        self._stream_state.stop_stream()
        self._state = InteractionState.IDLE
        
    def _on_tool_call_started(self, tool_call_id: str, tool_name: str, arguments: dict, round_id: str):
        self._stream_state.tool_call_depth += 1
        self._stream_state.pending_tool_calls += 1
        self._stream_state.first_tool_result = True
        
    def _on_tool_result_received(self, tool_call_id: str, result: Any, success: bool):
        self._stream_state.pending_tool_calls -= 1
        self._stream_state.first_tool_result = False
```

- [ ] **Step 3: 创建 interaction/__init__.py**

```python
# app/llm_chatter/widgets/interaction/__init__.py
from .state import InteractionState, StreamState
from .controller import InteractionController
```

- [ ] **Step 4: Commit**

```bash
git add app/llm_chatter/widgets/interaction/
git commit -m "feat(widgets): add InteractionController for state management"
```

---

## Phase 2: UI 拆分

### Task 4: 拆分 MessageCard

**Files:**
- Create: `app/llm_chatter/widgets/message/style.py`
- Create: `app/llm_chatter/widgets/message/content.py`
- Create: `app/llm_chatter/widgets/message/renderer.py`
- Create: `app/llm_chatter/widgets/message/card.py`
- Create: `app/llm_chatter/widgets/message/__init__.py`
- Modify: `app/llm_chatter/widgets/__init__.py`
- Backup: `app/llm_chatter/widgets/message_card.py` (稍后删除)

- [ ] **Step 1: 分析 message_card.py 结构**

读取 message_card.py，识别主要代码段：
- 样式定义（颜色、字体、动画）
- 内容块处理（text/tool_result）
- Markdown 渲染
- 卡片容器

```bash
grep -n "^class\|^def " app/llm_chatter/widgets/message_card.py
```

- [ ] **Step 2: 创建 message/style.py**

```python
# app/llm_chatter/widgets/message/style.py
# -*- coding: utf-8 -*-
"""消息样式定义"""
from PyQt5.QtGui import QColor

# 动作颜色映射
ACTION_COLOR_MAP = {
    "jump": "#FFA500",
    "create": "#9370DB",
    "generate": "#32CD32",
    "ask": "#FF6347",
    "view": "#4169E1",
}
DEFAULT_ACTION_COLOR = "#888888"

# 预编译正则
import re
_CODE_BLOCK_PATTERN = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_CODE_BLOCK_WITH_LANG_PATTERN = re.compile(r"<pre><code(?:\s+class=\"([^\"]*)\")?>(.*?)</code></pre>", re.DOTALL)
_CONTEXT_LINK_PATTERN = re.compile(r"`*\[([^\[\]]+?)\]\(([^)\s]+)\)`*")

# 卡片样式模板
CARD_STYLE_TEMPLATE = """
MessageCard {{
    background-color: {bg_color};
    border: {border};
    border-radius: 12px;
    padding: 12px;
}}
"""

USER_CARD_STYLE = CARD_STYLE_TEMPLATE.format(
    bg_color="rgba(40, 50, 70, 180)",
    border="1px solid rgba(80, 100, 140, 150)"
)

ASSISTANT_CARD_STYLE = CARD_STYLE_TEMPLATE.format(
    bg_color="rgba(30, 35, 45, 200)",
    border="1px solid rgba(60, 80, 110, 120)"
)

TOOL_CARD_STYLE = CARD_STYLE_TEMPLATE.format(
    bg_color="rgba(25, 30, 40, 220)",
    border="1px solid rgba(100, 120, 160, 100)"
)
```

- [ ] **Step 3: 创建 message/content.py**

```python
# app/llm_chatter/widgets/message/content.py
# -*- coding: utf-8 -*-
"""消息内容块定义"""
from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class TextBlock:
    """文本块"""
    text: str
    is_thinking: bool = False
    
@dataclass  
class ToolResultBlock:
    """工具结果块"""
    name: str
    arguments: dict
    result: str
    success: bool = True
    tool_call_id: Optional[str] = None

@dataclass
class MessageContent:
    """消息内容容器"""
    blocks: List[Any]  # TextBlock or ToolResultBlock
    
    @classmethod
    def from_raw(cls, content: Any) -> "MessageContent":
        """从原始内容创建"""
        # 复用现有的 ensure_content_blocks
        from app.llm_chatter.utils.message_content import ensure_content_blocks
        blocks = ensure_content_blocks(content)
        return cls(blocks=blocks)
```

- [ ] **Step 4: 创建 message/renderer.py**

```python
# app/llm_chatter/widgets/message/renderer.py
# -*- coding: utf-8 -*-
"""消息渲染器 - Markdown 解析、代码高亮、HTML 生成"""
import base64
import re
from typing import Optional, Callable
from functools import lru_cache
from markdown import Markdown

from app.llm_chatter.widgets.message.style import (
    ACTION_COLOR_MAP, DEFAULT_ACTION_COLOR,
    _CODE_BLOCK_PATTERN, _CONTEXT_LINK_PATTERN,
)

# Markdown 实例（模块级缓存）
_md_instance = None

def get_markdown_instance():
    global _md_instance
    if _md_instance is None:
        _md_instance = Markdown(
            extensions=["fenced_code", "nl2br", "tables"],
            output_format="html5",
            safe=False,
        )
    return _md_instance

@lru_cache(maxsize=128)
def render_markdown(content: str) -> str:
    """渲染 Markdown（带缓存）"""
    md = get_markdown_instance()
    # 重置状态
    md.reset()
    return md.convert(content)

def render_code_block(code: str, lang: str = "") -> str:
    """渲染代码块"""
    try:
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name, TextLexer
        from pygments.formatters import HtmlFormatter
        
        lexer = get_lexer_by_name(lang) if lang else TextLexer()
        formatter = HtmlFormatter(nowrap=True)
        highlighted = highlight(code, lexer, formatter)
        
        # 添加行号
        lines = code.splitlines()
        if len(lines) > 1:
            line_numbers = "\n".join(f"<span class='line-num'>{i+1}</span>" for i in range(len(lines)))
            return f"<div class='code-block'>{line_numbers}{highlighted}</div>"
        return highlighted
    except Exception:
        return f"<pre><code>{code}</code></pre>"

def render_tool_block(tool_name: str, arguments: dict, result: str, success: bool) -> str:
    """渲染工具调用块"""
    status_class = "success" if success else "error"
    status_icon = "✓" if success else "✗"
    return f"""
    <div class='tool-block {status_class}'>
        <div class='tool-header'>
            <span class='tool-icon'>{status_icon}</span>
            <span class='tool-name'>{tool_name}</span>
        </div>
        <div class='tool-result'>{result}</div>
    </div>
    """
```

- [ ] **Step 5: 创建 message/card.py（精简版）**

```python
# app/llm_chatter/widgets/message/card.py
# -*- coding: utf-8 -*-
"""消息卡片 - 精简版容器"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from qfluentwidgets import CardWidget

from app.llm_chatter.widgets.message.style import (
    USER_CARD_STYLE, ASSISTANT_CARD_STYLE
)
from app.llm_chatter.widgets.message.renderer import (
    render_markdown, render_tool_block
)


class MessageCard(CardWidget):
    """消息卡片 - 精简版容器"""
    
    diffRequested = pyqtSignal(int)  # round_index
    copyRequested = pyqtSignal(str)
    
    def __init__(self, role: str = "assistant", parent=None):
        super().__init__(parent)
        self._role = role
        self._round_index = -1
        self._setup_ui()
        
    def _setup_ui(self):
        style = USER_CARD_STYLE if self._role == "user" else ASSISTANT_CARD_STYLE
        self.setStyleSheet(style)
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        
        self._content_label = QLabel(self)
        self._content_label.setWordWrap(True)
        self._layout.addWidget(self._content_label)
        
    def set_content(self, blocks: list):
        """设置内容块"""
        html_parts = []
        for block in blocks:
            if block.get("type") == "text":
                text = block.get("text", "")
                html_parts.append(render_markdown(text))
            elif block.get("type") == "tool_result":
                html_parts.append(render_tool_block(
                    block.get("name", "tool"),
                    block.get("arguments", {}),
                    block.get("result", ""),
                    block.get("success", True)
                ))
        self._content_label.setText("\n".join(html_parts))
        
    def set_round_index(self, index: int):
        self._round_index = index
        
    def get_round_index(self) -> int:
        return self._round_index


def create_welcome_card() -> MessageCard:
    """创建欢迎卡片"""
    card = MessageCard(role="assistant")
    card.set_content([{
        "type": "text",
        "text": "# 欢迎使用 DriFox\n\n我是你的 AI 编程助手，可以帮你：\n\n- 编写和修改代码\n- 执行终端命令\n- 搜索和分析代码库\n- 回答技术问题"
    }])
    return card
```

- [ ] **Step 6: 创建 message/__init__.py**

```python
# app/llm_chatter/widgets/message/__init__.py
from .card import MessageCard, create_welcome_card
from .content import MessageContent, TextBlock, ToolResultBlock
from .renderer import render_markdown, render_code_block, render_tool_block
from .style import ACTION_COLOR_MAP, DEFAULT_ACTION_COLOR
```

- [ ] **Step 7: 更新 widgets/__init__.py**

```python
# 添加到 app/llm_chatter/widgets/__init__.py
from .message import MessageCard, create_welcome_card
```

- [ ] **Step 8: Commit**

```bash
git add app/llm_chatter/widgets/message/
git commit -m "refactor(widgets): split message_card.py into message/ module"
```

---

### Task 5: 合并 FloatingWidgets

**Files:**
- Create: `app/llm_chatter/widgets/floating/base.py`
- Create: `app/llm_chatter/widgets/floating/tool.py`
- Create: `app/llm_chatter/widgets/floating/todo.py`
- Create: `app/llm_chatter/widgets/floating/question.py`
- Create: `app/llm_chatter/widgets/floating/agent.py`
- Create: `app/llm_chatter/widgets/floating/__init__.py`
- Modify: `app/llm_chatter/widgets/__init__.py`

- [ ] **Step 1: 分析现有浮窗组件**

```bash
grep -n "class.*FloatingWidget" app/llm_chatter/widgets/*.py
```

识别共同模式：位置计算、透明度、显示/隐藏动画

- [ ] **Step 2: 创建 floating/base.py**

```python
# app/llm_chatter/widgets/floating/base.py
# -*- coding: utf-8 -*-
"""浮窗基类"""
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, pyqtProperty
from PyQt5.QtWidgets import QWidget

class FloatingWidgetBase(QWidget):
    """浮窗基类：统一位置、动画、透明度处理"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._opacity = 1.0
        self._setup_base()
        
    def _setup_base(self):
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
    def set_opacity(self, opacity: float):
        """设置透明度"""
        self._opacity = opacity
        self._update_opacity()
        
    def _update_opacity(self):
        self.setWindowOpacity(self._opacity)
        
    def position_at_top_right(self, reference_widget: QWidget, offset_x: int = 0, offset_y: int = 0):
        """定位到参考控件的右上角"""
        ref_pos = reference_widget.mapToGlobal(reference_widget.rect().topRight())
        self.move(ref_pos.x() + offset_x, ref_pos.y() + offset_y)
        
    def position_at_bottom_right(self, reference_widget: QWidget, offset_x: int = 0, offset_y: int = 0):
        """定位到参考控件的右下角"""
        ref_pos = reference_widget.mapToGlobal(reference_widget.rect().bottomRight())
        self.move(ref_pos.x() + offset_x, ref_pos.y() + offset_y)
        
    def show_with_animation(self):
        """带动画显示"""
        self.show()
        effect = self.graphicsEffect()
        if effect:
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(200)
            anim.setStartValue(0)
            anim.setEndValue(self._opacity)
            anim.start()
            
    def hide_with_animation(self):
        """带动画隐藏"""
        self.hide()
```

- [ ] **Step 3: 创建各浮窗实现（复用现有逻辑）**

具体实现从现有文件提取：
- `tool.py` - 从 `tool_floating_widget.py` 提取
- `todo.py` - 从 `todo_floating_widget.py` 提取
- `question.py` - 从 `question_floating_widget.py` 提取
- `agent.py` - 从 `sub_agent_floating_widget.py` 提取

- [ ] **Step 4: Commit**

```bash
git add app/llm_chatter/widgets/floating/
git commit -m "refactor(widgets): merge floating widgets into floating/ module"
```

---

## Phase 3: 核心重构

### Task 6: 重构 main_widget.py

**Files:**
- Modify: `app/llm_chatter/main_widget.py` (大幅精简)

- [ ] **Step 1: 分析 main_widget.py 中的代码分类**

```bash
# 统计各功能块的行数分布
grep -n "def _" app/llm_chatter/main_widget.py | head -50
```

识别主要方法类别：
- UI 设置 (`setup_ui`, `_setup_title_bar`)
- 会话管理 (`_create_new_session`, `_restore_latest_or_create_session`)
- 消息渲染 (`_render_message_to_card`, `_create_history_card`)
- 事件处理 (`_on_content_received`, `_on_tool_call_started`)
- 浮窗管理 (`_show_*_floating_widget`)

- [ ] **Step 2: 移除直接回调，改为事件订阅**

将 `set_callback` 调用改为：

```python
# 在 __init__ 中
self._event_bus = EventBus()
self._interaction_controller = InteractionController(self._event_bus)

# 将 set_callback 替换为事件订阅
self._event_bus.on("content_received", self._on_content_received)
self._event_bus.on("stream_started", self._on_stream_started)
# ... 其他事件
```

- [ ] **Step 3: 提取 UI 代码到独立方法组**

```python
# ===== UI 设置 =====
def _setup_ui(self): ...
def _setup_title_bar(self): ...
def _setup_chat_area(self): ...
def _setup_input_area(self): ...

# ===== 会话管理 =====
def _create_new_session(self): ...
def _restore_latest_or_create_session(self): ...
def _auto_save_current_session(self): ...

# ===== 消息渲染 =====
def _render_message_to_card(self, batches): ...
def _create_history_card(self, session): ...
def _clear_chat_area(self): ...

# ===== 事件处理 (精简后) =====
def _on_content_received(self, content): ...
def _on_stream_started(self): ...
# ... 其他事件处理
```

- [ ] **Step 4: 验证功能完整性**

运行应用测试基本功能：
1. 新建会话
2. 发送消息
3. 接收流式响应
4. 工具调用
5. 切换历史会话

- [ ] **Step 5: Commit**

```bash
git add app/llm_chatter/main_widget.py
git commit -m "refactor(main_widget): use EventBus and simplify to ~2000 lines"
```

---

### Task 7: 优化 ChatEngine

**Files:**
- Modify: `app/llm_chatter/core/chat_engine.py`

- [ ] **Step 1: 分析 chat_engine.py 结构**

```bash
grep -n "def _" app/llm_chatter/core/chat_engine.py
```

识别可提取的方法：
- 上下文构建逻辑 → ContextManager
- 回调管理 → EventBus
- Worker 管理 → 保持

- [ ] **Step 2: 简化 chat_engine.py**

```python
# 简化后的 chat_engine.py
class ChatEngine:
    def __init__(self, session_manager, event_bus, context_manager, ...):
        self._session_manager = session_manager
        self._event_bus = event_bus
        self._context_manager = context_manager
        
    # 保留核心接口，移除冗余
    def send_message(self, message: str): ...
    def stop(self): ...
    def get_streaming_state(self): ...
```

- [ ] **Step 3: Commit**

```bash
git commit -m "refactor(chat_engine): use EventBus and ContextManager"
```

---

## Phase 4: 清理优化

### Task 8: 清理 utils/ 重复代码

**Files:**
- Modify: 多个 utils 文件

- [ ] **Step 1: 识别重复代码**

```bash
# 查找相似函数
grep -r "def.*token" app/llm_chatter/utils/
grep -r "def.*message" app/llm_chatter/utils/
```

- [ ] **Step 2: 统一工具函数**

主要清理项：
- Token 计算：`token_estimator.py` 作为唯一来源
- 消息处理：`message_content.py` 作为唯一来源
- 文件操作：`file_tools.py` 统一

- [ ] **Step 3: Commit**

```bash
git commit -m "chore(utils): remove duplicate code"
```

---

### Task 9: 性能优化

**Files:**
- Modify: `app/llm_chatter/widgets/message/renderer.py`
- Modify: `app/llm_chatter/main_widget.py`

- [ ] **Step 1: 渲染缓存**

```python
# 在 renderer.py 添加
from functools import lru_cache

@lru_cache(maxsize=256)
def cached_render_markdown(content_hash, content):
    """带内容哈希的缓存渲染"""
    return render_markdown(content)
```

- [ ] **Step 2: 批量更新优化**

```python
# 在流式响应中
class StreamBatcher:
    """批量更新，防抖 100ms"""
    def __init__(self, callback, interval_ms=100):
        self._callback = callback
        self._pending = []
        self._timer = QTimer()
        self._timer.singleShot(interval_ms, self._flush)
        
    def add(self, content):
        self._pending.append(content)
        
    def _flush(self):
        self._callback("\n".join(self._pending))
        self._pending = []
```

- [ ] **Step 3: Commit**

```bash
git commit -m "perf: add rendering cache and stream batching"
```

---

## 验收标准

| 指标 | 目标 | 验证方法 |
|------|------|----------|
| `main_widget.py` 行数 | < 2000 行 | `wc -l` |
| `message_card.py` 行数 | < 500 行 | `wc -l` |
| 模块独立性 | EventBus 解耦 | 单元测试 |
| 功能完整性 | 所有现有功能可用 | 手动测试 |
| 性能 | 渲染 +30% | 对比测试 |

---

## 回滚计划

如遇问题：
1. 保留 `message_card.py.bak` 备份
2. 每个 Phase 完成后运行完整测试
3. 使用 git bisect 定位问题

---

**Plan complete.** 建议使用 Subagent-Driven 执行，每个 Task 独立完成并验证。
