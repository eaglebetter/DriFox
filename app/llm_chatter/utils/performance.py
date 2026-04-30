# -*- coding: utf-8 -*-
"""性能优化工具 - 批量更新、缓存管理"""
from typing import Callable, Any, Optional
from PyQt5.QtCore import QTimer


class StreamBatcher:
    """
    流式响应批量更新器
    
    将高频的小更新合并为批量更新，减少 UI 刷新次数。
    """
    
    def __init__(self, callback: Callable[[str], None], interval_ms: int = 50):
        """
        Args:
            callback: 批量更新回调函数
            interval_ms: 批量更新间隔（毫秒）
        """
        self._callback = callback
        self._interval_ms = interval_ms
        self._pending_content = []
        self._timer: Optional[QTimer] = None
        self._locked = False
        
    def add(self, content: str):
        """添加内容到待处理队列"""
        if self._locked:
            return
        self._pending_content.append(content)
        self._schedule_flush()
        
    def _schedule_flush(self):
        """调度批量刷新"""
        if self._timer is None or not self._timer.isActive():
            self._timer = QTimer()
            self._timer.setSingleShot(True)
            self._timer.timeout.connect(self._flush)
        if not self._timer.isActive():
            self._timer.start(self._interval_ms)
            
    def _flush(self):
        """执行批量更新"""
        if not self._pending_content:
            return
            
        self._locked = True
        try:
            # 合并所有待处理内容
            combined = "".join(self._pending_content)
            self._pending_content.clear()
            # 调用回调
            self._callback(combined)
        finally:
            self._locked = False
            
    def clear(self):
        """清空待处理内容"""
        self._pending_content.clear()
        if self._timer and self._timer.isActive():
            self._timer.stop()
            
    def flush_now(self):
        """立即刷新"""
        self._flush()


class LRUCache:
    """简单的 LRU 缓存实现"""
    
    def __init__(self, max_size: int = 128):
        self._max_size = max_size
        self._cache = {}
        self._order = []
        
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self._cache:
            # 移动到末尾（最近使用）
            self._order.remove(key)
            self._order.append(key)
            return self._cache[key]
        return None
        
    def put(self, key: str, value: Any):
        """设置缓存值"""
        if key in self._cache:
            self._order.remove(key)
        elif len(self._cache) >= self._max_size:
            # 移除最旧的
            oldest = self._order.pop(0)
            del self._cache[oldest]
            
        self._cache[key] = value
        self._order.append(key)
        
    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._order.clear()
        
    def size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)


class Debouncer:
    """防抖器 - 用于延迟执行高频事件"""
    
    def __init__(self, callback: Callable, delay_ms: int = 100):
        self._callback = callback
        self._delay_ms = delay_ms
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._execute)
        self._pending_args = None
        self._pending_kwargs = None
        
    def trigger(self, *args, **kwargs):
        """触发防抖"""
        self._pending_args = args
        self._pending_kwargs = kwargs
        self._timer.start(self._delay_ms)
        
    def _execute(self):
        """执行回调"""
        if self._pending_args is not None or self._pending_kwargs is not None:
            self._callback(*self._pending_args, **self._pending_kwargs)
            self._pending_args = None
            self._pending_kwargs = None
            
    def cancel(self):
        """取消待执行的回调"""
        if self._timer.isActive():
            self._timer.stop()
        self._pending_args = None
        self._pending_kwargs = None