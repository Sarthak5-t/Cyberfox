from __future__ import annotations

import json
import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CheckpointData:
    """Checkpoint data for an agent."""
    agent_id: str
    engagement_id: int
    state: dict[str, Any]
    progress: dict[str, Any]
    findings: list[dict[str, Any]]
    timestamp: float
    reason: str = ""
    parent_checkpoint: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentCheckpointManager:
    """Manages agent checkpoints for recovery and state transfer."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self._checkpoints: dict[str, list[CheckpointData]] = {}
        self._lock = threading.Lock()
        self._storage_dir = storage_dir or Path.home() / ".cyberfox" / "ares" / "checkpoints"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._max_checkpoints_per_agent = 50

    def save_checkpoint(
        self,
        agent_id: str,
        engagement_id: int,
        state: dict[str, Any],
        progress: dict[str, Any],
        findings: list[dict[str, Any]],
        reason: str = "",
        parent_checkpoint: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> CheckpointData:
        """Save a checkpoint for an agent."""
        checkpoint = CheckpointData(
            agent_id=agent_id,
            engagement_id=engagement_id,
            state=state,
            progress=progress,
            findings=findings,
            timestamp=time.time(),
            reason=reason,
            parent_checkpoint=parent_checkpoint,
            metadata=metadata or {},
        )

        with self._lock:
            if agent_id not in self._checkpoints:
                self._checkpoints[agent_id] = []

            self._checkpoints[agent_id].append(checkpoint)

            # Trim old checkpoints
            if len(self._checkpoints[agent_id]) > self._max_checkpoints_per_agent:
                self._checkpoints[agent_id] = self._checkpoints[agent_id][
                    -self._max_checkpoints_per_agent:
                ]

        # Save to disk
        self._persist_checkpoint(checkpoint)

        logger.info(
            f"Checkpoint saved for agent {agent_id}: {reason or 'manual'}"
        )
        return checkpoint

    def load_checkpoint(
        self,
        agent_id: str,
        checkpoint_index: int = -1,
    ) -> Optional[CheckpointData]:
        """Load a checkpoint for an agent."""
        with self._lock:
            if agent_id not in self._checkpoints:
                # Try loading from disk
                self._load_checkpoints_from_disk(agent_id)

            if agent_id not in self._checkpoints:
                return None

            checkpoints = self._checkpoints[agent_id]
            if not checkpoints:
                return None

            return checkpoints[checkpoint_index]

    def get_latest_checkpoint(self, agent_id: str) -> Optional[CheckpointData]:
        """Get the latest checkpoint for an agent."""
        return self.load_checkpoint(agent_id, checkpoint_index=-1)

    def get_checkpoints(
        self,
        agent_id: str,
        limit: Optional[int] = None,
    ) -> list[CheckpointData]:
        """Get all checkpoints for an agent."""
        with self._lock:
            if agent_id not in self._checkpoints:
                self._load_checkpoints_from_disk(agent_id)

            if agent_id not in self._checkpoints:
                return []

            checkpoints = self._checkpoints[agent_id]
            if limit:
                return checkpoints[-limit:]
            return checkpoints.copy()

    def get_checkpoints_by_engagement(
        self,
        engagement_id: int,
    ) -> dict[str, list[CheckpointData]]:
        """Get all checkpoints for an engagement."""
        result: dict[str, list[CheckpointData]] = {}

        with self._lock:
            for agent_id, checkpoints in self._checkpoints.items():
                eng_checkpoints = [
                    cp for cp in checkpoints
                    if cp.engagement_id == engagement_id
                ]
                if eng_checkpoints:
                    result[agent_id] = eng_checkpoints

        return result

    def delete_checkpoint(self, agent_id: str, checkpoint_index: int) -> bool:
        """Delete a specific checkpoint."""
        with self._lock:
            if agent_id not in self._checkpoints:
                return False

            checkpoints = self._checkpoints[agent_id]
            if abs(checkpoint_index) > len(checkpoints):
                return False

            deleted = checkpoints.pop(checkpoint_index)
            logger.info(f"Checkpoint deleted for agent {agent_id}")
            return True

    def clear_checkpoints(self, agent_id: str) -> int:
        """Clear all checkpoints for an agent."""
        with self._lock:
            if agent_id not in self._checkpoints:
                return 0

            count = len(self._checkpoints[agent_id])
            self._checkpoints[agent_id] = []
            logger.info(f"Cleared {count} checkpoints for agent {agent_id}")
            return count

    def transfer_state(
        self,
        source_agent_id: str,
        target_agent_id: str,
        checkpoint_index: int = -1,
    ) -> Optional[CheckpointData]:
        """Transfer state from one agent to another via checkpoint."""
        source_checkpoint = self.load_checkpoint(source_agent_id, checkpoint_index)
        if not source_checkpoint:
            return None

        # Create new checkpoint for target agent
        new_checkpoint = self.save_checkpoint(
            agent_id=target_agent_id,
            engagement_id=source_checkpoint.engagement_id,
            state=source_checkpoint.state,
            progress=source_checkpoint.progress,
            findings=source_checkpoint.findings,
            reason=f"transfer from {source_agent_id}",
            metadata={
                **source_checkpoint.metadata,
                "transferred_from": source_agent_id,
                "original_timestamp": source_checkpoint.timestamp,
            },
        )

        return new_checkpoint

    def _persist_checkpoint(self, checkpoint: CheckpointData) -> None:
        """Persist checkpoint to disk."""
        try:
            agent_dir = self._storage_dir / checkpoint.agent_id
            agent_dir.mkdir(exist_ok=True)

            checkpoint_file = agent_dir / f"{int(checkpoint.timestamp)}.json"
            data = {
                "agent_id": checkpoint.agent_id,
                "engagement_id": checkpoint.engagement_id,
                "state": checkpoint.state,
                "progress": checkpoint.progress,
                "findings": checkpoint.findings,
                "timestamp": checkpoint.timestamp,
                "reason": checkpoint.reason,
                "parent_checkpoint": checkpoint.parent_checkpoint,
                "metadata": checkpoint.metadata,
            }
            checkpoint_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Checkpoint persisted to {checkpoint_file}")
        except Exception as e:
            logger.error(f"Failed to persist checkpoint: {e}")

    def _load_checkpoints_from_disk(self, agent_id: str) -> None:
        """Load checkpoints from disk for an agent."""
        try:
            agent_dir = self._storage_dir / agent_id
            if not agent_dir.exists():
                return

            checkpoints = []
            for checkpoint_file in sorted(agent_dir.glob("*.json")):
                try:
                    data = json.loads(checkpoint_file.read_text())
                    checkpoint = CheckpointData(
                        agent_id=data["agent_id"],
                        engagement_id=data["engagement_id"],
                        state=data["state"],
                        progress=data["progress"],
                        findings=data["findings"],
                        timestamp=data["timestamp"],
                        reason=data.get("reason", ""),
                        parent_checkpoint=data.get("parent_checkpoint"),
                        metadata=data.get("metadata", {}),
                    )
                    checkpoints.append(checkpoint)
                except Exception as e:
                    logger.warning(f"Failed to load checkpoint {checkpoint_file}: {e}")

            with self._lock:
                self._checkpoints[agent_id] = checkpoints

            logger.info(f"Loaded {len(checkpoints)} checkpoints for agent {agent_id}")
        except Exception as e:
            logger.error(f"Failed to load checkpoints from disk: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get checkpoint statistics."""
        with self._lock:
            total_checkpoints = sum(
                len(checkpoints) for checkpoints in self._checkpoints.values()
            )
            return {
                "agents": len(self._checkpoints),
                "total_checkpoints": total_checkpoints,
                "storage_dir": str(self._storage_dir),
            }


# Global instance
_checkpoint_manager: Optional[AgentCheckpointManager] = None


def get_checkpoint_manager() -> AgentCheckpointManager:
    """Get the global checkpoint manager instance."""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = AgentCheckpointManager()
    return _checkpoint_manager
