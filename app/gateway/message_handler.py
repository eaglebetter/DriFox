# -*- coding: utf-8 -*-
"""
Gateway 消息处理器

处理来自企业微信/钉钉的消息。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, Optional

from loguru import logger

from app.gateway.base import (
    BasePlatformAdapter,
    MessageEvent,
    Platform,
    SendResult,
)
from app.gateway.session_manager import GatewaySession, GatewaySessionManager

logger = logging.getLogger(__name__)


class MessageHandler:
    """
    Gateway 消息处理器
    
    负责：
    1. 接收平台消息
    2. 获取/创建会话
    3. 调用 AI 处理
    4. 发送响应
    """
    
    def __init__(
        self,
        session_manager: GatewaySessionManager,
        process_message_callback: Callable,
        send_message_callback: Callable[[Platform, str, str, Any], SendResult],
    ):
        """
        初始化消息处理器
        
        Args:
            session_manager: 会话管理器
            process_message_callback: 处理消息的回调，签名为：
                async def process(session_id: str, text: str, ...) -> str
            send_message_callback: 发送消息的回调，签名为：
                async def send(platform: Platform, chat_id: str, content: str, ...) -> SendResult
        """
        self._session_manager = session_manager
        self._process_message = process_message_callback
        self._send_message = send_message_callback
    
    async def handle(self, event: MessageEvent) -> None:
        """
        处理消息
        
        Args:
            event: 消息事件
        """
        # 处理命令
        if event.is_command:
            await self._handle_command(event)
            return
        
        # 获取或创建会话
        session = self._session_manager.get_or_create_session(event)
        
        # 调用 AI 处理
        try:
            response = await self._process_message(
                session_id=session.session_id,
                text=event.text,
                platform=event.platform,
                chat_id=event.chat_id,
                user_id=event.user_id,
                media_urls=event.media_urls,
            )
            
            if response:
                # 发送响应
                result = await self._send_message(
                    platform=event.platform,
                    chat_id=event.chat_id,
                    content=response,
                )
                
                if not result.success:
                    logger.warning("[MessageHandler] Failed to send response: %s", result.error)
                    
        except asyncio.TimeoutError:
            logger.error("[MessageHandler] AI processing timeout")
            await self._send_message(
                platform=event.platform,
                chat_id=event.chat_id,
                content="抱歉，AI 处理超时了。请稍后重试。",
            )
        except Exception as e:
            logger.error("[MessageHandler] Processing error: %s", e, exc_info=True)
            await self._send_message(
                platform=event.platform,
                chat_id=event.chat_id,
                content=f"处理消息时出错: {str(e)[:200]}",
            )
    
    async def _handle_command(self, event: MessageEvent) -> None:
        """处理命令"""
        command = event.command_name
        args = event.command_args
        
        if command in ("new", "reset"):
            # 获取会话
            session = self._session_manager.get_session_by_platform_user(
                event.platform, event.user_id
            )
            
            if session:
                # 重置会话
                self._session_manager.reset_session(session.session_id)
                
                await self._send_message(
                    platform=event.platform,
                    chat_id=event.chat_id,
                    content="✅ 会话已重置，开始新的对话！",
                )
            else:
                await self._send_message(
                    platform=event.platform,
                    chat_id=event.chat_id,
                    content="没有找到现有会话，直接开始新的对话吧！",
                )
        
        elif command == "clear":
            session = self._session_manager.get_session_by_platform_user(
                event.platform, event.user_id
            )
            
            if session:
                self._session_manager.reset_session(session.session_id)
                
            await self._send_message(
                platform=event.platform,
                chat_id=event.chat_id,
                content="✅ 聊天记录已清除！",
            )
        
        elif command == "help":
            help_text = """
🤖 **DriFox Gateway 命令**

- `/new` - 开始新会话
- `/reset` - 重置当前会话
- `/clear` - 清除聊天记录
- `/help` - 显示帮助

**注意**: 企业微信/钉钉的会话与桌面端是隔离的。
"""
            await self._send_message(
                platform=event.platform,
                chat_id=event.chat_id,
                content=help_text.strip(),
            )
        
        else:
            # 未知命令，转发给 AI
            await self.handle(MessageEvent(
                text=f"/{command} {args}",
                message_type=event.message_type,
                message_id=event.message_id,
                chat_id=event.chat_id,
                user_id=event.user_id,
                user_name=event.user_name,
                platform=event.platform,
                chat_type=event.chat_type,
            ))