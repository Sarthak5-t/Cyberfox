from __future__ import annotations

import json
import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """A skill in the skill hub."""
    skill_id: str
    name: str
    description: str
    category: str
    version: str
    parameters: dict[str, Any]
    handler: Optional[Callable] = None
    success_rate: float = 1.0
    usage_count: int = 0
    last_used: Optional[float] = None
    avg_duration: float = 0.0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class SkillExecution:
    """Record of a skill execution."""
    execution_id: str
    skill_id: str
    agent_id: str
    engagement_id: int
    start_time: float
    end_time: Optional[float] = None
    outcome: str = "pending"
    input_params: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0


class SkillHub:
    """Central repository for all skills with metadata and versioning."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self._skills: dict[str, Skill] = {}
        self._executions: dict[str, list[SkillExecution]] = {}
        self._lock = threading.Lock()
        self._storage_dir = storage_dir or Path.home() / ".cyberfox" / "ares" / "skills"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._execution_counter = 0

    def register_skill(
        self,
        name: str,
        description: str,
        category: str,
        version: str = "1.0.0",
        parameters: Optional[dict[str, Any]] = None,
        handler: Optional[Callable] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Skill:
        """Register a new skill."""
        with self._lock:
            skill_id = f"skill_{category}_{name.lower().replace(' ', '_')}"

            skill = Skill(
                skill_id=skill_id,
                name=name,
                description=description,
                category=category,
                version=version,
                parameters=parameters or {},
                handler=handler,
                tags=tags or [],
                metadata=metadata or {},
            )

            self._skills[skill_id] = skill

            # Persist to disk
            self._persist_skill(skill)

            logger.info(f"Skill registered: {skill_id}")
            return skill

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID."""
        with self._lock:
            return self._skills.get(skill_id)

    def search_skills(
        self,
        query: str,
        category: Optional[str] = None,
        min_success_rate: float = 0.0,
    ) -> list[Skill]:
        """Search skills by query."""
        with self._lock:
            results = []
            for skill in self._skills.values():
                if category and skill.category != category:
                    continue
                if skill.success_rate < min_success_rate:
                    continue
                if (query.lower() in skill.name.lower() or
                    query.lower() in skill.description.lower() or
                    any(query.lower() in tag.lower() for tag in skill.tags)):
                    results.append(skill)
            return results

    def get_skills_by_category(self, category: str) -> list[Skill]:
        """Get all skills in a category."""
        with self._lock:
            return [
                s for s in self._skills.values()
                if s.category == category
            ]

    def start_execution(
        self,
        skill_id: str,
        agent_id: str,
        engagement_id: int,
        input_params: Optional[dict[str, Any]] = None,
    ) -> Optional[SkillExecution]:
        """Start executing a skill."""
        with self._lock:
            if skill_id not in self._skills:
                return None

            self._execution_counter += 1
            execution = SkillExecution(
                execution_id=f"exec_{self._execution_counter}",
                skill_id=skill_id,
                agent_id=agent_id,
                engagement_id=engagement_id,
                start_time=time.time(),
                input_params=input_params or {},
            )

            if engagement_id not in self._executions:
                self._executions[engagement_id] = []
            self._executions[engagement_id].append(execution)

            logger.info(f"Skill execution started: {execution.execution_id}")
            return execution

    def complete_execution(
        self,
        execution_id: str,
        outcome: str,
        output: Any = None,
        error: Optional[str] = None,
    ) -> Optional[SkillExecution]:
        """Complete a skill execution."""
        with self._lock:
            for executions in self._executions.values():
                for execution in executions:
                    if execution.execution_id == execution_id:
                        execution.end_time = time.time()
                        execution.outcome = outcome
                        execution.output = output
                        execution.error = error
                        execution.duration = execution.end_time - execution.start_time

                        # Update skill stats
                        self._update_skill_stats(execution)

                        return execution
            return None

    def _update_skill_stats(self, execution: SkillExecution) -> None:
        """Update skill statistics based on execution."""
        if execution.skill_id not in self._skills:
            return

        skill = self._skills[execution.skill_id]
        skill.usage_count += 1
        skill.last_used = execution.start_time
        skill.updated_at = time.time()

        # Update success rate with exponential moving average
        alpha = 0.1
        success = 1.0 if execution.outcome == "success" else 0.0
        skill.success_rate = (1 - alpha) * skill.success_rate + alpha * success

        # Update average duration
        skill.avg_duration = (
            (skill.avg_duration * (skill.usage_count - 1) + execution.duration)
            / skill.usage_count
        )

    def get_executions(
        self,
        engagement_id: int,
        skill_id: Optional[str] = None,
    ) -> list[SkillExecution]:
        """Get executions for an engagement."""
        with self._lock:
            if engagement_id not in self._executions:
                return []

            executions = self._executions[engagement_id]
            if skill_id:
                executions = [e for e in executions if e.skill_id == skill_id]

            return executions

    def get_statistics(self) -> dict[str, Any]:
        """Get skill hub statistics."""
        with self._lock:
            stats = {
                "total_skills": len(self._skills),
                "total_executions": sum(
                    len(execs) for execs in self._executions.values()
                ),
                "by_category": {},
                "top_skills": [],
            }

            # Count by category
            for skill in self._skills.values():
                category = skill.category
                stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

            # Get top skills by usage
            sorted_skills = sorted(
                self._skills.values(),
                key=lambda s: s.usage_count,
                reverse=True,
            )
            stats["top_skills"] = [
                {
                    "name": s.name,
                    "usage_count": s.usage_count,
                    "success_rate": s.success_rate,
                }
                for s in sorted_skills[:10]
            ]

            return stats

    def _persist_skill(self, skill: Skill) -> None:
        """Persist skill to disk."""
        try:
            cat_dir = self._storage_dir / skill.category
            cat_dir.mkdir(exist_ok=True)

            skill_file = cat_dir / f"{skill.skill_id}.json"
            data = {
                "skill_id": skill.skill_id,
                "name": skill.name,
                "description": skill.description,
                "category": skill.category,
                "version": skill.version,
                "parameters": skill.parameters,
                "success_rate": skill.success_rate,
                "usage_count": skill.usage_count,
                "last_used": skill.last_used,
                "avg_duration": skill.avg_duration,
                "tags": skill.tags,
                "metadata": skill.metadata,
                "created_at": skill.created_at,
                "updated_at": skill.updated_at,
            }
            skill_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Skill persisted to {skill_file}")
        except Exception as e:
            logger.error(f"Failed to persist skill: {e}")


# Global instance
_skill_hub: Optional[SkillHub] = None


def get_skill_hub() -> SkillHub:
    """Get the global skill hub instance."""
    global _skill_hub
    if _skill_hub is None:
        _skill_hub = SkillHub()
    return _skill_hub
