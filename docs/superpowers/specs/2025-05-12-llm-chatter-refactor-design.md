# LLM Chatter 重构设计方案

## 目标

将从强耦合系统拆出的 LLM 对话模块进行分层解耦，消除冗余代码，提升性能，为后续迭代打下基础。

## 当前问题诊断

| 文件 | 行数 | 问题 |
|------|------|------|
| `main_widget.py` | 3850 | 职责混杂：UI、会话、交互、工具调用全在一起 |
| `message_card.py` | 2022 | 渲染逻辑、样式、内容处理耦合 |
| `chat_engine.py` | 1122 | 上下文管理、会话持久化边界不清 |
| `utils/*.py` | 多处 | 重复的工具函数 |

## 架构设计

```
llm_chatter/
├── core/                      # 核心层（无 UI 依赖）
│   ├── chat_engine.py        # 对话引擎接口
│   ├── context_manager.py    # 上下文管理（新增）
│   ├── session_store.py      # 会话持久化（新增）
│   ├── event_bus.py          # 事件总线（新增）
│   ├── tool_executor.py      # 工具执行器
│   ├── agent.py              # Agent 管理
│   └── memory_manager.py     # 记忆管理
│
├── widgets/                   # UI 层
│   ├── message/              # 消息卡片模块（拆分）
│   │   ├── card.py           # 卡片容器
│   │   ├── renderer.py       # Markdown/代码渲染
│   │   ├── content.py        # 内容解析
│   │   └── style.py          # 样式管理
│   ├── floating/             # 浮窗组件（合并）
│   │   ├── base.py           # 基类
│   │   ├── tool.py           # 工具浮窗
│   │   ├── todo.py           # 待办浮窗
│   │   └── question.py       # 问答浮窗
│   ├── interaction/          # 交互控制（新增）
│   │   ├── controller.py     # 交互状态机
│   │   └── state.py          # 交互状态定义
│   └── [其他 UI 组件]
│
├── utils/                     # 工具层
│   ├── message_content.py    # 消息内容处理
│   ├── token_estimator.py   # Token 计算
│   └── [其他工具]
│
└── main_widget.py            # 组装层（大幅精简）
```

## 模块职责

### 1. EventBus（事件总线）

```python
# core/event_bus.py
class EventBus:
    """事件总线，替代直接回调，解耦模块间通信"""
    
    # 事件类型
    CONTENT_RECEIVED = "content_received"
    STREAM_STARTED = "stream_started"
    STREAM_FINISHED = "stream_finished"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_RESULT_RECEIVED = "tool_result_received"
    ERROR = "error"
    
    def emit(self, event_type: str, data: Any): ...
    def on(self, event_type: str, handler: Callable): ...
    def off(self, event_type: str, handler: Callable): ...
```

**好处**：
- 消除直接回调依赖
- 支持事件订阅/退订
- 便于调试和日志记录

### 2. ContextManager（上下文管理器）

```python
# core/context_manager.py
class ContextManager:
    """上下文管理：Token 预算、历史压缩、消息组装"""
    
    def __init__(self, budget_tokens: int):
        self._budget = budget_tokens
        
    def build_messages(self, session, memory_context: str = "") -> List[Dict]: ...
    def estimate_tokens(self, messages: List[Dict]) -> int: ...
    def should_compact(self, messages: List[Dict]) -> bool: ...
    def compact(self, messages: List[Dict]) -> Tuple[List[Dict], Dict]: ...
```

**好处**：
- 隔离 Token 计算逻辑
- 统一历史压缩策略
- 便于性能优化（缓存计算结果）

### 3. InteractionController（交互控制器）

```python
# core/interaction_controller.py
class InteractionController:
    """交互状态机：管理 Agent 切换、权限确认、状态同步"""
    
    class State(Enum):
        IDLE = "idle"
        STREAMING = "streaming"
        WAITING_PERMISSION = "waiting_permission"
        WAITING_QUESTION = "waiting_question"
        
    def __init__(self, event_bus: EventBus): ...
    def start_stream(self): ...
    def stop_stream(self): ...
    def request_permission(self, tool_call_id: str, details: Dict): ...
    def confirm_permission(self): ...
```

**好处**：
- 状态转移明确
- 便于测试边界情况
- 减少 main_widget.py 的条件判断

### 4. MessageCard 拆分

```
message/card.py       # 卡片容器：生命周期、事件转发
message/renderer.py  # Markdown 解析、代码高亮、HTML 生成
message/content.py    # 内容块解析（text/tool_result）
message/style.py      # 样式配置：暗色/亮色、动画、边框
```

**拆分原则**：
- `renderer.py`：纯函数，无状态，可缓存
- `content.py`：数据结构定义
- `style.py`：常量配置
- `card.py`：组装上述模块，绑定 UI 事件

### 5. FloatingWidget 合并

现有：
- `todo_floating_widget.py`
- `question_floating_widget.py`
- `tool_floating_widget.py`
- `sub_agent_floating_widget.py`

合并为：
```
widgets/floating/
├── base.py      # 基础浮窗：位置、动画、透明度
├── tool.py      # 工具执行状态
├── todo.py      # 待办列表
├── question.py  # 用户问答
└── agent.py     # 子 Agent 状态
```

## 性能优化

### 1. 渲染优化

| 问题 | 优化方案 |
|------|----------|
| Markdown 重复解析 | 缓存解析结果，消息 ID + 内容哈希作为 key |
| 代码高亮耗时 | 预热常见语言的高亮器，延迟非可见区域渲染 |
| 卡片创建开销 | 使用对象池复用卡片组件 |

### 2. 流式响应优化

| 问题 | 优化方案 |
|------|----------|
| 每个 token 触发更新 | 批量更新，100ms 防抖 |
| 思考内容干扰正文渲染 | 分离思考/正文缓冲，优先渲染正文 |
| 工具结果阻塞主线程 | 后台线程预处理，UI 只做展示 |

### 3. 内存优化

| 问题 | 优化方案 |
|------|----------|
| 大文件内容占用内存 | 懒加载，渲染时截断显示 |
| 历史会话卡片缓存 | LRU 缓存，超过限制自动清理 |
| Token 统计重复计算 | 单次计算，多处引用 |

## 重构顺序

### Phase 1：基础设施（风险低）
1. 创建 `core/event_bus.py`
2. 创建 `core/context_manager.py`
3. 创建 `core/session_store.py`

### Phase 2：UI 拆分（风险中）
4. 拆分 `widgets/message_card.py`
5. 合并 `widgets/floating/*.py`

### Phase 3：核心重构（风险中）
6. 创建 `widgets/interaction/controller.py`
7. 重构 `main_widget.py`，接入 EventBus

### Phase 4：清理优化（收尾）
8. 清理 `utils/` 重复代码
9. 应用性能优化

## 兼容性策略

- 旧接口保留代理对象
- 渐进式迁移，不破坏现有调用
- 每个 Phase 完成后可运行验证

## 验收标准

1. `main_widget.py` 行数降至 1500 行以下
2. `message_card.py` 行数降至 500 行以下
3. 消息渲染性能提升 30%+
4. 流式响应无明显卡顿
5. 现有功能测试通过
