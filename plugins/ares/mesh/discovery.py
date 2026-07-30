from __future__ import annotations

import json
import logging
import os
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from plugins.ares.mesh.transport import DEFAULT_PORT

logger = logging.getLogger(__name__)


@dataclass
class MeshPeerConfig:
    url: str
    node_id: str = ""
    roles: list[str] = field(default_factory=list)


class DiscoveryProvider:
    def discover(self) -> list[MeshPeerConfig]:
        raise NotImplementedError


class ConfigDiscoveryProvider(DiscoveryProvider):
    def __init__(self, config_path: Optional[str] = None):
        self._config_path = config_path or os.path.expanduser(
            "~/.cyberfox/ares/mesh_peers.json"
        )
        self._lock = threading.Lock()
        self._peers: list[MeshPeerConfig] = []
        self._load()

    def _load(self):
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path) as f:
                    data = json.load(f)
                self._peers = [MeshPeerConfig(**p) for p in data.get("peers", [])]
                logger.info("Loaded %d mesh peers from config", len(self._peers))
        except Exception as e:
            logger.warning("Failed to load mesh peers config: %s", e)

    def add_peer(self, url: str, node_id: str = "", roles: list[str] | None = None):
        with self._lock:
            self._peers.append(MeshPeerConfig(url=url, node_id=node_id, roles=roles or []))
            self._save()

    def remove_peer(self, url: str):
        with self._lock:
            self._peers = [p for p in self._peers if p.url != url]
            self._save()

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, "w") as f:
                json.dump({"peers": [{"url": p.url, "node_id": p.node_id, "roles": p.roles}
                                     for p in self._peers]}, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save mesh peers config: %s", e)

    def discover(self) -> list[MeshPeerConfig]:
        with self._lock:
            return list(self._peers)


class BroadcastDiscoveryProvider(DiscoveryProvider):
    DISCOVERY_PORT = 9877
    DISCOVERY_MSG = b"ARES_MESH_DISCOVER"
    RESPONSE_MSG = b"ARES_MESH_HERE"

    def __init__(self, listen_port: int = DEFAULT_PORT):
        self._listen_port = listen_port
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._discovered: list[MeshPeerConfig] = []
        self._lock = threading.Lock()

    def discover(self) -> list[MeshPeerConfig]:
        self._broadcast_discover()
        time.sleep(2)
        with self._lock:
            return list(self._discovered)

    def start_listener(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("Broadcast discovery listener started on UDP %d", self.DISCOVERY_PORT)

    def stop_listener(self):
        self._running = False

    def _broadcast_discover(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(1)
            sock.sendto(self.DISCOVERY_MSG, ("255.255.255.255", self.DISCOVERY_PORT))
            sock.close()
        except Exception as e:
            logger.warning("Broadcast discovery failed: %s", e)

    def _listen_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1)
        try:
            sock.bind(("0.0.0.0", self.DISCOVERY_PORT))
        except Exception as e:
            logger.warning("Cannot bind discovery port %d: %s", self.DISCOVERY_PORT, e)
            return

        while self._running:
            try:
                data, addr = sock.recvfrom(1024)
                if data == self.DISCOVERY_MSG:
                    resp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    resp_sock.sendto(
                        f"{self.RESPONSE_MSG.decode()}:{self._listen_port}".encode(),
                        addr,
                    )
                    resp_sock.close()
                elif data.startswith(self.RESPONSE_MSG):
                    port_str = data.decode().split(":")[1] if ":" in data.decode() else str(DEFAULT_PORT)
                    url = f"ws://{addr[0]}:{port_str}"
                    with self._lock:
                        if not any(p.url == url for p in self._discovered):
                            self._discovered.append(MeshPeerConfig(url=url))
                            logger.info("Discovered mesh peer: %s", url)
            except socket.timeout:
                pass
            except Exception as e:
                logger.warning("Discovery listener error: %s", e)
        sock.close()
