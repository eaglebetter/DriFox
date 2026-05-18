# -*- coding: utf-8 -*-
"""
统一的设计系统 - Design Tokens 和样式常量
所有 UI 组件应引用此模块以保持视觉一致性
"""

from PyQt5.QtCore import QSize


# ============ 颜色系统 ============
class Colors:
    """颜色 Token"""
    # 主背景
    CARD_BG = "rgba(33, 33, 38, {alpha})"  # 卡片背景，alpha 可配置
    CARD_BG_SOLID = "rgba(33, 33, 38, 250)"  # 固定透明度版本
    
    # 内容区背景
    CONTENT_BG = "#2a2a2e"
    
    # 边框
    BORDER = "#3d3d3d"
    BORDER_ACCENT = "#f59e0b"  # 强调边框（如工具折叠框）
    
    # 文字颜色
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "rgba(255, 255, 255, 0.5)"
    TEXT_SECONDARY_HOVER = "rgba(255, 255, 255, 0.8)"
    TEXT_ACCENT = "#f59e0b"  # 标题强调色
    TEXT_MUTED = "#888888"
    
    # 标签颜色
    TAB_ACTIVE_BG = "rgba(102, 198, 255, 0.3)"
    TAB_INACTIVE = "rgba(255, 255, 255, 0.5)"
    TAB_HOVER_BG = "rgba(255, 255, 255, 0.1)"
    
    # 交互状态
    HOVER_BG = "rgba(255, 255, 255, 0.08)"
    SELECTED_BG = "rgba(102, 198, 255, 0.35)"
    
    # 语义色
    SUCCESS = "#22c55e"
    WARNING = "#f59e0b"
    ERROR = "#ef4444"
    INFO = "#3b82f6"


# ============ 圆角系统 ============
class BorderRadius:
    """圆角 Token"""
    SM = "4px"   # 小标签、小按钮
    MD = "8px"   # 卡片、输入框
    LG = "18px"  # 搜索框、输入区域


# ============ 间距系统 ============
class Spacing:
    """间距 Token（单位：px）"""
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 20
    XXL = 24


# ============ 字体系统 ============
class FontSizes:
    """字体大小 Token"""
    XS = "10px"
    SM = "11px"   # 正文、标签
    MD = "12px"   # 标题
    LG = "14px"   # 大标题


class FontWeights:
    """字重 Token"""
    NORMAL = ""
    BOLD = "bold"


# ============ 组件尺寸 ============
class Sizes:
    """组件尺寸 Token"""
    ICON_SM = QSize(12, 12)
    ICON_MD = QSize(16, 16)
    ICON_LG = QSize(20, 20)

    BUTTON_H_SM = 29  # 小按钮高度
    BUTTON_H_MD = 36  # 中按钮高度

    CARD_MIN_H = 53   # 列表项最小高度

    # ToolButton 统一规格
    TOOL_BUTTON_SZ = QSize(28, 28)
    TOOL_ICON_SZ = QSize(14, 14)

    # SwitchButton 统一规格
    SWITCH_WIDTH = 50


# ============ CSS 模板 ============
class CardStyles:
    """卡片样式模板"""
    
    @staticmethod
    def card(alpha: int = 250) -> str:
        """标准卡片样式"""
        return f"""
            CardWidget, SimpleCardWidget {{
                background-color: rgba(33, 33, 38, {alpha});
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }}
        """
    
    @staticmethod
    def card_content() -> str:
        """卡片内容区样式"""
        return """
            background-color: #2a2a2e;
            border-radius: 6px;
        """
    
    @staticmethod
    def scroll_area() -> str:
        """滚动区域样式"""
        return """
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """
    
    @staticmethod
    def title_icon(emoji: str = "⚙️") -> str:
        """标题图标样式（返回 emoji）"""
        return emoji
    
    @staticmethod
    def title_label() -> str:
        """标题文字样式"""
        return "color: #f59e0b;"
    
    @staticmethod
    def close_button() -> str:
        """关闭按钮样式"""
        return "color: #888888; cursor: pointer; padding: 4px;"


class TabStyles:
    """标签样式模板"""
    
    @staticmethod
    def active() -> str:
        return """
            QLabel {
                color: #fff;
                font-size: 11px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 4px;
                background-color: rgba(102, 198, 255, 0.3);
            }
        """
    
    @staticmethod
    def inactive() -> str:
        return """
            QLabel {
                color: rgba(255, 255, 255, 0.5);
                font-size: 11px;
                padding: 3px 8px;
                border-radius: 4px;
                cursor: pointer;
            }
            QLabel:hover {
                color: rgba(255, 255, 255, 0.8);
                background-color: rgba(255, 255, 255, 0.1);
            }
        """


class ItemStyles:
    """列表项样式模板"""
    
    @staticmethod
    def radio_button() -> str:
        """单选按钮样式"""
        return """
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 2px solid #8e8e8e;
                background-color: transparent;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #0078d4;
                background-color: #0078d4;
            }
        """
    
    @staticmethod
    def tag() -> str:
        """标签样式"""
        return """
            color: #fff; 
            font-weight: bold; 
            background-color: rgba(102, 198, 255, 0.35); 
            border-radius: 4px; 
            padding: 2px 8px;
        """


class ButtonStyles:
    """按钮统一样式模板"""

    @staticmethod
    def tool_button() -> str:
        """ToolButton 透明背景样式"""
        return "background-color: transparent; border-radius: 4px;"

    @staticmethod
    def primary_action() -> str:
        """主操作按钮样式（用于 ManualUpdateCard 等）"""
        return f"""
            PrimaryPushButton {{
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 5px 16px;
                font-size: 13px;
            }}
            PrimaryPushButton:hover {{
                background-color: #1a86d9;
            }}
            PrimaryPushButton:pressed {{
                background-color: #006cbd;
            }}
            PrimaryPushButton:disabled {{
                background-color: #444;
                color: #888;
            }}
        """


class SwitchStyles:
    """开关统一样式模板"""

    @staticmethod
    def configure(switch) -> None:
        """统一配置 SwitchButton：无文字标签 + 固定宽度"""
        switch.setOnText("")
        switch.setOffText("")
        switch.setFixedWidth(Sizes.SWITCH_WIDTH)


class ComboBoxStyles:
    """下拉框统一样式模板"""

    @staticmethod
    def dark_combo() -> str:
        """深色主题下拉框样式"""
        return f"""
            QComboBox {{
                color: #e8e8e8;
                background-color: {Colors.CONTENT_BG};
                border: 1px solid #4a4a4e;
                border-radius: 5px;
                padding: 5px 12px 5px 10px;
                min-height: 28px;
            }}
            QComboBox:hover {{
                border: 1px solid #0078d4;
                background-color: #333338;
            }}
            QComboBox:focus {{
                border: 1px solid #0078d4;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
                subcontrol-origin: padding;
                subcontrol-position: right center;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #888888;
                width: 0px;
                height: 0px;
                margin-right: 4px;
            }}
            QComboBox::down-arrow:hover {{
                border-top-color: #0078d4;
            }}
        """

    @staticmethod
    def dark_combo_dropdown() -> str:
        """深色主题下拉框弹出列表样式"""
        return f"""
            QAbstractItemView {{
                color: #e8e8e8;
                background-color: {Colors.CONTENT_BG};
                border: 1px solid #4a4a4e;
                border-radius: 6px;
                padding: 4px;
                outline: none;
                show-decoration-selected: 1;
            }}
            QAbstractItemView::item {{
                padding: 6px 14px 6px 12px;
                min-height: 36px;
                border-radius: 3px;
            }}
            QAbstractItemView::item:hover {{
                background-color: #3a3a3e;
            }}
            QAbstractItemView::item:selected {{
                background-color: #0078d4;
                color: white;
            }}
            QScrollBar:vertical {{
                background: {Colors.CONTENT_BG};
                border: none;
                width: 14px;
                margin: 4px 2px 4px 2px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """


# ============ 便捷函数 ============
def get_card_style(alpha: int = 250) -> str:
    """获取卡片样式字符串"""
    return CardStyles.card(alpha)


def get_scroll_style() -> str:
    """获取滚动区域样式字符串"""
    return CardStyles.scroll_area()


def get_content_bg_style() -> str:
    """获取内容区背景样式"""
    return f"""
        background-color: {Colors.CONTENT_BG};
        border-radius: 6px;
    """


# 从 utils 导入字体家族 CSS 函数供复用
from app.utils.utils import get_font_family_css