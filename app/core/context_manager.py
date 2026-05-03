# -*- coding: utf-8 -*-
"""上下文管理器 - Token 预算、历史压缩、消息组装"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger

from app.utils.token_estimator import count_messages_tokens
from app.utils.message_content import content_to_text

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
        
    def get_soft_limit(self) -> int:
        """获取软限制（75% 预算）"""
        return self._soft_limit
        
    def get_budget(self) -> int:
        """获取总预算"""
        return self._budget_tokens
        
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
        
    def get_history_snippet(self, messages: List[Dict]) -> str:
        """获取历史摘要（用于系统提示）"""
        if not messages:
            return ""
            
        # 只取最近几条
        recent = messages[-RECENT_HISTORY_MIN_MESSAGES:] if len(messages) >= RECENT_HISTORY_MIN_MESSAGES else messages
        
        parts = []
        for msg in recent:
            role = msg.get("role", "unknown")
            content = content_to_text(msg.get("content", ""))
            if content:
                # 截断过长内容
                if len(content) > MAX_HISTORY_SNIPPET_CHARS:
                    content = content[:MAX_HISTORY_SNIPPET_CHARS] + "..."
                parts.append(f"{role}: {content}")
                
        return "\n".join(parts) if parts else ""