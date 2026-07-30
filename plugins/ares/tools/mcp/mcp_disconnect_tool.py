from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_utility"


def _handle(args: dict, **kw) -> str:
    server = args.get("server", "")
    disconnect_all = args.get("all", False)

    try:
        from plugins.ares.tools.mcp import disconnect, list_connections
    except ImportError as e:
        return json_result(False, error=str(e))

    if disconnect_all:
        conns = list_connections()
        results = []
        for c in conns:
            try:
                disconnect(c["server"])
                results.append({"server": c["server"], "disconnected": True})
            except Exception as e:
                results.append({"server": c["server"], "error": str(e)})
        return json_result(True, data={"disconnected": results})

    if not server:
        return json_result(False, error="'server' is required (or set 'all': true to disconnect all)")

    try:
        result = disconnect(server)
        return json_result(True, data=result)
    except RuntimeError as e:
        return json_result(False, error=str(e))
    except Exception as e:
        logger.exception("MCP disconnect failed")
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "mcp_server_disconnect",
    "description": "Disconnect from an MCP server. Cleans up the session and releases resources. Use 'all': true to disconnect all connected servers.",
    "parameters": {
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "default": "",
                "description": "Name of the connected MCP server to disconnect",
            },
            "all": {
                "type": "boolean",
                "default": False,
                "description": "Set to true to disconnect all connected MCP servers",
            },
        },
        "required": [],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="mcp_server_disconnect",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
    )
