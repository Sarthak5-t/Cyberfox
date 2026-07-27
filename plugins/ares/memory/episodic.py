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
class Episode:
    """A single episodic memory entry."""
    episode_id: str
    engagement_id: int
    agent_id: str
    event_type: str
    description: str
    data: dict[str, Any]
    timestamp: float
    duration: Optional[float] = None
    outcome: str = "pending"
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class EpisodicMemory:
    """Memory for past engagement experiences and events."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self._episodes: dict[str, list[Episode]] = {}
        self._lock = threading.Lock()
        self._storage_dir = storage_dir or Path.home() / ".cyberfox" / "ares" / "episodes"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._episode_counter = 0

    def record_episode(
        self,
        engagement_id: int,
        agent_id: str,
        event_type: str,
        description: str,
        data: dict[str, Any],
        duration: Optional[float] = None,
        outcome: str = "pending",
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Episode:
        """Record a new episode."""
        with self._lock:
            self._episode_counter += 1
            episode = Episode(
                episode_id=f"ep_{engagement_id}_{self._episode_counter}",
                engagement_id=engagement_id,
                agent_id=agent_id,
                event_type=event_type,
                description=description,
                data=data,
                timestamp=time.time(),
                duration=duration,
                outcome=outcome,
                tags=tags or [],
                metadata=metadata or {},
            )

            if engagement_id not in self._episodes:
                self._episodes[engagement_id] = []
            self._episodes[engagement_id].append(episode)

            # Persist to disk
            self._persist_episode(episode)

            logger.info(f"Episode recorded: {episode.episode_id}")
            return episode

    def get_episodes(
        self,
        engagement_id: int,
        agent_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[Episode]:
        """Get episodes for an engagement."""
        with self._lock:
            if engagement_id not in self._episodes:
                return []

            episodes = self._episodes[engagement_id]

            # Apply filters
            if agent_id:
                episodes = [e for e in episodes if e.agent_id == agent_id]
            if event_type:
                episodes = [e for e in episodes if e.event_type == event_type]

            # Apply limit
            if limit:
                episodes = episodes[-limit:]

            return episodes

    def get_successful_episodes(
        self,
        engagement_id: int,
        event_type: Optional[str] = None,
    ) -> list[Episode]:
        """Get episodes with successful outcomes."""
        episodes = self.get_episodes(engagement_id, event_type=event_type)
        return [e for e in episodes if e.outcome == "success"]

    def get_failed_episodes(
        self,
        engagement_id: int,
        event_type: Optional[str] = None,
    ) -> list[Episode]:
        """Get episodes with failed outcomes."""
        episodes = self.get_episodes(engagement_id, event_type=event_type)
        return [e for e in episodes if e.outcome == "failure"]

    def search_episodes(
        self,
        query: str,
        engagement_id: Optional[int] = None,
    ) -> list[Episode]:
        """Search episodes by description or tags."""
        with self._lock:
            results = []
            for eng_id, episodes in self._episodes.items():
                if engagement_id and eng_id != engagement_id:
                    continue
                for episode in episodes:
                    if (query.lower() in episode.description.lower() or
                        any(query.lower() in tag.lower() for tag in episode.tags)):
                        results.append(episode)
            return results

    def get_patterns(
        self,
        engagement_id: int,
        event_type: str,
    ) -> dict[str, Any]:
        """Analyze patterns in episodes."""
        episodes = self.get_episodes(engagement_id, event_type=event_type)
        if not episodes:
            return {}

        patterns = {
            "total_episodes": len(episodes),
            "success_rate": sum(1 for e in episodes if e.outcome == "success") / len(episodes),
            "failure_rate": sum(1 for e in episodes if e.outcome == "failure") / len(episodes),
            "avg_duration": sum(e.duration or 0 for e in episodes) / len(episodes),
            "common_tags": self._get_common_tags(episodes),
            "time_distribution": self._get_time_distribution(episodes),
        }

        return patterns

    def _get_common_tags(self, episodes: list[Episode]) -> list[tuple[str, int]]:
        """Get most common tags across episodes."""
        tag_counts: dict[str, int] = {}
        for episode in episodes:
            for tag in episode.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    def _get_time_distribution(self, episodes: list[Episode]) -> dict[str, int]:
        """Get distribution of episodes by hour of day."""
        distribution: dict[str, int] = {}
        for episode in episodes:
            hour = time.strftime("%H", time.localtime(episode.timestamp))
            distribution[hour] = distribution.get(hour, 0) + 1
        return distribution

    def update_episode(
        self,
        episode_id: str,
        outcome: Optional[str] = None,
        duration: Optional[float] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[Episode]:
        """Update an existing episode."""
        with self._lock:
            for engagement_id, episodes in self._episodes.items():
                for episode in episodes:
                    if episode.episode_id == episode_id:
                        if outcome:
                            episode.outcome = outcome
                        if duration:
                            episode.duration = duration
                        if tags:
                            episode.tags = tags
                        if metadata:
                            episode.metadata.update(metadata)
                        return episode
            return None

    def _persist_episode(self, episode: Episode) -> None:
        """Persist episode to disk."""
        try:
            eng_dir = self._storage_dir / str(episode.engagement_id)
            eng_dir.mkdir(exist_ok=True)

            episode_file = eng_dir / f"{episode.episode_id}.json"
            data = {
                "episode_id": episode.episode_id,
                "engagement_id": episode.engagement_id,
                "agent_id": episode.agent_id,
                "event_type": episode.event_type,
                "description": episode.description,
                "data": episode.data,
                "timestamp": episode.timestamp,
                "duration": episode.duration,
                "outcome": episode.outcome,
                "tags": episode.tags,
                "metadata": episode.metadata,
            }
            episode_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Episode persisted to {episode_file}")
        except Exception as e:
            logger.error(f"Failed to persist episode: {e}")

    def _load_episodes_from_disk(self, engagement_id: int) -> list[Episode]:
        """Load episodes from disk for an engagement."""
        try:
            eng_dir = self._storage_dir / str(engagement_id)
            if not eng_dir.exists():
                return []

            episodes = []
            for episode_file in sorted(eng_dir.glob("*.json")):
                try:
                    data = json.loads(episode_file.read_text())
                    episode = Episode(**data)
                    episodes.append(episode)
                except Exception as e:
                    logger.warning(f"Failed to load episode {episode_file}: {e}")

            return episodes
        except Exception as e:
            logger.error(f"Failed to load episodes from disk: {e}")
            return []

    def get_stats(self) -> dict[str, Any]:
        """Get episodic memory statistics."""
        with self._lock:
            total_episodes = sum(
                len(episodes) for episodes in self._episodes.values()
            )
            return {
                "engagements": len(self._episodes),
                "total_episodes": total_episodes,
                "storage_dir": str(self._storage_dir),
            }


# Global instance
_episodic_memory: Optional[EpisodicMemory] = None


def get_episodic_memory() -> EpisodicMemory:
    """Get the global episodic memory instance."""
    global _episodic_memory
    if _episodic_memory is None:
        _episodic_memory = EpisodicMemory()
    return _episodic_memory
