from __future__ import annotations

import json
import logging
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Callable
from collections import defaultdict

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of inter-agent messages."""
    TASK_ASSIGN = "task_assign"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    FINDING_SHARE = "finding_share"
    REQUEST_HELP = "request_help"
    PROVIDE_HELP = "provide_help"
    STATUS_UPDATE = "status_update"
    COORDINATION = "coordination"
    ESCALATION = "escalation"
    HEARTBEAT = "heartbeat"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class AgentMessage:
    """Message between agents."""
    message_id: str
    sender: str
    receiver: str
    message_type: MessageType
    payload: dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    requires_response: bool = False
    response_to: Optional[str] = None
    ttl: Optional[float] = None  # Time to live in seconds


@dataclass
class MessageChannel:
    """A communication channel between agents."""
    channel_id: str
    participants: list[str]
    message_history: list[AgentMessage] = field(default_factory=list)
    handlers: dict[MessageType, list[Callable]] = field(default_factory=dict)
    max_history: int = 1000


class AgentCommunicationBus:
    """Inter-agent communication bus for message passing and coordination."""

    def __init__(self):
        self._channels: dict[str, MessageChannel] = {}
        self._agent_inboxes: dict[str, list[AgentMessage]] = defaultdict(list)
        self._lock = threading.Lock()
        self._message_counter = 0
        self._handlers: dict[MessageType, list[Callable]] = defaultdict(list)

    def create_channel(self, channel_id: str, participants: list[str]) -> MessageChannel:
        """Create a new communication channel."""
        with self._lock:
            if channel_id in self._channels:
                raise ValueError(f"Channel {channel_id} already exists")

            channel = MessageChannel(
                channel_id=channel_id,
                participants=participants,
            )
            self._channels[channel_id] = channel
            logger.info(f"Channel {channel_id} created with {len(participants)} participants")
            return channel

    def join_channel(self, channel_id: str, agent_id: str) -> None:
        """Add an agent to a channel."""
        with self._lock:
            if channel_id not in self._channels:
                raise ValueError(f"Channel {channel_id} not found")

            channel = self._channels[channel_id]
            if agent_id not in channel.participants:
                channel.participants.append(agent_id)
                logger.info(f"Agent {agent_id} joined channel {channel_id}")

    def leave_channel(self, channel_id: str, agent_id: str) -> None:
        """Remove an agent from a channel."""
        with self._lock:
            if channel_id not in self._channels:
                return

            channel = self._channels[channel_id]
            if agent_id in channel.participants:
                channel.participants.remove(agent_id)
                logger.info(f"Agent {agent_id} left channel {channel_id}")

    def send_message(
        self,
        sender: str,
        receiver: str,
        message_type: MessageType,
        payload: dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        requires_response: bool = False,
        response_to: Optional[str] = None,
        ttl: Optional[float] = None,
    ) -> AgentMessage:
        """Send a message from one agent to another."""
        with self._lock:
            self._message_counter += 1
            message = AgentMessage(
                message_id=f"msg_{self._message_counter}",
                sender=sender,
                receiver=receiver,
                message_type=message_type,
                payload=payload,
                priority=priority,
                requires_response=requires_response,
                response_to=response_to,
                ttl=ttl,
            )

            # Add to receiver's inbox
            self._agent_inboxes[receiver].append(message)

            # Add to relevant channels
            for channel in self._channels.values():
                if sender in channel.participants and receiver in channel.participants:
                    channel.message_history.append(message)
                    if len(channel.message_history) > channel.max_history:
                        channel.message_history = channel.message_history[-channel.max_history:]

            # Trigger handlers
            self._trigger_handlers(message)

            logger.debug(
                f"Message {message.message_id}: {sender} -> {receiver} "
                f"({message_type.value})"
            )
            return message

    def broadcast_message(
        self,
        sender: str,
        message_type: MessageType,
        payload: dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        channel_id: Optional[str] = None,
    ) -> list[AgentMessage]:
        """Broadcast a message to multiple agents."""
        messages = []
        targets = set()

        if channel_id and channel_id in self._channels:
            channel = self._channels[channel_id]
            targets = {p for p in channel.participants if p != sender}
        else:
            # Broadcast to all known agents
            targets = set(self._agent_inboxes.keys()) - {sender}

        for target in targets:
            msg = self.send_message(
                sender=sender,
                receiver=target,
                message_type=message_type,
                payload=payload,
                priority=priority,
            )
            messages.append(msg)

        return messages

    def get_inbox(self, agent_id: str, clear: bool = False) -> list[AgentMessage]:
        """Get messages from an agent's inbox."""
        with self._lock:
            messages = self._agent_inboxes.get(agent_id, []).copy()
            if clear:
                self._agent_inboxes[agent_id] = []
            return messages

    def get_messages_by_type(
        self,
        agent_id: str,
        message_type: MessageType,
        clear: bool = False,
    ) -> list[AgentMessage]:
        """Get messages of a specific type from an agent's inbox."""
        with self._lock:
            messages = [
                m for m in self._agent_inboxes.get(agent_id, [])
                if m.message_type == message_type
            ]
            if clear:
                self._agent_inboxes[agent_id] = [
                    m for m in self._agent_inboxes.get(agent_id, [])
                    if m.message_type != message_type
                ]
            return messages

    def get_channel_history(
        self,
        channel_id: str,
        limit: Optional[int] = None,
    ) -> list[AgentMessage]:
        """Get message history for a channel."""
        if channel_id not in self._channels:
            return []

        channel = self._channels[channel_id]
        if limit:
            return channel.message_history[-limit:]
        return channel.message_history.copy()

    def register_handler(
        self,
        message_type: MessageType,
        handler: Callable[[AgentMessage], None],
    ) -> None:
        """Register a handler for a message type."""
        self._handlers[message_type].append(handler)
        logger.debug(f"Handler registered for {message_type.value}")

    def _trigger_handlers(self, message: AgentMessage) -> None:
        """Trigger handlers for a message."""
        handlers = self._handlers.get(message.message_type, [])
        for handler in handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Handler error for {message.message_type.value}: {e}")

    def cleanup_expired_messages(self) -> int:
        """Remove expired messages from all inboxes."""
        now = time.time()
        removed = 0

        with self._lock:
            for agent_id in list(self._agent_inboxes.keys()):
                inbox = self._agent_inboxes[agent_id]
                valid_messages = []
                for msg in inbox:
                    if msg.ttl is None or (now - msg.timestamp) < msg.ttl:
                        valid_messages.append(msg)
                    else:
                        removed += 1
                self._agent_inboxes[agent_id] = valid_messages

        return removed

    def get_stats(self) -> dict[str, Any]:
        """Get communication statistics."""
        with self._lock:
            total_messages = sum(
                len(inbox) for inbox in self._agent_inboxes.values()
            )
            return {
                "channels": len(self._channels),
                "agents": len(self._agent_inboxes),
                "total_messages": total_messages,
                "total_sent": self._message_counter,
            }


class CoordinationManager:
    """Higher-level coordination between agents."""

    def __init__(self, communication_bus: AgentCommunicationBus):
        self._bus = communication_bus
        self._tasks: dict[str, dict[str, Any]] = {}
        self._dependencies: dict[str, list[str]] = defaultdict(list)
        self._lock = threading.Lock()

    def assign_task(
        self,
        task_id: str,
        assignee: str,
        task_data: dict[str, Any],
        dependencies: Optional[list[str]] = None,
    ) -> AgentMessage:
        """Assign a task to an agent."""
        with self._lock:
            self._tasks[task_id] = {
                "assignee": assignee,
                "data": task_data,
                "status": "assigned",
                "created_at": time.time(),
            }
            if dependencies:
                self._dependencies[task_id] = dependencies

        return self._bus.send_message(
            sender="orchestrator",
            receiver=assignee,
            message_type=MessageType.TASK_ASSIGN,
            payload={"task_id": task_id, **task_data},
            priority=MessagePriority.HIGH,
            requires_response=True,
        )

    def complete_task(
        self,
        task_id: str,
        assignee: str,
        results: dict[str, Any],
    ) -> list[AgentMessage]:
        """Mark a task as complete and notify dependents."""
        messages = []

        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["status"] = "completed"
                self._tasks[task_id]["results"] = results

        # Notify orchestrator
        msg = self._bus.send_message(
            sender=assignee,
            receiver="orchestrator",
            message_type=MessageType.TASK_COMPLETE,
            payload={"task_id": task_id, "results": results},
        )
        messages.append(msg)

        # Check for dependent tasks
        with self._lock:
            for dependent_id, deps in self._dependencies.items():
                if task_id in deps:
                    deps.remove(task_id)
                    if not deps:
                        # All dependencies met, notify assignee
                        dependent_task = self._tasks.get(dependent_id)
                        if dependent_task:
                            notify_msg = self._bus.send_message(
                                sender="orchestrator",
                                receiver=dependent_task["assignee"],
                                message_type=MessageType.TASK_ASSIGN,
                                payload={
                                    "task_id": dependent_id,
                                    "reason": "dependencies_met",
                                    **dependent_task["data"],
                                },
                            )
                            messages.append(notify_msg)

        return messages

    def get_task_status(self, task_id: str) -> Optional[dict[str, Any]]:
        """Get the status of a task."""
        return self._tasks.get(task_id)

    def get_pending_tasks(self) -> list[dict[str, Any]]:
        """Get all pending tasks."""
        with self._lock:
            return [
                {"task_id": tid, **task}
                for tid, task in self._tasks.items()
                if task["status"] == "assigned"
            ]


# Global instances
_communication_bus: Optional[AgentCommunicationBus] = None
_coordination_manager: Optional[CoordinationManager] = None


def get_communication_bus() -> AgentCommunicationBus:
    """Get the global communication bus instance."""
    global _communication_bus
    if _communication_bus is None:
        _communication_bus = AgentCommunicationBus()
    return _communication_bus


def get_coordination_manager() -> CoordinationManager:
    """Get the global coordination manager instance."""
    global _coordination_manager
    if _coordination_manager is None:
        _coordination_manager = CoordinationManager(get_communication_bus())
    return _coordination_manager
