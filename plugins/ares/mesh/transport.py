from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional, Callable, Awaitable

import websockets.asyncio.server
import websockets.asyncio.client

logger = logging.getLogger(__name__)


HEARTBEAT_INTERVAL = 30.0
HEARTBEAT_TIMEOUT = 90.0
RECONNECT_BASE_DELAY = 1.0
RECONNECT_MAX_DELAY = 30.0
DEFAULT_PORT = 9876


class MeshMessageType(Enum):
    AGENT_MESSAGE = "agent_message"
    REGISTER = "register"
    REGISTER_ACK = "register_ack"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    DISCOVER = "discover"
    DISCOVER_RESPONSE = "discover_response"
    DISCONNECT = "disconnect"
    ERROR = "error"


@dataclass
class MeshEnvelope:
    type: MeshMessageType | str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    target: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    version: int = 1

    def to_json(self) -> str:
        d = asdict(self)
        d["type"] = self.type.value if isinstance(self.type, MeshMessageType) else self.type
        return json.dumps(d)

    @classmethod
    def from_json(cls, raw: str) -> "MeshEnvelope":
        d = json.loads(raw)
        try:
            d["type"] = MeshMessageType(d["type"])
        except ValueError:
            pass
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


MessageHandler = Callable[[str, MeshEnvelope], Awaitable[None]]


class MeshTransport:
    def __init__(
        self,
        node_id: str,
        roles: list[str] | None = None,
        capabilities: dict | None = None,
    ):
        self.node_id = node_id
        self.roles = roles or []
        self.capabilities = capabilities or {}

        self._server: Optional[websockets.asyncio.server.WebSocketServer] = None
        self._connections: dict[str, set[asyncio.Task]] = {}
        self._peers: dict[str, websockets.asyncio.client.WebSocketClientProtocol] = {}
        self._server_peers: dict[str, websockets.asyncio.server.WebSocketServerProtocol] = {}
        self._handlers: dict[str, list[MessageHandler]] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._reconnect_tasks: dict[str, asyncio.Task] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None

    # --- Event handlers ---

    def on(self, msg_type: str | MeshMessageType):
        def decorator(handler: MessageHandler):
            key = msg_type.value if isinstance(msg_type, MeshMessageType) else msg_type
            self._handlers.setdefault(key, []).append(handler)
            return handler
        return decorator

    def on_any(self, handler: MessageHandler):
        self._handlers.setdefault("*", []).append(handler)
        return handler

    async def _dispatch(self, sender: str, envelope: MeshEnvelope):
        key = envelope.type.value if isinstance(envelope.type, MeshMessageType) else envelope.type
        for h in self._handlers.get(key, []):
            try:
                await h(sender, envelope)
            except Exception as e:
                logger.error("Handler error for %s: %s", key, e)
        for h in self._handlers.get("*", []):
            try:
                await h(sender, envelope)
            except Exception as e:
                logger.error("Wildcard handler error: %s", e)

    def _get_or_create_loop(self):
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        return self._loop

    # --- Server ---

    async def start_server(self, host: str = "0.0.0.0", port: int = DEFAULT_PORT):
        self._server = await websockets.asyncio.server.serve(
            self._handle_connection,
            host,
            port,
        )
        logger.info("Mesh server listening on ws://%s:%s", host, port)
        return self._server

    async def _handle_connection(self, websocket):
        remote = websocket.remote_address
        peer_id = f"peer@{remote[0]}:{remote[1]}"
        self._server_peers[peer_id] = websocket
        logger.info("New mesh connection from %s:%s", remote[0], remote[1])
        try:
            async for raw in websocket:
                try:
                    envelope = MeshEnvelope.from_json(raw)
                    await self._dispatch(peer_id, envelope)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON from %s", peer_id)
                except Exception as e:
                    logger.error("Error handling message from %s: %s", peer_id, e)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed: %s", peer_id)
        except Exception as e:
            logger.error("Connection error: %s", e)
        finally:
            self._server_peers.pop(peer_id, None)

    async def stop_server(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    # --- Client ---

    async def connect(self, url: str, target_id: Optional[str] = None) -> bool:
        peer_id = target_id or url
        try:
            ws = await websockets.asyncio.client.connect(url)
            self._peers[peer_id] = ws
            logger.info("Connected to mesh peer: %s", url)

            async def reader():
                try:
                    async for raw in ws:
                        try:
                            envelope = MeshEnvelope.from_json(raw)
                            await self._dispatch(peer_id, envelope)
                        except json.JSONDecodeError:
                            logger.warning("Invalid JSON from %s", peer_id)
                        except Exception as e:
                            logger.error("Error from %s: %s", peer_id, e)
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("Peer connection closed: %s", peer_id)
                except Exception as e:
                    logger.error("Peer reader error: %s", e)
                finally:
                    self._peers.pop(peer_id, None)
                    self._schedule_reconnect(url, peer_id)

            task = asyncio.create_task(reader())
            self._connections.setdefault(peer_id, set()).add(task)
            return True

        except Exception as e:
            logger.warning("Failed to connect to %s: %s", url, e)
            self._schedule_reconnect(url, peer_id)
            return False

    def _schedule_reconnect(self, url: str, peer_id: str, delay: float = RECONNECT_BASE_DELAY):
        if peer_id in self._reconnect_tasks:
            return

        async def reconnect_loop():
            nonlocal delay
            while peer_id not in self._peers and self._running:
                await asyncio.sleep(delay)
                try:
                    ws = await websockets.asyncio.client.connect(url)
                    self._peers[peer_id] = ws
                    logger.info("Reconnected to %s", url)

                    async def reader():
                        try:
                            async for raw in ws:
                                envelope = MeshEnvelope.from_json(raw)
                                await self._dispatch(peer_id, envelope)
                        except Exception:
                            pass
                        finally:
                            self._peers.pop(peer_id, None)
                            delay = RECONNECT_BASE_DELAY

                    task = asyncio.create_task(reader())
                    self._connections.setdefault(peer_id, set()).add(task)
                    return
                except Exception:
                    delay = min(delay * 2, RECONNECT_MAX_DELAY)
                    logger.debug("Reconnect to %s in %.1fs", url, delay)

        self._reconnect_tasks[peer_id] = asyncio.create_task(reconnect_loop())

    async def disconnect(self, peer_id: str):
        ws = self._peers.pop(peer_id, None)
        if ws:
            await ws.close()
        ws = self._server_peers.pop(peer_id, None)
        if ws:
            await ws.close()
        tasks = self._connections.pop(peer_id, set())
        for t in tasks:
            t.cancel()
        rt = self._reconnect_tasks.pop(peer_id, None)
        if rt:
            rt.cancel()

    # --- Send ---

    async def send(self, target: str, envelope: MeshEnvelope):
        envelope.sender = self.node_id
        raw = envelope.to_json()

        ws = self._peers.get(target)
        if ws:
            try:
                await ws.send(raw)
                return
            except Exception as e:
                logger.warning("Send to %s failed: %s", target, e)
                self._peers.pop(target, None)

        ws = self._server_peers.get(target)
        if ws:
            try:
                await ws.send(raw)
                return
            except Exception as e:
                logger.warning("Send to server peer %s failed: %s", target, e)
                self._server_peers.pop(target, None)

        logger.warning("No connection to %s", target)

    async def broadcast(self, envelope: MeshEnvelope, exclude: Optional[list[str]] = None):
        exclude = exclude or []
        envelope.sender = self.node_id
        raw = envelope.to_json()
        for peer_id, ws in list(self._peers.items()):
            if peer_id in exclude:
                continue
            try:
                await ws.send(raw)
            except Exception as e:
                logger.warning("Broadcast to %s failed: %s", peer_id, e)
        for peer_id, ws in list(self._server_peers.items()):
            if peer_id in exclude:
                continue
            try:
                await ws.send(raw)
            except Exception as e:
                logger.warning("Broadcast to server peer %s failed: %s", peer_id, e)

    # --- Heartbeat ---

    async def _heartbeat_loop(self):
        while self._running:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            env = MeshEnvelope(
                type=MeshMessageType.HEARTBEAT,
                sender=self.node_id,
                payload={"roles": self.roles, "capabilities": self.capabilities},
            )
            await self.broadcast(env)

    # --- Lifecycle ---

    async def start(self):
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("Mesh transport started for node %s", self.node_id)

    async def stop(self):
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        for peer_id in list(self._peers.keys()):
            await self.disconnect(peer_id)
        for rt in self._reconnect_tasks.values():
            rt.cancel()
        await self.stop_server()
        logger.info("Mesh transport stopped")

    def run_forever(self, host: str = "0.0.0.0", port: int = DEFAULT_PORT):
        loop = self._get_or_create_loop()
        loop.run_until_complete(self.start_server(host, port))
        loop.run_until_complete(self.start())
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.run_until_complete(self.stop())
            loop.close()
