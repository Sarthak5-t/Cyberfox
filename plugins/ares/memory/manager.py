from __future__ import annotations

import logging
import time
from typing import Any, Optional
from pathlib import Path

from plugins.ares.memory.working import WorkingMemory, get_working_memory
from plugins.ares.memory.episodic import EpisodicMemory, get_episodic_memory
from plugins.ares.memory.semantic import SemanticMemory, get_semantic_memory
from plugins.ares.memory.procedural import ProceduralMemory, get_procedural_memory
from plugins.ares.memory.longterm import LongTermMemory, get_longterm_memory

logger = logging.getLogger(__name__)


class MemoryManager:
    """Unified interface for all memory tiers."""

    def __init__(self):
        self.working = get_working_memory()
        self.episodic = get_episodic_memory()
        self.semantic = get_semantic_memory()
        self.procedural = get_procedural_memory()
        self.longterm = get_longterm_memory()

    def store_context(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
    ) -> None:
        """Store in working memory (current context)."""
        self.working.store(key, value, ttl=ttl)

    def get_context(self, key: str) -> Optional[Any]:
        """Get from working memory."""
        return self.working.retrieve(key)

    def record_event(
        self,
        engagement_id: int,
        agent_id: str,
        event_type: str,
        description: str,
        data: dict[str, Any],
        outcome: str = "success",
        tags: Optional[list[str]] = None,
    ) -> None:
        """Record an episodic event."""
        self.episodic.record_episode(
            engagement_id=engagement_id,
            agent_id=agent_id,
            event_type=event_type,
            description=description,
            data=data,
            outcome=outcome,
            tags=tags,
        )

    def store_knowledge(
        self,
        category: str,
        subcategory: str,
        key: str,
        value: Any,
        confidence: float = 1.0,
        source: str = "agent",
    ) -> None:
        """Store in semantic memory (knowledge)."""
        self.semantic.store_knowledge(
            category=category,
            subcategory=subcategory,
            key=key,
            value=value,
            confidence=confidence,
            source=source,
        )

    def get_knowledge(
        self,
        category: str,
        subcategory: str,
        key: str,
    ) -> Optional[Any]:
        """Get from semantic memory."""
        return self.semantic.retrieve_knowledge(category, subcategory, key)

    def store_procedure(
        self,
        name: str,
        description: str,
        steps: list[dict[str, Any]],
        category: str,
    ) -> str:
        """Store in procedural memory (how-to)."""
        procedure = self.procedural.store_procedure(
            name=name,
            description=description,
            steps=steps,
            category=category,
        )
        return procedure.procedure_id

    def get_procedure(self, procedure_id: str) -> Optional[dict[str, Any]]:
        """Get from procedural memory."""
        procedure = self.procedural.retrieve_procedure(procedure_id)
        if procedure:
            return {
                "name": procedure.name,
                "description": procedure.description,
                "steps": procedure.steps,
                "success_rate": procedure.success_rate,
            }
        return None

    def store_learning(
        self,
        category: str,
        key: str,
        value: Any,
        importance: float = 0.5,
    ) -> None:
        """Store in long-term memory (persistent learning)."""
        self.longterm.store(
            category=category,
            key=key,
            value=value,
            importance=importance,
        )

    def get_learning(
        self,
        category: str,
        key: str,
    ) -> Optional[Any]:
        """Get from long-term memory."""
        entries = self.longterm.get_by_category(category)
        for entry in entries:
            if entry.key == key:
                return entry.value
        return None

    def search_all(self, query: str) -> dict[str, list[Any]]:
        """Search across all memory tiers."""
        results = {
            "working": [],
            "episodic": [],
            "semantic": [],
            "procedural": [],
            "longterm": [],
        }

        # Search working memory
        for key, value in self.working.items():
            if query.lower() in key.lower() or query.lower() in str(value).lower():
                results["working"].append({"key": key, "value": value})

        # Search semantic memory
        semantic_results = self.semantic.search_knowledge(query)
        results["semantic"] = [
            {"key": item.key, "value": item.value, "category": item.category}
            for item in semantic_results
        ]

        # Search procedural memory
        procedural_results = self.procedural.search_procedures(query)
        results["procedural"] = [
            {"name": p.name, "description": p.description, "success_rate": p.success_rate}
            for p in procedural_results
        ]

        # Search long-term memory
        longterm_results = self.longterm.search(query)
        results["longterm"] = [
            {"key": e.key, "value": e.value, "importance": e.importance}
            for e in longterm_results
        ]

        return results

    def get_memory_stats(self) -> dict[str, Any]:
        """Get statistics for all memory tiers."""
        return {
            "working": self.working.get_stats(),
            "episodic": self.episodic.get_stats(),
            "semantic": self.semantic.get_statistics(),
            "procedural": self.procedural.get_statistics(),
            "longterm": self.longterm.get_statistics(),
        }

    def cleanup(self) -> dict[str, int]:
        """Cleanup expired entries across all tiers."""
        return {
            "working_expired": self.working.cleanup_expired(),
        }

    def export_context(self, engagement_id: int) -> dict[str, Any]:
        """Export full context for an engagement."""
        context = {
            "working": self.working.export_context(),
            "episodic": [],
            "semantic": [],
            "procedural": [],
        }

        # Get episodic memory
        episodes = self.episodic.get_episodes(engagement_id)
        context["episodic"] = [
            {
                "event_type": e.event_type,
                "description": e.description,
                "outcome": e.outcome,
                "timestamp": e.timestamp,
            }
            for e in episodes
        ]

        # Get semantic memory
        knowledge = self.semantic.get_knowledge_by_category("targets")
        context["semantic"] = [
            {"key": k.key, "value": k.value, "category": k.category}
            for k in knowledge
        ]

        return context


# Global instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get the global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
