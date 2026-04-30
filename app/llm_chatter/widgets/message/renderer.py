# -*- coding: utf-8 -*-
"""消息渲染器 - Markdown 解析、代码高亮、HTML 生成"""
import base64
import hashlib
import re
from html import escape
from functools import lru_cache
from markdown import Markdown

from app.llm_chatter.widgets.message.style import MARKDOWN_CSS, ACTION_COLOR_MAP, DEFAULT_ACTION_COLOR

# 预编译正则
_CODE_BLOCK_PATTERN = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_CODE_BLOCK_WITH_LANG_PATTERN = re.compile(r"<pre><code(?:\s+class=\"([^\"]*)\")?>(.*?)</code></pre>", re.DOTALL)
_CONTEXT_LINK_PATTERN = re.compile(r"`*\[([^\[\]]+?)\]\(([^)\s]+)\)`*")

# Markdown 实例缓存
_md_instance = None

def get_markdown_instance():
    global _md_instance
    if _md_instance is None:
        _md_instance = Markdown(
            extensions=["fenced_code", "nl2br", "tables"],
            output_format="html5",
            safe=False,
        )
    return _md_instance

# 内容哈希缓存
_content_hash_cache = {}

def _get_content_hash(content: str) -> str:
    """获取内容的 MD5 哈希（带缓存）"""
    if content in _content_hash_cache:
        return _content_hash_cache[content]
    h = hashlib.md5(content.encode('utf-8')).hexdigest()
    if len(_content_hash_cache) < 1000:  # 限制缓存大小
        _content_hash_cache[content] = h
    return h

@lru_cache(maxsize=512)
def _render_markdown_cached(content_hash: str, content: str) -> str:
    """带缓存的 Markdown 渲染"""
    md = get_markdown_instance()
    md.reset()
    return md.convert(content)

def render_markdown(content: str) -> str:
    """渲染 Markdown 为 HTML"""
    if not content:
        return ""
    return _render_markdown_cached(_get_content_hash(content), content)

def render_markdown_batch(contents: list) -> list:
    """批量渲染 Markdown（优化多内容渲染）"""
    return [render_markdown(c) for c in contents]

def unwrap_code_blocks_with_context_links(md_text: str) -> str:
    """处理带有上下文链接的代码块"""
    def replacer(match):
        lang_part = match.group(1) or ""
        code_content = match.group(2)
        if re.search(r"\[[^\[\]]+\]\([^)\s]+\)", code_content) and lang_part not in ("python",):
            return code_content
        else:
            return f"```{lang_part}\n{code_content}```" if lang_part else f"```\n{code_content}```"
    return _CODE_BLOCK_PATTERN.sub(replacer, md_text)

def strip_code_blocks(text: str) -> str:
    """移除 markdown 代码块"""
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = text.replace("`", "")
    return text

def get_action_color(action: str) -> str:
    """获取动作颜色"""
    return ACTION_COLOR_MAP.get(action.lower(), DEFAULT_ACTION_COLOR)

def render_tool_block(tool_name: str, arguments: dict, result: str, success: bool) -> str:
    """渲染工具调用块"""
    status_class = "success" if success else "error"
    status_icon = "✓" if success else "✗"
    args_str = ""
    if arguments:
        try:
            import json
            args_str = json.dumps(arguments, ensure_ascii=False, indent=2)
        except:
            args_str = str(arguments)
    
    return f'''
<div class="tool-block {status_class}">
    <div class="tool-header">
        <span class="tool-icon">{status_icon}</span>
        <span class="tool-name">{escape(tool_name)}</span>
    </div>
    {f'<pre style="margin:8px 0;padding:8px;background:rgba(0,0,0,0.2);border-radius:4px;font-size:12px;"><code>{escape(args_str)}</code></pre>' if args_str else ''}
    <div class="tool-result">{escape(str(result)[:300])}</div>
</div>
'''

def wrap_html_with_css(html_content: str, role: str = "assistant") -> str:
    """包装 HTML 内容，添加基础 CSS"""
    # 包含通用样式
    base_style = """
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px; 
            line-height: 1.6; 
            color: #E0E0E0;
            background: transparent;
            margin: 0;
            padding: 0;
        }
        pre { 
            background: rgba(30, 32, 40, 0.8); 
            padding: 12px; 
            border-radius: 8px; 
            overflow-x: auto;
        }
        code { 
            font-family: 'Cascadia Code', Consolas, monospace; 
            font-size: 13px;
        }
        p { margin: 8px 0; }
        h1, h2, h3, h4 { color: #FFFFFF; margin: 16px 0 8px 0; }
        a { color: #64B5F6; }
        blockquote { 
            border-left: 3px solid #64B5F6; 
            margin: 8px 0; 
            padding-left: 12px;
            color: #B0B0B0;
        }
    </style>
    """
    return f"<!DOCTYPE html><html><head>{base_style}</head><body>{html_content}</body></html>"

def render_thinking_box(content: str, expanded: bool = False) -> str:
    """渲染思考内容框"""
    display = "block" if expanded else "none"
    return f'''
<div style="
    background: rgba(255, 165, 0, 0.08);
    border: 1px solid rgba(255, 165, 0, 0.3);
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
">
    <div style="color: #FFA500; font-size: 12px; margin-bottom: 8px;">
        💭 思考过程
    </div>
    <div style="font-size: 13px; color: #C0C0C0;">
        {content}
    </div>
</div>
'''


class StreamingRenderer:
    """
    流式渲染器 - 用于流式响应的增量渲染
    
    优化点：
    1. 增量更新，避免全量重渲染
    2. 批量更新，减少 DOM 操作
    3. 思考内容和正文分离渲染
    """
    
    def __init__(self):
        self._content_buffer = []
        self._thinking_buffer = []
        self._rendered_html = ""
        self._thinking_html = ""
        self._last_update_len = 0
        
    def append_content(self, chunk: str):
        """追加内容块"""
        self._content_buffer.append(chunk)
        
    def append_thinking(self, chunk: str):
        """追加思考内容"""
        self._thinking_buffer.append(chunk)
        
    def get_rendered_content(self) -> str:
        """获取渲染后的正文内容"""
        new_content = "".join(self._content_buffer)
        if len(new_content) > self._last_update_len:
            # 只渲染增量部分
            incremental = new_content[self._last_update_len:]
            self._rendered_html += render_markdown(incremental)
            self._last_update_len = len(new_content)
        return self._rendered_html
        
    def get_rendered_thinking(self) -> str:
        """获取渲染后的思考内容"""
        thinking = "".join(self._thinking_buffer)
        self._thinking_html = render_markdown(thinking)
        return self._thinking_html
        
    def get_combined_html(self) -> str:
        """获取组合后的 HTML"""
        thinking = self.get_rendered_thinking()
        content = self.get_rendered_content()
        if thinking:
            return render_thinking_box(thinking, expanded=False) + content
        return content
        
    def reset(self):
        """重置渲染器"""
        self._content_buffer.clear()
        self._thinking_buffer.clear()
        self._rendered_html = ""
        self._thinking_html = ""
        self._last_update_len = 0
        
    def flush(self):
        """刷新缓冲区"""
        self.get_rendered_content()
        self.get_rendered_thinking()