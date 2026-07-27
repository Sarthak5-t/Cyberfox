from __future__ import annotations

import json
import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Optional
from collections import OrderedDict

logger = logging.getLogger(__name__)


@dataclass
class WorkingMemoryEntry:
    """A single entry in working memory."""
    key: str
    value: Any
    timestamp: float
    ttl: Optional[float] = None  # Time to live in seconds
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return (time.time() - self.timestamp) > self.ttl


class WorkingMemory:
    """Short-term memory for current engagement context."""

    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = 3600):
        self._memory: OrderedDict[str, WorkingMemoryEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._access_count: dict[str, int] = {}

    def store(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Store a value in working memory."""
        with self._lock:
            if key in self._memory:
                # Update existing entry
                self._memory[key].value = value
                self._memory[key].timestamp = time.time()
                self._memory[key].ttl = ttl or self._default_ttl
                if metadata:
                    self._memory[key].metadata.update(metadata)
            else:
                # Add new entry
                if len(self._memory) >= self._max_size:
                    # Remove oldest entry
                    self._memory.popitem(last=False)

                self._memory[key] = WorkingMemoryEntry(
                    key=key,
                    value=value,
                    timestamp=time.time(),
                    ttl=ttl or self._default_ttl,
                    metadata=metadata or {},
                )

            # Update access count for LRU
            self._access_count[key] = self._access_count.get(key, 0) + 1
            self._memory.move_to_end(key)

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a value from working memory."""
        with self._lock:
            if key not in self._memory:
                return None

            entry = self._memory[key]
            if entry.is_expired:
                del self._memory[key]
                self._access_count.pop(key, None)
                return None

            # Update access count and move to end
            self._access_count[key] = self._access_count.get(key, 0) + 1
            self._memory.move_to_end(key)

            return entry.value

    def delete(self, key: str) -> bool:
        """Delete a value from working memory."""
        with self._lock:
            if key in self._memory:
                del self._memory[key]
                self._access_count.pop(key, None)
                return True
            return False

    def exists(self, key: str) -> bool:
        """Check if a key exists in working memory."""
        with self._lock:
            if key not in self._memory:
                return False
            return not self._memory[key].is_expired

    def clear(self) -> int:
        """Clear all entries from working memory."""
        with self._lock:
            count = len(self._memory)
            self._memory.clear()
            self._access_count.clear()
            return count

    def keys(self) -> list[str]:
        """Get all keys in working memory."""
        with self._lock:
            return [k for k in self._memory.keys() if not self._memory[k].is_expired]

    def values(self) -> list[Any]:
        """Get all values in working memory."""
        with self._lock:
            return [
                v.value for v in self._memory.values()
                if not v.is_expired
            ]

    def items(self) -> list[tuple[str, Any]]:
        """Get all key-value pairs in working memory."""
        with self._lock:
            return [
                (k, v.value) for k, v in self._memory.items()
                if not v.is_expired
            ]

    def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        with self._lock:
            expired_keys = [
                k for k, v in self._memory.items()
                if v.is_expired
            ]
            for key in expired_keys:
                del self._memory[key]
                self._access_count.pop(key, None)
            return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """Get working memory statistics."""
        with self._lock:
            return {
                "size": len(self._memory),
                "max_size": self._max_size,
                "total_accesses": sum(self._access_count.values()),
                "most_accessed": max(
                    self._access_count.items(),
                    key=lambda x: x[1],
                )[0] if self._access_count else None,
            }

    def export_context(self) -> dict[str, Any]:
        """Export working memory as context dictionary."""
        with self._lock:
            context = {}
            for key, entry in self._memory.items():
                if not entry.is_expired:
                    context[key] = entry.value
            return context

    def import_context(self, context: dict[str, Any]) -> int:
        """Import context dictionary into working memory."""
        count = 0
        for key, value in context.items():
            self.store(key, value)
            count += 1
        return count


# Global instance
_working_memory: Optional[WorkingMemory] = None


def get_working_memory() -> WorkingMemory:
    """Get the global working memory instance."""
    global _working_memory
    if _working_memory is None:
        _working_memory = WorkingMemory()
    return _working_memory
