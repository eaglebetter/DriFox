# -*- coding: utf-8 -*-
"""
消息上下文构建器 - 从 ChatEngine 提取

负责构建 LLM 消息上下文和预算计算。
"""

import anyio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable

from loguru import logger

from app.core.message_content import consolidate_messages
from app.core.provider_profile import get_provider_profile
from app.core.token_estimator import count_messages_tokens
from app.utils.config import Settings


class ContextBuilder:
    """负责构建 LLM 消息上下文和预算计算"""

    def __init__(
        self,
        agent_manager,
        compactor=None,
        backend=None
    ):
        """
        Args:
            agent_manager: AgentManager 实例
            memory_context_getter: 获取记忆上下文的回调
            compactor: HistoryCompactor 实例
        """
        self._agent_manager = agent_manager
        self.backend = backend
        self._compactor = compactor

    def build_messages(
        self,
        session,
        llm_config: Dict,
        allow_llm_summary: bool = False,
        current_agent: Optional[str] = None,
    ) -> List[Dict]:
        """
        构建发送给 LLM 的消息列表。
        
        Args:
            session: ChatSession 实例
            llm_config: LLM 配置字典
            allow_llm_summary: 是否允许 LLM 摘要
            current_agent: 当前智能体名称
            
        Returns:
            消息列表
        """
        messages: List[Dict[str, Any]] = []

        # 获取系统提示
        if current_agent:
            full_system_prompt = self._agent_manager.get_agent_system_prompt(
                current_agent, is_subagent_call=False
            )
        else:
            full_system_prompt = self._agent_manager.get_unified_system_prompt()

        prompt_parts = [full_system_prompt]

        # 添加时间
        time_part = f"# 当前系统时间\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # 添加启用的技能内容
        enabled_skills = Settings.get_instance().llm_enabled_skills.value
        if enabled_skills and self._agent_manager:
            skills_content = self._agent_manager.get_enabled_skills_content(enabled_skills)
            if skills_content:
                prompt_parts.append(skills_content)

        # 添加自定义提示
        custom_prompt = llm_config.get("系统提示", "").strip()
        if custom_prompt:
            prompt_parts.append(custom_prompt)

        prompt_parts.append(time_part)

        # 添加记忆上下文
        memory_context = self.backend.get_memory_context_string()
        prompt_parts.append(memory_context)

        # 使用单一 join 操作
        full_system_content = "\n\n".join(prompt_parts)

        messages.append({
            "role": "system",
            "content": full_system_content,
        })

        session.system_prompt = full_system_content

        # 处理历史消息
        normalized_session_messages = consolidate_messages(session.get_context_messages())
        latest_user_message = ""
        latest_user_timestamp = ""
        params = {}
        history_messages = normalized_session_messages

        if history_messages and history_messages[-1].get("role") == "user":
            latest_user_message = history_messages[-1].get("content", "")
            latest_user_timestamp = history_messages[-1].get("timestamp", "")
            params = history_messages[-1].get("params", {})
            history_messages = history_messages[:-1]

        # 上下文压缩
        budget = self._compactor.get_budget(llm_config)
        history_for_api, compaction_state, compaction_cache = anyio.run(
            anyio.to_thread.run_sync,
            lambda: self._compactor.compact(
                history_messages,
                budget,
                existing_cache=getattr(session, "compaction_cache", None),
                allow_llm_summary=allow_llm_summary,
            )
        )
        session.set_compaction_state(compaction_state)
        session.set_compaction_cache(compaction_cache)

        # 过滤 system 消息并添加到结果
        filtered_history = [m for m in history_for_api if m.get("role") != "system"]
        messages.extend(filtered_history)

        # 添加用户消息
        user_msg = {"role": "user", "content": latest_user_message, "params": params}
        if latest_user_timestamp:
            user_msg["timestamp"] = latest_user_timestamp
        messages.append(user_msg)

        return messages

    def get_context_budget(self, llm_config: Dict) -> int:
        """
        计算上下文预算。
        
        Args:
            llm_config: LLM 配置字典
            
        Returns:
            可用的上下文 token 数
        """
        profile = get_provider_profile(llm_config)
        context_limit = int(profile.get("context_limit", 128000))

        # 支持多种上下文长度配置字段名
        for key in (
            "context_limit",
            "context_window",
            "max_context_tokens",
            "max_input_tokens",
            "最大Token",
        ):
            value = llm_config.get(key)
            if value not in (None, ""):
                try:
                    context_limit = int(value)
                    break
                except (ValueError, TypeError):
                    logger.debug(f"Failed to parse context_limit: {value}")
                    continue

        max_output_tokens = llm_config.get(
            "最大新Token",
            llm_config.get(
                "max_tokens",
                llm_config.get("max_output_tokens", profile.get("max_output_tokens", 4096)),
            ),
        )
        try:
            max_output_tokens = int(max_output_tokens)
        except (ValueError, TypeError):
            logger.debug(f"Failed to parse max_output_tokens: {max_output_tokens}")
            max_output_tokens = int(profile.get("max_output_tokens", 4096))

        model_name = str(llm_config.get("model", "")).lower()
        profile_max_output = int(profile.get("max_output_tokens", 4096))

        if max_output_tokens > profile_max_output * 2:
            context_limit = min(context_limit, max_output_tokens)

        reserved = min(800, max_output_tokens)
        if "o1" in model_name or "o3" in model_name:
            reserved = min(max_output_tokens, 32000)

        return max(500, context_limit - reserved)

    def count_tokens(self, messages: List[Dict]) -> int:
        """计算消息列表的 token 数"""
        return count_messages_tokens(messages)