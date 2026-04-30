# main_widget.py 重构计划

## 当前状态

`main_widget.py` 当前约 3850 行，需要逐步拆分。

## 拆分目标

### 1. UI 组件提取
- [ ] `_setup_ui()` → 拆分为独立 UI 初始化器
- [ ] `_setup_title_bar()` → `ui/title_bar.py`
- [ ] `_setup_chat_area()` → `ui/chat_area.py`
- [ ] `_setup_input_area()` → `ui/input_area.py`

### 2. 会话管理提取
- [ ] `_create_new_session()` → `session/session_manager_ext.py`
- [ ] `_restore_latest_or_create_session()` → 保持
- [ ] `_auto_save_current_session()` → 保持

### 3. 消息渲染提取
- [ ] `_render_message_to_card()` → `widgets/message/renderer_ext.py`
- [ ] `_create_history_card()` → `widgets/history_card_ext.py`
- [ ] `_clear_chat_area()` → 保持

### 4. 事件处理提取
- [ ] 使用 EventBus 替代直接回调
- [ ] 提取 `_on_content_received()` → `handlers/content_handler.py`
- [ ] 提取 `_on_tool_call_started()` → `handlers/tool_handler.py`

### 5. 浮窗管理提取
- [ ] `_show_todo_floating_widget()` → `widgets/floating/todo.py`
- [ ] `_show_question_floating_widget()` → `widgets/floating/question.py`
- [ ] `_show_tool_floating_widget()` → `widgets/floating/tool.py`

## 重构顺序

1. **第一阶段**：提取 UI 组件（风险低）
2. **第二阶段**：接入 EventBus（风险中）
3. **第三阶段**：提取事件处理（风险中）
4. **第四阶段**：最终清理（风险低）

## 保留项

以下功能保持在 main_widget.py 中：
- 窗口生命周期管理
- 主布局组装
- 与外部系统（如 ToolWindow）的接口
- 配置加载和保存

## 验收标准

- main_widget.py 行数降至 2000 行以下
- 所有现有功能保持不变
- EventBus 解耦完成
