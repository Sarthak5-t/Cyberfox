from __future__ import annotations

import logging

from plugins.ares.tools.base import json_result
from plugins.ares.mesh.client import get_mesh_client

logger = logging.getLogger(__name__)

TOOLSET = "ares_utility"


def _handle(args: dict, **kw) -> str:
    client = get_mesh_client()

    if not client.is_connected:
        return json_result(False, error="Not connected to any mesh")

    try:
        node_id = client.node_id
        client.stop()
        return json_result(True, data={
            "node_id": node_id,
            "status": "disconnected",
            "message": "Left the mesh successfully",
        })
    except Exception as e:
        return json_result(False, error=f"Failed to leave mesh: {e}")


SCHEMA = {
    "name": "mesh_leave",
    "description": "Disconnect from the ACP agent mesh. Stops the WebSocket server and closes all peer connections.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="mesh_leave",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🚪",
    )
