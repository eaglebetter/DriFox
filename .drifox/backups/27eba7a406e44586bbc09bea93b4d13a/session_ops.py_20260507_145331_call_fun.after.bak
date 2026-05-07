# -*- coding: utf-8 -*-
"""
会话操作模块 - 提供会话数据的纯逻辑操作

与 UI 解耦，可以在不依赖 PyQt 的环境中使用。
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from loguru import logger

from app.core.message_content import (
    consolidate_messages,
    get_user_round_ranges,
    content_to_text,
)


def find_user_round_index(
    session,
    user_text: str,
    timestamp: str,
) -> Optional[int]:
    """
    从 session 数据中找到 user 消息对应的 round_index。

    通过在 session.messages 中定位 user 消息，然后计算它是第几个 user。

    Args:
        session: ChatSession 对象
        user_text: 用户消息的纯文本内容
        timestamp: 用户消息的时间戳

    Returns:
        round_index 或 None
    """
    canonical_messages = consolidate_messages(session.messages)
    user_count_total = sum(1 for msg in canonical_messages if msg.get("role") == "user")

    # 规范化时间戳进行比较（去掉秒）
    # MessageCard 的 timestamp 格式是 "YYYY-MM-DD HH:MM"（无秒）
    # session.messages 的 timestamp 格式是 "YYYY-MM-DD HH:MM:SS"（有秒）
    card_ts_prefix = timestamp[:16] if timestamp else ""

    logger.debug(f"[SessionOps] Searching for user message: card_ts={card_ts_prefix}, content_len={len(user_text)}")
    logger.debug(f"[SessionOps] Session has {len(canonical_messages)} messages, {user_count_total} user messages")

    # 在消息列表中查找匹配的 user 消息
    # 关键修复：同时匹配时间戳+内容，避免多条消息匹配到同一条
    user_count = 0
    for msg in canonical_messages:
        if msg.get("role") == "user":
            msg_content = msg.get("content", "")
            msg_timestamp = msg.get("timestamp", "") or ""
            msg_ts_prefix = msg_timestamp[:16]

            # 同时匹配时间戳和内容，确保唯一性
            # 时间戳精确到分钟，内容完全匹配
            if msg_ts_prefix == card_ts_prefix and msg_content == user_text:
                logger.info(
                    f"[SessionOps] Matched user message: user_count={user_count}, "
                    f"ts={card_ts_prefix}, content_len={len(user_text)}"
                )
                return user_count
            user_count += 1

    # 兜底：如果时间戳+内容都没匹配到，尝试内容匹配（兼容旧数据）
    user_count = 0
    for msg in canonical_messages:
        if msg.get("role") == "user":
            msg_content = msg.get("content", "")
            if msg_content == user_text:
                logger.warning(
                    f"[SessionOps] Fallback match by content only: user_count={user_count}, "
                    f"content_len={len(user_text)}"
                )
                return user_count
            user_count += 1

    # 调试：显示所有 user 消息的时间戳，帮助诊断
    logger.warning(f"[SessionOps] No match found for user message. Total user messages: {user_count_total}")
    if user_count_total > 0:
        logger.warning("[SessionOps] Available user messages in session:")
        for i, msg in enumerate(canonical_messages):
            if msg.get("role") == "user":
                msg_ts = (msg.get("timestamp", "") or "")[:16]
                msg_content_preview = (msg.get("content", "") or "")[:50]
                logger.warning(f"[SessionOps]   [{i}] ts={msg_ts}, content={msg_content_preview}...")

    return None


def get_round_message_indices(session, round_index: int) -> Optional[Tuple[int, int]]:
    """
    获取指定 round 的消息索引范围。

    Args:
        session: ChatSession 对象
        round_index: round 索引

    Returns:
        (start_idx, end_idx) 或 None
    """
    canonical_messages = consolidate_messages(session.messages)
    round_ranges = get_user_round_ranges(canonical_messages)

    if round_index < 0 or round_index >= len(round_ranges):
        return None

    return round_ranges[round_index]


def get_current_round_index(session) -> int:
    """
    获取当前会话的 round_index（消息总数对应的 round）。

    Args:
        session: ChatSession 对象

    Returns:
        当前 round index
    """
    if not session or not session.messages:
        return 0

    canonical_messages = consolidate_messages(session.messages)
    user_count = sum(1 for msg in canonical_messages if msg.get("role") == "user")
    return user_count


def export_messages_to_markdown(
    messages: List[Dict[str, Any]],
    timestamp: str = None,
) -> str:
    """
    将消息列表导出为 Markdown 格式。

    Args:
        messages: 消息列表
        timestamp: 可选的导出时间戳

    Returns:
        Markdown 格式的字符串
    """
    if timestamp is None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    lines = [
        "# 对话记录\n",
        f"导出时间: {timestamp}\n",
    ]

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        msg_timestamp = msg.get("timestamp", "")

        role_display = {
            "system": "系统",
            "user": "用户",
            "assistant": "助手",
            "tool": "工具",
        }.get(role, role)

        # 提取文本内容
        text = content_to_text(content) if isinstance(content, (list, dict)) else str(content)

        lines.append(f"\n## {role_display}\n")
        if msg_timestamp:
            lines.append(f"*{msg_timestamp}*\n")
        lines.append(f"{text}\n")

    return "".join(lines)


def export_messages_to_json(messages: List[Dict[str, Any]]) -> str:
    """
    将消息列表导出为 JSON 格式。

    Args:
        messages: 消息列表

    Returns:
        JSON 格式的字符串
    """
    import json
    return json.dumps(messages, ensure_ascii=False, indent=2)


def truncate_messages_for_round(
    session,
    round_index: int,
) -> bool:
    """
    截断会话到指定 round 之前的数据。

    Args:
        session: ChatSession 对象
        round_index: 要保留到的 round 索引

    Returns:
        是否成功
    """
    if not session:
        return False

    canonical_messages = consolidate_messages(session.messages)
    round_ranges = get_user_round_ranges(canonical_messages)

    if round_index <= 0:
        # 保留所有消息
        return True

    if round_index >= len(round_ranges):
        # 指定的 round 不存在，保留所有消息
        return True

    # 获取目标 round 之前的所有消息
    _, last_idx = round_ranges[round_index - 1]
    truncated_messages = canonical_messages[:last_idx]

    # 更新 session
    session.set_messages(truncated_messages, preserve_compaction=True)
    return True


def merge_sessions(sessions: List[Dict], name: str = None) -> Dict:
    """
    合并多个会话。

    Args:
        sessions: 会话数据列表
        name: 合并后的会话名称

    Returns:
        合并后的会话数据
    """
    merged_messages = []
    for session_data in sessions:
        messages = session_data.get("messages", [])
        if messages:
            merged_messages.extend(messages)

    return {
        "name": name or f"合并会话 {datetime.now().strftime('%m-%d %H:%M')}",
        "messages": merged_messages,
        "topic_summary": "",
    }
