# -*- coding: utf-8 -*-
"""
通用设置卡片基类 — 现在继承自 AnimatedCardFrame，获得彩虹边框动画

保留原有 API 兼容，继承动画和标准头部布局
"""

from app.widgets.animated_card_frame import AnimatedCardFrame


class BaseSettingsCard(AnimatedCardFrame):
    """通用设置卡片基类（向后兼容）"""

    def __init__(self, title: str, icon: str = "⚙️", parent=None):
        super().__init__(parent)
        self.set_icon(icon)
        self.set_title_text(title)

    def set_title(self, title: str):
        """动态设置卡片标题"""
        if " " in title:
            parts = title.split(" ", 1)
            self.set_icon(parts[0])
            self.set_title_text(parts[1])
        else:
            self.set_title_text(title)