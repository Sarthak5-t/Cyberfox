from __future__ import annotations

import json
import logging
import socket

from plugins.ares.tools.base import json_result
from plugins.ares.mesh.client import get_mesh_client

logger = logging.getLogger(__name__)

TOOLSET = "ares_utility"

AVAILABLE_ROLES = [
    "lead_orchestrator", "pentester", "soc_analyst", "osint_analyst",
    "web_attacker", "ad_specialist", "privesc_specialist",
    "cloud_specialist", "mobile_specialist", "wireless_specialist",
    "social_engineer", "malware_analyst",
    "swarm_recon", "swarm_web", "swarm_network", "swarm_ad", "swarm_exploit",
]


def _handle(args: dict, **kw) -> str:
    port = args.get("port", 9876)
    host = args.get("host", "0.0.0.0")
    node_id = args.get("node_id", "")
    roles = args.get("roles", "pentester")
    peers = args.get("peers", "")
    auth_secret = args.get("auth_secret", "")

    if not node_id:
        node_id = f"ares-{socket.gethostname()}-{port}"

    role_list = [r.strip() for r in roles.split(",") if r.strip()]
    peer_list = [p.strip() for p in peers.split(",") if p.strip() if p.strip()]

    client = get_mesh_client()

    if client.is_connected:
        return json_result(False, error="Already connected to a mesh. Use mesh_leave first.")

    if not peer_list:
        return json_result(True, data={
            "node_id": node_id,
            "port": port,
            "roles": role_list,
            "note": "No peers specified. Provide peers to join a mesh, or start this node as a standalone hub.",
            "peers_connected": 0,
            "peers": [],
        })

    import threading, time
    result_holder = {}

    def _start():
        try:
            ok = client.start(
                node_id=node_id,
                roles=role_list,
                host=host,
                port=port,
                peers=peer_list,
                auth_secret=auth_secret,
            )
            result_holder["ok"] = ok
            if ok:
                result_holder["discovered"] = client.discover()
                result_holder["peers"] = client.list_peers()
        except Exception as e:
            result_holder["error"] = str(e)

    t = threading.Thread(target=_start, daemon=True)
    t.start()
    t.join(timeout=10)

    if "error" in result_holder:
        return json_result(False, error=result_holder["error"])

    if not result_holder.get("ok"):
        return json_result(False, error="Failed to start mesh client (timeout or connection refused)")

    return json_result(True, data={
        "node_id": node_id,
        "host": host,
        "port": port,
        "roles": role_list,
        "peers_connected": len(result_holder.get("peers", [])),
        "peers": result_holder.get("peers", [])[:20],
        "discovered_agents": len(result_holder.get("discovered", [])),
    })


SCHEMA = {
    "name": "mesh_join",
    "description": "Join the ACP agent mesh as a node. Connects to peer nodes via WebSocket, announces capabilities, and discovers other agents. Enables distributed multi-agent operations.",
    "parameters": {
        "type": "object",
        "properties": {
            "node_id": {
                "type": "string",
                "default": "",
                "description": "Unique node identifier (auto-generated if empty)",
            },
            "roles": {
                "type": "string",
                "default": "pentester",
                "description": "Comma-separated roles this node can fulfill",
            },
            "host": {
                "type": "string",
                "default": "0.0.0.0",
                "description": "Bind address for the mesh WebSocket server",
            },
            "port": {
                "type": "integer",
                "default": 9876,
                "description": "Port for the mesh WebSocket server",
            },
            "peers": {
                "type": "string",
                "default": "",
                "description": "Comma-separated peer WebSocket URLs to connect to (e.g. 'ws://10.0.0.1:9876,ws://10.0.0.2:9876')",
            },
            "auth_secret": {
                "type": "string",
                "default": "",
                "description": "Shared secret for mesh authentication (empty = no auth)",
            },
        },
        "required": [],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="mesh_join",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🌐",
    )
