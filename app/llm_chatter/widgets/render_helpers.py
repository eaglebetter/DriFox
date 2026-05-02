# -*- coding: utf-8 -*-
"""
UI 渲染辅助函数
"""

import hashlib
import json
import re
from html import escape

# 预编译正则表达式
_CODE_BLOCK_PATTERN = re.compile(r"```[\w]*\n")
_CODE_BLOCK_FINAL_PATTERN = re.compile(r"```")
# 匹配 HTML 代码块标签
_HTML_CODE_BLOCK_PATTERN = re.compile(r"<(pre|code)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)


def format_tool_block(
    tool_name: str,
    tool_args: dict,
    result: str = None,
    success: bool = True,
) -> str:
    """格式化工具块为纯文本标记，用于存储"""
    args_json = json.dumps(tool_args, ensure_ascii=False)
    result_str = str(result) if result else ""

    return (
        f"<tool>\nname: {tool_name}\nargs: {args_json}\n"
        f"result: {result_str}\nsuccess: {success}\n</tool>"
    )


def _escape_text_for_plain(text: str) -> str:
    """
    清理文本中的特殊字符，避免纯文本渲染错误。
    移除：
    - HTML 标签 <...>
    - Markdown 代码块标记 ```language, ```
    - 独立反引号 `
    - 其他可能导致渲染问题的特殊字符
    """
    if not text:
        return ""
    # 1. 先移除 HTML 代码块标签 <pre>...</pre> <code>...</code>
    text = _HTML_CODE_BLOCK_PATTERN.sub("", text)
    # 2. 移除 markdown 代码块标记 ```language 和 ```
    text = _CODE_BLOCK_PATTERN.sub("", text)
    text = _CODE_BLOCK_FINAL_PATTERN.sub("", text)
    # 3. 移除独立的反引号
    text = text.replace("`", "")
    # 4. 移除 HTML 标签（用于清理残留的 HTML 标记）
    text = re.sub(r"<[^>]+>", "", text)
    # 5. 移除可能造成渲染问题的特殊空白字符
    text = text.replace("\x00", "")  # 移除 null 字符
    # 6. 规范化换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def _truncate_value(v, max_len: int = 50) -> str:
    """截断单个参数值"""
    if isinstance(v, dict):
        s = json.dumps(v, ensure_ascii=False)
        return s[:max_len] + "..." if len(s) > max_len else s
    elif isinstance(v, list):
        s = json.dumps(v, ensure_ascii=False)
        return s[:max_len] + "..." if len(s) > max_len else s
    elif isinstance(v, str):
        return v[:max_len] + "..." if len(v) > max_len else v
    else:
        s = str(v)
        return s[:max_len] + "..." if len(s) > max_len else s


def _format_args_preview(tool_args: dict, max_total_len: int = 120) -> str:
    """
    格式化参数预览为 '参数1=值1; 参数2=值2' 格式。
    限制总字数，超过则截断并添加 '...'。
    """
    if not tool_args:
        return ""
    
    parts = []
    total_len = 0
    
    for key, value in tool_args.items():
        # 清理值中的特殊字符
        value_str = _truncate_value(value)
        value_str = _escape_text_for_plain(value_str)
        
        # 构建参数片段
        part = f"{key}={value_str}"
        
        # 检查加上分隔符后是否会超过限制
        if parts:
            next_len = total_len + len(part) + 2  # +2 for "; "
            if next_len > max_total_len:
                # 检查当前是否已经超过限制
                if total_len >= max_total_len:
                    break
                # 添加当前部分（如果还没超过）
                remaining = max_total_len - total_len - 3  # space for "..."
                if remaining > 0:
                    parts.append(part[:remaining] + "...")
                else:
                    parts.append("...")
                break
        
        parts.append(part)
        total_len += len(part) + 2
        
        # 再次检查是否超过总长度
        if total_len > max_total_len:
            break
    
    result = "; ".join(parts)
    if len(result) > max_total_len:
        result = result[:max_total_len] + "..."
    
    return result


def _format_args_as_table(tool_args: dict) -> str:
    """
    将参数字典格式化为横向表格 HTML。
    左侧是参数名，右侧是对应的值。
    """
    if not tool_args:
        return '<div class="args-table"><div class="args-row empty">无参数</div></div>'
    
    rows = []
    for key, value in tool_args.items():
        # 清理值中的特殊字符
        if isinstance(value, dict):
            value_str = json.dumps(value, ensure_ascii=False)
        elif isinstance(value, list):
            value_str = json.dumps(value, ensure_ascii=False)
        else:
            value_str = str(value)
        
        # 清理特殊字符
        value_str = _escape_text_for_plain(value_str)
        
        # 截断过长的值
        max_value_len = 200
        if len(value_str) > max_value_len:
            value_str = value_str[:max_value_len] + "..."
        
        # 转义显示
        escaped_key = escape(key)
        escaped_value = escape(value_str)
        
        rows.append(f'''
        <div class="args-row">
            <span class="args-key">{escaped_key}</span>
            <span class="args-value">{escaped_value}</span>
        </div>''')
    
    return f'<div class="args-table">{"".join(rows)}</div>'


def _format_result_for_display(result: str, max_len: int = 500) -> str:
    """
    格式化结果显示，清理特殊字符并截断。
    """
    if not result:
        return '<div class="result-empty">无结果</div>'
    
    # 清理特殊字符
    cleaned = _escape_text_for_plain(str(result))
    
    # 截断
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len] + "..."
    
    # 转义
    return f'<div class="result-content">{escape(cleaned)}</div>'


def render_tool_block(
    tool_name: str,
    tool_args: dict,
    result: str = None,
    success: bool = None,
    collapsed: bool = False,
    tool_call_id: str = None,
) -> str:
    """渲染工具块，参数横向表格展示（左列参数名，右列结果值）"""
    
    # 检测是否为子智能体任务（包括旧的 task 和新的 task_batch）
    is_sub_agent_task = tool_name in ("task", "task_batch")

    # 状态图标
    status_html = ""
    if success is not None:
        status_color = "#4CAF50" if success else "#F44336"
        status_text = "✓" if success else "✗"
        status_html = (
            f'<span style="color: {status_color}; font-weight: bold; '
            f'margin-left: 6px;">{status_text}</span>'
        )

    icon = "🤖" if is_sub_agent_task else "🔧"
    title_color = "#9C27B0" if is_sub_agent_task else "#FFA500"

    # 子智能体任务特殊处理
    if is_sub_agent_task:
        agent_name = tool_args.get("agent", "unknown")
        task_desc = tool_args.get("description", "")[:50]
        if tool_args.get("description"):
            task_desc = tool_args["description"][:50] + ("..." if len(tool_args["description"]) > 50 else "")

    # 文件编辑工具判断
    file_edit_tools = {"write", "edit", "multiedit", "patch"}
    is_file_edit = tool_name in file_edit_tools and tool_args.get("path")

    # 差异对比按钮
    diff_icon_html = ""
    if is_file_edit and tool_call_id:
        diff_icon_html = f'''
        <span class="tool-diff-icon-btn" data-tool-call-id="{escape(tool_call_id)}"
            role="button" tabindex="0"
            style="display: inline-flex; align-items: center; justify-content: center; flex: 0 0 auto; background: transparent; cursor: pointer; padding: 4px; margin-left: 8px; border-radius: 4px;"
            onclick="event.stopPropagation(); window._requestToolDiff(this.dataset.toolCallId)"
            onkeydown="if(event.key === 'Enter' || event.key === ' '){{ event.preventDefault(); event.stopPropagation(); window._requestToolDiff(this.dataset.toolCallId); }}"
            title="查看文件差异">
            <img src="qrc:/icons/差异对比.svg" style="width: 16px; height: 16px;" />
        </span>'''

    # 生成参数预览（折叠时显示）
    args_preview = _format_args_preview(tool_args)
    
    # 生成参数表格（展开时显示）
    args_table_html = _format_args_as_table(tool_args)
    
    # 生成结果内容
    result_section_label = "调用子智能体" if is_sub_agent_task else "结果"
    result_content_html = _format_result_for_display(result) if result else '<div class="result-empty">无结果</div>'

    # 结果区域 HTML
    result_html = f"""
    <div class="tool-result-section">
        <div class="tool-section-label">{result_section_label}</div>
        {result_content_html}
    </div>"""

    # 完整的展开内容（参数表格 + 结果）
    expanded_content = f"""
    <div class="tool-expanded-content">
        <div class="tool-params-section">
            <div class="tool-section-label">参数</div>
            {args_table_html}
        </div>
        {result_html}
    </div>"""

    # 生成哈希 key
    block_seed = "|".join([
        str(tool_name or ""),
        json.dumps(tool_args or {}, ensure_ascii=False, sort_keys=True),
        str(result or ""),
        str(success),
    ])
    block_key = "tool-" + hashlib.sha1(block_seed.encode("utf-8")).hexdigest()[:12]
    expanded_attr = "false" if collapsed else "true"
    body_style = "" if collapsed else ' style="height:auto; opacity:1;"'

    return f"""<div class="cm-collapsible tool-block" data-block-key="{block_key}" data-expanded="{expanded_attr}" data-tool-call-id="{escape(tool_call_id or '')}" style="margin: 8px 0; background: rgba(30, 32, 40, 0.28); border: 1px solid var(--border); border-radius: 6px;">
    <button type="button" class="cm-collapsible__summary tool-block__summary" aria-expanded="{expanded_attr}" style="cursor: pointer; padding: 6px 10px; color: {title_color}; font-size: 13px; font-weight: 500; display: flex; align-items: center; gap: 10px; width: 100%; background: transparent; border: none; text-align: left; box-sizing: border-box;">
        <span style="display: inline-flex; align-items: center; gap: 6px; min-width: 0; flex: 0 1 auto;">
            <span class="cm-collapsible__chevron" aria-hidden="true"></span>
            <span style="flex: 0 0 auto;">{icon}</span>
            <span style="white-space: nowrap; flex: 0 0 auto;">{escape(tool_name)}</span>
            {status_html}
        </span>
        <span style="display: flex; align-items: flex-end; gap: 8px; margin-left: auto; min-width: 0; flex: 0 1 300px; justify-content: flex-end;">
            <span style="color: #888; font-size: 11px; text-align: right; word-break: break-all; white-space: normal; line-height: 1.4;">
                {escape(args_preview)}
            </span>
        </span>
        <span style="display: flex; align-items: center; flex: 0 0 auto;">
            {diff_icon_html}
        </span>
    </button>
    <div class="cm-collapsible__body"{body_style}>
        {expanded_content}
    </div>
</div>"""


def format_timestamp(ts: str) -> str:
    """格式化时间戳"""
    if not ts:
        return ""
    if len(ts) > 5:
        return ts[-5:]
    return ts