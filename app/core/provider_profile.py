# -*- coding: utf-8 -*-
"""
Provider profile helpers.

These helpers intentionally derive capabilities from the application's
live provider config (`API_URL`, `模型名称`, `认证方式`) so the chatter layer
stays aligned with software-level provider settings.
"""

from typing import Any, Dict


# 合理的输出 token 上限（基于各模型已知的 API 限制）
# 这些值作为用户未指定 max_tokens 时的默认值，
# 不再作为硬性截断上限（具体截断逻辑在 chat_worker 中处理）
PROVIDER_CAPABILITIES = {
    "anthropic": {
        "context_limit": 200000,
        "max_output_tokens": 8192,
        "absolute_limit": 65536,
        "supports_vision": True,
        "supports_thinking": False,
        "thinking_param": None,
    },
    "openai": {
        "context_limit": 128000,
        "max_output_tokens": 16384,
        "absolute_limit": 65536,
        "supports_vision": True,
        "supports_thinking": False,
        "thinking_param": None,
    },
    "gemini": {
        "context_limit": 1000000,
        "max_output_tokens": 8192,
        "absolute_limit": 65536,
        "supports_vision": True,
        "supports_thinking": False,
        "thinking_param": None,
    },
    "dashscope": {
        "context_limit": 1000000,
        "max_output_tokens": 8192,
        "absolute_limit": 65536,
        "supports_vision": True,
        "supports_thinking": False,
        "thinking_param": None,
    },
    "zhipu": {
        "context_limit": 128000,
        "max_output_tokens": 8192,
        "absolute_limit": 65536,
        "supports_vision": True,
        "supports_thinking": True,
        "thinking_param": "thinking",         # extra_body.thinking = {type}
        "reasoning_effort_param": None,
    },
    "deepseek": {
        "context_limit": 320000,
        "max_output_tokens": 8192,
        "absolute_limit": 65536,
        "supports_vision": False,
        "supports_thinking": True,
        "thinking_param": "thinking",         # extra_body.thinking = {type}
        "reasoning_effort_param": "reasoning_effort",
    },
    "groq": {
        "context_limit": 128000,
        "max_output_tokens": 8192,
        "absolute_limit": 65536,
        "supports_vision": False,
        "supports_thinking": False,
        "thinking_param": None,
    },
    "minimax": {
        "context_limit": 1000000,
        "max_output_tokens": 8192,
        "absolute_limit": 65536,
        "supports_vision": False,
        "supports_thinking": False,
        "thinking_param": None,
    },
    "siliconflow": {
        "context_limit": 131072,
        "max_output_tokens": 16384,
        "absolute_limit": 65536,
        "supports_vision": False,
        "supports_thinking": True,
        "thinking_param": "thinking_budget",  # 硅基流动用 thinking_budget 控制推理长度
        "reasoning_effort_param": None,
    },
    "baidu_qianfan": {
        "context_limit": 128000,
        "max_output_tokens": 8192,
        "absolute_limit": 65536,
        "supports_vision": False,
        "supports_thinking": False,
        "thinking_param": None,
    },
    "ollama": {
        "context_limit": 128000,
        "max_output_tokens": 8192,
        "absolute_limit": 65536,
        "supports_vision": True,
        "supports_thinking": False,
        "thinking_param": None,
    },
    "volcengine": {
        "context_limit": 1000000,
        "max_output_tokens": 8192,
        "absolute_limit": 65536,
        "supports_vision": False,
        "supports_thinking": False,
        "thinking_param": None,
    },
    "lmstudio": {
        "context_limit": 128000,
        "max_output_tokens": 8192,
        "absolute_limit": 65536,
        "supports_vision": True,
        "supports_thinking": False,
        "thinking_param": None,
    },
    "custom": {
        "context_limit": 128000,
        "max_output_tokens": 8192,
        "absolute_limit": 65536,
        "supports_vision": False,
        "supports_thinking": False,
        "thinking_param": None,
    },
}


def detect_provider_family(llm_config: Dict[str, Any]) -> str:
    api_url = str(llm_config.get("API_URL", "") or "").lower()
    model = str(llm_config.get("模型名称", "") or "").lower()
    auth = str(llm_config.get("认证方式", "") or "").lower()

    if "anthropic" in api_url or model.startswith("claude"):
        return "anthropic"
    if "generativelanguage.googleapis.com" in api_url or model.startswith("gemini"):
        return "gemini"
    if "dashscope.aliyuncs.com" in api_url or model.startswith("qwen"):
        return "dashscope"
    if "bigmodel.cn" in api_url or model.startswith("glm"):
        return "zhipu"
    if "deepseek.com" in api_url or model.startswith("deepseek"):
        return "deepseek"
    if "api.groq.com" in api_url or "groq/" in model:
        return "groq"
    if "siliconflow.cn" in api_url:
        return "siliconflow"
    if "minimax" in api_url or model.startswith("minimax"):
        return "minimax"
    if "volces.com" in api_url or "ark.cn-beijing" in api_url or model.startswith("doubao"):
        return "volcengine"
    if "qianfan.baidubce.com" in api_url or auth == "bce":
        return "baidu_qianfan"
    if "localhost:11434" in api_url or auth == "none":
        return "ollama"
    if "localhost:1234" in api_url:
        return "lmstudio"
    if "api.openai.com" in api_url or model.startswith(("gpt-", "o1", "o3")):
        return "openai"
    return "custom"


def get_provider_profile(llm_config: Dict[str, Any]) -> Dict[str, Any]:
    family = detect_provider_family(llm_config)
    profile = dict(PROVIDER_CAPABILITIES.get(family, PROVIDER_CAPABILITIES["custom"]))
    profile["family"] = family
    profile["auth_type"] = str(llm_config.get("认证方式", "bearer") or "bearer").lower()
    return profile


def supports_vision(llm_config: Dict[str, Any]) -> bool:
    model = str(llm_config.get("模型名称", "") or "").lower()
    # 只有模型名称里包含视觉相关关键词时才返回 True，不要根据整个服务商判断
    vision_markers = ("vision", "vl", "llava", "glm-4v", "gpt-4o", "gpt-4o-mini", "claude-3")
    if any(marker in model for marker in vision_markers):
        return True
    return False
