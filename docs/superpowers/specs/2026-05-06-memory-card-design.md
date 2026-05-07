# 记忆管理卡片化改造设计

**日期**: 2026-05-06
**状态**: 设计中
**负责人**: AI Assistant

---

## 1. 背景

将现有的 `MemoryManagerDialog` 弹窗改造为卡片形式，与历史会话卡片保持一致的设计语言。

### 现有设计
- 独立 `QDialog` 弹窗
- 模态显示，`exec_()` 阻塞
- 包含分类 Tab 切换

### 目标设计
- 使用 `BaseSettingsCard` 容器
- 与历史会话卡片并列显示
- 点击按钮切换显示/隐藏
- 移除复杂 Tab，简化分类筛选

---

## 2. 组件设计

### 2.1 文件结构

```
app/widgets/memory_card.py  (新建)
├── MemoryCardContent     (内容区域)
├── MemoryItemCard        (单条记忆项)
└── MemoryFilterBar       (筛选栏)
```

### 2.2 MemoryCardContent

| 属性 | 说明 |
|------|------|
| 布局 | 垂直布局：筛选栏 + 滚动列表 + 添加区 |
| 滚动区域 | QScrollArea，内容可滚动 |
| 输入区 | LineEdit + PushButton，底部固定 |

### 2.3 MemoryItemCard

| 属性 | 说明 |
|------|------|
| 样式 | 圆角卡片，hover 效果 |
| 布局 | 水平布局：内容 + 元信息 + 开关 + 删除 |
| 内容 | BodyLabel，支持显示/编辑 |
| 元信息 | CaptionLabel，显示来源/置信度 |
| 开关 | SwitchButton，启用/禁用 |
| 删除 | TransparentToolButton |

### 2.4 MemoryFilterBar

| 属性 | 说明 |
|------|------|
| 布局 | 水平标签组 |
| 标签 | 全部 / 智能体 / 用户 / 偏好 / 禁忌 / 知识 |
| 样式 | SegmentedWidget 或紧凑按钮组 |

---

## 3. 集成方式

### 3.1 main_widget.py 修改

```python
# 新增导入
from app.widgets.memory_card import MemoryCardContent

# 新增卡片实例 (在 _history_card 附近)
self._memory_card = BaseSettingsCard("记忆管理", "🧠", self)
self._memory_card.setFixedHeight(400)
self._memory_card_popup = MemoryCardContent(...)
self._memory_card.content_layout.addWidget(self._memory_card_popup)
self._memory_card.setVisible(False)
layout.addWidget(self._memory_card)

# 新增切换方法
def _toggle_memory_card(self):
    if self._memory_card.isVisible():
        self._memory_card.hide()
    else:
        self._hide_main_popups()
        self._memory_card.show()
        self._memory_card_popup.load_memories()

# 连接按钮
self.soul_btn.clicked.connect(self._toggle_memory_card)
```

### 3.2 信号设计

| 信号 | 类型 | 说明 |
|------|------|------|
| `memorySaved` | pyqtSignal(list) | 保存时触发，传递更新后的记忆列表 |
| `memoryDeleted` | pyqtSignal(int) | 删除时触发，传递索引 |
| `memoryToggled` | pyqtSignal(int, bool) | 开关切换，传递索引和状态 |

---

## 4. 数据流

```
用户操作 (添加/删除/开关/筛选)
    ↓
MemoryCardContent 更新内部状态
    ↓
用户点击「保存」
    ↓
memorySaved signal 携带 memories 列表
    ↓
main_widget._on_memory_updated 接收
    ↓
调用 _memory_manager.update_user_memories()
    ↓
InfoBar 提示保存成功
```

---

## 5. 与弹窗的差异

| 维度 | 弹窗 | 卡片 |
|------|------|------|
| 显示方式 | `dialog.exec_()` 模态 | `setVisible(True/False)` 非阻塞 |
| 分类切换 | Dialog 内 Tab | 卡片内 FilterBar |
| 数据获取 | 构造函数传入 `memories` | 每次显示时从 `_memory_manager` 加载 |
| 保存 | 关闭弹窗时自动保存 | 点击「保存」按钮显式保存 |
| 关闭 | `accept()` / `reject()` | `setVisible(False)` |

---

## 6. 实施步骤

### Step 1: 新建 memory_card.py
- [ ] 创建 `MemoryFilterBar` 筛选栏组件
- [ ] 创建 `MemoryItemCard` 记忆项卡片
- [ ] 创建 `MemoryCardContent` 内容区域
- [ ] 实现添加/删除/开关/筛选逻辑

### Step 2: 集成到 main_widget.py
- [ ] 添加 `_memory_card` 实例
- [ ] 添加 `_toggle_memory_card` 方法
- [ ] 连接 `soul_btn` 按钮
- [ ] 连接信号到 `_on_memory_updated`

### Step 3: 移除弹窗调用
- [ ] 注释掉 `_show_soul_memory` 中的弹窗代码
- [ ] 保留 `_on_memory_updated` 逻辑（信号处理）

---

## 7. 风险与注意事项

1. **数据一致性**: 卡片内修改后需点击保存才生效，避免意外丢失
2. **分类保留**: 筛选只是显示过滤，不改变数据结构
3. **向后兼容**: 原有的 `MemoryManagerDialog` 可保留，暂不删除
