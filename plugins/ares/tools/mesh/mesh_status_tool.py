from __future__ import annotations

import logging

from plugins.ares.tools.base import json_result
from plugins.ares.mesh.client import get_mesh_client

logger = logging.getLogger(__name__)

TOOLSET = "ares_utility"


def _handle(args: dict, **kw) -> str:
    role = args.get("role", "")
    client = get_mesh_client()

    if not client.is_connected:
        return json_result(True, data={
            "connected": False,
            "message": "Not connected to any mesh. Use mesh_join first.",
        })

    if role:
        agents = client.discover(role=role)
    else:
        agents = client.discover()

    stats = client.get_stats()

    stale_count = 0
    from plugins.ares.mesh.registry import get_registry
    try:
        stale_count = get_registry().cleanup_stale()
    except Exception:
        pass

    return json_result(True, data={
        "connected": True,
        "node_id": client.node_id,
        "peers": stats.get("peer_list", []),
        "peers_count": stats.get("peers", 0),
        "discovered_agents": len(agents) if role else stats.get("registry", {}),
        "stale_removed": stale_count,
        "registry_stats": stats.get("registry", {}),
    })


SCHEMA = {
    "name": "mesh_status",
    "description": "Show ACP mesh connection status, connected peers, and discovered agents. Optionally filter by role.",
    "parameters": {
        "type": "object",
        "properties": {
            "role": {
                "type": "string",
                "default": "",
                "description": "Filter discovered agents by role (empty = show all)",
            },
        },
        "required": [],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="mesh_status",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="📊",
    )
