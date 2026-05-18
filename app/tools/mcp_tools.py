# -*- coding: utf-8 -*-
"""
MCP 工具模块 - 管理 MCP Server 连接、工具发现与调用

核心设计：
- MCPClientManager 是全局单例，多窗口共享连接池
- 所有 MCP 异步操作在一个专用后台线程的事件循环中执行
- 外部调用通过 run_coroutine_threadsafe 调度到该循环，同步等待结果
"""

import asyncio
import threading
from typing import Dict, List, Optional

from loguru import logger
from mcp import types as mcp_types
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
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
        self._cm_stack = None

    @property
    def server_type(self) -> str:
        return self.config.get("type", "stdio")

    @property
    def enabled(self) -> bool:
        return self.config.get("enabled", True)


class MCPClientManager:
    """
    MCP 客户端管理器（全局单例）

    所有异步 MCP 操作在专用后台线程的持久事件循环中执行，
    解决跨线程/跨事件循环问题。
    """

    TOOL_PREFIX = "mcp__"

    _instance = None
    _ref_count = 0

    @classmethod
    def get_instance(cls) -> "MCPClientManager":
        if cls._instance is None:
            cls._instance = MCPClientManager()
        return cls._instance

    def __init__(self):
        if MCPClientManager._instance is not None and MCPClientManager._instance is not self:
            raise RuntimeError("请使用 MCPClientManager.get_instance() 获取单例")

        self._connections: Dict[str, MCPServerConnection] = {}
        self._connected = False

        # 专用后台线程 + 持久事件循环
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._start_loop()

    def _start_loop(self):
        """启动后台线程的持久事件循环"""
        self._loop_ready = threading.Event()

        def _run():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop_ready.set()
            self._loop.run_forever()

        self._thread = threading.Thread(target=_run, name="mcp-eventloop", daemon=True)
        self._thread.start()
        self._loop_ready.wait(timeout=5)
        logger.info("[MCP] 后台事件循环已启动")

    def _run_async(self, coro, timeout: float = 60):
        """
        在后台事件循环中执行协程，同步等待结果。

        这是所有外部调用 MCP 异步方法的统一入口。
        """
        if not self._loop or self._loop.is_closed():
            raise RuntimeError("MCP 事件循环未运行")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    # ── 连接管理 ──────────────────────────────────────

    def connect_all_sync(self, servers_config: List[dict]) -> None:
        """同步连接所有 MCP 服务器（供外部调用）"""
        self._run_async(self._connect_all(servers_config))

    async def _connect_all(self, servers_config: List[dict]) -> None:
        if self._connected:
            await self._disconnect_all()

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
                logger.info(f"[MCP] 已连接服务器 '{name}'，发现 {len(conn.tools)} 个工具")
            except Exception as e:
                logger.error(f"[MCP] 连接服务器 '{name}' 失败: {e}")

        self._connected = True

    async def _connect_server(self, conn: MCPServerConnection) -> None:
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
        command = conn.config.get("command", "")
        args = conn.config.get("args", [])
        env = conn.config.get("env")

        server_params = StdioServerParameters(command=command, args=args, env=env)

        cm = stdio_client(server_params)
        read_stream, write_stream = await cm.__aenter__()
        conn._cm_stack = [cm]

        session_cm = ClientSession(read_stream, write_stream)
        session = await session_cm.__aenter__()
        conn._cm_stack.append(session_cm)

        await session.initialize()
        conn.session = session

        result = await session.list_tools()
        conn.tools = result.tools

    async def _connect_sse(self, conn: MCPServerConnection) -> None:
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

    # ── 断开连接 ──────────────────────────────────────

    def disconnect_all_sync(self) -> None:
        """同步断开所有连接（供外部调用）"""
        try:
            self._run_async(self._disconnect_all())
        except Exception as e:
            logger.warning(f"[MCP] 断开连接失败: {e}")

    async def _disconnect_all(self) -> None:
        for name, conn in self._connections.items():
            try:
                await self._disconnect_server(conn)
            except Exception as e:
                logger.error(f"[MCP] 断开服务器 '{name}' 失败: {e}")

        self._connections.clear()
        self._connected = False

    async def _disconnect_server(self, conn: MCPServerConnection) -> None:
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

    # ── 工具 Schema ──────────────────────────────────

    def get_tool_schemas(self) -> List[Dict]:
        """获取所有 MCP 工具的 OpenAI function calling schema"""
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

    # ── 工具调用 ──────────────────────────────────────

    def call_tool_sync(self, prefixed_name: str, arguments: dict) -> ToolResult:
        """同步调用 MCP 工具（供 ToolExecutor 调用）"""
        try:
            return self._run_async(self._call_tool(prefixed_name, arguments))
        except Exception as e:
            logger.error(f"[MCP] 调用工具 '{prefixed_name}' 失败: {e}")
            return ToolResult(False, error=f"MCP 工具调用失败: {e}")

    async def _call_tool(self, prefixed_name: str, arguments: dict) -> ToolResult:
        parsed = self._parse_tool_name(prefixed_name)
        if not parsed:
            return ToolResult(False, error=f"无效的 MCP 工具名: {prefixed_name}")

        server_name, tool_name = parsed
        conn = self._connections.get(server_name)
        if not conn or not conn.session:
            return ToolResult(False, error=f"MCP 服务器 '{server_name}' 未连接")

        try:
            result = await conn.session.call_tool(tool_name, arguments)

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

    # ── 辅助方法 ──────────────────────────────────────

    def _parse_tool_name(self, prefixed_name: str) -> Optional[tuple]:
        if not prefixed_name.startswith(self.TOOL_PREFIX):
            return None
        remainder = prefixed_name[len(self.TOOL_PREFIX):]
        if "__" not in remainder:
            return None
        server_name, tool_name = remainder.split("__", 1)
        return server_name, tool_name

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get_status(self) -> List[Dict]:
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

    # ── 引用计数（多窗口生命周期）──────────────────────

    def acquire(self):
        MCPClientManager._ref_count += 1
        logger.debug(f"[MCP] acquire, ref_count={MCPClientManager._ref_count}")

    def release(self):
        MCPClientManager._ref_count = max(0, MCPClientManager._ref_count - 1)
        logger.debug(f"[MCP] release, ref_count={MCPClientManager._ref_count}")
        if MCPClientManager._ref_count == 0 and self._connected:
            self.disconnect_all_sync()

    def shutdown(self):
        """彻底关闭后台事件循环（进程退出时调用）"""
        if self._connected:
            self.disconnect_all_sync()
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)
        logger.info("[MCP] 后台事件循环已停止")
