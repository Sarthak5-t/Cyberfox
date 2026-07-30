from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_utility"


def _handle(args: dict, **kw) -> str:
    name = args.get("name", "")
    url = args.get("url", "")
    transport = args.get("transport", "sse")
    command = args.get("command", "")
    cmd_args = args.get("args", "")
    headers_raw = args.get("headers", "")
    timeout = args.get("timeout", 30)

    if not name:
        return json_result(False, error="'name' is required")

    try:
        from plugins.ares.tools.mcp import connect
    except ImportError as e:
        return json_result(False, error=str(e))

    try:
        headers = None
        if headers_raw:
            headers = {}
            for pair in headers_raw.split(","):
                if ":" in pair:
                    k, v = pair.split(":", 1)
                    headers[k.strip()] = v.strip()

        parsed_args = [a.strip() for a in cmd_args.split(",") if a.strip()] if cmd_args else None
        env = None

        result = connect(
            name=name,
            url=url or None,
            transport=transport,
            command=command or None,
            args=parsed_args,
            env=env,
            headers=headers,
            timeout=float(timeout),
        )
        return json_result(True, data=result)
    except RuntimeError as e:
        return json_result(False, error=str(e))
    except ValueError as e:
        return json_result(False, error=str(e))
    except TimeoutError as e:
        return json_result(False, error=str(e))
    except Exception as e:
        logger.exception("MCP connect failed")
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "mcp_server_connect",
    "description": "Connect to an external MCP server (e.g., Burp Suite MCP) and discover its tools. After connecting, use mcp_server_call to invoke tools on the server.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Unique name for this MCP server connection (used as handle for subsequent calls)",
            },
            "url": {
                "type": "string",
                "description": "URL of the MCP server (e.g., http://localhost:8090/mcp for SSE, ws://localhost:8090/mcp for WebSocket)",
            },
            "transport": {
                "type": "string",
                "enum": ["sse", "stdio", "ws"],
                "default": "sse",
                "description": "Transport protocol: sse (HTTP Server-Sent Events), stdio (local subprocess), ws (WebSocket)",
            },
            "command": {
                "type": "string",
                "default": "",
                "description": "Executable command for stdio transport (e.g., 'npx', 'python')",
            },
            "args": {
                "type": "string",
                "default": "",
                "description": "Comma-separated arguments for stdio transport command",
            },
            "headers": {
                "type": "string",
                "default": "",
                "description": "Comma-separated key:value headers for HTTP connections (e.g., 'Authorization:Bearer tok')",
            },
            "timeout": {
                "type": "integer",
                "default": 30,
                "description": "Connection timeout in seconds",
            },
        },
        "required": ["name"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="mcp_server_connect",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
    )
