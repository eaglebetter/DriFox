# -*- coding: utf-8 -*-
"""
权限缓存模块 - 统一管理工具权限的两级缓存

设计原则：
- Round-level: 单轮对话内自动允许，工具执行完自动清理
- Session-level: 整个会话有效，跨 Worker 持久化
- 每个 ChatEngine 实例有独立的 PermissionCache，多窗口隔离
"""

from typing import Dict, Optional
from loguru import logger


class PermissionCache:
    """工具权限缓存管理器"""

    def __init__(self):
        # Round-level 缓存：该轮对话内自动允许
        self._round_cache: Dict[str, bool] = {}
        
        # Session-level 缓存：本次会话内自动允许
        self._session_cache: Dict[str, bool] = {}

    def is_allowed(self, tool_name: str) -> bool:
        """
        检查工具是否在缓存中被允许。
        
        优先级：round_cache > session_cache
        """
        if tool_name in self._round_cache:
            return True
        if tool_name in self._session_cache:
            return True
        return False

    def allow_round(self, tool_name: str) -> None:
        """允许该工具一轮（round-level）"""
        self._round_cache[tool_name] = True
        logger.info(f"[PermissionCache] 设置 round 缓存: tool={tool_name}")

    def allow_session(self, tool_name: str) -> None:
        """允许该工具会话级（session-level）"""
        self._session_cache[tool_name] = True
        logger.info(f"[PermissionCache] 设置 session 缓存: tool={tool_name}")

    def deny(self, tool_name: str) -> None:
        """从缓存中移除该工具"""
        if tool_name in self._round_cache:
            del self._round_cache[tool_name]
        if tool_name in self._session_cache:
            del self._session_cache[tool_name]

    def clear_round(self) -> None:
        """清理 round-level 缓存（工具执行完成后调用）"""
        self._round_cache.clear()

    def clear_session(self) -> None:
        """清理 session-level 缓存（会话清除时调用）"""
        self._session_cache.clear()

    def clear_all(self) -> None:
        """清理所有缓存"""
        self._round_cache.clear()
        self._session_cache.clear()

    def get_session_cache(self) -> Dict[str, bool]:
        """导出 session cache（用于跨 Worker 持久化）"""
        return self._session_cache.copy()

    def sync_session_cache(self, cache: Dict[str, bool]) -> None:
        """从外部同步 session cache"""
        self._session_cache = cache.copy()
        logger.info(f"[PermissionCache] 同步 session 缓存: {len(cache)} 项")

    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计（用于调试）"""
        return {
            "round_count": len(self._round_cache),
            "session_count": len(self._session_cache),
        }
