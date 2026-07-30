from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from typing import Any, Optional

from plugins.ares.mesh.agent import MeshNode, RemoteAgentProxy
from plugins.ares.mesh.registry import AgentInfo, get_registry
from plugins.ares.mesh.discovery import (
    ConfigDiscoveryProvider,
    BroadcastDiscoveryProvider,
    MeshPeerConfig,
)

logger = logging.getLogger(__name__)


class MeshClient:
    def __init__(self):
        self._node: Optional[MeshNode] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._config_discovery = ConfigDiscoveryProvider()
        self._broadcast_discovery = BroadcastDiscoveryProvider()
        self._running = False

    @property
    def is_connected(self) -> bool:
        return self._node is not None and self._running

    @property
    def node_id(self) -> str:
        return self._node.node_id if self._node else ""

    def start(
        self,
        node_id: str,
        roles: list[str] | None = None,
        capabilities: dict | None = None,
        host: str = "0.0.0.0",
        port: int = 9876,
        peers: list[str] | None = None,
        auth_secret: str = "",
        use_broadcast: bool = True,
    ) -> bool:
        if self._running:
            logger.warning("Mesh client already running")
            return False

        self._node = MeshNode(
            node_id=node_id,
            roles=roles or [],
            capabilities=capabilities or {},
            host=host,
            port=port,
            auth_secret=auth_secret,
        )
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._running = True

        def run():
            try:
                self._loop.run_until_complete(self._node.start())
            except Exception as e:
                logger.error("Mesh client start error: %s", e)
                self._running = False
                return

            if use_broadcast:
                self._broadcast_discovery.start_listener()

            peer_urls = list(peers or [])
            config_peers = self._config_discovery.discover()
            peer_urls.extend(p.url for p in config_peers)

            for url in set(peer_urls):
                try:
                    self._loop.run_until_complete(
                        self._node.connect_peer(url)
                    )
                except Exception as e:
                    logger.warning("Failed to connect to peer %s: %s", url, e)

            try:
                self._loop.run_until_complete(self._auto_discover())
            except Exception as e:
                logger.warning("Auto-discover error: %s", e)

            try:
                self._loop.run_forever()
            except Exception as e:
                logger.error("Mesh event loop error: %s", e)
            finally:
                self._running = False

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        time.sleep(1)
        return True

    async def _auto_discover(self):
        for _ in range(3):
            await self._node.discover_peers()
            await asyncio.sleep(2)

    def stop(self):
        self._running = False
        self._broadcast_discovery.stop_listener()
        if self._loop and not self._loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(
                    self._node.stop(), self._loop
                )
            except Exception:
                pass
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Mesh client stopped")

    def connect_peer(self, url: str) -> bool:
        if not self._loop or not self._running:
            return False
        future = asyncio.run_coroutine_threadsafe(
            self._node.connect_peer(url), self._loop
        )
        try:
            return future.result(timeout=10)
        except Exception as e:
            logger.error("Failed to connect peer: %s", e)
            return False

    def discover(self, role: str = "") -> list[AgentInfo]:
        if not self._loop or not self._running:
            return []
        future = asyncio.run_coroutine_threadsafe(
            self._node.discover_peers(role), self._loop
        )
        try:
            return future.result(timeout=10)
        except Exception as e:
            logger.error("Discover error: %s", e)
            return []

    def list_peers(self) -> list[dict[str, Any]]:
        agents = get_registry().list_connected()
        return [
            {
                "node_id": a.node_id,
                "host": a.host,
                "port": a.port,
                "roles": a.roles,
                "capabilities": a.capabilities,
                "last_seen": a.last_seen,
                "uri": a.uri,
            }
            for a in agents
        ]

    def delegate_remote(
        self,
        role: str,
        goal: str,
        context: str = "",
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        if not self._node:
            return {"success": False, "error": "Mesh not connected"}

        agents = get_registry().discover_by_role(role)
        if not agents:
            return {"success": False, "error": f"No agent found with role '{role}'"}

        target = agents[0]
        proxy = self._node.get_proxy(target.node_id)
        if not proxy:
            return {"success": False, "error": f"Cannot create proxy for {target.node_id}"}

        if not self._loop:
            return {"success": False, "error": "No event loop"}

        future = asyncio.run_coroutine_threadsafe(
            proxy.send_task(
                task_type="task_assign",
                payload={
                    "task_id": f"remote_{int(time.time())}",
                    "goal": goal,
                    "context": context,
                    "role": role,
                },
                timeout=timeout,
            ),
            self._loop,
        )
        try:
            result = future.result(timeout=timeout + 5)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_peer_config(self, url: str, node_id: str = "", roles: list[str] | None = None):
        self._config_discovery.add_peer(url, node_id, roles)

    def remove_peer_config(self, url: str):
        self._config_discovery.remove_peer(url)

    def get_stats(self) -> dict[str, Any]:
        agents = self.list_peers()
        registry_stats = get_registry().get_stats()
        return {
            "connected": self._running,
            "node_id": self.node_id if self._node else "",
            "peers": len(agents),
            "peer_list": agents,
            "registry": registry_stats,
        }


_client: Optional[MeshClient] = None
_client_lock = threading.Lock()


def get_mesh_client() -> MeshClient:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = MeshClient()
    return _client
