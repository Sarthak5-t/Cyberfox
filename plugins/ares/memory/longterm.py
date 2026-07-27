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
class LongTermEntry:
    """A long-term memory entry."""
    entry_id: str
    category: str
    key: str
    value: Any
    importance: float
    created_at: float
    last_accessed: float
    access_count: int = 0
    decay_rate: float = 0.01
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class LongTermMemory:
    """Persistent storage across engagements for learning and strategy optimization."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self._entries: dict[str, LongTermEntry] = {}
        self._lock = threading.Lock()
        self._storage_dir = storage_dir or Path.home() / ".cyberfox" / "ares" / "longterm"
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def store(
        self,
        category: str,
        key: str,
        value: Any,
        importance: float = 0.5,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> LongTermEntry:
        """Store a long-term memory entry."""
        with self._lock:
            entry_id = f"lt_{category}_{hash(key) % 100000}"
            now = time.time()

            entry = LongTermEntry(
                entry_id=entry_id,
                category=category,
                key=key,
                value=value,
                importance=importance,
                created_at=now,
                last_accessed=now,
                tags=tags or [],
                metadata=metadata or {},
            )

            self._entries[entry_id] = entry

            # Persist to disk
            self._persist_entry(entry)

            logger.debug(f"Long-term memory stored: {entry_id}")
            return entry

    def retrieve(
        self,
        entry_id: str,
    ) -> Optional[Any]:
        """Retrieve a long-term memory entry."""
        with self._lock:
            if entry_id not in self._entries:
                return None

            entry = self._entries[entry_id]
            entry.last_accessed = time.time()
            entry.access_count += 1

            return entry.value

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        min_importance: float = 0.0,
    ) -> list[LongTermEntry]:
        """Search long-term memory entries."""
        with self._lock:
            results = []
            for entry in self._entries.values():
                if category and entry.category != category:
                    continue
                if entry.importance < min_importance:
                    continue
                if (query.lower() in entry.key.lower() or
                    query.lower() in str(entry.value).lower() or
                    any(query.lower() in tag.lower() for tag in entry.tags)):
                    results.append(entry)
            return results

    def get_by_category(
        self,
        category: str,
        limit: Optional[int] = None,
    ) -> list[LongTermEntry]:
        """Get entries by category."""
        with self._lock:
            entries = [
                e for e in self._entries.values()
                if e.category == category
            ]
            entries.sort(key=lambda e: e.importance, reverse=True)
            if limit:
                entries = entries[:limit]
            return entries

    def update_importance(
        self,
        entry_id: str,
        new_importance: float,
    ) -> bool:
        """Update importance for an entry."""
        with self._lock:
            if entry_id not in self._entries:
                return False

            self._entries[entry_id].importance = new_importance
            return True

    def decay_importance(self) -> int:
        """Apply decay to all entries' importance."""
        with self._lock:
            now = time.time()
            decayed = 0
            for entry in self._entries.values():
                time_since_access = now - entry.last_accessed
                decay = entry.decay_rate * (time_since_access / 86400)  # Daily decay
                entry.importance = max(0.0, entry.importance - decay)
                decayed += 1
            return decayed

    def consolidate(self) -> dict[str, Any]:
        """Consolidate long-term memory (merge similar entries, update stats)."""
        with self._lock:
            # Group by category and key
            by_category_key: dict[str, dict[str, list[LongTermEntry]]] = {}
            for entry in self._entries.values():
                if entry.category not in by_category_key:
                    by_category_key[entry.category] = {}
                if entry.key not in by_category_key[entry.category]:
                    by_category_key[entry.category][entry.key] = []
                by_category_key[entry.category][entry.key].append(entry)

            consolidated = 0
            for category, keys in by_category_key.items():
                for key, entries in keys.items():
                    if len(entries) > 1:
                        # Merge entries
                        best_entry = max(entries, key=lambda e: e.importance)
                        for entry in entries:
                            if entry.entry_id != best_entry.entry_id:
                                # Merge metadata
                                best_entry.metadata.update(entry.metadata)
                                # Merge tags
                                best_entry.tags = list(set(best_entry.tags + entry.tags))
                                # Remove duplicate
                                del self._entries[entry.entry_id]
                                consolidated += 1

            return {
                "consolidated": consolidated,
                "remaining": len(self._entries),
            }

    def get_statistics(self) -> dict[str, Any]:
        """Get long-term memory statistics."""
        with self._lock:
            stats = {
                "total_entries": len(self._entries),
                "by_category": {},
                "avg_importance": 0.0,
                "total_accesses": 0,
            }

            for entry in self._entries.values():
                stats["by_category"][entry.category] = (
                    stats["by_category"].get(entry.category, 0) + 1
                )
                stats["total_accesses"] += entry.access_count

            if self._entries:
                stats["avg_importance"] = (
                    sum(e.importance for e in self._entries.values())
                    / len(self._entries)
                )

            return stats

    def _persist_entry(self, entry: LongTermEntry) -> None:
        """Persist entry to disk."""
        try:
            cat_dir = self._storage_dir / entry.category
            cat_dir.mkdir(exist_ok=True)

            entry_file = cat_dir / f"{entry.entry_id}.json"
            data = {
                "entry_id": entry.entry_id,
                "category": entry.category,
                "key": entry.key,
                "value": entry.value,
                "importance": entry.importance,
                "created_at": entry.created_at,
                "last_accessed": entry.last_accessed,
                "access_count": entry.access_count,
                "decay_rate": entry.decay_rate,
                "tags": entry.tags,
                "metadata": entry.metadata,
            }
            entry_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Long-term entry persisted to {entry_file}")
        except Exception as e:
            logger.error(f"Failed to persist long-term entry: {e}")

    def _load_entries_from_disk(self, category: str) -> list[LongTermEntry]:
        """Load entries from disk for a category."""
        try:
            cat_dir = self._storage_dir / category
            if not cat_dir.exists():
                return []

            entries = []
            for entry_file in sorted(cat_dir.glob("*.json")):
                try:
                    data = json.loads(entry_file.read_text())
                    entry = LongTermEntry(**data)
                    entries.append(entry)
                except Exception as e:
                    logger.warning(f"Failed to load long-term entry {entry_file}: {e}")

            return entries
        except Exception as e:
            logger.error(f"Failed to load long-term entries from disk: {e}")
            return []


# Global instance
_longterm_memory: Optional[LongTermMemory] = None


def get_longterm_memory() -> LongTermMemory:
    """Get the global long-term memory instance."""
    global _longterm_memory
    if _longterm_memory is None:
        _longterm_memory = LongTermMemory()
    return _longterm_memory
