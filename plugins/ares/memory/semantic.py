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
class KnowledgeItem:
    """A single knowledge item in semantic memory."""
    item_id: str
    category: str
    subcategory: str
    key: str
    value: Any
    confidence: float
    source: str
    timestamp: float
    last_accessed: float
    access_count: int = 0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SemanticMemory:
    """Knowledge about targets, vulnerabilities, and attack patterns."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self._knowledge: dict[str, dict[str, dict[str, KnowledgeItem]]] = {}
        self._lock = threading.Lock()
        self._storage_dir = storage_dir or Path.home() / ".cyberfox" / "ares" / "semantic"
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def store_knowledge(
        self,
        category: str,
        subcategory: str,
        key: str,
        value: Any,
        confidence: float = 1.0,
        source: str = "unknown",
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> KnowledgeItem:
        """Store a knowledge item."""
        with self._lock:
            item_id = f"{category}_{subcategory}_{hash(key) % 100000}"

            if category not in self._knowledge:
                self._knowledge[category] = {}
            if subcategory not in self._knowledge[category]:
                self._knowledge[category][subcategory] = {}

            item = KnowledgeItem(
                item_id=item_id,
                category=category,
                subcategory=subcategory,
                key=key,
                value=value,
                confidence=confidence,
                source=source,
                timestamp=time.time(),
                last_accessed=time.time(),
                tags=tags or [],
                metadata=metadata or {},
            )

            self._knowledge[category][subcategory][key] = item

            # Persist to disk
            self._persist_item(item)

            logger.debug(f"Knowledge stored: {category}/{subcategory}/{key}")
            return item

    def retrieve_knowledge(
        self,
        category: str,
        subcategory: str,
        key: str,
    ) -> Optional[Any]:
        """Retrieve a knowledge item."""
        with self._lock:
            if (category not in self._knowledge or
                subcategory not in self._knowledge[category] or
                key not in self._knowledge[category][subcategory]):
                return None

            item = self._knowledge[category][subcategory][key]
            item.last_accessed = time.time()
            item.access_count += 1

            return item.value

    def search_knowledge(
        self,
        query: str,
        category: Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> list[KnowledgeItem]:
        """Search knowledge items by query."""
        with self._lock:
            results = []
            for cat, subcats in self._knowledge.items():
                if category and cat != category:
                    continue
                for subcat, items in subcats.items():
                    for item in items.values():
                        if (item.confidence >= min_confidence and
                            (query.lower() in item.key.lower() or
                             query.lower() in str(item.value).lower() or
                             any(query.lower() in tag.lower() for tag in item.tags))):
                            results.append(item)
            return results

    def get_knowledge_by_category(
        self,
        category: str,
        subcategory: Optional[str] = None,
    ) -> list[KnowledgeItem]:
        """Get all knowledge items in a category."""
        with self._lock:
            if category not in self._knowledge:
                return []

            items = []
            if subcategory:
                if subcategory in self._knowledge[category]:
                    items = list(self._knowledge[category][subcategory].values())
            else:
                for subcat in self._knowledge[category].values():
                    items.extend(subcat.values())

            return items

    def update_confidence(
        self,
        category: str,
        subcategory: str,
        key: str,
        new_confidence: float,
    ) -> bool:
        """Update confidence for a knowledge item."""
        with self._lock:
            if (category not in self._knowledge or
                subcategory not in self._knowledge[category] or
                key not in self._knowledge[category][subcategory]):
                return False

            item = self._knowledge[category][subcategory][key]
            item.confidence = new_confidence
            item.metadata["confidence_updated"] = time.time()

            return True

    def delete_knowledge(
        self,
        category: str,
        subcategory: str,
        key: str,
    ) -> bool:
        """Delete a knowledge item."""
        with self._lock:
            if (category not in self._knowledge or
                subcategory not in self._knowledge[category] or
                key not in self._knowledge[category][subcategory]):
                return False

            del self._knowledge[category][subcategory][key]
            return True

    def get_statistics(self) -> dict[str, Any]:
        """Get knowledge statistics."""
        with self._lock:
            stats = {
                "categories": len(self._knowledge),
                "total_items": 0,
                "by_category": {},
                "by_confidence": {"high": 0, "medium": 0, "low": 0},
            }

            for cat, subcats in self._knowledge.items():
                cat_count = 0
                for subcat, items in subcats.items():
                    cat_count += len(items)
                    for item in items.values():
                        if item.confidence >= 0.8:
                            stats["by_confidence"]["high"] += 1
                        elif item.confidence >= 0.5:
                            stats["by_confidence"]["medium"] += 1
                        else:
                            stats["by_confidence"]["low"] += 1
                stats["by_category"][cat] = cat_count
                stats["total_items"] += cat_count

            return stats

    def _persist_item(self, item: KnowledgeItem) -> None:
        """Persist knowledge item to disk."""
        try:
            cat_dir = self._storage_dir / item.category
            cat_dir.mkdir(exist_ok=True)

            item_file = cat_dir / f"{item.item_id}.json"
            data = {
                "item_id": item.item_id,
                "category": item.category,
                "subcategory": item.subcategory,
                "key": item.key,
                "value": item.value,
                "confidence": item.confidence,
                "source": item.source,
                "timestamp": item.timestamp,
                "last_accessed": item.last_accessed,
                "access_count": item.access_count,
                "tags": item.tags,
                "metadata": item.metadata,
            }
            item_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Knowledge item persisted to {item_file}")
        except Exception as e:
            logger.error(f"Failed to persist knowledge item: {e}")

    def _load_items_from_disk(self, category: str) -> list[KnowledgeItem]:
        """Load knowledge items from disk for a category."""
        try:
            cat_dir = self._storage_dir / category
            if not cat_dir.exists():
                return []

            items = []
            for item_file in sorted(cat_dir.glob("*.json")):
                try:
                    data = json.loads(item_file.read_text())
                    item = KnowledgeItem(**data)
                    items.append(item)
                except Exception as e:
                    logger.warning(f"Failed to load knowledge item {item_file}: {e}")

            return items
        except Exception as e:
            logger.error(f"Failed to load knowledge items from disk: {e}")
            return []


# Global instance
_semantic_memory: Optional[SemanticMemory] = None


def get_semantic_memory() -> SemanticMemory:
    """Get the global semantic memory instance."""
    global _semantic_memory
    if _semantic_memory is None:
        _semantic_memory = SemanticMemory()
    return _semantic_memory
