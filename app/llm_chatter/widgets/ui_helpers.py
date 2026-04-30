# -*- coding: utf-8 -*-
"""
UI 辅助模块 - 从 main_widget.py 提取的 UI 辅助方法

这些方法独立于主类，可以安全使用。
"""
from typing import Optional
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt
from loguru import logger


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
