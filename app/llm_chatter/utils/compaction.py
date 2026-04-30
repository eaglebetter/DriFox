# -*- coding: utf-8 -*-
"""
消息压缩器 - 统一处理上下文压缩逻辑

从 worker.py 提取的消息压缩功能。
"""
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from loguru import logger


def extract_text_content(content: Any, max_len: int = 1800) -> str:
    """从消息内容中提取纯文本"""
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        return "\n".join(text_parts)[:max_len]
    return str(content)[:max_len]


def build_compaction_prompt(
    old_messages: List[Dict],
    recent_messages: List[Dict],
    compaction_prompt: str = ""
) -> List[Dict]:
    """
    构建压缩用的提示词
    
    Args:
        old_messages: 需要压缩的旧消息
        recent_messages: 保留的最近消息
        compaction_prompt: 自定义压缩提示
        
    Returns:
        包含压缩提示的消息列表
    """
    transcript_lines = []
    for msg in old_messages:
        role = msg.get("role", "unknown")
        content = extract_text_content(msg.get('content', ''), 1800)
        transcript_lines.append(f"[{role}] {content}")

    recent_hint = []
    for msg in recent_messages[-4:]:
        role = msg.get("role", "unknown")
        content = extract_text_content(msg.get('content', ''), 400)
        recent_hint.append(f"[{role}] {content}")

    default_prompt = (
        "请压缩较早的对话上下文，生成一个后续可继续执行编码任务的摘要。\n\n"
        "要求：\n"
        "1. 保留任务目标、已做决定、相关文件、关键工具结果、未完成事项。\n"
        "2. 删除重复探索和无关寒暄。\n"
        "3. 输出简洁 Markdown，不要使用 JSON。\n"
        "4. 如果最近消息与旧消息有潜在冲突，请明确标出。\n\n"
    )

    prompt = (
        (compaction_prompt or default_prompt)
        + "\n\n【较早对话】\n"
        + "\n".join(transcript_lines)
        + "\n\n【最近保留消息提示】\n"
        + "\n".join(recent_hint)
    )

    return [
        {
            "role": "system",
            "content": compaction_prompt or "你是一个上下文压缩助手，负责提炼编码任务继续执行所需的摘要。",
        },
        {"role": "user", "content": prompt},
    ]


def make_compaction_state(
    active: bool = False,
    source: str = "compactor",
    kind: str = "",
    original_count: int = 0,
    summarized_count: int = 0,
    kept_count: int = 0,
    summary_count: int = 0,
    note: str = "",
) -> Dict[str, Any]:
    """创建压缩状态的工厂函数"""
    return {
        "active": bool(active),
        "source": source,
        "kind": kind,
        "original_count": int(original_count or 0),
        "summarized_count": int(summarized_count or 0),
        "kept_count": int(kept_count or 0),
        "summary_count": int(summary_count or 0),
        "note": note or "",
    }


def make_compaction_cache(
    active: bool = False,
    kind: str = "",
    cutoff_index: int = 0,
    source_message_count: int = 0,
    summarized_count: int = 0,
    tail_count: int = 0,
    budget_tokens: int = 0,
    summary_message: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """创建压缩缓存的工厂函数"""
    return {
        "active": bool(active),
        "kind": kind or "",
        "cutoff_index": int(cutoff_index or 0),
        "source_message_count": int(source_message_count or 0),
        "summarized_count": int(summarized_count or 0),
        "tail_count": int(tail_count or 0),
        "budget_tokens": int(budget_tokens or 0),
        "summary_message": dict(summary_message) if isinstance(summary_message, dict) else None,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if active else "",
    }


class Compactor:
    """
    消息压缩器
    
    负责：
    1. 判断是否需要压缩
    2. 执行消息压缩
    3. 生成压缩摘要
    """
    
    def __init__(
        self,
        budget_tokens: int = 120000,
        soft_limit_ratio: float = 0.75,
        target_limit_ratio: float = 0.65,
    ):
        self._budget_tokens = budget_tokens
        self._soft_limit = int(budget_tokens * soft_limit_ratio)
        self._target_limit = int(budget_tokens * target_limit_ratio)
        
    def set_budget(self, budget_tokens: int) -> None:
        """设置 Token 预算"""
        self._budget_tokens = budget_tokens
        self._soft_limit = int(budget_tokens * 0.75)
        self._target_limit = int(budget_tokens * 0.65)
        
    def should_compact(self, current_tokens: int) -> bool:
        """检查是否需要压缩"""
        return current_tokens > self._soft_limit
        
    def get_target_count(self, current_count: int, current_tokens: int) -> int:
        """获取目标保留消息数"""
        if current_tokens <= self._target_limit:
            return current_count
            
        ratio = self._target_limit / max(current_tokens, 1)
        return max(6, int(current_count * ratio))  # 至少保留 6 条
        
    def compact_messages(
        self,
        messages: List[Dict],
        keep_count: int = 6,
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        执行消息压缩
        
        Args:
            messages: 原始消息列表
            keep_count: 保留的最近消息数
            
        Returns:
            (压缩后的消息, 压缩元数据)
        """
        if not messages:
            return [], make_compaction_state()
            
        if len(messages) <= keep_count:
            return messages, make_compaction_state()
            
        old_messages = messages[:-keep_count]
        recent_messages = messages[-keep_count:]
        
        return recent_messages, make_compaction_state(
            active=True,
            source="compactor",
            original_count=len(messages),
            summarized_count=len(old_messages),
            kept_count=len(recent_messages),
            note=f"保留最近 {keep_count} 条消息",
        )
        
    def compact_with_summary(
        self,
        messages: List[Dict],
        summary: str,
        keep_count: int = 6,
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        执行带摘要的消息压缩
        
        Args:
            messages: 原始消息列表
            summary: 压缩摘要
            keep_count: 保留的最近消息数
            
        Returns:
            (压缩后的消息, 压缩元数据)
        """
        if not messages:
            return [], make_compaction_state()
            
        old_messages = messages[:-keep_count]
        recent_messages = messages[-keep_count:]
        
        # 构建摘要消息
        summary_msg = {
            "role": "system",
            "content": f"[{len(old_messages)} 条历史消息已压缩]\n\n{summary}"
        }
        
        result = [summary_msg] + recent_messages
        
        meta = make_compaction_state(
            active=True,
            source="compactor_with_summary",
            original_count=len(messages),
            summarized_count=len(old_messages),
            kept_count=len(recent_messages),
            summary_count=1,
            note=f"压缩为 {len(summary)} 字符的摘要",
        )
        
        return result, meta
