# -*- coding: utf-8 -*-
"""消息样式定义"""
from PyQt5.QtGui import QColor

# 动作颜色映射
ACTION_COLOR_MAP = {
    "jump": "#FFA500",
    "create": "#9370DB",
    "generate": "#32CD32",
    "ask": "#FF6347",
    "view": "#4169E1",
}
DEFAULT_ACTION_COLOR = "#888888"

# 卡片样式模板
def get_card_style(role: str = "assistant", custom_bg: str = None, custom_border: str = None) -> str:
    """获取卡片样式"""
    if role == "user":
        bg = custom_bg or "rgba(40, 50, 70, 180)"
        border = custom_border or "1px solid rgba(80, 100, 140, 150)"
    elif role == "tool":
        bg = custom_bg or "rgba(25, 30, 40, 220)"
        border = custom_border or "1px solid rgba(100, 120, 160, 100)"
    elif role == "welcome":
        bg = custom_bg or "rgba(30, 35, 45, 200)"
        border = custom_border or "1px solid rgba(60, 80, 110, 120)"
    else:  # assistant
        bg = custom_bg or "rgba(30, 35, 45, 200)"
        border = custom_border or "1px solid rgba(60, 80, 110, 120)"
    
    return f"""
        MessageCard {{
            background-color: {bg};
            border: {border};
            border-radius: 12px;
            padding: 12px;
        }}
    """

# 渲染器颜色常量
MARKDOWN_CSS = """
<style>
    .code-container {{
        display: flex;
        margin: 12px 0;
        background: rgba(30, 32, 40, 0.85);
        border: 1px solid rgba(58, 63, 71, 0.6);
        border-radius: 10px;
        overflow: hidden;
        font-family: Consolas, monospace;
        font-size: 13px;
    }}
    .line-numbers {{
        padding: 12px 8px;
        background: rgba(20, 22, 30, 0.8);
        color: #606060;
        font-size: 12px;
        user-select: none;
        border-right: 1px solid rgba(58, 63, 71, 0.6);
        white-space: pre;
        line-height: 1.5;
        min-width: 40px;
        text-align: right;
    }}
    .code-content {{
        flex: 1;
        overflow-x: auto;
        padding: 12px;
        line-height: 1.5;
    }}
    .code-content pre {{
        margin: 0;
        padding: 0;
        background: transparent;
        font-family: inherit;
        font-size: inherit;
    }}
    .tool-block {{
        margin: 8px 0;
        padding: 10px 12px;
        border-radius: 8px;
        font-size: 13px;
    }}
    .tool-block.success {{
        background: rgba(40, 50, 35, 0.9);
        border: 1px solid rgba(60, 120, 60, 0.3);
    }}
    .tool-block.error {{
        background: rgba(50, 35, 35, 0.9);
        border: 1px solid rgba(120, 60, 60, 0.3);
    }}
    .tool-header {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
    }}
    .tool-icon {{
        font-weight: bold;
    }}
    .tool-block.success .tool-icon {{
        color: #4CAF50;
    }}
    .tool-block.error .tool-icon {{
        color: #f44336;
    }}
    .tool-name {{
        color: #9E9E9E;
        font-size: 12px;
    }}
    .tool-result {{
        color: #E0E0E0;
        word-break: break-all;
    }}
</style>
"""