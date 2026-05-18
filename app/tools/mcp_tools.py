# -*- coding: utf-8 -*-
"""
MCP 工具模块 - 管理 MCP Server 连接、工具发现与调用

核心设计：
- MCPClientManager 是全局单例，多窗口共享连接池
- 所有 MCP 异步操作在一个专用后台线程的事件循环中执行
- 每个连接由一个持久 Task 管理，__aenter__/__aexit__ 在同一 Task 中
- 断开连接通过 Event 信号通知 Task 自然退出 async with 块
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
        # 持久 Task 管理（__aenter__/__aexit__ 在同一 Task 中）
        self._task: Optional[asyncio.Task] = None
        self._disconnect_event: Optional[asyncio.Event] = None
        self._ready_event: Optional[asyncio.Event] = None
        self._connect_error: Optional[Exception] = None

    @property
    def server_type(self) -> str:
        return self.config.get("type", "stdio")

    @property
    def enabled(self) -> bool:
        return self.config.get("enabled", True)


class MCPClientManager:
    """
    MCP 客户端管理器（全局单例）

    所有异步 MCP 操作在专用后台线程的持久事件循环中执行。
    每个服务器连接由一个持久 asyncio.Task 管理：
    - Task 内部用 async with 持有 transport + session
    - 断开时设置 Event 信号，Task 自然退出 async with 块
    - 确保 __aenter__ / __aexit__ 在同一 Task 中执行
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
        """在后台事件循环中执行协程，同步等待结果"""
        if not self._loop or self._loop.is_closed():
            raise RuntimeError("MCP 事件循环未运行")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    # ── 连接生命周期（持久 Task 模式）──────────────

    async def _server_lifespan(self, conn: MCPServerConnection) -> None:
        """
        连接生命周期 — 在专属 Task 中运行。

        用 async with 管理 transport 和 session，
        保证 __aenter__/__aexit__ 在同一 Task 中执行。
        断开时通过 _disconnect_event 信号自然退出。
        """
        server_type = conn.server_type
        try:
            if server_type == "stdio":
                await self._lifespan_stdio(conn)
            elif server_type == "sse":
                await self._lifespan_sse(conn)
            elif server_type == "http":
                await self._lifespan_http(conn)
            else:
                conn._connect_error = ValueError(f"不支持的 MCP 服务器类型: {server_type}")
                conn._ready_event.set()
        except asyncio.CancelledError:
            logger.debug(f"[MCP] 服务器 '{conn.name}' 的生命周期 Task 被取消")
        except Exception as e:
            if not conn._ready_event.is_set():
                conn._connect_error = e
                conn._ready_event.set()
            else:
                logger.warning(f"[MCP] 服务器 '{conn.name}' 生命周期异常: {e}")
        finally:
            conn.session = None
            conn.tools = []
            logger.info(f"[MCP] 已断开服务器 '{conn.name}'")

    async def _lifespan_stdio(self, conn: MCPServerConnection) -> None:
        command = conn.config.get("command", "")
        args = conn.config.get("args", [])
        env = conn.config.get("env")

        params = StdioServerParameters(command=command, args=args, env=env)

        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                conn.session = session
                conn.tools = result.tools
                conn._ready_event.set()
                await conn._disconnect_event.wait()

    async def _lifespan_sse(self, conn: MCPServerConnection) -> None:
        url = conn.config.get("url", "")
        headers = conn.config.get("headers")

        async with sse_client(url=url, headers=headers) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                conn.session = session
                conn.tools = result.tools
                conn._ready_event.set()
                await conn._disconnect_event.wait()

    async def _lifespan_http(self, conn: MCPServerConnection) -> None:
        url = conn.config.get("url", "")
        headers = conn.config.get("headers")

        async with streamablehttp_client(url=url, headers=headers) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                conn.session = session
                conn.tools = result.tools
                conn._ready_event.set()
                await conn._disconnect_event.wait()

    # ── 连接操作 ──────────────────────────────────────

    def connect_all_sync(self, servers_config: List[dict]) -> None:
        """同步连接所有 MCP 服务器（阻塞调用线程，慎用）"""
        self._run_async(self._connect_all(servers_config))

    def connect_all_background(self, servers_config: List[dict], on_done=None) -> None:
        """后台连接所有 MCP 服务器（不阻塞 UI 线程）"""
        def _worker():
            try:
                self._run_async(self._connect_all(servers_config))
            except Exception as e:
                logger.error(f"[MCP] 后台连接失败: {e}")
            finally:
                if on_done:
                    connected = sum(1 for c in self._connections.values() if c.session)
                    failed = [
                        s.get("name", "?") for s in servers_config
                        if s.get("enabled", True) and s.get("name") not in self._connections
                    ]
                    try:
                        on_done(connected, len(servers_config), failed)
                    except Exception as e:
                        logger.warning(f"[MCP] on_done 回调异常: {e}")

        threading.Thread(target=_worker, name="mcp-connect", daemon=True).start()
        logger.info("[MCP] 后台连接已启动")

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

            try:
                await self._connect_single(name, server_cfg)
            except Exception as e:
                logger.error(f"[MCP] 连接服务器 '{name}' 失败: {e}")

        self._connected = True

    def connect_server_sync(self, name: str, config: dict) -> bool:
        """同步连接单个 MCP 服务器（热添加）"""
        try:
            return self._run_async(self._connect_single(name, config))
        except Exception as e:
            logger.error(f"[MCP] 热添加服务器 '{name}' 失败: {e}")
            return False

    def connect_server_background(self, name: str, config: dict, on_done=None) -> None:
        """后台连接单个 MCP 服务器（不阻塞 UI）"""
        def _worker():
            success = False
            try:
                success = self._run_async(self._connect_single(name, config))
            except Exception as e:
                logger.error(f"[MCP] 热添加服务器 '{name}' 失败: {e}")
            finally:
                if on_done:
                    try:
                        on_done(name, success)
                    except Exception as e:
                        logger.warning(f"[MCP] on_done 回调异常: {e}")

        threading.Thread(target=_worker, name="mcp-hot-add", daemon=True).start()

    async def _connect_single(self, name: str, config: dict) -> bool:
        """连接单个服务器：启动生命周期 Task 并等待就绪"""
        # 如果已存在，先断开
        if name in self._connections:
            await self._disconnect_single(name)

        conn = MCPServerConnection(name, config)
        conn._disconnect_event = asyncio.Event()
        conn._ready_event = asyncio.Event()
        conn._connect_error = None

        # 在后台事件循环中启动生命周期 Task
        conn._task = asyncio.ensure_future(self._server_lifespan(conn), loop=self._loop)

        # 等待就绪或出错（最多 30 秒）
        try:
            await asyncio.wait_for(conn._ready_event.wait(), timeout=30)
        except asyncio.TimeoutError:
            conn._task.cancel()
            logger.error(f"[MCP] 连接服务器 '{name}' 超时")
            return False

        if conn._connect_error:
            logger.error(f"[MCP] 连接服务器 '{name}' 失败: {conn._connect_error}")
            return False

        self._connections[name] = conn
        self._connected = True
        logger.info(f"[MCP] 已连接服务器 '{name}'，发现 {len(conn.tools)} 个工具")
        return True

    # ── 断开连接 ──────────────────────────────────────

    def disconnect_server_sync(self, name: str) -> bool:
        """同步断开单个 MCP 服务器（快，不等待 Task 清理）"""
        try:
            return self._run_async(self._disconnect_single(name))
        except Exception as e:
            logger.error(f"[MCP] 热断开服务器 '{name}' 失败: {e}")
            return False

    def disconnect_server_background(self, name: str, on_done=None) -> None:
        """后台断开单个 MCP 服务器（不阻塞 UI）"""
        def _worker():
            try:
                self._run_async(self._disconnect_single(name))
            except Exception as e:
                logger.error(f"[MCP] 热断开服务器 '{name}' 失败: {e}")
            finally:
                if on_done:
                    try:
                        on_done(name)
                    except Exception as e:
                        logger.warning(f"[MCP] on_done 回调异常: {e}")

        threading.Thread(target=_worker, name="mcp-hot-disconnect", daemon=True).start()

    async def _disconnect_single(self, name: str) -> bool:
        """断开单个服务器：信号通知 + 取消 Task，不等待清理完成"""
        conn = self._connections.pop(name, None)
        if not conn:
            return False

        # 通知生命周期 Task 退出（走 async with 正常清理路径）
        if conn._disconnect_event:
            conn._disconnect_event.set()

        # 取消 Task 作为备份（CancelledError 在 async with 内触发 __aexit__）
        if conn._task and not conn._task.done():
            conn._task.cancel()

        # 立即清除引用，不等待 Task 完成
        conn.session = None
        conn.tools = []

        if not self._connections:
            self._connected = False
        return True

    def disconnect_all_sync(self) -> None:
        """同步断开所有连接（快，不等待 Task 清理）"""
        try:
            self._run_async(self._disconnect_all())
        except Exception as e:
            logger.warning(f"[MCP] 断开连接失败: {e}")

    def disconnect_all_background(self, on_done=None) -> None:
        """后台断开所有连接（不阻塞 UI）"""
        def _worker():
            try:
                self._run_async(self._disconnect_all())
            except Exception as e:
                logger.error(f"[MCP] 后台断开所有连接失败: {e}")
            finally:
                if on_done:
                    try:
                        on_done()
                    except Exception as e:
                        logger.warning(f"[MCP] on_done 回调异常: {e}")

        threading.Thread(target=_worker, name="mcp-disconnect-all", daemon=True).start()

    async def _disconnect_all(self) -> None:
        names = list(self._connections.keys())
        for name in names:
            try:
                await self._disconnect_single(name)
            except Exception as e:
                logger.error(f"[MCP] 断开服务器 '{name}' 失败: {e}")

        self._connections.clear()
        self._connected = False

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
