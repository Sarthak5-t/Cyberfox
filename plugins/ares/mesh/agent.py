from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any, Optional

from plugins.ares.mesh.transport import (
    MeshTransport,
    MeshEnvelope,
    MeshMessageType,
)
from plugins.ares.mesh.registry import AgentInfo, get_registry

logger = logging.getLogger(__name__)


class RemoteAgentProxy:
    def __init__(self, transport: MeshTransport, node_id: str, host: str = "", port: int = 0):
        self.transport = transport
        self.node_id = node_id
        self.host = host
        self.port = port
        self._pending_responses: dict[str, asyncio.Future] = {}
        self._lock = threading.Lock()

    async def connect(self) -> bool:
        if self.host and self.port:
            url = f"ws://{self.host}:{self.port}"
            return await self.transport.connect(url, target_id=self.node_id)
        return False

    async def send_task(
        self,
        task_type: str,
        payload: dict[str, Any],
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        msg_id = f"task_{int(time.time() * 1000)}_{id(payload)}"
        future = asyncio.get_event_loop().create_future()

        with self._lock:
            self._pending_responses[msg_id] = future

        env = MeshEnvelope(
            type=MeshMessageType.AGENT_MESSAGE,
            message_id=msg_id,
            target=self.node_id,
            payload={
                "message_type": task_type,
                "payload": payload,
            },
        )

        await self.transport.send(self.node_id, env)

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            with self._lock:
                self._pending_responses.pop(msg_id, None)
            return {"success": False, "error": f"Remote task timed out after {timeout}s"}

    def resolve_response(self, message_id: str, data: dict[str, Any]):
        with self._lock:
            future = self._pending_responses.pop(message_id, None)
        if future and not future.done():
            future.set_result(data)

    @property
    def info(self) -> Optional[AgentInfo]:
        return get_registry().get(self.node_id)

    def __repr__(self) -> str:
        return f"RemoteAgentProxy({self.node_id}@{self.host}:{self.port})"


class MeshNode:
    def __init__(
        self,
        node_id: str,
        roles: list[str] | None = None,
        capabilities: dict | None = None,
        host: str = "0.0.0.0",
        port: int = 9876,
        auth_secret: str = "",
    ):
        self.node_id = node_id
        self.roles = roles or []
        self.capabilities = capabilities or {}
        self.host = host
        self.port = port

        self.transport = MeshTransport(node_id, self.roles, self.capabilities)
        self.registry = get_registry()
        self.registry.set_local(node_id)

        self._proxies: dict[str, RemoteAgentProxy] = {}
        self._connected_peers: dict[str, bool] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        from plugins.ares.mesh.auth import MeshAuthenticator
        self.auth = MeshAuthenticator(auth_secret)

        self._setup_handlers()

    def _setup_handlers(self):
        t = self.transport

        @t.on(MeshMessageType.REGISTER)
        async def on_register(sender: str, env: MeshEnvelope):
            node_id = env.payload.get("node_id", sender)
            is_new = self.registry.get(node_id) is None
            info = AgentInfo(
                node_id=node_id,
                host=env.payload.get("host", ""),
                port=env.payload.get("port", 0),
                roles=env.payload.get("roles", []),
                capabilities=env.payload.get("capabilities", {}),
            )
            self.registry.register(info)
            # Map node_id to connection for routing
            if sender != node_id:
                ws = self.transport._server_peers.get(sender) or self.transport._peers.get(sender)
                if ws:
                    is_client = sender in self.transport._peers
                    if is_client:
                        self.transport._peers[node_id] = ws
                    else:
                        self.transport._server_peers[node_id] = ws
            ack = MeshEnvelope(
                type=MeshMessageType.REGISTER_ACK,
                target=node_id,
                payload={"status": "ok", "node_id": self.node_id},
            )
            await t.send(node_id, ack)
            # Send our own registration so new peers learn about us (avoid echo loop)
            if is_new and node_id != self.node_id:
                my_reg = MeshEnvelope(
                    type=MeshMessageType.REGISTER,
                    target=node_id,
                    payload={
                        "node_id": self.node_id,
                        "host": self.host,
                        "port": self.port,
                        "roles": self.roles,
                        "capabilities": self.capabilities,
                    },
                )
                await t.send(node_id, my_reg)

        @t.on(MeshMessageType.REGISTER_ACK)
        async def on_register_ack(sender: str, env: MeshEnvelope):
            logger.info("Registration acknowledged by %s", sender)

        @t.on(MeshMessageType.HEARTBEAT)
        async def on_heartbeat(sender: str, env: MeshEnvelope):
            self.registry.heartbeat(env.payload.get("node_id", sender))
            ack = MeshEnvelope(
                type=MeshMessageType.HEARTBEAT_ACK,
                target=sender,
            )
            await t.send(sender, ack)

        @t.on(MeshMessageType.HEARTBEAT_ACK)
        async def on_heartbeat_ack(sender: str, env: MeshEnvelope):
            self.registry.heartbeat(env.payload.get("node_id", sender))

        @t.on(MeshMessageType.DISCOVER)
        async def on_discover(sender: str, env: MeshEnvelope):
            role_filter = env.payload.get("role", "")
            if role_filter:
                agents = self.registry.discover_by_role(role_filter)
            else:
                agents = self.registry.list_connected()
            resp = MeshEnvelope(
                type=MeshMessageType.DISCOVER_RESPONSE,
                target=sender,
                payload={
                    "agents": [
                        {
                            "node_id": a.node_id,
                            "host": a.host,
                            "port": a.port,
                            "roles": a.roles,
                            "capabilities": a.capabilities,
                        }
                        for a in agents
                    ]
                },
            )
            await t.send(sender, resp)

        @t.on(MeshMessageType.DISCOVER_RESPONSE)
        async def on_discover_response(sender: str, env: MeshEnvelope):
            for a_data in env.payload.get("agents", []):
                info = AgentInfo(**a_data)
                self.registry.register(info)

        @t.on(MeshMessageType.AGENT_MESSAGE)
        async def on_agent_message(sender: str, env: MeshEnvelope):
            msg_type = env.payload.get("message_type", "")
            msg_payload = env.payload.get("payload", {})

            if msg_type == "task_assign" and "task_id" in msg_payload:
                task_id = msg_payload["task_id"]
                from plugins.ares.agents.communication import get_communication_bus
                from plugins.ares.agents.communication import MessageType
                bus = get_communication_bus()
                bus.send_message(
                    sender=env.sender,
                    receiver=self.node_id,
                    message_type=MessageType.TASK_ASSIGN,
                    payload=msg_payload,
                )

            env_resp = MeshEnvelope(
                type=MeshMessageType.AGENT_MESSAGE,
                target=sender,
                payload={
                    "message_type": "task_result",
                    "payload": {
                        "status": "routed",
                        "node_id": self.node_id,
                    },
                },
            )
            await t.send(sender, env_resp)

        @t.on_any
        async def log_all(sender: str, env: MeshEnvelope):
            logger.debug("Mesh message: %s -> %s (%s)", sender, self.node_id, env.type)

    # --- Public API ---

    async def start(self):
        await self.transport.start_server(self.host, self.port)
        await self.transport.start()

        env = MeshEnvelope(
            type=MeshMessageType.REGISTER,
            payload={
                "node_id": self.node_id,
                "host": self.host,
                "port": self.port,
                "roles": self.roles,
                "capabilities": self.capabilities,
            },
        )
        await self.transport.broadcast(env)
        logger.info("Mesh node %s started on ws://%s:%s", self.node_id, self.host, self.port)

    async def connect_peer(self, url: str, peer_id: Optional[str] = None) -> bool:
        ok = await self.transport.connect(url, peer_id)
        if ok:
            env = MeshEnvelope(
                type=MeshMessageType.REGISTER,
                payload={
                    "node_id": self.node_id,
                    "host": self.host,
                    "port": self.port,
                    "roles": self.roles,
                    "capabilities": self.capabilities,
                },
            )
            await self.transport.send(peer_id or url, env)
        return ok

    async def discover_peers(self, role: str = "") -> list[AgentInfo]:
        env = MeshEnvelope(
            type=MeshMessageType.DISCOVER,
            payload={"role": role},
        )
        await self.transport.broadcast(env)
        await asyncio.sleep(1)
        if role:
            return self.registry.discover_by_role(role)
        return self.registry.list_connected()

    def get_proxy(self, node_id: str) -> Optional[RemoteAgentProxy]:
        if node_id not in self._proxies:
            info = self.registry.get(node_id)
            if not info:
                return None
            self._proxies[node_id] = RemoteAgentProxy(
                self.transport, node_id, info.host, info.port
            )
        return self._proxies[node_id]

    async def stop(self):
        env = MeshEnvelope(type=MeshMessageType.DISCONNECT, payload={})
        await self.transport.broadcast(env)
        await self.transport.stop()

    def run_forever(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self.start())
        try:
            self._loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self._loop.run_until_complete(self.stop())
            self._loop.close()
