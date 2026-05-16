# -*- coding: utf-8 -*-
"""
历史消息压缩器 - HistoryCompactor

独立工具类，负责对话历史的上下文压缩：
1. 尾保留策略 + 工具调用配对保护
2. LLM 摘要 + 启发式截断回退
3. 缓存复用机制
4. 可在任何时机调用（对话开始前、工具迭代中）

使用方式：
    compactor = HistoryCompactor(get_model_config, agent_manager)
    
    # 判断是否需要压缩
    if compactor.should_compact(messages, budget):
        compressed, state, cache = compactor.compact(messages, budget)
        
    # 获取当前使用情况
    usage = compactor.get_usage(messages, budget)
"""
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable

import orjson as json
from loguru import logger
from openai import OpenAI

from app.core.message_content import (
    consolidate_messages,
    content_to_text,
)
from app.core.retry_helper import create_api_call_with_retry
from app.core.token_estimator import count_messages_tokens, estimate_tokens
from app.core.provider_profile import get_provider_profile

# ========== 常量 ==========
MAX_HISTORY_SNIPPET_CHARS = 1200
RECENT_HISTORY_MIN_MESSAGES = 6
SOFT_LIMIT_RATIO = 0.7  # 触发压缩检查
TARGET_LIMIT_RATIO = 0.6  # 压缩目标（tail保留60% budget，留更多实际消息）
MIN_RECENT_TOKEN_RATIO = 0.5  # 最小保留比例（tail最少30% budget）
SUMMARY_OVERHEAD = 500  # 摘要基础开销

# ========== 安全保护常量 ==========
# 单条消息最大比例：超过此比例的消息内容会被截断
MAX_SINGLE_MESSAGE_RATIO = 0.15
# 紧急压缩目标：压缩结果必须控制在 budget * EMERGENCY_TARGET_RATIO 以内
EMERGENCY_TARGET_RATIO = 0.7
# 启发式摘要字符硬上限（无论budget是否有效，都应用此上限）
# 当压缩消息数较多时动态扩大
# 每条被压缩消息分配更多字符，保证摘要可读性
MAX_HEURISTIC_SUMMARY_CHARS = 5000
MAX_HEURISTIC_SUMMARY_CHARS_PER_MSG = 40  # 每条压缩消息额外允许的摘要字符
MAX_HEURISTIC_SUMMARY_CHARS_ABS = 25000  # 摘要绝对硬上限
# 工具结果内容最大保留字符数
MAX_TOOL_CONTENT_CHARS = 3000
# 工具配对保护导致tail跑飞时的硬限制倍数
MAX_TAIL_OVERFLOW_MULTIPLIER = 2.5

# ========== 工具保护配置 ==========
# 不应被压缩的工具列表（这些工具的内容需要完整保留）
PROTECTED_TOOLS = {"skill"}  # 可以添加更多工具


class HistoryCompactor:
    """
    历史消息压缩器
    
    职责：
    1. 判断是否需要压缩
    2. 执行压缩（尾保留 + 摘要）
    3. 提供使用情况统计
    
    特点：
    - 独立于 ChatEngine，可在任意时机调用
    - 统一处理普通消息和工具调用（不拆分 tool 配对）
    - 支持缓存复用，避免重复压缩
    """

    def __init__(
        self,
        get_model_config: Callable[[], Dict[str, Any]],
        agent_manager: Any = None,
    ):
        self._get_model_config = get_model_config
        self._agent_manager = agent_manager
        
        # HTTP 客户端缓存（性能优化）
        self._compaction_http_client: Optional[OpenAI] = None
        self._compaction_cache_config: Optional[str] = None

    # ========== 公共接口 ==========

    def should_compact(self, messages: List[Dict], budget: int) -> bool:
        """
        判断是否需要压缩
        
        Args:
            messages: 消息列表
            budget: 可用 token 预算
            
        Returns:
            bool: 是否需要压缩
        """
        if not messages or budget <= 0:
            return False
        
        soft_limit = self._get_soft_limit(budget)
        return count_messages_tokens(messages) > soft_limit

    def compact(
        self,
        messages: List[Dict[str, Any]],
        budget: int,
        existing_cache: Optional[Dict[str, Any]] = None,
        allow_llm_summary: bool = True,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
        """
        执行压缩
        
        Args:
            messages: 原始消息列表
            budget: 可用 token 预算
            existing_cache: 已有的压缩缓存（用于复用）
            allow_llm_summary: 是否允许 LLM 摘要（False 则只用启发式截断）
            
        Returns:
            tuple:
                - 压缩后的消息列表
                - 压缩状态 (compaction_state)
                - 压缩缓存 (compaction_cache)
        """
        if not messages or budget <= 0:
            return [], self._make_state(), self._make_cache()

        soft_limit = self._get_soft_limit(budget)
        
        # 消息规范化
        normalized = consolidate_messages(messages)
        if not normalized:
            return [], self._make_state(), self._make_cache()

        # 未超软限制，无需压缩
        if count_messages_tokens(normalized) <= soft_limit:
            return (
                normalized,
                self._make_state(original_count=len(normalized), kept_count=len(normalized)),
                self._make_cache(),
            )

        # 尝试复用缓存
        cached = existing_cache or {}
        if cached.get("active") and cached.get("summary_message"):
            result = self._try_use_cache(normalized, cached, soft_limit)
            if result:
                return result

        # 执行压缩：尾保留 + 摘要
        return self._do_compact(normalized, budget, allow_llm_summary)

    def get_usage(
        self,
        messages: List[Dict],
        budget: int,
    ) -> Dict[str, Any]:
        """
        获取当前使用情况
        
        Args:
            messages: 消息列表
            budget: 可用预算
            
        Returns:
            dict: { used_tokens, budget_tokens, percent, compaction_state }
        """
        used_tokens = count_messages_tokens(messages)
        budget_tokens = max(1, budget)
        percent = max(0, min(100, int((used_tokens / budget_tokens) * 100)))
        
        return {
            "used_tokens": used_tokens,
            "budget_tokens": budget_tokens,
            "percent": percent,
        }

    def get_budget(self, llm_config: Optional[Dict] = None) -> int:
        """
        计算可用历史预算
        
        Args:
            llm_config: 模型配置（不传则用 get_model_config）
            
        Returns:
            int: 可用于历史的 token 预算
        """
        if llm_config is None:
            llm_config = self._get_model_config() or {}
        
        profile = get_provider_profile(llm_config)
        context_limit = int(profile.get("context_limit", 128000))

        # 支持多种配置字段名
        for key in ("context_limit", "context_window", "max_context_tokens", "最大Token"):
            value = llm_config.get(key)
            if value not in (None, ""):
                try:
                    context_limit = int(value)
                    break
                except (ValueError, TypeError):
                    logger.debug(f"Failed to parse context_limit from: {value}")

        max_output_tokens = llm_config.get("最大新Token", 
            llm_config.get("max_tokens",
                llm_config.get("max_output_tokens", 
                    profile.get("max_output_tokens", 4096)
                )
            )
        )
        try:
            max_output_tokens = int(max_output_tokens)
        except (ValueError, TypeError):
            logger.debug(f"Failed to parse max_output_tokens: {max_output_tokens}, using default")
            max_output_tokens = int(profile.get("max_output_tokens", 4096))

        # O1 模型需要更大的输出预留
        model_name = str(llm_config.get("model", "")).lower()
        reserved = min(800, max_output_tokens)
        if "o1" in model_name or "o3" in model_name:
            reserved = min(max_output_tokens, 32000)

        return max(500, context_limit - reserved)

    # ========== 内部方法 ==========

    def _get_soft_limit(self, budget: int) -> int:
        """软限制 = 70% 预算"""
        return max(1, int(budget * SOFT_LIMIT_RATIO))

    def _get_target_limit(self, budget: int) -> int:
        """目标限制 = 50% 预算"""
        return max(1, int(budget * TARGET_LIMIT_RATIO))

    def _make_state(
        self,
        active: bool = False,
        source: str = "history",
        kind: str = "",
        original_count: int = 0,
        summarized_count: int = 0,
        kept_count: int = 0,
        summary_count: int = 0,
        note: str = "",
    ) -> Dict[str, Any]:
        """构建压缩状态"""
        return {
            "active": bool(active),
            "source": source,
            "kind": "structured",
            "original_count": int(original_count or 0),
            "summarized_count": int(summarized_count or 0),
            "kept_count": int(kept_count or 0),
            "summary_count": int(summary_count or 0),
            "note": note or "",
        }

    def _make_cache(
        self,
        active: bool = False,
        kind: str = "",
        cutoff_index: int = 0,
        source_message_count: int = 0,
        summarized_count: int = 0,
        tail_count: int = 0,
        budget_tokens: int = 0,
        summary_message: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """构建压缩缓存"""
        return {
            "active": bool(active),
            "kind": kind or "",
            "cutoff_index": int(cutoff_index or 0),
            "source_message_count": int(source_message_count or 0),
            "summarized_count": int(summarized_count or 0),
            "tail_count": int(tail_count or 0),
            "budget_tokens": int(budget_tokens or 0),
            "summary_message": dict(summary_message) if isinstance(summary_message, dict) else None,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if active else "",
        }

    def _try_use_cache(
        self,
        normalized: List[Dict],
        cached: Dict,
        soft_limit: int,
    ) -> Optional[tuple]:
        """尝试复用缓存"""
        cutoff_index = int(cached.get("cutoff_index", 0) or 0)
        if 0 < cutoff_index <= len(normalized):
            cached_messages = [
                cached.get("summary_message"),
                *normalized[cutoff_index:],
            ]
            if count_messages_tokens(cached_messages) <= soft_limit:
                summarized_count = int(cached.get("summarized_count", cutoff_index) or cutoff_index)
                tail_count = len(normalized) - cutoff_index
                return (
                    cached_messages,
                    self._make_state(
                        active=True,
                        source="history",
                        kind=str(cached.get("kind", "plain") or "plain"),
                        original_count=len(normalized),
                        summarized_count=summarized_count,
                        kept_count=tail_count,
                        summary_count=1,
                        note=f"复用已压缩摘要，覆盖 {summarized_count} 条较早消息",
                    ),
                    self._make_cache(
                        active=True,
                        kind=str(cached.get("kind", "plain") or "plain"),
                        cutoff_index=cutoff_index,
                        source_message_count=len(normalized),
                        summarized_count=summarized_count,
                        tail_count=tail_count,
                        budget_tokens=cached.get("budget_tokens", 0),
                        summary_message=cached.get("summary_message"),
                    ),
                )
        return None

    def _do_compact(
        self,
        normalized: List[Dict],
        budget: int,
        allow_llm_summary: bool,
    ) -> tuple:
        """
        执行压缩的核心逻辑：
        1. 从后向前尾保留（不拆分 tool 配对）
        2. 对被截断的部分生成摘要
        """
        target_limit = self._get_target_limit(budget)
        min_recent_tokens = int(target_limit * MIN_RECENT_TOKEN_RATIO)

        # ========== 尾保留（从后向前） ==========
        recent_messages: List[Dict[str, Any]] = []
        recent_tokens = 0
        pending_tool_results: set = set()  # 等待找到对应 assistant 的 tool_call_id

        i = len(normalized) - 1
        # 单条消息 token 硬上限：超过此值的内容会被截断
        single_msg_max = max(500, int(budget * MAX_SINGLE_MESSAGE_RATIO))
        while i >= 0:
            msg = normalized[i]
            msg_tokens = count_messages_tokens([msg])
            role = msg.get("role")
            
            # 工具调用配对保护
            if role == "assistant":
                tool_calls = msg.get("tool_calls", [])
                for tc in tool_calls:
                    tool_id = tc.get("id")
                    if tool_id in pending_tool_results:
                        pending_tool_results.discard(tool_id)
            elif role == "tool":
                pending_tool_results.add(msg.get("tool_call_id"))

            # ========== 单条消息截断保护 ==========
            # 避免一条超大 tool 结果撑爆整个 budget
            if msg_tokens > single_msg_max and role != "system":
                # 创建副本，不修改原始消息
                msg = dict(msg)
                content = msg.get("content", "")
                if isinstance(content, str) and len(content) > MAX_TOOL_CONTENT_CHARS:
                    # 工具结果：保留首尾
                    head_len = MAX_TOOL_CONTENT_CHARS // 2
                    tail_len = MAX_TOOL_CONTENT_CHARS // 2
                    # 如果是 tool 角色，限制更严格
                    max_chars = MAX_TOOL_CONTENT_CHARS if role == "tool" else MAX_HISTORY_SNIPPET_CHARS * 3
                    if len(content) > max_chars:
                        msg["content"] = content[:head_len] + "\n\n... [内容已截断，省略 " + str(len(content) - head_len - tail_len) + " 字符] ...\n\n" + content[-tail_len:]
                        msg["_truncated"] = True
                elif isinstance(content, list):
                    # 多段 content（如文本+图片url），截断超大文本段
                    truncated_blocks = []
                    for block in content if isinstance(content, list) else [content]:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = block.get("text", "")
                            if len(text) > MAX_TOOL_CONTENT_CHARS:
                                block = dict(block)
                                block["text"] = text[:MAX_TOOL_CONTENT_CHARS // 2] + "\n\n... [内容截断] ...\n\n" + text[-MAX_TOOL_CONTENT_CHARS // 2:]
                                msg["_truncated"] = True
                        truncated_blocks.append(block)
                    msg["content"] = truncated_blocks
                # 重新计算 token
                msg_tokens = count_messages_tokens([msg])

            # 添加到 recent（从后向前插入）
            recent_messages.insert(0, msg)
            recent_tokens += msg_tokens

            # 停止条件
            if (
                recent_messages
                and recent_tokens > target_limit
                and not pending_tool_results
                and len(recent_messages) >= RECENT_HISTORY_MIN_MESSAGES
                and recent_tokens >= min_recent_tokens
            ):
                break

            # ========== tail 跑飞保护 ==========
            # 工具配对保护可能导致 tail 远超 target_limit。
            # 设置硬上限，超过时即使有 pending 配对也强制截断。
            hard_tail_cap = int(target_limit * MAX_TAIL_OVERFLOW_MULTIPLIER)
            if recent_tokens > hard_tail_cap and len(recent_messages) >= RECENT_HISTORY_MIN_MESSAGES * 2:
                logger.warning(
                    f"[Compactor] tail 达到硬上限: {recent_tokens} > {hard_tail_cap}，"
                    f"强制截断 (pending_tool_results={len(pending_tool_results)})"
                )
                break

            i -= 1

        # 没有需要压缩的内容
        if len(recent_messages) == len(normalized):
            return (
                recent_messages,
                self._make_state(original_count=len(normalized), kept_count=len(recent_messages)),
                self._make_cache(),
            )

        # 被截断的部分
        compacted = normalized[: len(normalized) - len(recent_messages)]

        # ========== 生成摘要 ==========
        # 即使 summary_budget 为负，也传一个最小正预算给 _summarize
        # 确保启发式摘要始终有字符硬上限控制（避免 budget=None 跳过截断）
        summary_budget = budget - recent_tokens - SUMMARY_OVERHEAD
        summary_budget_for_heuristic = max(1, summary_budget) if summary_budget > 0 else 500
        compact_summary = self._summarize(
            compacted, 
            allow_llm=allow_llm_summary,
            budget=summary_budget_for_heuristic,
            compacted_count=len(compacted),
        )
        
        if not compact_summary:
            # 摘要失败，只保留 tail
            return (
                recent_messages,
                self._make_state(original_count=len(normalized), kept_count=len(recent_messages)),
                self._make_cache(),
            )

        summary_message = {"role": "user", "content": compact_summary}
        # 跳过开头的 tool 角色（配对保护遗留的孤立 tool 结果）
        first_non_tool = 0
        for idx, msg in enumerate(recent_messages):
            if msg["role"] != "tool":
                first_non_tool = idx
                break
        if first_non_tool > 0:
            recent_messages = recent_messages[first_non_tool:]
        result_messages = [summary_message] + recent_messages
        current_tokens = count_messages_tokens(result_messages)
        kept_count = len(recent_messages)

        # ========== 压缩后预算校验 ==========
        # 如果压缩结果仍然超过 budget，执行紧急缩减
        if current_tokens > budget:
            logger.warning(
                f"[Compactor] 压缩结果仍超 budget: {current_tokens} > {budget}，"
                f"执行紧急缩减 (tail={kept_count}, summary={len(compacted)})"
            )
            result_messages, kept_count, summary_note = self._ensure_budget(
                result_messages, recent_messages, summary_message, budget,
                normalized_len=len(normalized), compacted_len=len(compacted)
            )
            # 重新计数
            current_tokens = count_messages_tokens(result_messages)
        else:
            summary_note = f"已压缩 {len(compacted)} 条较早消息"

        return (
            result_messages,
            self._make_state(
                active=True,
                source="history",
                kind="structured",
                original_count=len(normalized),
                summarized_count=len(compacted),
                kept_count=kept_count,
                summary_count=current_tokens - count_messages_tokens(recent_messages),
                note=summary_note,
            ),
            self._make_cache(
                active=True,
                kind="structured",
                cutoff_index=len(compacted),
                source_message_count=len(normalized),
                summarized_count=len(compacted),
                tail_count=kept_count,
                budget_tokens=budget,
                summary_message=summary_message,
            ),
        )

    def _ensure_budget(
        self,
        result_messages: List[Dict],
        recent_messages: List[Dict],
        summary_message: Dict,
        budget: int,
        normalized_len: int,
        compacted_len: int,
    ) -> tuple:
        """
        紧急预算保障：当压缩结果仍超过 budget 时，
        迭代减少直到 fit。

        Returns:
            (result_messages, kept_count, note)
        """
        emergency_target = int(budget * EMERGENCY_TARGET_RATIO)
        kept_count = len(recent_messages)
        note = f"紧急缩减：原始 {normalized_len} 条"
        
        # 摘要保留底线：至少 2000 字符（约 500 tokens），
        # 保证压缩结果对早期对话仍有可用信息
        MIN_SUMMARY_CHARS = 2000

        result_tokens = count_messages_tokens(result_messages)
        
        # 策略1：截断超大摘要内容（保留底线）
        if result_tokens > emergency_target:
            summary_content = summary_message.get("content", "")
            if isinstance(summary_content, str) and len(summary_content) > MIN_SUMMARY_CHARS:
                # 仅当摘要远超底线时才截断
                target_chars = max(MIN_SUMMARY_CHARS, min(len(summary_content), MAX_HEURISTIC_SUMMARY_CHARS))
                if len(summary_content) > target_chars:
                    summary_message = dict(summary_message)
                    summary_message["content"] = (
                        summary_content[:target_chars // 2]
                        + "\n\n[摘要因预算限制截断]\n\n"
                        + summary_content[-target_chars // 2:]
                    )
                    result_messages = [summary_message] + recent_messages
                    result_tokens = count_messages_tokens(result_messages)
                    note = "紧急缩减：截断摘要"

        # 策略2：从 tail 中移除最旧的消息
        while result_tokens > emergency_target and len(result_messages) > 2:
            removed = result_messages.pop(1)  # index 0 是 summary
            if removed in recent_messages:
                recent_messages.remove(removed)
                kept_count -= 1
            result_tokens = count_messages_tokens(result_messages)

        # 策略3：截断剩余 tail 中的工具消息内容
        if result_tokens > emergency_target:
            for idx, msg in enumerate(result_messages):
                if idx == 0:
                    continue
                if result_tokens <= emergency_target:
                    break
                if msg.get("role") == "tool":
                    content = msg.get("content", "")
                    tool_name = msg.get("name", "")
                    if isinstance(content, str) and len(content) > MAX_TOOL_CONTENT_CHARS:
                        new_msg = dict(msg)
                        new_msg["content"] = content[:MAX_TOOL_CONTENT_CHARS // 2] + "\n\n...[工具结果截断]...\n\n" + content[-MAX_TOOL_CONTENT_CHARS // 2:]
                        result_messages[idx] = new_msg
                        result_tokens = count_messages_tokens(result_messages)
                        note = f"紧急缩减：截断工具 {tool_name} 的内容"

        kept_count = len([m for m in recent_messages if m in result_messages])
        return result_messages, kept_count, note + f"，保留 {kept_count}/{compacted_len} 条"

    def _calculate_dynamic_summary_chars(self, compacted_count: int) -> int:
        """根据压缩消息数动态计算摘要字符上限"""
        return min(
            MAX_HEURISTIC_SUMMARY_CHARS_ABS,
            MAX_HEURISTIC_SUMMARY_CHARS + compacted_count * MAX_HEURISTIC_SUMMARY_CHARS_PER_MSG
        )

    def _summarize(
        self,
        messages: List[Dict],
        allow_llm: bool = True,
        budget: Optional[int] = None,
        compacted_count: int = 0,
    ) -> str:
        """
        生成摘要：优先 LLM，回退启发式
        """
        if not messages:
            return ""
        
        # 优先 LLM 摘要
        if allow_llm:
            llm_summary = self._summarize_with_llm(messages)
            if llm_summary:
                return llm_summary
        
        # 启发式截断（遗忘曲线）
        heuristic = self._summarize_heuristic(messages, budget)
        
        # 启发式摘要长度硬上限（无论 budget 是否有效，始终应用）
        # 动态上限：base + 压缩消息数 * 每条额外字符
        max_chars = MAX_HEURISTIC_SUMMARY_CHARS
        if compacted_count > 0:
            max_chars = min(
                MAX_HEURISTIC_SUMMARY_CHARS_ABS,
                MAX_HEURISTIC_SUMMARY_CHARS + compacted_count * MAX_HEURISTIC_SUMMARY_CHARS_PER_MSG
            )
        if len(heuristic) > max_chars:
            logger.warning(
                f"[Compactor] 启发式摘要超长: {len(heuristic)} > {max_chars} "
                f"(compacted={compacted_count})，强制截断"
            )
            head = heuristic[:max_chars // 2]
            tail = heuristic[-max_chars // 2:]
            heuristic = head + "\n\n[摘要因长度限制截断]\n\n" + tail
        
        return heuristic

    def _summarize_with_llm(self, messages: List[Dict]) -> str:
        """使用 LLM 生成摘要"""
        llm_config = self._get_model_config() or {}
        api_key = str(llm_config.get("API_KEY", "")).strip()
        base_url = llm_config.get("API_URL") or None
        auth_type = llm_config.get("认证方式", "bearer")
        
        if not api_key and auth_type != "none":
            return ""

        # 获取 compaction agent 配置
        compaction_config = {}
        if self._agent_manager and self._agent_manager.get_agent("compaction"):
            compaction_config = self._agent_manager.get_agent_config("compaction")

        model = str(compaction_config.get("model") or llm_config.get("模型名称", "gpt-4o"))
        
        # 动态 max_tokens
        max_tokens = self._get_summary_max_tokens(model)
        
        client = self._get_http_client(api_key, base_url, auth_type)

        req_kwargs = {
            "model": model,
            "messages": self._build_compaction_messages(messages),
            "stream": False,
            "max_tokens": max_tokens,
        }
        
        temperature = compaction_config.get("temperature")
        if temperature is not None:
            req_kwargs["temperature"] = temperature
        top_p = compaction_config.get("top_p")
        if top_p is not None:
            req_kwargs["top_p"] = top_p

        try:
            def create_task():
                return client.chat.completions.create(**req_kwargs)

            resp = create_api_call_with_retry(client, create_task)
            content = (resp.choices[0].message.content or "").strip()
            return content
        except Exception as exc:
            logger.warning(f"[Compactor] LLM summarization failed, fallback to heuristic: {exc}")
            return ""

    def _get_summary_max_tokens(self, model: str) -> int:
        """根据模型大小动态调整摘要长度"""
        model_lower = model.lower()
        if any(s in model_lower for s in ["mini", "small", "flash", "lite"]):
            return 600
        elif any(s in model_lower for s in ["32k", "128k"]):
            return 2000
        return 1200

    def _get_http_client(self, api_key: str, base_url: str, auth_type: str) -> OpenAI:
        """获取或创建 HTTP 客户端（复用）"""
        config_key = f"{auth_type}:{api_key[:8] if api_key else 'none'}:{base_url or 'default'}"
        
        if (self._compaction_http_client is not None and 
            self._compaction_cache_config == config_key):
            return self._compaction_http_client
        
        self._compaction_http_client = OpenAI(
            api_key=api_key if api_key and auth_type != "none" else "dummy",
            base_url=base_url,
            timeout=60.0,
        )
        self._compaction_cache_config = config_key
        return self._compaction_http_client

    def _build_compaction_messages(self, messages: List[Dict]) -> List[Dict]:
        """构建压缩用的 prompt"""
        transcript_lines = []
        for msg in messages or []:
            role = msg.get("role", "unknown")
            content = content_to_text(msg.get("content", "")).strip()
            if not content:
                continue
            single_line = " ".join(content.split())
            if role == "tool":
                tool_name = msg.get("name") or msg.get("tool_call_id") or "tool"
                transcript_lines.append(f"[tool:{tool_name}] {single_line[:1200]}")
            else:
                transcript_lines.append(f"[{role}] {single_line[:1200]}")

        prompt = (
            "请压缩下面的较早对话，使后续模型可以继续当前编码任务。\n\n"
            "输出要求：\n"
            "1. 使用 Markdown。\n"
            "2. 优先保留：任务目标、已完成工作、关键文件/模块、关键工具结果、当前剩余问题。\n"
            "3. 不要只重复用户原始提问。\n"
            "4. 删除寒暄、重复探索、低价值调试细节。\n"
            "5. 如果信息不足，不要编造。\n\n"
            f"【待压缩对话】\n" + "\n".join(transcript_lines)
        )

        system_prompt = ""
        if self._agent_manager and self._agent_manager.get_agent("compaction"):
            system_prompt = self._agent_manager.get_agent_system_prompt("compaction")
        if not system_prompt:
            system_prompt = "你是一个上下文压缩专家，负责提炼后续继续执行编码任务所需的摘要。"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

    def _summarize_heuristic(
        self,
        messages: List[Dict],
        budget: Optional[int] = None,
    ) -> str:
        """
        启发式摘要：遗忘曲线自适应截断
        
        越旧的消息，保留越少
        """
        if "content" in messages[0] and messages[0]["content"].startswith("## Earlier Conversation Summary"):
            summary_lines = [messages[0]["content"]]
        else:
            summary_lines = [
                "## Earlier Conversation Summary",
                "以下是为节省上下文窗口而压缩的较早对话，请把它当作已确认的历史上下文继续工作。",
            ]
        total_messages = len(messages)
        if total_messages == 0:
            return ""

        # 计算每条消息的内容长度比例
        contents = []
        for msg in messages:
            content = content_to_text(msg.get("content", "")).strip()
            single_line = " ".join(content.split())
            contents.append(single_line)

        total_content_length = sum(len(c) for c in contents)
        content_ratios = [
            len(c) / total_content_length if total_content_length > 0 else 1 / total_messages
            for c in contents
        ]

        # 目标总长度
        target_total_length: Optional[int] = None
        if budget is not None and budget > 0:
            target_total_length = int(budget * 0.6)

        # ========== 预处理: 内容清理（在所有消息上统一执行）==========
        cleaned_contents = []
        for idx, msg in enumerate(messages):
            raw_content = contents[idx] if idx < len(contents) else ""
            # 移除 <hook> 标签
            raw_content = re.sub(r'<hook[^>]*>.*?</hook>', '', raw_content, flags=re.DOTALL)
            # 移除 <think> 标签
            raw_content = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL)
            # 移除 Tool args 内容
            raw_content = re.sub(r'Tool args:\s*\{[^}]*\}', '', raw_content)
            cleaned_contents.append(raw_content)

        for idx, msg in enumerate(messages):
            role = msg.get("role")
            content = cleaned_contents[idx] if idx < len(cleaned_contents) else ""
            
            # ========== 内容过滤 ==========
            # 1. 跳过失败的工具执行
            if role == "tool" and not msg.get("success"):
                continue
            # 2. 跳过纯工具调用的 assistant 消息（无有用文本，只有 tool_calls）
            if role == "assistant":
                tool_calls = msg.get("tool_calls")
                if tool_calls and (not content or len(content) < 20):
                    continue
            # 3. 跳过 tool 消息中的无价值结果
            if role == "tool":
                empty_results = [
                    "(command completed with no output)",
                    "(completed with no output)",
                    "No results found",
                ]
                stripped = content.strip()
                if any(er in stripped for er in empty_results) and len(stripped) < 100:
                    continue
            
            # 对于受保护的工具（如 skill），保留完整内容不截断
            is_protected_tool = False
            if role == "tool":
                tool_name = msg.get("name", "")
                if tool_name in PROTECTED_TOOLS:
                    is_protected_tool = True

            # 自适应截断：越旧截断越多（受保护工具除外）
            if not is_protected_tool:
                content = self._adaptive_truncate(
                    content,
                    position=idx,
                    total=total_messages,
                    target_total=target_total_length,
                    ratios=content_ratios if total_content_length > 1000 else None,
                )

            if role == "user":
                summary_lines.append(f"# User\n{content}")
            elif role == "assistant":
                summary_lines.append(f"# Assistant\n{content}")
            elif role == "tool":
                tool_name = msg.get("name", "")
                arguments = msg.get("arguments", "")
                arguments = self._adaptive_truncate(
                    arguments,
                    position=idx,
                    total=total_messages,
                    target_total=int(budget *  content_ratios[idx]),
                    ratios=content_ratios if total_content_length > 1000 else None,
                )
                # 标记受保护的工具
                prefix = "[🔒] " if tool_name in PROTECTED_TOOLS else ""
                summary_lines.append(f"{prefix}# {tool_name}\nTool Res: {content}")

        return "\n".join(summary_lines)

    def _adaptive_truncate(
        self,
        content: str,
        position: int,
        total: int,
        target_total: Optional[int] = None,
        ratios: Optional[List[float]] = None,
    ) -> str:
        """
        自适应截断：基于遗忘曲线
        
        公式：keep_ratio = 0.2 + 0.5 * (position / total) ** 0.5
        - 最早的消息：约 20%
        - 最新的消息：约 70%
        """
        content_len = len(content)
        
        # 基础保留比例（遗忘曲线）
        position_ratio = position / max(1, total - 1)
        min_keep = 0.2
        max_keep = 0.7
        keep_ratio = min_keep + (max_keep - min_keep) * (position_ratio ** 0.5)
        
        # 动态目标长度
        if target_total is not None and target_total > 0:
            msg_ratio = ratios[position] if ratios and position < len(ratios) else (1 / total)
            avg_ratio = 1.0 / total
            ratio_factor = 0.5 + 0.5 * (msg_ratio / max(avg_ratio, 0.001))
            target_quota = (target_total / max(1, total)) * ratio_factor
            keep_length = int(target_quota)
        else:
            keep_length = int(content_len * keep_ratio)
        
        # 限制
        keep_length = min(keep_length, MAX_HISTORY_SNIPPET_CHARS)
        keep_length = max(keep_length, 20)
        
        if keep_length >= content_len:
            return content
        
        # 首尾保留策略
        head_ratio = 0.4
        head_length = int(keep_length * head_ratio)
        tail_length = int(keep_length * head_ratio)
        
        head = content[:head_length]
        tail = content[-tail_length:] if tail_length > 0 else ""
        
        return f"{head}...{tail}"
