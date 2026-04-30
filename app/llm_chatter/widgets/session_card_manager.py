# -*- coding: utf-8 -*-
"""
会话卡片管理器 - 处理会话卡片的缓存和渲染

从 main_widget.py 提取的会话卡片管理逻辑。
"""
import re
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget, QLayout
    from app.llm_chatter.widgets.message import MessageCard
    from app.llm_chatter.utils.chat_session import ChatSession

try:
    import sip
except ImportError:
    sip = None


class SessionCardManager:
    """
    会话卡片管理器
    
    负责：
    1. 会话卡片的缓存（避免重复创建）
    2. 卡片生命周期管理
    3. 欢迎卡片的缓存
    """
    
    def __init__(self, max_cache_size: int = 10):
        self._session_card_cache: Dict[str, List["MessageCard"]] = {}
        self._welcome_card_cache: Dict[str, "MessageCard"] = {}
        self._max_cache_size = max_cache_size
        
    def cache_session_cards(
        self, 
        session_id: str, 
        cards: List["MessageCard"],
        all_session_ids: set
    ) -> None:
        """缓存会话卡片"""
        self._session_card_cache[session_id] = cards
        self._cleanup_stale_cache(all_session_ids)
        
    def get_cached_cards(self, session_id: str) -> Optional[List["MessageCard"]]:
        """获取缓存的会话卡片"""
        cached = self._session_card_cache.get(session_id)
        if not cached:
            return None
            
        # 过滤已删除的卡片
        alive_cards = [c for c in cached if self._is_widget_alive(c)]
        if len(alive_cards) != len(cached):
            self._session_card_cache.pop(session_id, None)
            
        return alive_cards if alive_cards else None
        
    def cache_welcome_card(self, cache_key: str, card: "MessageCard") -> None:
        """缓存欢迎卡片"""
        self._welcome_card_cache[cache_key] = card
        
    def get_welcome_card(self, cache_key: str) -> Optional["MessageCard"]:
        """获取缓存的欢迎卡片"""
        card = self._welcome_card_cache.get(cache_key)
        if card and self._is_widget_alive(card):
            return card
        elif card:
            self._welcome_card_cache.pop(cache_key, None)
        return None
        
    def _is_widget_alive(self, widget: Optional["QWidget"]) -> bool:
        """检查 widget 是否仍然存活"""
        if widget is None:
            return False
        if sip is None:
            return True
        try:
            return not sip.isdeleted(widget)
        except Exception:
            return False
            
    def _cleanup_stale_cache(self, valid_session_ids: set) -> None:
        """清理过期的缓存"""
        # 移除不存在的会话缓存
        stale_ids = set(self._session_card_cache.keys()) - valid_session_ids
        for sid in stale_ids:
            self._session_card_cache.pop(sid, None)
            
        # 如果缓存过大，移除最旧的缓存
        if len(self._session_card_cache) <= self._max_cache_size:
            return
            
        current_ids = valid_session_ids & set(self._session_card_cache.keys())
        for sid in list(self._session_card_cache.keys()):
            if sid not in current_ids:
                self._session_card_cache.pop(sid, None)
                if len(self._session_card_cache) <= self._max_cache_size:
                    break
                    
    def clear(self) -> None:
        """清空所有缓存"""
        self._session_card_cache.clear()
        self._welcome_card_cache.clear()
        
    def get_cache_size(self) -> int:
        """获取缓存大小"""
        return len(self._session_card_cache)
