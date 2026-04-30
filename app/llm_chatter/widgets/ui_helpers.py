# -*- coding: utf-8 -*-
"""
UI 辅助模块 - 从 main_widget.py 提取的 UI 辅助方法

这些方法独立于主类，可以安全使用。
"""
import re
from typing import Optional, List, Dict, Any, Tuple, Callable
from datetime import datetime
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt
from loguru import logger

# 延迟导入 content_to_text（避免循环导入）
_content_to_text_getter: Optional[Callable] = None

def _get_content_to_text() -> Callable:
    """延迟获取 content_to_text 函数"""
    global _content_to_text_getter
    if _content_to_text_getter is None:
        from app.llm_chatter.utils.message_content import content_to_text
        _content_to_text_getter = content_to_text
    return _content_to_text_getter


# ==================== 样式常量 ====================

WINDOW_STYLE = """
    OpenAIChatToolWindow {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(10, 14, 22, 255),
            stop:1 rgba(15, 20, 30, 255));
    }
"""

CHAT_SCROLL_STYLE = """
    SingleDirectionScrollArea {
        background-color: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 18px;
    }
"""

TITLE_STYLE = """
    QLabel {
        color: #f3f6fc;
        font-size: 15px;
        font-weight: bold;
        padding: 6px 10px;
        border-radius: 10px;
        background-color: rgba(255, 255, 255, 0.03);
    }
    QLabel:hover {
        background-color: rgba(255, 255, 255, 0.06);
    }
"""

MODEL_BTN_STYLE = """
    QWidget {
        background-color: rgba(255, 255, 255, 0.06);
        border-radius: 8px;
        padding: 0px;
    }
    QWidget:hover {
        background-color: rgba(255, 255, 255, 0.10);
    }
"""

MODEL_BTN_TEXT_STYLE = "color: #f3f6fc; font-size: 13px; font-weight: bold; background: transparent;"


# ==================== 预编译正则 ====================

# 用户消息清理正则
_USER_MESSAGE_PATTERN = re.compile(
    r"^\[Task Stage:.*?\]\n\[Current Goal:.*?\]\n\[Verification:.*?\]\n\n",
    re.DOTALL,
)


# ==================== UI 辅助函数 ====================

def setup_background_label(viewport: QLabel, parent: Optional[object] = None) -> QLabel:
    """
    创建背景图片标签
    
    Args:
        viewport: 父控件的 viewport
        parent: 父对象
        
    Returns:
        配置好的背景标签
    """
    from PyQt5.QtWidgets import QGraphicsOpacityEffect
    
    bg_label = QLabel(viewport)
    bg_label.setPixmap(QPixmap(":/icons/fox_bg.png"))
    bg_label.setScaledContents(True)
    
    opacity_effect = QGraphicsOpacityEffect(bg_label)
    opacity_effect.setOpacity(0.1)
    bg_label.setGraphicsEffect(opacity_effect)
    bg_label.lower()
    bg_label.setAttribute(Qt.WA_TransparentForMouseEvents)
    bg_label.resize(viewport.size())
    bg_label.show()
    
    return bg_label


def is_widget_alive(widget: Optional[object]) -> bool:
    """检查 widget 是否仍然存活"""
    if widget is None:
        return False
    try:
        import sip
        return not sip.isdeleted(widget)
    except Exception:
        return True


def sanitize_user_message_for_display(content: str) -> str:
    """
    清理用户消息用于显示
    
    移除消息开头的任务阶段标记。
    """
    if not isinstance(content, str):
        return content
    return _USER_MESSAGE_PATTERN.sub("", content, count=1)


def get_default_timestamp() -> str:
    """获取默认时间戳"""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def filter_alive_cards(cards: List[Any]) -> Tuple[List[Any], bool]:
    """
    过滤存活的卡片
    
    Returns:
        (存活的卡片列表, 是否有卡片被移除)
    """
    alive = [c for c in cards if is_widget_alive(c)]
    removed = len(alive) != len(cards)
    return alive, removed


# ==================== 卡片管理辅助 ====================

def cleanup_stale_card_cache(
    session_card_cache: dict,
    all_session_ids: set,
    max_size: int = 10
) -> None:
    """
    清理过期的卡片缓存
    
    Args:
        session_card_cache: 会话卡片缓存字典
        all_session_ids: 所有有效的会话 ID 集合
        max_size: 最大缓存数量
    """
    # 移除不存在的会话缓存
    stale_ids = set(session_card_cache.keys()) - all_session_ids
    for sid in stale_ids:
        session_card_cache.pop(sid, None)

    # 如果缓存过大，移除最旧的缓存
    if len(session_card_cache) <= max_size:
        return
        
    current_ids = all_session_ids & set(session_card_cache.keys())
    for sid in list(session_card_cache.keys()):
        if sid not in current_ids:
            session_card_cache.pop(sid, None)
            if len(session_card_cache) <= max_size:
                break


# ==================== Diff 辅助 ====================

def normalize_lines(content: str) -> list:
    """
    规范化文本行，确保每行都有换行符
    
    Args:
        content: 原始文本内容
        
    Returns:
        行列表
    """
    lines = content.splitlines(keepends=True)
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'
    return lines


def truncate_text(text: str, max_length: int = 300) -> str:
    """
    截断过长的文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def collect_tool_call_ids(messages: list, start_idx: int, end_idx: int) -> list:
    """
    收集指定范围内的 tool_call_id
    
    Args:
        messages: 消息列表
        start_idx: 起始索引
        end_idx: 结束索引
        
    Returns:
        tool_call_id 列表
    """
    call_ids = []
    for i in range(start_idx, end_idx):
        if i >= len(messages):
            break
        msg = messages[i]
        role = msg.get("role")
        if role == "assistant":
            tool_calls = msg.get("tool_calls", [])
            for tc in tool_calls:
                if isinstance(tc, dict):
                    tid = tc.get("id")
                    if tid and tid not in call_ids:
                        call_ids.append(tid)
        elif role == "tool":
            tid = msg.get("tool_call_id")
            if tid and tid not in call_ids:
                call_ids.append(tid)
    return call_ids


def format_file_list(files: list, max_count: int = 5) -> str:
    """
    格式化文件列表用于显示
    
    Args:
        files: 文件列表
        max_count: 最大显示数量
        
    Returns:
        格式化后的字符串
    """
    if not files:
        return ""
    display = files[:max_count]
    result = "\n".join(f"  - {f}" for f in display)
    if len(files) > max_count:
        result += f"\n  ... 还有 {len(files) - max_count} 个文件"
    return result


# ==================== 动作颜色辅助 ====================

ACTION_COLORS = {
    "jump": "#FFA500",
    "create": "#9370DB",
    "generate": "#32CD32",
    "ask": "#FF6347",
    "view": "#4169E1",
}
DEFAULT_ACTION_COLOR = "#888888"

def get_action_color(action: str) -> str:
    """获取动作对应的颜色"""
    return ACTION_COLORS.get(action.lower(), DEFAULT_ACTION_COLOR)


# ==================== Diff 辅助 ====================

def read_backup_files(backup_path: str) -> tuple:
    """
    读取编辑前后的备份文件
    
    Args:
        backup_path: 编辑前备份文件路径
        
    Returns:
        (old_content, new_content, backup_file) 或抛出异常
    """
    import difflib
    from pathlib import Path
    
    backup_file = Path(backup_path)
    after_backup_path = str(backup_file.with_suffix('.after.bak'))
    
    # 检查编辑后备份是否存在
    after_backup_file = Path(after_backup_path)
    if not after_backup_file.exists():
        raise FileNotFoundError("编辑后备份文件不存在")
    
    # 读取文件
    with open(backup_path, 'r', encoding='utf-8', errors='replace') as f:
        old_content = f.read()
    with open(after_backup_path, 'r', encoding='utf-8', errors='replace') as f:
        new_content = f.read()
    
    return old_content, new_content, backup_file


def generate_diff_html(old_content: str, new_content: str, backup_file) -> str:
    """
    生成 diff HTML 报告
    
    Args:
        old_content: 原始内容
        new_content: 新内容
        backup_file: 文件路径对象
        
    Returns:
        HTML 报告字符串
    """
    import difflib
    from app.llm_chatter.utils.diff_viewer import DiffHtmlGenerator
    
    old_lines = normalize_lines(old_content)
    new_lines = normalize_lines(new_content)
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=backup_file.name,
        tofile=backup_file.name,
        lineterm='\n'
    )
    
    diff_output = ''.join(diff)
    return DiffHtmlGenerator.generate_html_report(diff_output, "")


def generate_multi_file_diff_html(operations: list) -> str:
    """
    为多个文件生成合并的 diff HTML 报告
    
    Args:
        operations: 文件操作列表，每个元素包含 backup_path
        
    Returns:
        HTML 报告字符串
    """
    import difflib
    from pathlib import Path
    from app.llm_chatter.utils.diff_viewer import DiffHtmlGenerator
    
    diff_parts = []
    
    for op in operations:
        backup_path = op.get("backup_path", "")
        if not backup_path:
            continue
        
        try:
            old_content, new_content, backup_file = read_backup_files(backup_path)
        except Exception:
            continue
        
        old_lines = normalize_lines(old_content)
        new_lines = normalize_lines(new_content)
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{backup_file.name}",
            tofile=f"b/{backup_file.name}",
            lineterm='\n'
        )
        diff_output = ''.join(diff)
        if diff_output:
            diff_parts.append(diff_output)
    
    combined_diff = ''.join(diff_parts)
    return DiffHtmlGenerator.generate_html_report(combined_diff, "")


# ==================== Node Preview 辅助 ====================

def build_node_preview_data(messages: list, content_getter: Optional[Callable] = None, max_len: int = 30) -> list:
    """
    从消息列表构建 node preview 数据
    
    Args:
        messages: 消息列表
        content_getter: 获取消息内容的函数，默认为 content_to_text
        max_len: 最大内容长度
        
    Returns:
        [(content, timestamp), ...] 列表
    """
    if content_getter is None:
        content_getter = _get_content_to_text()
        
    node_data = []
    current_user_msg = None

    for msg in messages:
        if msg.get("role") == "user":
            content = content_getter(msg.get("content", ""))[:max_len]
            current_user_msg = content
        elif msg.get("role") == "assistant" and current_user_msg:
            timestamp = msg.get("timestamp", "")
            timestamp_short = timestamp[-5:] if timestamp else ""
            node_data.append((current_user_msg, timestamp_short))
            current_user_msg = None

    # 处理最后未配对的 user message
    if current_user_msg:
        node_data.append((current_user_msg, ""))

    return node_data


# ==================== 卡片删除辅助 ====================

def find_widgets_to_remove_for_round(
    chat_layout,
    round_index: int,
    user_card_count: int,
) -> list:
    """
    找出指定 round 需要删除的消息卡片
    
    Args:
        chat_layout: 聊天布局
        round_index: 目标 round 索引
        user_card_count: 用户消息卡片总数
        
    Returns:
        需要删除的卡片列表
    """
    if round_index >= user_card_count:
        return []
    
    widgets_to_remove = []
    user_card_idx = 0
    removing = False
    
    for i in range(chat_layout.count()):
        item = chat_layout.itemAt(i)
        if not item or not item.widget():
            continue
        widget = item.widget()
        
        if not hasattr(widget, 'role'):
            continue
        if getattr(widget, "_is_welcome", False):
            continue
        if widget.role not in ("user", "assistant"):
            continue

        if widget.role == "user":
            if user_card_idx >= round_index:
                widgets_to_remove.append(widget)
                removing = True
            else:
                user_card_idx += 1
        elif widget.role == "assistant" and removing:
            widgets_to_remove.append(widget)
    
    return widgets_to_remove


def deduplicate_operations(operations: list) -> list:
    """
    对文件操作列表去重
    
    Args:
        operations: 文件操作列表
        
    Returns:
        去重后的列表
    """
    seen = set()
    unique_ops = []
    for op in operations:
        key = (op.get("id"), op.get("file_path"), op.get("call_id"))
        if key not in seen:
            seen.add(key)
            unique_ops.append(op)
    return unique_ops


def delete_widgets_from_layout(widgets_to_remove: list, chat_layout) -> int:
    """
    从布局中删除指定的 widgets
    
    Args:
        widgets_to_remove: 要删除的 widget 列表
        chat_layout: 聊天布局
        
    Returns:
        删除的数量
    """
    deleted = 0
    for widget in widgets_to_remove:
        if not is_widget_alive(widget):
            logger.warning(f"[DELETE] Widget already deleted: {widget}")
            continue
        
        # 从 layout 移除
        layout_removed = False
        for i in range(chat_layout.count()):
            item = chat_layout.itemAt(i)
            if item and item.widget() is widget:
                chat_layout.removeItem(item)
                layout_removed = True
                break
        
        if layout_removed:
            widget.deleteLater()
            deleted += 1
            logger.info(f"[DELETE] Widget deleted: role={widget.role}")
        else:
            logger.warning(f"[DELETE] Widget not found in layout: role={widget.role}")
    
    return deleted


def find_last_tool_call_id_after_round(messages: list, round_ranges: list, round_index: int) -> Optional[str]:
    """
    查找指定 round 之后最后一个 tool_call_id
    
    Args:
        messages: 消息列表
        round_ranges: round 范围列表
        round_index: 目标 round 索引
        
    Returns:
        最后一个 tool_call_id 或 None
    """
    if round_index < 0 or round_index >= len(round_ranges):
        return None
    
    # 获取该 round 之后的所有消息的 start index
    _, end_idx = round_ranges[round_index]
    
    # 查找 end_idx 之后的所有 tool_call_id
    last_call_id = None
    for i in range(end_idx, len(messages)):
        msg = messages[i]
        if msg.get("role") == "tool":
            call_id = msg.get("tool_call_id")
            if call_id:
                last_call_id = call_id
    
    return last_call_id


def create_assistant_card_widget(
    parent,
    timestamp: str,
    round_index: int,
    on_action=None,
    on_context_action=None,
    on_tool_diff=None,
    on_card_diff=None,
    on_save_file=None,
) -> Any:
    """
    创建助手消息卡片（带标准配置）
    
    Args:
        parent: 父控件
        timestamp: 时间戳
        round_index: 轮次索引
        on_action: 动作回调
        on_context_action: 上下文动作回调
        on_tool_diff: 工具差异回调
        on_card_diff: 卡片差异回调
        on_save_file: 保存文件回调
        
    Returns:
        配置好的 MessageCard
    """
    from app.llm_chatter.widgets.message_card import MessageCard
    
    card = MessageCard(parent=parent, role="assistant", timestamp=timestamp)
    card._round_index = round_index
    card.viewer._install_dialog_filter()
    
    if on_action:
        card.actionRequested.connect(on_action)
    if on_context_action:
        card.contextActionRequested.connect(on_context_action)
    if on_tool_diff:
        card.toolDiffRequested.connect(on_tool_diff)
    if on_card_diff:
        card.cardDiffRequested.connect(on_card_diff)
    if on_save_file:
        card.saveFileRequested.connect(on_save_file)
        
    return card
    """
    对文件操作列表去重
    
    Args:
        operations: 文件操作列表
        
    Returns:
        去重后的列表
    """
    seen = set()
    unique_ops = []
    for op in operations:
        key = (op.get("id"), op.get("file_path"), op.get("call_id"))
        if key not in seen:
            seen.add(key)
            unique_ops.append(op)
    return unique_ops


# ==================== 滚动位置辅助 ====================

def calculate_scroll_progress(
    visible_top: float,
    viewport_height: float,
    widget_tops: list
) -> tuple:
    """
    计算滚动进度和可见索引
    
    Args:
        visible_top: 滚动条当前值（可见区域顶部）
        viewport_height: 视口高度
        widget_tops: 用户消息卡片顶部位置列表
        
    Returns:
        (progress, visible_index)
    """
    anchor_y = visible_top + max(viewport_height / 2, 1)
    
    if len(widget_tops) == 1:
        return 0.0, 0
    elif anchor_y <= widget_tops[0]:
        return 0.0, 0
    elif anchor_y >= widget_tops[-1]:
        return float(len(widget_tops) - 1), len(widget_tops) - 1
    else:
        progress = 0.0
        for idx in range(len(widget_tops) - 1):
            start_top = widget_tops[idx]
            end_top = widget_tops[idx + 1]
            if start_top <= anchor_y <= end_top:
                span = max(end_top - start_top, 1)
                ratio = (anchor_y - start_top) / span
                progress = idx + ratio
                break
        visible_index = min(max(int(round(progress)), 0), len(widget_tops) - 1)
        return progress, visible_index
