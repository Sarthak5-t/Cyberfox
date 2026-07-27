from __future__ import annotations

import json
import logging
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent lifecycle states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CHECKPOINTED = "checkpointed"


@dataclass
class AgentContext:
    """Context passed to an agent during execution."""
    agent_id: str
    role: str
    goal: str
    context: str
    engagement_id: int
    target: str
    toolsets: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_agent: Optional[str] = None
    child_agents: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class AgentCheckpoint:
    """Checkpoint data for an agent."""
    agent_id: str
    state: AgentState
    context: AgentContext
    progress: dict[str, Any]
    findings: list[dict[str, Any]]
    timestamp: float
    reason: str = ""


class AgentLifecycleManager:
    """Manages agent lifecycle: start, stop, pause, resume, checkpoint."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self._agents: dict[str, AgentContext] = {}
        self._states: dict[str, AgentState] = {}
        self._checkpoints: dict[str, list[AgentCheckpoint]] = {}
        self._lock = threading.RLock()
        self._storage_dir = storage_dir or Path.home() / ".cyberfox" / "ares" / "checkpoints"
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def create_agent(
        self,
        agent_id: str,
        role: str,
        goal: str,
        context: str,
        engagement_id: int,
        target: str,
        toolsets: list[str],
        parent_agent: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AgentContext:
        """Create a new agent and initialize its lifecycle."""
        with self._lock:
            if agent_id in self._agents:
                raise ValueError(f"Agent {agent_id} already exists")

            agent_ctx = AgentContext(
                agent_id=agent_id,
                role=role,
                goal=goal,
                context=context,
                engagement_id=engagement_id,
                target=target,
                toolsets=toolsets,
                parent_agent=parent_agent,
                metadata=metadata or {},
            )

            self._agents[agent_id] = agent_ctx
            self._states[agent_id] = AgentState.IDLE
            self._checkpoints[agent_id] = []

            # Register with parent if specified
            if parent_agent and parent_agent in self._agents:
                self._agents[parent_agent].child_agents.append(agent_id)

            logger.info(f"Agent {agent_id} created with role {role}")
            return agent_ctx

    def start_agent(self, agent_id: str) -> AgentState:
        """Start or resume an agent."""
        with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent {agent_id} not found")

            current_state = self._states[agent_id]
            if current_state == AgentState.RUNNING:
                logger.warning(f"Agent {agent_id} is already running")
                return current_state

            if current_state in (AgentState.IDLE, AgentState.PAUSED, AgentState.CHECKPOINTED):
                self._states[agent_id] = AgentState.RUNNING
                self._agents[agent_id].updated_at = time.time()
                logger.info(f"Agent {agent_id} started")
                return self._states[agent_id]

            raise ValueError(f"Cannot start agent in state {current_state}")

    def pause_agent(self, agent_id: str) -> AgentState:
        """Pause a running agent."""
        with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent {agent_id} not found")

            if self._states[agent_id] != AgentState.RUNNING:
                raise ValueError(f"Cannot pause agent in state {self._states[agent_id]}")

            self._states[agent_id] = AgentState.PAUSED
            self._agents[agent_id].updated_at = time.time()
            logger.info(f"Agent {agent_id} paused")
            return self._states[agent_id]

    def stop_agent(self, agent_id: str, reason: str = "stopped") -> AgentState:
        """Stop an agent permanently."""
        with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent {agent_id} not found")

            self._states[agent_id] = AgentState.COMPLETED
            self._agents[agent_id].updated_at = time.time()
            logger.info(f"Agent {agent_id} stopped: {reason}")
            return self._states[agent_id]

    def fail_agent(self, agent_id: str, reason: str = "failed") -> AgentState:
        """Mark an agent as failed."""
        with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent {agent_id} not found")

            self._states[agent_id] = AgentState.FAILED
            self._agents[agent_id].updated_at = time.time()
            logger.error(f"Agent {agent_id} failed: {reason}")
            return self._states[agent_id]

    def checkpoint_agent(
        self,
        agent_id: str,
        progress: dict[str, Any],
        findings: list[dict[str, Any]],
        reason: str = "checkpoint",
    ) -> AgentCheckpoint:
        """Create a checkpoint for an agent."""
        with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent {agent_id} not found")

            checkpoint = AgentCheckpoint(
                agent_id=agent_id,
                state=self._states[agent_id],
                context=self._agents[agent_id],
                progress=progress,
                findings=findings,
                timestamp=time.time(),
                reason=reason,
            )

            if agent_id not in self._checkpoints:
                self._checkpoints[agent_id] = []
            self._checkpoints[agent_id].append(checkpoint)

            # Save to disk
            self._save_checkpoint(checkpoint)

            logger.info(f"Agent {agent_id} checkpointed: {reason}")
            return checkpoint

    def restore_checkpoint(self, agent_id: str, checkpoint_idx: int = -1) -> AgentContext:
        """Restore an agent from a checkpoint."""
        with self._lock:
            if agent_id not in self._checkpoints:
                raise ValueError(f"No checkpoints for agent {agent_id}")

            checkpoints = self._checkpoints[agent_id]
            if not checkpoints:
                raise ValueError(f"No checkpoints for agent {agent_id}")

            checkpoint = checkpoints[checkpoint_idx]
            self._agents[agent_id] = checkpoint.context
            self._states[agent_id] = AgentState.CHECKPOINTED
            logger.info(f"Agent {agent_id} restored from checkpoint {checkpoint.timestamp}")
            return self._agents[agent_id]

    def get_agent(self, agent_id: str) -> Optional[AgentContext]:
        """Get agent context."""
        return self._agents.get(agent_id)

    def get_state(self, agent_id: str) -> Optional[AgentState]:
        """Get agent state."""
        return self._states.get(agent_id)

    def list_agents(self, state: Optional[AgentState] = None) -> list[AgentContext]:
        """List all agents, optionally filtered by state."""
        with self._lock:
            agents = []
            for agent_id, agent_ctx in self._agents.items():
                if state is None or self._states.get(agent_id) == state:
                    agents.append(agent_ctx)
            return agents

    def get_agent_tree(self, root_agent_id: str) -> dict[str, Any]:
        """Get the agent hierarchy tree."""
        with self._lock:
            if root_agent_id not in self._agents:
                return {}

            root = self._agents[root_agent_id]
            tree = {
                "agent_id": root.agent_id,
                "role": root.role,
                "state": self._states.get(root.agent_id, AgentState.IDLE).value,
                "children": [],
            }

            for child_id in root.child_agents:
                child_tree = self.get_agent_tree(child_id)
                if child_tree:
                    tree["children"].append(child_tree)

            return tree

    def _save_checkpoint(self, checkpoint: AgentCheckpoint) -> None:
        """Save checkpoint to disk."""
        try:
            checkpoint_file = (
                self._storage_dir
                / f"{checkpoint.agent_id}_{int(checkpoint.timestamp)}.json"
            )
            data = {
                "agent_id": checkpoint.agent_id,
                "state": checkpoint.state.value,
                "progress": checkpoint.progress,
                "findings": checkpoint.findings,
                "timestamp": checkpoint.timestamp,
                "reason": checkpoint.reason,
                "context": {
                    "role": checkpoint.context.role,
                    "goal": checkpoint.context.goal,
                    "context": checkpoint.context.context,
                    "engagement_id": checkpoint.context.engagement_id,
                    "target": checkpoint.context.target,
                    "toolsets": checkpoint.context.toolsets,
                    "metadata": checkpoint.context.metadata,
                },
            }
            checkpoint_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Checkpoint saved to {checkpoint_file}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")


# Global instance
_lifecycle_manager: Optional[AgentLifecycleManager] = None


def get_lifecycle_manager() -> AgentLifecycleManager:
    """Get the global lifecycle manager instance."""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = AgentLifecycleManager()
    return _lifecycle_manager
