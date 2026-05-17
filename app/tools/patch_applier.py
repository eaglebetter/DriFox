# -*- coding: utf-8 -*-
"""
PatchApplier 模块 - unified diff 格式补丁应用器

从 FileTools 中提取的补丁应用逻辑，专门负责：
1. 解析 unified diff 格式
2. 验证 context 行匹配
3. 将补丁应用到原始文件内容

纯函数式设计，可独立测试。
"""

import re
from typing import Dict, List, Tuple

# 预编译hunk头信息正则
_HUNK_HEADER_PATTERN = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PatchApplierError(Exception):
    """PatchApplier 专用异常"""
    pass


class PatchApplier:
    """Unified diff 补丁应用器"""

    @staticmethod
    def parse_unified_diff(patch_lines: List[str]) -> List[Dict]:
        """
        解析 unified diff 格式，返回 hunks 列表。

        Args:
            patch_lines: patch 文件的每一行

        Returns:
            hunks 列表，每个 hunk 包含:
            - old_start: 旧文件起始行号（1-based）
            - old_count: 旧文件受影响行数
            - new_count: 新文件受影响行数
            - content: [(typ, text), ...] 其中 typ=' '/'-'/ '+'
        """
        hunks = []
        i = 0

        # 跳过头部（--- a/... 和 +++ b/... 等）
        while i < len(patch_lines) and not patch_lines[i].startswith("@@"):
            i += 1

        while i < len(patch_lines):
            line = patch_lines[i]
            if not line.startswith("@@"):
                i += 1
                continue

            m = _HUNK_HEADER_PATTERN.match(line)
            if not m:
                i += 1
                continue

            old_start = int(m.group(1))
            old_count = int(m.group(2)) if m.group(2) else 1
            new_count = int(m.group(4)) if m.group(4) else 1
            hunk_content = []

            i += 1
            while i < len(patch_lines):
                pl = patch_lines[i]

                # 检测下一个 hunk 开始
                if pl.startswith("@@"):
                    break

                # 空行处理：检查是否属于 hunk 的一部分
                # 如果上一行是 context/+/-，空行可能是实际的 context 行
                if not pl:
                    # 空行处理：检查周围上下文决定是否属于 hunk
                    # 简化处理：跳过空行
                    i += 1
                    continue

                # 解析 hunk 内容行
                if pl.startswith("+") and not pl.startswith("+++"):
                    hunk_content.append(('+', pl[1:]))
                elif pl.startswith("-") and not pl.startswith("---"):
                    hunk_content.append(('-', pl[1:]))
                elif pl.startswith(" "):
                    hunk_content.append((' ', pl[1:]))
                elif pl.startswith("\\"):  # 尾部空行标记 "\ No newline at end of file"
                    i += 1
                    continue
                else:
                    # 不认识的行，可能不属于这个 hunk
                    break

                i += 1

            if hunk_content:
                hunks.append({
                    'old_start': old_start,
                    'old_count': old_count,
                    'new_count': new_count,
                    'content': hunk_content
                })

        return hunks

    @staticmethod
    def validate_hunk(original_lines: List[str], hunk: Dict) -> Tuple[bool, str]:
        """
        验证 hunk 的 context 行是否与原始文件匹配。

        Args:
            original_lines: 原始文件的行列表
            hunk: 解析后的 hunk 字典

        Returns:
            (is_valid, error_message)
        """
        content = hunk['content']
        old_start = hunk['old_start']

        file_pos = old_start - 1  # 转为 0-based
        for typ, text in content:
            if typ in (' ', '-'):
                if file_pos >= len(original_lines):
                    return False, (
                        f"Patch context mismatch at line {file_pos + 1} "
                        f"(hunk @@ -{old_start},... @@):\n"
                        f"  Patch expects: {repr(text)}\n"
                        f"  File has:      <EOF>"
                    )

                if original_lines[file_pos] != text:
                    prev_line = repr(original_lines[file_pos - 1]) if file_pos > 0 else '<start>'
                    next_line = repr(original_lines[file_pos + 1]) if file_pos + 1 < len(original_lines) else '<EOF>'
                    return False, (
                        f"Patch context mismatch at line {file_pos + 1} (hunk @@ -{old_start},... @@):\n"
                        f"  Patch expects:  {repr(text)}\n"
                        f"  File has:       {repr(original_lines[file_pos])}\n"
                        f"  File line {file_pos}:     {prev_line}\n"
                        f"  File line {file_pos + 2}: {next_line}\n\n"
                        f"Possible causes:\n"
                        f"  1. @@ line number is wrong — the first context line '{content[0][1] if content else ''}' "
                        f"actually starts at a different position\n"
                        f"  2. Patch content doesn't exactly match the file (check indentation/spaces)\n"
                        f"  3. The file has been modified since it was last read"
                    )
                file_pos += 1
            # '+' 行不消耗文件行，跳过

        return True, ""

    @staticmethod
    def apply_hunk(original_lines: List[str], hunk: Dict) -> List[str]:
        """
        将单个 hunk 应用到原始文件行列表。

        Args:
            original_lines: 原始文件的行列表
            hunk: 解析后的 hunk 字典

        Returns:
            应用 hunk 后的行列表
        """
        content = hunk['content']
        old_start = hunk['old_start']

        file_pos = old_start - 1  # 转为 0-based
        replace_start = file_pos
        replacement = []

        for typ, text in content:
            if typ == ' ':
                # context 行：保留原文件行
                replacement.append(original_lines[file_pos])
                file_pos += 1
            elif typ == '-':
                # delete 行：跳过原文件行，不加入替换结果
                file_pos += 1
            elif typ == '+':
                # add 行：加入替换结果，不推进文件指针
                replacement.append(text)

        replace_end = file_pos

        result = list(original_lines)
        result[replace_start:replace_end] = replacement
        return result

    @classmethod
    def apply_to_content(cls, original_content: str, patch_content: str) -> Tuple[bool, str, str]:
        """
        将补丁应用到原始内容。

        Args:
            original_content: 原始文件内容
            patch_content: unified diff 格式的补丁内容

        Returns:
            (success, error_message, modified_content)
            失败时 modified_content 为空字符串
        """
        try:
            # 处理换行符转义
            processed_content = patch_content.strip()
            real_newlines = processed_content.count('\n')
            escaped_newlines = processed_content.count('\\n')
            if escaped_newlines > real_newlines:
                processed_content = processed_content.replace('\\n', '\n')

            # 解析 patch
            patch_lines = processed_content.split('\n')
            hunks = cls.parse_unified_diff(patch_lines)

            if not hunks:
                return False, "No valid hunk found in patch", ""

            # 按行分割原始内容
            original_lines = original_content.splitlines()

            # 从后往前处理每个 hunk
            result = list(original_lines)
            for hunk in reversed(hunks):
                # 验证
                is_valid, error = cls.validate_hunk(result, hunk)
                if not is_valid:
                    return False, error, ""

                # 应用
                result = cls.apply_hunk(result, hunk)

            # 重组内容（保持原始换行风格）
            if original_content.endswith('\n'):
                modified_content = "\n".join(result) + "\n"
            else:
                modified_content = "\n".join(result)

            return True, "", modified_content

        except PatchApplierError as e:
            return False, str(e), ""
        except Exception as e:
            return False, f"Patch error: {str(e)}", ""