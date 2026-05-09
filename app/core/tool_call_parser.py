# -*- coding: utf-8 -*-
"""
ToolCall 解析器模块 - 从 LLM 响应中提取和修复工具调用参数

从 ChatWorker 中提取的工具调用解析逻辑，专门负责：
1. 预编译正则表达式
2. 修复模型生成的不规范 JSON
3. 智能解析 arguments
"""

import copy
import json
import re
from typing import Dict, Optional, Tuple

# ========== 预编译正则表达式 ==========
RE_PATH = re.compile(r'"path"\s*:\s*"([^"]*)"')
RE_FILE_PATH = re.compile(r'"filePath"\s*:\s*"([^"]*)"')
RE_COMMAND = re.compile(r'"command"\s*:\s*"([^"]*)"')
RE_CONTENT_KEY = re.compile(r'"content"\s*:\s*"')
RE_ARG_PATTERN = {
    "url": re.compile(r'"url"\s*:\s*"([^"]*)"'),
    "pattern": re.compile(r'"pattern"\s*:\s*"([^"]*)"'),
    "query": re.compile(r'"query"\s*:\s*"([^"]*)"'),
    "name": re.compile(r'"name"\s*:\s*"([^"]*)"'),
    "question": re.compile(r'"question"\s*:\s*"([^"]*)"'),
}
RE_GENERIC_ARG = re.compile(r'"({param})"\s*:\s*"([^"]*)"')


def try_fix_malformed_json_arguments(raw_args: str, tool_name: str) -> Tuple[Optional[Dict], str]:
    """
    尝试修复模型生成的不规范 JSON。
    
    模型有时会生成不规范的 JSON，例如：
    - 只有 path 但没有完整的 JSON 结构
    - content 字段被截断
    - 缺少引号或转义

    Args:
        raw_args: 原始参数字符串
        tool_name: 工具名称（用于特定工具的修复策略）

    Returns:
        (修复后的参数字典, 修复状态字符串)
        状态: "fixed_content", "fixed_truncated", "fixed_content_only", 
             "fixed_bash", "fixed_partial", "fix_failed", "empty_or_invalid_input"
    """
    if not raw_args or not isinstance(raw_args, str):
        return None, "empty_or_invalid_input"

    args = {}

    # 提取常见参数
    path_match = RE_PATH.search(raw_args)
    if path_match:
        args["path"] = path_match.group(1)

    if "filePath" not in args:
        file_path_match = RE_FILE_PATH.search(raw_args)
        if file_path_match:
            args["filePath"] = file_path_match.group(1)

    command_match = RE_COMMAND.search(raw_args)
    if command_match:
        args["command"] = command_match.group(1)

    for param_name, pattern in RE_ARG_PATTERN.items():
        matches = pattern.finditer(raw_args)
        for match in matches:
            args[param_name] = match.group(1)

    # 检测 content 字段
    is_write_format = '"path"' in raw_args and '"content"' in raw_args
    is_content_only = raw_args.strip().startswith('"content"') or '"content"' in raw_args

    if is_write_format or is_content_only:
        content_key_match = RE_CONTENT_KEY.search(raw_args)
        if content_key_match:
            content_start = content_key_match.end()
            last_brace = raw_args.rfind('}')
            last_bracket = raw_args.rfind(']')
            json_end = max(last_brace, last_bracket) if last_bracket > 0 else last_brace

            if json_end > content_start:
                content_value = raw_args[content_start:json_end]
                content_value = content_value.rstrip('"').rstrip()

                if content_value:
                    try:
                        test_json = copy.deepcopy(args)
                        test_json["content"] = content_value
                        json.dumps(test_json)
                        args["content"] = content_value
                        return args, "fixed_content"
                    except Exception:
                        pass

                if content_value.endswith(',') or content_value.endswith(';'):
                    extended = content_value.rstrip(',;').rstrip()
                    if extended:
                        args["content"] = extended
                        return args, "fixed_truncated"

                args["content"] = content_value
                return args, "fixed_content_only"

    # 特定工具的修复策略
    if tool_name == "bash":
        if "command" in args:
            return {"command": args["command"]}, "fixed_bash"
    elif args:
        return args, "fixed_partial"

    return None, "fix_failed"


def smart_parse_arguments(raw_args: str, tool_name: str) -> Optional[Dict]:
    """
    智能解析 arguments，优先尝试标准 JSON 解析，失败后尝试修复。

    Args:
        raw_args: 原始参数字符串
        tool_name: 工具名称

    Returns:
        解析后的参数字典，解析失败返回 None（空字符串返回空字典）
    """
    if not raw_args:
        return {}

    try:
        return json.loads(raw_args)
    except json.JSONDecodeError:
        pass

    fixed_args, status = try_fix_malformed_json_arguments(raw_args, tool_name)
    if fixed_args:
        return fixed_args

    return None