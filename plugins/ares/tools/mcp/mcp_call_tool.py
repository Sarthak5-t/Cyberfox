from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_utility"


def _handle(args: dict, **kw) -> str:
    server = args.get("server", "")
    tool = args.get("tool", "")
    arguments_raw = args.get("arguments", "")
    timeout = args.get("timeout", 300)

    if not server:
        return json_result(False, error="'server' is required")
    if not tool:
        return json_result(False, error="'tool' is required")

    try:
        from plugins.ares.tools.mcp import call_tool as mcp_call
    except ImportError as e:
        return json_result(False, error=str(e))

    try:
        arguments = None
        if arguments_raw:
            if isinstance(arguments_raw, str):
                arguments = json.loads(arguments_raw)
            else:
                arguments = arguments_raw

        result = mcp_call(
            name=server,
            tool_name=tool,
            arguments=arguments,
            timeout=float(timeout),
        )
        return json_result(True, data=result)
    except RuntimeError as e:
        return json_result(False, error=str(e))
    except json.JSONDecodeError as e:
        return json_result(False, error=f"Invalid JSON in arguments: {e}")
    except TimeoutError as e:
        return json_result(False, error=str(e))
    except Exception as e:
        logger.exception("MCP call failed")
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "mcp_server_call",
    "description": "Call a tool on a connected MCP server. First use mcp_server_connect to connect, then this to invoke any tool the server exposes.",
    "parameters": {
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "Name of the connected MCP server (from mcp_server_connect)",
            },
            "tool": {
                "type": "string",
                "description": "Name of the tool to call on the MCP server",
            },
            "arguments": {
                "type": "string",
                "default": "",
                "description": "JSON object of arguments to pass to the tool (e.g., '{\"url\": \"https://target.com\"}')",
            },
            "timeout": {
                "type": "integer",
                "default": 300,
                "description": "Tool call timeout in seconds",
            },
        },
        "required": ["server", "tool"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="mcp_server_call",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
    )
