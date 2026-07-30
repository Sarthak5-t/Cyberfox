from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

STALE_TIMEOUT = 120.0


@dataclass
class AgentInfo:
    node_id: str
    host: str = ""
    port: int = 0
    roles: list[str] = field(default_factory=list)
    capabilities: dict[str, Any] = field(default_factory=dict)
    last_seen: float = field(default_factory=time.time)
    connected: bool = True

    @property
    def is_stale(self) -> bool:
        return time.time() - self.last_seen > STALE_TIMEOUT

    @property
    def uri(self) -> str:
        return f"ws://{self.host}:{self.port}" if self.host and self.port else ""


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, AgentInfo] = {}
        self._local_node_id: str = ""
        self._lock = threading.Lock()

    def set_local(self, node_id: str):
        self._local_node_id = node_id

    def register(self, info: AgentInfo) -> None:
        with self._lock:
            existing = self._agents.get(info.node_id)
            if existing:
                existing.host = info.host or existing.host
                existing.port = info.port or existing.port
                existing.roles = info.roles or existing.roles
                existing.capabilities = info.capabilities or existing.capabilities
                existing.last_seen = time.time()
                existing.connected = True
            else:
                self._agents[info.node_id] = info
            logger.info("Registered agent: %s (roles: %s)", info.node_id, info.roles)

    def unregister(self, node_id: str) -> None:
        with self._lock:
            self._agents.pop(node_id, None)
        logger.info("Unregistered agent: %s", node_id)

    def mark_stale(self, node_id: str) -> None:
        with self._lock:
            agent = self._agents.get(node_id)
            if agent:
                agent.connected = False

    def heartbeat(self, node_id: str) -> None:
        with self._lock:
            agent = self._agents.get(node_id)
            if agent:
                agent.last_seen = time.time()
                agent.connected = True

    def get(self, node_id: str) -> Optional[AgentInfo]:
        with self._lock:
            return self._agents.get(node_id)

    def discover_by_role(self, role: str) -> list[AgentInfo]:
        with self._lock:
            return [
                a for a in self._agents.values()
                if role in a.roles and a.connected and not a.is_stale
            ]

    def discover_by_capability(self, key: str, value: Any = None) -> list[AgentInfo]:
        with self._lock:
            results = []
            for a in self._agents.values():
                if not a.connected or a.is_stale:
                    continue
                cap_val = a.capabilities.get(key)
                if value is None and cap_val is not None:
                    results.append(a)
                elif cap_val == value:
                    results.append(a)
            return results

    def list_agents(self) -> list[AgentInfo]:
        with self._lock:
            return list(self._agents.values())

    def list_connected(self) -> list[AgentInfo]:
        with self._lock:
            return [a for a in self._agents.values() if a.connected and not a.is_stale]

    def cleanup_stale(self) -> int:
        now = time.time()
        removed = 0
        with self._lock:
            stale = [nid for nid, a in self._agents.items()
                     if a.is_stale and a.node_id != self._local_node_id]
            for nid in stale:
                del self._agents[nid]
                removed += 1
        if removed:
            logger.info("Cleaned up %d stale agents", removed)
        return removed

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            connected = sum(1 for a in self._agents.values() if a.connected and not a.is_stale)
            return {
                "total": len(self._agents),
                "connected": connected,
                "stale": len(self._agents) - connected,
                "roles": list({r for a in self._agents.values() for r in a.roles}),
            }


_registry: Optional[AgentRegistry] = None
_registry_lock = threading.Lock()


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = AgentRegistry()
    return _registry
