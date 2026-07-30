"""Ares MCP client — connect to external MCP servers and call their tools."""

import asyncio
import logging
import threading
from datetime import timedelta

logger = logging.getLogger(__name__)

_MCP_AVAILABLE = False
try:
    from mcp.client.sse import sse_client
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.websocket import websocket_client
    from mcp.client.session import ClientSession
    from mcp.types import TextContent
    _MCP_AVAILABLE = True
except ImportError:
    pass

_sessions: dict[str, dict] = {}
_pending_connect: set[str] = set()
_lock = threading.Lock()
_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None


def _check_mcp() -> None:
    if not _MCP_AVAILABLE:
        raise ImportError("MCP SDK not installed. Run: pip install 'cyberfox-agent[mcp]'")


def _ensure_loop():
    global _loop, _loop_thread
    if _loop is not None and _loop.is_running():
        return _loop
    _loop = asyncio.new_event_loop()
    _loop_thread = threading.Thread(target=_loop.run_forever, daemon=True)
    _loop_thread.start()
    return _loop


async def _connection_task(name: str, transport: str,
                           url: str | None = None,
                           command: str | None = None,
                           cmd_args: list[str] | None = None,
                           env: dict | None = None,
                           headers: dict | None = None,
                           timeout: float = 30):
    """Background task: holds transport + session open until disconnect requested."""
    disconnect_event = asyncio.Event()
    session_ref: dict = {}
    tools_ref: dict = {}

    with _lock:
        if name in _sessions:
            _pending_connect.discard(name)
            raise RuntimeError(f"MCP server '{name}' is already connected")
        _sessions[name] = {
            "disconnect_event": disconnect_event,
            "session_ref": session_ref,
            "tools_ref": tools_ref,
            "loop": _loop,
        }

    try:
        if transport == "sse":
            async with sse_client(url, headers=headers, timeout=timeout) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    session_ref["session"] = session
                    tools_ref["tools"] = result.tools
                    await disconnect_event.wait()

        elif transport == "stdio":
            params = StdioServerParameters(command=command, args=cmd_args or [], env=env)
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    session_ref["session"] = session
                    tools_ref["tools"] = result.tools
                    await disconnect_event.wait()

        elif transport == "ws":
            async with websocket_client(url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    session_ref["session"] = session
                    tools_ref["tools"] = result.tools
                    await disconnect_event.wait()
        else:
            raise ValueError(f"Unknown transport: {transport}")

    except asyncio.CancelledError:
        pass
    except Exception:
        with _lock:
            _sessions.pop(name, None)
        raise
    finally:
        with _lock:
            _pending_connect.discard(name)


def connect(name: str, url: str | None = None, transport: str = "sse",
            command: str | None = None, args: list[str] | None = None,
            env: dict | None = None, headers: dict | None = None,
            timeout: float = 30) -> dict:
    _check_mcp()
    _ensure_loop()

    if transport == "sse" and not url:
        raise ValueError("url is required for SSE transport")
    if transport == "stdio" and not command:
        raise ValueError("command is required for stdio transport")
    if transport == "ws" and not url:
        raise ValueError("url is required for WebSocket transport")

    with _lock:
        if name in _sessions:
            raise RuntimeError(f"MCP server '{name}' is already connected")
        if name in _pending_connect:
            raise RuntimeError(f"MCP server '{name}' connection is already in progress")
        _pending_connect.add(name)

    task = asyncio.run_coroutine_threadsafe(
        _connection_task(
            name=name, transport=transport, url=url,
            command=command, cmd_args=args, env=env,
            headers=headers, timeout=timeout,
        ),
        _loop,
    )

    import time as _time
    deadline = _time.monotonic() + timeout + 10
    while _time.monotonic() < deadline:
        if task.done():
            exc = task.exception()
            if exc:
                raise RuntimeError(f"Failed to connect MCP '{name}': {exc}".split("\n")[0])
            break
        with _lock:
            conn = _sessions.get(name)
            if conn and conn["session_ref"].get("session") is not None:
                tools = conn["tools_ref"].get("tools", [])
                tools_info = [
                    {"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
                    for t in tools
                ]
                return {
                    "server": name,
                    "transport": transport,
                    "tools": tools_info,
                    "tool_count": len(tools_info),
                }
        _time.sleep(0.05)

    raise TimeoutError(f"Connection to MCP server '{name}' timed out after {timeout}s")


def call_tool(name: str, tool_name: str, arguments: dict | None = None,
              timeout: float = 300) -> dict:
    _check_mcp()
    with _lock:
        conn = _sessions.get(name)
    if not conn:
        raise RuntimeError(f"MCP server '{name}' is not connected. Use mcp_server_connect first.")
    session = conn["session_ref"].get("session")
    if not session:
        raise RuntimeError(f"MCP server '{name}' is not yet ready (connecting...)")
    loop = conn["loop"]

    import concurrent.futures
    future = asyncio.run_coroutine_threadsafe(
        session.call_tool(
            tool_name,
            arguments=arguments,
            read_timeout_seconds=timedelta(seconds=timeout),
        ),
        loop,
    )
    try:
        result = future.result(timeout=timeout + 10)
    except concurrent.futures.TimeoutError:
        future.cancel()
        raise TimeoutError(f"MCP call '{name}/{tool_name}' timed out after {timeout}s")

    text_parts = []
    for block in result.content:
        if isinstance(block, TextContent):
            text_parts.append(block.text)

    return {
        "server": name,
        "tool": tool_name,
        "isError": result.isError,
        "content": "\n".join(text_parts),
        "content_blocks": len(result.content),
    }


def disconnect(name: str) -> dict:
    _check_mcp()
    with _lock:
        conn = _sessions.pop(name, None)
    if not conn:
        raise RuntimeError(f"MCP server '{name}' is not connected")

    _pending_connect.discard(name)
    disconnect_event = conn.get("disconnect_event")
    if disconnect_event:
        disconnect_event.set()
    return {"server": name, "disconnected": True}


def list_connections() -> list[dict]:
    _check_mcp()
    with _lock:
        return [
            {
                "server": name,
                "tools": [{"name": t.name, "description": t.description}
                          for t in conn["tools_ref"].get("tools", [])],
                "tool_count": len(conn["tools_ref"].get("tools", [])),
            }
            for name, conn in _sessions.items()
        ]
