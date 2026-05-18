# -*- coding: utf-8 -*-
"""
MCP 工具模块 - 管理 MCP Server 连接、工具发现与调用

核心类：
- MCPClientManager: 管理所有 MCP Server 连接，提供工具 schema 和调用接口
"""

import asyncio
from typing import Any, Dict, List, Optional

from loguru import logger
from mcp import types as mcp_types
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

from app.tools.result import ToolResult


class MCPServerConnection:
    """单个 MCP Server 的连接管理"""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.session: Optional[ClientSession] = None
        self.tools: List[mcp_types.Tool] = []
        self._cm_stack = None  # 上下文管理器栈，用于退出时清理

    @property
    def server_type(self) -> str:
        return self.config.get("type", "stdio")

    @property
    def enabled(self) -> bool:
        return self.config.get("enabled", True)


class MCPClientManager:
    """
    MCP 客户端管理器（全局单例）

    职责：
    1. 根据配置连接/断开 MCP Server
    2. 发现 MCP Server 提供的工具
    3. 将 MCP 工具转为 OpenAI function calling schema
    4. 调用 MCP 工具并返回结果

    设计：多窗口共享同一个 MCP 连接池，避免同一个 stdio server 启动多个子进程。
    通过 MCPClientManager.get_instance() 获取单例。
    """

    # MCP 工具名前缀，避免与内置工具冲突
    TOOL_PREFIX = "mcp__"

    _instance = None
    _ref_count = 0  # 引用计数，最后一个释放时断开连接

    @classmethod
    def get_instance(cls) -> "MCPClientManager":
        """获取全局单例"""
        if cls._instance is None:
            cls._instance = MCPClientManager()
        return cls._instance

    def __init__(self):
        if MCPClientManager._instance is not None and MCPClientManager._instance is not self:
            raise RuntimeError("请使用 MCPClientManager.get_instance() 获取单例")
        self._connections: Dict[str, MCPServerConnection] = {}
        self._connected = False

    async def connect_all(self, servers_config: List[dict]) -> None:
        """
        连接所有启用的 MCP Server

        Args:
            servers_config: 配置列表，每项格式:
                {"name": "xxx", "type": "stdio"|"sse"|"http", "enabled": True, ...}
        """
        if self._connected:
            await self.disconnect_all()

        for server_cfg in servers_config:
            name = server_cfg.get("name", "")
            if not name:
                continue
            if not server_cfg.get("enabled", True):
                logger.info(f"[MCP] 跳过已禁用的服务器: {name}")
                continue

            conn = MCPServerConnection(name, server_cfg)
            try:
                await self._connect_server(conn)
                self._connections[name] = conn
                logger.info(
                    f"[MCP] 已连接服务器 '{name}'，发现 {len(conn.tools)} 个工具"
                )
            except Exception as e:
                logger.error(f"[MCP] 连接服务器 '{name}' 失败: {e}")

        self._connected = True

    async def _connect_server(self, conn: MCPServerConnection) -> None:
        """连接单个 MCP Server 并发现工具"""
        server_type = conn.server_type

        if server_type == "stdio":
            await self._connect_stdio(conn)
        elif server_type == "sse":
            await self._connect_sse(conn)
        elif server_type == "http":
            await self._connect_http(conn)
        else:
            raise ValueError(f"不支持的 MCP 服务器类型: {server_type}")

    async def _connect_stdio(self, conn: MCPServerConnection) -> None:
        """通过 stdio 连接 MCP Server"""
        from mcp.client.stdio import StdioServerParameters

        command = conn.config.get("command", "")
        args = conn.config.get("args", [])
        env = conn.config.get("env")

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env,
        )

        # 使用上下文管理器保持连接
        cm = stdio_client(server_params)
        read_stream, write_stream = await cm.__aenter__()
        conn._cm_stack = [cm]

        session_cm = ClientSession(read_stream, write_stream)
        session = await session_cm.__aenter__()
        conn._cm_stack.append(session_cm)

        # 初始化会话
        await session.initialize()
        conn.session = session

        # 发现工具
        result = await session.list_tools()
        conn.tools = result.tools

    async def _connect_sse(self, conn: MCPServerConnection) -> None:
        """通过 SSE 连接 MCP Server"""
        url = conn.config.get("url", "")
        headers = conn.config.get("headers")

        cm = sse_client(url=url, headers=headers)
        read_stream, write_stream = await cm.__aenter__()
        conn._cm_stack = [cm]

        session_cm = ClientSession(read_stream, write_stream)
        session = await session_cm.__aenter__()
        conn._cm_stack.append(session_cm)

        await session.initialize()
        conn.session = session

        result = await session.list_tools()
        conn.tools = result.tools

    async def _connect_http(self, conn: MCPServerConnection) -> None:
        """通过 Streamable HTTP 连接 MCP Server"""
        url = conn.config.get("url", "")
        headers = conn.config.get("headers")

        cm = streamablehttp_client(url=url, headers=headers)
        read_stream, write_stream, _ = await cm.__aenter__()
        conn._cm_stack = [cm]

        session_cm = ClientSession(read_stream, write_stream)
        session = await session_cm.__aenter__()
        conn._cm_stack.append(session_cm)

        await session.initialize()
        conn.session = session

        result = await session.list_tools()
        conn.tools = result.tools

    async def disconnect_all(self) -> None:
        """断开所有 MCP Server 连接"""
        for name, conn in self._connections.items():
            try:
                await self._disconnect_server(conn)
            except Exception as e:
                logger.error(f"[MCP] 断开服务器 '{name}' 失败: {e}")

        self._connections.clear()
        self._connected = False

    async def _disconnect_server(self, conn: MCPServerConnection) -> None:
        """断开单个服务器连接，按 LIFO 顺序退出上下文"""
        if conn._cm_stack:
            for cm in reversed(conn._cm_stack):
                try:
                    await cm.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"[MCP] 清理连接时出错: {e}")
            conn._cm_stack = None

        conn.session = None
        conn.tools = []
        logger.info(f"[MCP] 已断开服务器 '{conn.name}'")

    def get_tool_schemas(self) -> List[Dict]:
        """
        获取所有 MCP 工具的 OpenAI function calling schema

        工具名格式: mcp__<server_name>__<tool_name>
        """
        schemas = []

        for server_name, conn in self._connections.items():
            if not conn.session or not conn.enabled:
                continue

            for tool in conn.tools:
                prefixed_name = f"{self.TOOL_PREFIX}{server_name}__{tool.name}"
                schema = {
                    "type": "function",
                    "function": {
                        "name": prefixed_name,
                        "description": tool.description or f"MCP tool: {tool.name}",
                        "parameters": tool.inputSchema or {
                            "type": "object",
                            "properties": {},
                        },
                    },
                }
                schemas.append(schema)

        return schemas

    def parse_tool_name(self, prefixed_name: str) -> Optional[tuple]:
        """
        解析带前缀的工具名

        Returns:
            (server_name, tool_name) 或 None
        """
        if not prefixed_name.startswith(self.TOOL_PREFIX):
            return None

        remainder = prefixed_name[len(self.TOOL_PREFIX):]
        if "__" not in remainder:
            return None

        server_name, tool_name = remainder.split("__", 1)
        return server_name, tool_name

    async def call_tool(self, prefixed_name: str, arguments: dict) -> ToolResult:
        """
        调用 MCP 工具

        Args:
            prefixed_name: 带前缀的工具名 (mcp__server__tool)
            arguments: 工具参数
        """
        parsed = self.parse_tool_name(prefixed_name)
        if not parsed:
            return ToolResult(False, error=f"无效的 MCP 工具名: {prefixed_name}")

        server_name, tool_name = parsed
        conn = self._connections.get(server_name)
        if not conn or not conn.session:
            return ToolResult(False, error=f"MCP 服务器 '{server_name}' 未连接")

        try:
            result = await conn.session.call_tool(tool_name, arguments)

            # 提取文本内容
            text_parts = []
            for content in (result.content or []):
                if isinstance(content, mcp_types.TextContent):
                    text_parts.append(content.text)
                elif hasattr(content, "text"):
                    text_parts.append(str(content.text))

            output = "\n".join(text_parts) if text_parts else str(result)

            if result.isError:
                return ToolResult(False, error=output)

            return ToolResult(True, content=output)

        except Exception as e:
            logger.error(f"[MCP] 调用工具 '{prefixed_name}' 失败: {e}")
            return ToolResult(False, error=f"MCP 工具调用失败: {e}")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get_status(self) -> List[Dict]:
        """获取所有 MCP Server 的状态信息"""
        status = []
        for name, conn in self._connections.items():
            status.append({
                "name": name,
                "type": conn.server_type,
                "enabled": conn.enabled,
                "connected": conn.session is not None,
                "tool_count": len(conn.tools),
                "tools": [t.name for t in conn.tools],
            })
        return status

    def acquire(self):
        """增加引用计数（窗口创建时调用）"""
        MCPClientManager._ref_count += 1
        logger.debug(f"[MCP] acquire, ref_count={MCPClientManager._ref_count}")

    def release(self):
        """
        减少引用计数（窗口关闭时调用）。
        只有当引用计数归零时才真正断开连接。
        """
        MCPClientManager._ref_count = max(0, MCPClientManager._ref_count - 1)
        logger.debug(f"[MCP] release, ref_count={MCPClientManager._ref_count}")
        if MCPClientManager._ref_count == 0 and self._connected:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self.disconnect_all())
                else:
                    loop.run_until_complete(self.disconnect_all())
            except Exception as e:
                logger.warning(f"[MCP] 释放时断开连接出错: {e}")
