# 前后端分离重构计划

> **Goal:** 将 UI 层（main_widget.py）与业务逻辑层（core/）分离，实现真正的 MVC/MVP 架构

> **Architecture:** 
> - **Backend (core/):** 纯业务逻辑，不依赖 PyQt/Qt
> - **Frontend (widgets/, main_widget.py):** 只负责 UI 渲染和用户交互
> - **Communication:** 通过信号槽和回调函数，不直接调用 UI 组件

> **Tech Stack:** PyQt5, Python, loguru

---

## 阶段一：创建 Backend 统一接口

### Task 1: 创建 ChatBackend 类

**Files:**
- Create: `app/core/backend.py`
- Modify: `app/core/__init__.py`

- [ ] **Step 1: 创建 backend.py 骨架**

```python
# -*- coding: utf-8 -*-
"""
ChatBackend - 统一后端接口
持有所有核心组件，提供给 UI 层调用
"""

from PyQt5.QtCore import QObject, pyqtSignal

from app.core import (
    ChatEngine,
    ToolExecutor,
    MemoryManagerCore,
    AgentManager,
    SessionManager,
    ChatSession,
)

class ChatBackend(QObject):
    """聊天后端 - 持有核心组件，暴露统一接口"""
    
    # 信号定义
    session_changed = pyqtSignal(str)  # session_id
    message_received = pyqtSignal(dict)  # 新消息
    stream_started = pyqtSignal()
    stream_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    context_updated = pyqtSignal(int, int)  # token_count, limit
    
    def __init__(self):
        super().__init__()
        self._agent_manager = None
        self._tool_executor = None
        self._memory_manager = None
        self._session_manager = SessionManager()
        self._chat_engine = None
        
    def initialize(self, get_model_config, tool_executor, agent_manager, memory_manager):
        """初始化后端"""
        self._get_model_config = get_model_config
        self._tool_executor = tool_executor
        self._agent_manager = agent_manager
        self._memory_manager = memory_manager
        
        self._chat_engine = ChatEngine(
            session_manager=self._session_manager,
            get_model_config=get_model_config,
            tool_executor=tool_executor,
            agent_manager=agent_manager,
        )
        
    @property
    def session_manager(self) -> SessionManager:
        return self._session_manager
    
    @property
    def chat_engine(self) -> ChatEngine:
        return self._chat_engine
    
    def send_message(self, text: str, **kwargs):
        """发送消息"""
        # 调用 chat_engine 处理
        pass
    
    def stop_streaming(self):
        """停止流式输出"""
        pass
```

- [ ] **Step 2: 更新 core/__init__.py 导出 Backend**

```python
from app.core.backend import ChatBackend
```

- [ ] **Step 3: 验证导入**

```bash
python -c "from app.core import ChatBackend; print('OK')"
```

---

## 阶段二：提取 UI 回调逻辑

### Task 2: 分析 main_widget.py 中的回调函数

**Files:**
- Modify: `app/main_widget.py`
- Create: `app/core/callbacks.py`

**目标：** 将 main_widget.py 中的 worker 信号连接代码提取为回调函数

- [ ] **Step 1: 创建 callbacks.py 定义回调接口**

```python
# -*- coding: utf-8 -*-
"""
UI 回调接口定义
定义后端调用 UI 的标准接口
"""

from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class UICallbacks:
    """UI 回调集合"""
    on_message_start: Callable[[], None] = None
    on_message_chunk: Callable[[str], None] = None
    on_message_complete: Callable[[dict], None] = None
    on_tool_call_start: Callable[[str, str, dict], None] = None
    on_tool_call_result: Callable[[str, str, dict, bool], None] = None
    on_error: Callable[[str], None] = None
    on_context_update: Callable[[int, int], None] = None
    on_stream_stop: Callable[[], None] = None
```

- [ ] **Step 2: 在 ChatBackend 添加 set_ui_callbacks 方法**

```python
def set_ui_callbacks(self, callbacks: UICallbacks):
    """设置 UI 回调"""
    self._ui_callbacks = callbacks
```

---

## 阶段三：迁移会话管理到 Backend

### Task 3: 将会话相关逻辑从 main_widget.py 提取到 Backend

**Files:**
- Modify: `app/core/backend.py`
- Modify: `app/main_widget.py`

- [ ] **Step 1: 在 Backend 添加会话管理方法**

```python
def create_session(self) -> ChatSession:
    """创建新会话"""
    return self._session_manager.create_new_session()

def get_current_session(self) -> Optional[ChatSession]:
    """获取当前会话"""
    return self._session_manager.get_current_session()

def switch_session(self, session_id: str):
    """切换会话"""
    # 查找并切换
    pass

def delete_session(self, index: int) -> bool:
    """删除会话"""
    return self._session_manager.delete_session(index)
```

- [ ] **Step 2: main_widget.py 中替换为 backend 调用**

```python
# 原来:
session = self.session_manager.create_new_session()

# 改为:
session = self.backend.create_session()
```

---

## 阶段四：迁移对话逻辑到 Backend

### Task 4: 将发送消息逻辑提取到 Backend

**Files:**
- Modify: `app/core/backend.py`
- Modify: `app/main_widget.py`

- [ ] **Step 1: 在 Backend 添加 send_message**

```python
def send_message(self, text: str, agent_name: str = None, **kwargs):
    """发送消息到 LLM"""
    session = self.get_current_session()
    if not session:
        session = self.create_session()
    
    session.add_user_message(text, params=kwargs)
    
    # 调用 chat_engine
    self._chat_engine.send_message(
        text,
        session=session,
        agent_name=agent_name,
        # callbacks...
    )
```

- [ ] **Step 2: 更新 main_widget.py 中的 _on_send_clicked**

```python
def _on_send_clicked(self):
    text = self._get_input_text()
    if text:
        self.backend.send_message(text, agent_name=self._current_agent)
```

---

## 阶段五：拆分 main_widget.py

### Task 5: 按功能拆分主窗口

**Files:**
- Create: `app/frontend/__init__.py`
- Create: `app/frontend/main_window.py` (从 main_widget.py 提取)
- Create: `app/frontend/session_panel.py` (会话列表)
- Create: `app/frontend/chat_area.py` (聊天区域)
- Create: `app/frontend/input_area.py` (输入区域)

**拆分策略:**
- `main_window.py`: 主容器，管理布局
- `chat_area.py`: 消息卡片渲染区域
- `session_panel.py`: 会话列表侧边栏
- `input_area.py`: 底部输入框

- [ ] **Step 1: 创建 frontend 目录结构**

```bash
mkdir app/frontend
touch app/frontend/__init__.py
```

- [ ] **Step 2: 创建 ChatAreaWidget**

```python
# app/frontend/chat_area.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea

class ChatAreaWidget(QWidget):
    """聊天消息显示区域"""
    
    def __init__(self, backend: ChatBackend, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self.scroll_area = QScrollArea()
        layout.addWidget(self.scroll_area)
        
    def append_message(self, message: dict):
        """追加消息卡片"""
        pass
        
    def clear(self):
        """清空聊天区域"""
        pass
```

---

## 阶段六：更新导入路径

### Task 6: 更新所有引用

**Files:**
- Modify: `app/main_widget.py`
- Modify: `app/api/api_server.py`
- Modify: `app/api/api_session_handler.py`

- [ ] **Step 1: 统一使用 ChatBackend**

```python
# main_widget.py
from app.core import ChatBackend

class OpenAIChatToolWindow:
    def __init__(self):
        self.backend = ChatBackend()
        self.backend.initialize(
            get_model_config=self._get_current_model_config,
            tool_executor=self._tool_executor,
            agent_manager=self._agent_manager,
            memory_manager=self._memory_manager,
        )
```

---

## 阶段七：测试和验证

### Task 7: 验证前后端分离

- [ ] **Step 1: 验证导入**

```bash
python -c "from app.core import ChatBackend; from app.frontend import ChatAreaWidget; print('OK')"
```

- [ ] **Step 2: 运行主程序**

```bash
python main.py
```

- [ ] **Step 3: 测试基本功能**

- 创建新会话
- 发送消息
- 切换会话
- 子智能体任务

---

## 文件变更摘要

| 操作 | 文件 |
|------|------|
| Create | `app/core/backend.py` |
| Create | `app/core/callbacks.py` |
| Create | `app/frontend/__init__.py` |
| Create | `app/frontend/chat_area.py` |
| Create | `app/frontend/session_panel.py` |
| Create | `app/frontend/input_area.py` |
| Modify | `app/core/__init__.py` |
| Modify | `app/main_widget.py` (逐步提取逻辑) |

---

## 风险点

1. **信号槽迁移**: worker 的多个信号需要映射到 Backend 的信号
2. **状态同步**: Backend 和 UI 层状态需要保持一致
3. **循环导入**: Frontend 导入 Backend，Backend 可能需要导入 Frontend 类型

---

## 完成标准

- [ ] `python main.py` 正常运行
- [ ] 发送消息功能正常
- [ ] 会话切换正常
- [ ] 子智能体任务正常
- [ ] main_widget.py 减少到 2000 行以内
