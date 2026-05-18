# -*- coding: utf-8 -*-
"""
Git Diff 差异对比模块

提供生成 HTML diff 报告和在 PyQt WebEngine 中显示的功能
样式 100% 复刻 GitHub 网页合并差异审核界面
"""
import orjson as json
import difflib
import re

from datetime import datetime
from pathlib import Path
from typing import List, Dict

from loguru import logger

# 预编译正则表达式
_HUNK_HEADER_PATTERN = re.compile(r"@@ -(\d+),?\d* \+(\d+),?\d* @@")


class DiffHtmlGenerator:
    """Git Diff HTML 生成器 - GitHub 风格 100% 复刻"""

    # GitHub Dark 主题样式 - 完整复刻 GitHub Diff Review Interface
    GITHUB_DARK_CSS = """
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --gh-bg-primary: #0d1117;
            --gh-bg-secondary: #161b22;
            --gh-bg-tertiary: #21262d;
            --gh-border: #30363d;
            --gh-text-primary: #c9d1d9;
            --gh-text-secondary: #8b949e;
            --gh-text-link: #58a6ff;
            --gh-green-bg: rgba(63, 185, 80, 0.15);
            --gh-green-text: #3fb950;
            --gh-green-border: rgba(63, 185, 80, 0.4);
            --gh-red-bg: rgba(248, 81, 73, 0.15);
            --gh-red-text: #f85149;
            --gh-red-border: rgba(248, 81, 73, 0.4);
            --gh-blue-bg: rgba(31, 111, 235, 0.15);
            --gh-blue-text: #388bfd;
            --gh-blue-border: rgba(31, 111, 235, 0.4);
            --gh-purple-bg: rgba(163, 113, 247, 0.15);
            --gh-purple-text: #a371f7;
            --gh-font-mono: 'Consolas', 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            --gh-font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
        }

        body {
            font-family: var(--gh-font-sans);
            background: var(--gh-bg-primary);
            color: var(--gh-text-primary);
            line-height: 1.5;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
            font-size: 12px;
        }

        .diff-app {
            display: flex;
            flex: 1;
            overflow: hidden;
        }

        .file-tree {
            width: 280px;
            min-width: 280px;
            background: var(--gh-bg-secondary);
            border-right: 1px solid var(--gh-border);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .file-tree-header {
            padding: 12px 16px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--gh-text-secondary);
            border-bottom: 1px solid var(--gh-border);
            flex-shrink: 0;
        }

        .file-tree-header .file-count {
            font-weight: 400;
            margin-left: 4px;
            opacity: 0.7;
        }

        .diff-summary {
            padding: 10px 16px;
            background: var(--gh-bg-tertiary);
            border-bottom: 1px solid var(--gh-border);
            display: flex;
            align-items: center;
            gap: 16px;
            font-size: 12px;
            flex-shrink: 0;
        }

        .diff-summary .summary-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .diff-summary .additions {
            color: var(--gh-green-text);
        }

        .diff-summary .deletions {
            color: var(--gh-red-text);
        }

        .diff-summary .separator {
            color: var(--gh-border);
        }

        .file-list {
            flex: 1;
            overflow-y: auto;
        }

        .file-item {
            display: flex;
            align-items: center;
            padding: 8px 16px;
            cursor: pointer;
            transition: background 0.1s;
            border-left: 3px solid transparent;
            text-decoration: none;
            color: var(--gh-text-primary);
            font-size: 12px;
        }

        .file-item:hover {
            background: rgba(255, 255, 255, 0.03);
        }

        .file-item.active {
            background: rgba(56, 139, 253, 0.15);
            border-left-color: var(--gh-blue-text);
        }

        .file-item .file-icon {
            margin-right: 10px;
            font-size: 14px;
            opacity: 0.8;
        }

        .file-item .file-name {
            flex: 1;
            font-family: var(--gh-font-mono);
            font-size: 12px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .file-item .file-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 11px;
            padding: 1px 6px;
            border-radius: 10px;
            margin-left: 8px;
        }

        .file-item .file-badge.added {
            background: var(--gh-green-bg);
            color: var(--gh-green-text);
        }

        .file-item .file-badge.deleted {
            background: var(--gh-red-bg);
            color: var(--gh-red-text);
        }

        .file-item .file-badge.renamed {
            background: var(--gh-purple-bg);
            color: var(--gh-purple-text);
        }

        .diff-content {
            flex: 1;
            overflow-y: auto;
        }

        .file-block {
            border-bottom: 1px solid var(--gh-border);
        }

        .file-block:last-child {
            border-bottom: none;
        }

        .file-header {
            position: sticky;
            top: 0;
            z-index: 10;
            background: var(--gh-bg-tertiary);
            padding: 10px 16px;
            border-bottom: 1px solid var(--gh-border);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .file-header .file-icon {
            font-size: 16px;
        }

        .file-header .file-path {
            color: var(--gh-text-link);
            font-family: var(--gh-font-mono);
            font-size: 13px;
            flex: 1;
        }

        .file-header .file-stats {
            display: flex;
            gap: 12px;
            font-size: 12px;
            font-family: var(--gh-font-mono);
        }

        .file-header .add-stat {
            color: var(--gh-green-text);
        }

        .file-header .del-stat {
            color: var(--gh-red-text);
        }

        .diff-table {
            width: 100%;
            border-collapse: collapse;
            font-family: var(--gh-font-mono);
            font-size: 12px;
        }

        .diff-line {
            display: flex;
        }

        .diff-line:hover {
            filter: brightness(1.1);
        }

        .line-num {
            width: 50px;
            min-width: 50px;
            padding: 0 8px;
            text-align: right;
            color: #6e7681;
            background: var(--gh-bg-primary);
            user-select: none;
            border-right: 1px solid var(--gh-border);
            vertical-align: top;
            white-space: pre;
            display: inline-block;
            font-size: 11px;
            line-height: 20px;
        }

        .line-num.old {
            background: rgba(248, 81, 73, 0.08);
            border-right-color: rgba(248, 81, 73, 0.2);
        }

        .line-num.new {
            background: rgba(63, 185, 80, 0.08);
            border-right-color: rgba(63, 185, 80, 0.2);
        }

        .line-sign {
            width: 20px;
            min-width: 20px;
            text-align: center;
            user-select: none;
            display: inline-block;
            vertical-align: top;
            font-size: 12px;
            line-height: 20px;
        }

        .line-code {
            flex: 1;
            padding: 0 12px;
            white-space: pre;
            vertical-align: top;
            display: inline-block;
            line-height: 20px;
            font-size: 12px;
            min-height: 20px;
        }

        .diff-line.added {
            background: var(--gh-green-bg);
        }

        .diff-line.added .line-num.new {
            color: var(--gh-green-text);
            background: rgba(63, 185, 80, 0.12);
        }

        .diff-line.added .line-sign {
            color: var(--gh-green-text);
        }

        .diff-line.added .line-code {
            color: var(--gh-green-text);
        }

        .diff-line.deleted {
            background: var(--gh-red-bg);
        }

        .diff-line.deleted .line-num.old {
            color: var(--gh-red-text);
            background: rgba(248, 81, 73, 0.12);
        }

        .diff-line.deleted .line-sign {
            color: var(--gh-red-text);
        }

        .diff-line.deleted .line-code {
            color: var(--gh-red-text);
        }

        .diff-line.context {
            background: transparent;
        }

        .diff-line.context .line-num {
            color: #6e7681;
        }

        .diff-line.context .line-sign {
            color: #6e7681;
        }

        .diff-line.context .line-code {
            color: var(--gh-text-primary);
        }

        .diff-line.hunk-header {
            background: var(--gh-blue-bg);
            border-top: 1px solid var(--gh-blue-border);
            border-bottom: 1px solid var(--gh-blue-border);
        }

        .diff-line.hunk-header .line-num {
            color: transparent;
            background: transparent;
            border: none;
        }

        .diff-line.hunk-header .line-sign {
            color: var(--gh-blue-text);
        }

        .diff-line.hunk-header .line-code {
            color: var(--gh-blue-text);
            font-size: 11px;
        }

        .diff-line.blank .line-code {
            background: var(--gh-bg-secondary);
        }

        .word-add {
            background: rgba(63, 185, 80, 0.35);
            border-radius: 2px;
        }

        .word-del {
            background: rgba(248, 81, 73, 0.35);
            border-radius: 2px;
            text-decoration: line-through;
        }

        .diff-expand {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 4px 16px;
            background: var(--gh-blue-bg);
            border-top: 1px dashed var(--gh-blue-border);
            border-bottom: 1px dashed var(--gh-blue-border);
            color: var(--gh-blue-text);
            cursor: pointer;
            font-family: var(--gh-font-sans);
            font-size: 11px;
            user-select: none;
            transition: background 0.15s;
            gap: 6px;
        }

        .diff-expand:hover {
            background: rgba(31, 111, 235, 0.25);
        }

        .diff-expand .expand-icon {
            font-size: 12px;
            opacity: 0.8;
        }

        .diff-expand .expand-lines {
            font-family: var(--gh-font-mono);
            font-size: 11px;
            opacity: 0.9;
        }

        .diff-collapsed-context {
            display: none;
        }

        .diff-collapsed-context.expanded {
            display: block;
        }

        .no-diff {
            text-align: center;
            padding: 80px 20px;
            color: var(--gh-text-secondary);
        }

        .no-diff-icon {
            font-size: 64px;
            margin-bottom: 20px;
            opacity: 0.5;
        }

        .no-diff h2 {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 8px;
            color: var(--gh-text-primary);
        }

        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: var(--gh-bg-secondary);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--gh-border);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #484f58;
        }

        ::-webkit-scrollbar-corner {
            background: var(--gh-bg-secondary);
        }
    </style>
    """

    @classmethod
    def escape_html(cls, text: str) -> str:
        """HTML 实体转义"""
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    @classmethod
    def generate_html_report(cls, diff_output: str, session_id: str = "", lazy_load: bool = True) -> str:
        """生成完整的 HTML diff 报告

        Args:
            diff_output: diff 文本
            session_id: 会话 ID
            lazy_load: 是否启用懒加载（启用后只渲染前3个文件，后续滚动加载）
        """
        if diff_output is None:
            diff_output = ""

        # 解析 diff
        files = cls._parse_diff(diff_output)

        # 计算统计
        total_additions = sum(f["additions"] for f in files)
        total_deletions = sum(f["deletions"] for f in files)
        total_files = len(files)

        # 生成文件树 HTML 和懒加载数据
        file_tree_html = ""
        file_blocks_html = ""

        # 预渲染前 3 个文件用于首屏快速显示
        preload_count = 3 if lazy_load and total_files > 3 else total_files

        # 生成所有文件的懒加载数据
        files_json = cls._generate_file_data_json(files)

        for i, file_info in enumerate(files):
            file_id = f"file-{i}"
            file_tree_html += cls._generate_file_tree_item(file_info, file_id, i)

            # 只预渲染前 preload_count 个文件
            if i < preload_count:
                file_blocks_html += cls._generate_file_block(file_info, file_id, i)

        # 如果没有差异
        if not files:
            file_blocks_html = """
            <div class="no-diff">
                <div class="no-diff-icon">&#9989;</div>
                <h2>没有检测到文件差异</h2>
                <p>当前会话没有修改任何文件，或所有文件已恢复到原始状态</p>
            </div>
            """

        # 生成完整 HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文件差异对比报告</title>
    {cls.GITHUB_DARK_CSS}
</head>
<body>
    <div class="diff-app">
        <div class="file-tree">
            <div class="file-tree-header">
                已修改的文件
                <span class="file-count">({total_files})</span>
            </div>
            <div class="diff-summary">
                <span class="summary-item additions">
                    <span>+{total_additions}</span>
                </span>
                <span class="separator">|</span>
                <span class="summary-item deletions">
                    <span>-{total_deletions}</span>
                </span>
                <span class="separator" style="margin-left: auto; opacity: 0.5;">
                    {datetime.now().strftime("%H:%M")}
                </span>
            </div>
            <div class="file-list">
                {file_tree_html}
            </div>
        </div>

        <div class="diff-content" id="diff-content">
            {file_blocks_html}
        </div>
    </div>

    <script>
        // 文件数据存储（用于懒加载）- 只存储diff行数据，前端按需生成HTML
        window._diffFiles = {files_json};
        window._loadedFiles = new Set({list(range(preload_count))});
        window._preloadCount = {preload_count};

        // HTML转义函数
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}

        // 字符级差异高亮（JS 端，与 Python _word_diff 保持一致）
        function wordDiff(oldText, newText) {{
            // 安全限制：行太长时跳过 word diff
            if (oldText.length + newText.length > 2000) {{
                return {{ oldHtml: escapeHtml(oldText), newHtml: escapeHtml(newText) }};
            }}

            const oldChars = Array.from(oldText);
            const newChars = Array.from(newText);
            const m = oldChars.length;
            const n = newChars.length;

            // LCS 动态规划
            const dp = [];
            for (let i = 0; i <= m; i++) {{
                dp[i] = new Uint16Array(n + 1);
            }}
            for (let i = 1; i <= m; i++) {{
                for (let j = 1; j <= n; j++) {{
                    if (oldChars[i-1] === newChars[j-1]) {{
                        dp[i][j] = dp[i-1][j-1] + 1;
                    }} else {{
                        dp[i][j] = Math.max(dp[i-1][j], dp[i][j-1]);
                    }}
                }}
            }}

            // 回溯获取操作序列
            const ops = [];
            let i = m, j = n;
            while (i > 0 || j > 0) {{
                if (i > 0 && j > 0 && oldChars[i-1] === newChars[j-1]) {{
                    ops.unshift({{ tag: 'equal', oi: i-1, nj: j-1 }});
                    i--; j--;
                }} else if (j > 0 && (i === 0 || dp[i][j-1] >= dp[i-1][j])) {{
                    ops.unshift({{ tag: 'insert', nj: j-1 }});
                    j--;
                }} else {{
                    ops.unshift({{ tag: 'delete', oi: i-1 }});
                    i--;
                }}
            }}

            // 合并连续相同 tag 的片段，生成 HTML
            const segments = [];
            for (const op of ops) {{
                const lastSeg = segments[segments.length - 1];
                if (lastSeg && lastSeg.tag === op.tag) {{
                    if (op.tag === 'equal') {{
                        lastSeg.oldEnd = op.oi + 1;
                        lastSeg.newEnd = op.nj + 1;
                    }} else if (op.tag === 'delete') {{
                        lastSeg.oldEnd = op.oi + 1;
                    }} else {{
                        lastSeg.newEnd = op.nj + 1;
                    }}
                }} else {{
                    if (op.tag === 'equal') {{
                        segments.push({{ tag: 'equal', oldStart: op.oi, oldEnd: op.oi + 1, newStart: op.nj, newEnd: op.nj + 1 }});
                    }} else if (op.tag === 'delete') {{
                        segments.push({{ tag: 'delete', oldStart: op.oi, oldEnd: op.oi + 1 }});
                    }} else {{
                        segments.push({{ tag: 'insert', newStart: op.nj, newEnd: op.nj + 1 }});
                    }}
                }}
            }}

            let oldParts = [];
            let newParts = [];
            for (const seg of segments) {{
                if (seg.tag === 'equal') {{
                    const text = oldChars.slice(seg.oldStart, seg.oldEnd).join('');
                    oldParts.push(escapeHtml(text));
                    newParts.push(escapeHtml(text));
                }} else if (seg.tag === 'delete') {{
                    const text = oldChars.slice(seg.oldStart, seg.oldEnd).join('');
                    oldParts.push('<span class="word-del">' + escapeHtml(text) + '</span>');
                }} else {{
                    const text = newChars.slice(seg.newStart, seg.newEnd).join('');
                    newParts.push('<span class="word-add">' + escapeHtml(text) + '</span>');
                }}
            }}

            return {{ oldHtml: oldParts.join(''), newHtml: newParts.join('') }};
        }}

        // 从diff行数据生成HTML行（支持行内差异高亮 + data-type 属性）
        function generateDiffRowsHtml(lines) {{
            let html = '';
            let oldLineNum = 1;
            let newLineNum = 1;
            let i = 0;

            while (i < lines.length) {{
                const line = lines[i];

                // @@ hunk header
                if (line.startsWith('@@')) {{
                    const match = line.match(/@@ -(\\d+),?\\d* \\+(\\d+),?\\d* @@/);
                    if (match) {{
                        oldLineNum = parseInt(match[1]);
                        newLineNum = parseInt(match[2]);
                    }}
                    html += `<div class="diff-line hunk-header" data-type="hunk-header">
                        <span class="line-num"></span>
                        <span class="line-num"></span>
                        <span class="line-sign"></span>
                        <span class="line-code">${{escapeHtml(line)}}</span>
                    </div>`;
                    i++;
                }}
                // deleted 行 → 收集连续的 -/+ 块做 word diff
                else if (line.startsWith('-') && !line.startsWith('---')) {{
                    const delStart = i;
                    while (i < lines.length && lines[i].startsWith('-') && !lines[i].startsWith('---')) i++;
                    const delCount = i - delStart;

                    const addStart = i;
                    while (i < lines.length && lines[i].startsWith('+') && !lines[i].startsWith('+++')) i++;
                    const addCount = i - addStart;

                    const pairCount = Math.min(delCount, addCount);
                    for (let k = 0; k < pairCount; k++) {{
                        const diff = wordDiff(lines[delStart + k].substring(1), lines[addStart + k].substring(1));
                        html += `<div class="diff-line deleted" data-type="deleted">
                            <span class="line-num old">${{oldLineNum}}</span>
                            <span class="line-num"></span>
                            <span class="line-sign">-</span>
                            <span class="line-code">${{diff.oldHtml}}</span>
                        </div>`;
                        html += `<div class="diff-line added" data-type="added">
                            <span class="line-num"></span>
                            <span class="line-num new">${{newLineNum}}</span>
                            <span class="line-sign">+</span>
                            <span class="line-code">${{diff.newHtml}}</span>
                        </div>`;
                        oldLineNum++;
                        newLineNum++;
                    }}
                    for (let k = pairCount; k < delCount; k++) {{
                        html += `<div class="diff-line deleted" data-type="deleted">
                            <span class="line-num old">${{oldLineNum}}</span>
                            <span class="line-num"></span>
                            <span class="line-sign">-</span>
                            <span class="line-code">${{escapeHtml(lines[delStart + k].substring(1))}}</span>
                        </div>`;
                        oldLineNum++;
                    }}
                    for (let k = pairCount; k < addCount; k++) {{
                        html += `<div class="diff-line added" data-type="added">
                            <span class="line-num"></span>
                            <span class="line-num new">${{newLineNum}}</span>
                            <span class="line-sign">+</span>
                            <span class="line-code">${{escapeHtml(lines[addStart + k].substring(1))}}</span>
                        </div>`;
                        newLineNum++;
                    }}
                }}
                // 独立的 added 行
                else if (line.startsWith('+') && !line.startsWith('+++')) {{
                    html += `<div class="diff-line added" data-type="added">
                        <span class="line-num"></span>
                        <span class="line-num new">${{newLineNum}}</span>
                        <span class="line-sign">+</span>
                        <span class="line-code">${{escapeHtml(line.substring(1))}}</span>
                    </div>`;
                    newLineNum++;
                    i++;
                }}
                // context 行
                else {{
                    const content = line.startsWith(' ') ? line.substring(1) : line;
                    html += `<div class="diff-line context" data-type="context">
                        <span class="line-num">${{oldLineNum}}</span>
                        <span class="line-num">${{newLineNum}}</span>
                        <span class="line-sign"></span>
                        <span class="line-code">${{escapeHtml(content)}}</span>
                    </div>`;
                    oldLineNum++;
                    newLineNum++;
                    i++;
                }}
            }}
            return html;
        }}

        // 生成文件块HTML（从数据按需生成）
        function generateFileBlockHtml(fileInfo) {{
            const addStat = fileInfo.additions > 0 ? `<span class="add-stat">+${{fileInfo.additions}}</span>` : '';
            const delStat = fileInfo.deletions > 0 ? `<span class="del-stat">-${{fileInfo.deletions}}</span>` : '';
            const headerHtml = `<div class="file-header">
                <span class="file-icon">${{fileInfo.icon}}</span>
                <span class="file-path">${{escapeHtml(fileInfo.path)}}</span>
                <div class="file-stats">${{addStat}}${{delStat}}</div>
            </div>`;
            const rowsHtml = generateDiffRowsHtml(fileInfo.lines);
            return headerHtml + `<div class="diff-table">${{rowsHtml}}</div>`;
        }}

        function loadFileContent(fileId, index) {{
            if (window._loadedFiles.has(index)) return;
            window._loadedFiles.add(index);

            const fileInfo = window._diffFiles[index];
            if (!fileInfo) return;

            const container = document.getElementById('diff-content');
            const placeholder = document.getElementById('placeholder-' + fileId);
            const blockHtml = generateFileBlockHtml(fileInfo);

            if (placeholder) {{
                placeholder.outerHTML = `<div class="file-block" id="${{fileId}}">${{blockHtml}}</div>`;
            }} else {{
                const div = document.createElement('div');
                div.id = fileId;
                div.className = 'file-block';
                div.innerHTML = blockHtml;
                container.appendChild(div);
            }}

            // 懒加载后对新生成的文件块执行折叠
            const block = document.getElementById(fileId);
            if (block) applyContextFolding(block);
        }}

        // 上下文折叠：对连续超过阈值的 context 行，折叠中间部分
        function applyContextFolding(container) {{
            const CONTEXT_THRESHOLD = 3;  // 连续 context 行超过此值时折叠中间部分
            const KEEP_HEAD = 1;           // 折叠区域前部保留的行数
            const KEEP_TAIL = 1;           // 折叠区域后部保留的行数

            const diffTables = container.querySelectorAll('.diff-table');
            diffTables.forEach(table => {{
                const allRows = table.querySelectorAll('.diff-line');
                if (allRows.length === 0) return;

                // 找出连续 context 行的区间
                const ranges = [];
                let rangeStart = -1;
                for (let i = 0; i < allRows.length; i++) {{
                    if (allRows[i].getAttribute('data-type') === 'context') {{
                        if (rangeStart === -1) rangeStart = i;
                    }} else {{
                        if (rangeStart !== -1) {{
                            ranges.push({{ start: rangeStart, end: i - 1 }});
                            rangeStart = -1;
                        }}
                    }}
                }}
                if (rangeStart !== -1) ranges.push({{ start: rangeStart, end: allRows.length - 1 }});

                // 对每个连续区间，如果行数超过阈值，折叠中间部分
                // 需要从后往前处理，避免索引偏移
                for (let r = ranges.length - 1; r >= 0; r--) {{
                    const range = ranges[r];
                    const count = range.end - range.start + 1;
                    const foldCount = count - KEEP_HEAD - KEEP_TAIL;

                    if (foldCount <= 0) continue;  // 不需要折叠

                    const foldStart = range.start + KEEP_HEAD;
                    const foldEnd = range.end - KEEP_TAIL;

                    // 将中间行包裹在折叠容器中
                    const foldedDiv = document.createElement('div');
                    foldedDiv.className = 'diff-collapsed-context';

                    // 展开按钮
                    const expandBtn = document.createElement('div');
                    expandBtn.className = 'diff-expand';
                    expandBtn.innerHTML = `<span class="expand-icon">&#9662;</span> <span class="expand-lines">${{foldCount}} 行未更改</span>`;
                    expandBtn.addEventListener('click', function() {{
                        // 展开：显示折叠的行，隐藏按钮
                        foldedDiv.classList.add('expanded');
                        this.style.display = 'none';
                        // 显示被折叠的行
                        const hiddenRows = foldedDiv.querySelectorAll('.diff-line');
                        hiddenRows.forEach(row => row.style.display = '');
                    }});

                    // 将中间行移入折叠容器
                    const rows = Array.from(allRows);
                    // 锚点：第一个 KEEP_TAIL 行（折叠区之后、keep_tail 保留行之前）
                    // 注意不能拿 range.end+1（整个context区之后），否则折叠容器会插在 keep_tail 行后面
                    const anchorRow = (foldEnd + 1 < rows.length) ? rows[foldEnd + 1] : null;
                    for (let i = foldEnd; i >= foldStart; i--) {{
                        rows[i].style.display = 'none';
                        foldedDiv.insertBefore(rows[i], foldedDiv.firstChild);
                    }}

                    // 在折叠区域起始位置插入按钮和容器
                    if (anchorRow && anchorRow.parentNode === table) {{
                        table.insertBefore(foldedDiv, anchorRow);
                        table.insertBefore(expandBtn, foldedDiv);
                    }} else {{
                        table.appendChild(expandBtn);
                        table.appendChild(foldedDiv);
                    }}
                }}
            }});
        }}

        // 点击文件列表项时加载并滚动
        document.querySelectorAll('.file-item').forEach(item => {{
            item.addEventListener('click', function(e) {{
                e.preventDefault();
                const targetId = this.getAttribute('data-target');
                const index = parseInt(targetId.replace('file-', ''));

                // 加载文件内容
                loadFileContent(targetId, index);

                // 更新激活状态
                document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
                this.classList.add('active');

                // 滚动到目标位置
                const target = document.getElementById(targetId);
                if (target) {{
                    target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }}
            }});
        }});

        // 滚动时懒加载可见区域的文件
        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    const id = entry.target.id;
                    const index = parseInt(id.replace('file-', ''));
                    loadFileContent(id, index);

                    // 更新激活状态
                    const correspondingItem = document.querySelector(`.file-item[data-target="${{id}}"]`);
                    if (correspondingItem) {{
                        document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
                        correspondingItem.classList.add('active');
                    }}
                }}
            }});
        }}, {{ threshold: 0.1, rootMargin: '200px' }});

        // 观察已加载的文件块
        document.querySelectorAll('.file-block').forEach(block => {{
            observer.observe(block);
        }});

        // 对预渲染的文件块执行上下文折叠
        document.querySelectorAll('.file-block').forEach(block => {{
            applyContextFolding(block);
        }});

        // 激活第一个文件
        const firstItem = document.querySelector('.file-item');
        if (firstItem) firstItem.classList.add('active');
    </script>
</body>
</html>"""

        return html

    @classmethod
    def _parse_diff(cls, diff_output: str) -> List[Dict]:
        """解析 unified diff 输出"""
        if not diff_output:
            return []

        files = []
        current_file = None
        current_lines = []
        current_stats = {"additions": 0, "deletions": 0}

        for line in diff_output.split("\n"):
            # 检测新文件开始
            if line.startswith("--- "):
                # 保存之前的文件
                if current_file and current_lines:
                    files.append(
                        {
                            "path": current_file,
                            "additions": current_stats["additions"],
                            "deletions": current_stats["deletions"],
                            "lines": current_lines,
                        }
                    )

                # 提取文件名
                parts = line[4:].strip()
                if parts.startswith("a/") or parts.startswith("b/"):
                    current_file = parts[2:]
                else:
                    current_file = parts

                current_lines = []
                current_stats = {"additions": 0, "deletions": 0}
                continue

            if current_file is None:
                continue

            # 统计
            if line.startswith("+") and not line.startswith("+++"):
                current_stats["additions"] += 1
            elif line.startswith("-") and not line.startswith("---"):
                current_stats["deletions"] += 1

            current_lines.append(line)

        # 保存最后一个文件
        if current_file and current_lines:
            files.append(
                {
                    "path": current_file,
                    "additions": current_stats["additions"],
                    "deletions": current_stats["deletions"],
                    "lines": current_lines,
                }
            )

        return files

    @classmethod
    def _generate_file_tree_item(cls, file_info: Dict, file_id: str, index: int) -> str:
        """生成文件树项 HTML"""
        path = file_info["path"]
        additions = file_info["additions"]
        deletions = file_info["deletions"]

        icon = cls._get_file_icon(path)
        file_name = Path(path).name

        badges = ""
        if additions > 0:
            badges += f'<span class="file-badge added">+{additions}</span>'
        if deletions > 0:
            badges += f'<span class="file-badge deleted">-{deletions}</span>'

        return f'''
        <a href="#{file_id}" class="file-item" data-target="{file_id}">
            <span class="file-icon">{icon}</span>
            <span class="file-name" title="{cls.escape_html(path)}">{cls.escape_html(file_name)}</span>
            {badges}
        </a>
        '''

    @classmethod
    def _generate_file_data_json(cls, files: List[Dict]) -> str:
        """生成文件数据 JSON（用于懒加载），只存储 diff 行数据，前端按需生成 HTML"""
        files_data = []
        for i, file_info in enumerate(files):
            file_id = f"file-{i}"
            path = file_info["path"]
            additions = file_info["additions"]
            deletions = file_info["deletions"]
            icon = cls._get_file_icon(path)

            # 只存储元数据和 diff 行，不生成 HTML
            files_data.append({
                "id": file_id,
                "path": path,
                "icon": icon,
                "additions": additions,
                "deletions": deletions,
                "lines": file_info["lines"]
            })

        result = json.dumps(files_data).decode('utf-8')
        # fix: 转义 </ 为 \u003C/，防止嵌入 <script> 标签时被浏览器提前关闭
        # 当 diff 内容包含 HTML/JS 代码（如 </script>、</div> 等）时，
        # 浏览器 HTML 解析器会误将 JSON 字符串中的 </ 识别为脚本结束标记
        result = result.replace('</', '\\u003C/')
        return result

    @classmethod
    def _word_diff(cls, old_text: str, new_text: str) -> tuple:
        """对两行文本做字符级差异高亮，返回 (old_html, new_html)"""
        # 安全限制：行太长时跳过 word diff，避免性能问题
        if len(old_text) + len(new_text) > 2000:
            return cls.escape_html(old_text), cls.escape_html(new_text)

        matcher = difflib.SequenceMatcher(None, old_text, new_text, autojunk=False)
        old_parts = []
        new_parts = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                old_parts.append(cls.escape_html(old_text[i1:i2]))
                new_parts.append(cls.escape_html(new_text[j1:j2]))
            elif tag == 'delete':
                old_parts.append(
                    f'<span class="word-del">{cls.escape_html(old_text[i1:i2])}</span>'
                )
            elif tag == 'insert':
                new_parts.append(
                    f'<span class="word-add">{cls.escape_html(new_text[j1:j2])}</span>'
                )
            elif tag == 'replace':
                old_parts.append(
                    f'<span class="word-del">{cls.escape_html(old_text[i1:i2])}</span>'
                )
                new_parts.append(
                    f'<span class="word-add">{cls.escape_html(new_text[j1:j2])}</span>'
                )
        return ''.join(old_parts), ''.join(new_parts)

    @classmethod
    def _generate_file_block_header(cls, file_info: Dict, file_id: str) -> str:
        """生成文件块头部 HTML"""
        path = file_info["path"]
        additions = file_info["additions"]
        deletions = file_info["deletions"]
        icon = cls._get_file_icon(path)

        return f'''<div class="file-header">
            <span class="file-icon">{icon}</span>
            <span class="file-path">{cls.escape_html(path)}</span>
            <div class="file-stats">
                {f'<span class="add-stat">+{additions}</span>' if additions > 0 else ""}
                {f'<span class="del-stat">-{deletions}</span>' if deletions > 0 else ""}
            </div>
        </div>'''

    @classmethod
    def _generate_file_block_rows(cls, file_info: Dict) -> str:
        """生成文件块的行内容 HTML（不含外层容器）

        支持行内差异高亮：连续的 -/+ 行对会做字符级 diff
        每行添加 data-type 属性，供 JS 端折叠逻辑使用
        """
        lines = file_info["lines"]
        diff_rows_html = ""
        old_line_num = 1
        new_line_num = 1
        i = 0

        while i < len(lines):
            line = lines[i]

            if line.startswith("@@"):
                match = _HUNK_HEADER_PATTERN.search(line)
                if match:
                    old_line_num = int(match.group(1))
                    new_line_num = int(match.group(2))
                diff_rows_html += f"""
                <div class="diff-line hunk-header" data-type="hunk-header">
                    <span class="line-num"></span>
                    <span class="line-num"></span>
                    <span class="line-sign"></span>
                    <span class="line-code">{cls.escape_html(line)}</span>
                </div>
                """
                i += 1

            elif line.startswith("-") and not line.startswith("---"):
                # 收集连续的 deleted 行
                del_start = i
                while i < len(lines) and lines[i].startswith("-") and not lines[i].startswith("---"):
                    i += 1
                del_count = i - del_start

                # 收集紧随的连续 added 行
                add_start = i
                while i < len(lines) and lines[i].startswith("+") and not lines[i].startswith("+++"):
                    i += 1
                add_count = i - add_start

                # 配对处理：做 word diff
                pair_count = min(del_count, add_count)
                for k in range(pair_count):
                    old_text = lines[del_start + k][1:]
                    new_text = lines[add_start + k][1:]
                    old_html, new_html = cls._word_diff(old_text, new_text)
                    diff_rows_html += f"""
                    <div class="diff-line deleted" data-type="deleted">
                        <span class="line-num old">{old_line_num}</span>
                        <span class="line-num"></span>
                        <span class="line-sign">-</span>
                        <span class="line-code">{old_html}</span>
                    </div>
                    """
                    diff_rows_html += f"""
                    <div class="diff-line added" data-type="added">
                        <span class="line-num"></span>
                        <span class="line-num new">{new_line_num}</span>
                        <span class="line-sign">+</span>
                        <span class="line-code">{new_html}</span>
                    </div>
                    """
                    old_line_num += 1
                    new_line_num += 1

                # 未配对的 deleted 行
                for k in range(pair_count, del_count):
                    diff_rows_html += f"""
                    <div class="diff-line deleted" data-type="deleted">
                        <span class="line-num old">{old_line_num}</span>
                        <span class="line-num"></span>
                        <span class="line-sign">-</span>
                        <span class="line-code">{cls.escape_html(lines[del_start + k][1:])}</span>
                    </div>
                    """
                    old_line_num += 1

                # 未配对的 added 行
                for k in range(pair_count, add_count):
                    diff_rows_html += f"""
                    <div class="diff-line added" data-type="added">
                        <span class="line-num"></span>
                        <span class="line-num new">{new_line_num}</span>
                        <span class="line-sign">+</span>
                        <span class="line-code">{cls.escape_html(lines[add_start + k][1:])}</span>
                    </div>
                    """
                    new_line_num += 1

            elif line.startswith("+") and not line.startswith("+++"):
                # 独立的 added 行（前面没有 deleted 行）
                diff_rows_html += f"""
                <div class="diff-line added" data-type="added">
                    <span class="line-num"></span>
                    <span class="line-num new">{new_line_num}</span>
                    <span class="line-sign">+</span>
                    <span class="line-code">{cls.escape_html(line[1:])}</span>
                </div>
                """
                new_line_num += 1
                i += 1

            elif line.startswith(" "):
                content = line[1:] if line else ""
                diff_rows_html += f"""
                <div class="diff-line context" data-type="context">
                    <span class="line-num">{old_line_num}</span>
                    <span class="line-num">{new_line_num}</span>
                    <span class="line-sign"></span>
                    <span class="line-code">{cls.escape_html(content)}</span>
                </div>
                """
                old_line_num += 1
                new_line_num += 1
                i += 1

            else:
                # 其他行（如 \ No newline at end of file）
                diff_rows_html += f"""
                <div class="diff-line context" data-type="context">
                    <span class="line-num"></span>
                    <span class="line-num"></span>
                    <span class="line-sign"></span>
                    <span class="line-code">{cls.escape_html(line)}</span>
                </div>
                """
                i += 1

        return diff_rows_html

    @classmethod
    def _generate_file_block(cls, file_info: Dict, file_id: str, index: int) -> str:
        """生成文件块 HTML（包含头部和内容）"""
        header_html = cls._generate_file_block_header(file_info, file_id)
        rows_html = cls._generate_file_block_rows(file_info)

        return f'''
        <div class="file-block" id="{file_id}">
            {header_html}
            <div class="diff-table">
                {rows_html}
            </div>
        </div>
        '''

    @classmethod
    def _get_file_icon(cls, path: str) -> str:
        """获取文件图标"""
        if path.endswith(".py"):
            return "&#128464;"
        elif path.endswith(".json"):
            return "&#128196;"
        elif path.endswith((".js", ".ts")):
            return "&#128203;"
        elif path.endswith((".html", ".css")):
            return "&#127760;"
        else:
            return "&#128196;"

    @classmethod
    def get_diff_for_files(cls, file_paths: List[str], session_id: str = "") -> str:
        """获取指定文件的差异（直接从备份目录对比）"""
        try:
            # 过滤存在的文件
            existing_files = [f for f in file_paths if Path(f).exists()]

            if not existing_files:
                logger.warning("[DiffHtml] 没有找到有效的文件路径")
                return ""

            # 备份目录: {app_data_dir}/backups/{session_id}/
            from app.utils.utils import get_app_data_dir
            backup_dir = get_app_data_dir() / "backups" / session_id

            if not backup_dir.exists():
                logger.warning(f"[DiffHtml] 备份目录不存在: {backup_dir}")
                return ""

            # 生成 unified diff
            diff_parts = []

            for current_path in existing_files:
                try:
                    filename = Path(current_path).name
                    file_stem = Path(current_path).stem

                    # 在备份目录中查找匹配的文件（跳过 .after.bak）
                    backup_path = None
                    bak_files = sorted(
                        f for f in backup_dir.glob(f"{file_stem}*.bak")
                        if not f.name.endswith('.after.bak')
                    )
                    if bak_files:
                        backup_path = bak_files[0]  # 选择最早的备份

                    if not backup_path:
                        logger.debug(f"[DiffHtml] 未找到备份: {filename}")
                        continue

                    # 读取文件内容
                    with open(
                            backup_path, "r", encoding="utf-8", errors="replace"
                    ) as f:
                        old_content = f.read()
                    with open(
                            current_path, "r", encoding="utf-8", errors="replace"
                    ) as f:
                        new_content = f.read()

                    # 使用 difflib 生成 unified diff（确保每行都有换行符，处理单行文件无末尾换行符的情况）
                    def normalize_lines(content):
                        lines = content.splitlines(keepends=True)
                        if lines and not lines[-1].endswith('\n'):
                            lines[-1] += '\n'
                        return lines

                    old_lines = normalize_lines(old_content)
                    new_lines = normalize_lines(new_content)

                    abs_path = str(Path(current_path).resolve())
                    diff = difflib.unified_diff(
                        old_lines,
                        new_lines,
                        fromfile=abs_path,
                        tofile=abs_path,
                        lineterm="\n",
                        n=5,
                    )

                    diff_text = "".join(diff)
                    if diff_text:
                        diff_parts.append(diff_text)
                        logger.debug(f"[DiffHtml] {filename}: 找到差异")

                except Exception as e:
                    logger.warning(f"[DiffHtml] 对比失败 {current_path}: {e}")
                    continue

            result = "\n".join(diff_parts)
            logger.info(
                f"[DiffHtml] 对比完成: {len(result)} 字符, {len(diff_parts)} 个文件"
            )
            return result

        except Exception as e:
            logger.error(f"[DiffHtml] 获取 diff 失败: {e}")
            return ""

    @classmethod
    def generate_report_for_files(
            cls, file_paths: List[str], session_id: str = ""
    ) -> str:
        """为指定文件生成 diff 报告"""
        diff_output = cls.get_diff_for_files(file_paths, session_id)
        return cls.generate_html_report(diff_output or "", session_id)


class DiffViewerWindow:
    """PyQt WebEngine 差异查看窗口"""

    _instances = []

    @classmethod
    def close_all(cls):
        """关闭所有实例"""
        for window in cls._instances[:]:
            try:
                window.close()
            except Exception:
                pass
        cls._instances.clear()

    def __init__(self, parent=None):
        """初始化窗口"""
        from PyQt5.QtWidgets import QDialog, QHBoxLayout
        from PyQt5.QtCore import Qt
        from PyQt5.QtWebEngineWidgets import QWebEngineView

        self._window = QDialog(parent)
        self._dialog_class = QDialog
        self._window.setWindowTitle("文件差异对比")
        self._window.resize(1200, 800)

        if parent:
            self._window.setWindowFlags(self._window.windowFlags() | Qt.WindowModal)

        # 创建布局
        layout = QHBoxLayout(self._window)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建 WebEngineView
        self._webview = QWebEngineView()

        layout.addWidget(self._webview)

        # 注册关闭事件
        self._window.destroyed.connect(lambda: self._on_closed())
        self._instances.append(self)

    def _on_closed(self):
        """窗口关闭回调"""
        # 释放 WebEngineView 中的 HTML 和 JS 内存
        page = self._webview.page()
        if page:
            try:
                page.runJavaScript("delete window._diffFiles; delete window._loadedFiles;")
            except Exception:
                pass
        try:
            self._webview.setHtml("")
        except Exception:
            pass
        self._current_html = None
        if self in self._instances:
            self._instances.remove(self)

    def load_html(self, html_content: str):
        """加载 HTML 内容（先清空再加载，避免内存累积）"""
        self._webview.setHtml(html_content or "")
        self._current_html = html_content

    def show(self):
        """显示窗口"""
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def close(self):
        """关闭窗口并释放资源"""
        # 清空 WebEngineView 释放 HTML 和 JS 内存
        page = self._webview.page()
        if page:
            try:
                page.runJavaScript("delete window._diffFiles; delete window._loadedFiles;")
            except Exception:
                pass
        
        self._webview.setHtml("")
        self._current_html = None
        self._window.close()

    @property
    def widget(self):
        """获取底层窗口部件"""
        return self._window
