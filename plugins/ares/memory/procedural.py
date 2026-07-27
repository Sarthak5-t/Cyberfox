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
class Procedure:
    """A procedure in procedural memory."""
    procedure_id: str
    name: str
    description: str
    steps: list[dict[str, Any]]
    category: str
    success_rate: float = 1.0
    usage_count: int = 0
    last_used: Optional[float] = None
    avg_duration: float = 0.0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcedureExecution:
    """Record of a procedure execution."""
    execution_id: str
    procedure_id: str
    agent_id: str
    engagement_id: int
    start_time: float
    end_time: Optional[float] = None
    outcome: str = "pending"
    steps_completed: int = 0
    total_steps: int = 0
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ProceduralMemory:
    """Memory for how to perform specific tasks and workflows."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self._procedures: dict[str, Procedure] = {}
        self._executions: dict[str, list[ProcedureExecution]] = {}
        self._lock = threading.Lock()
        self._storage_dir = storage_dir or Path.home() / ".cyberfox" / "ares" / "procedures"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._execution_counter = 0

    def store_procedure(
        self,
        name: str,
        description: str,
        steps: list[dict[str, Any]],
        category: str,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Procedure:
        """Store a new procedure."""
        with self._lock:
            procedure_id = f"proc_{category}_{hash(name) % 100000}"

            procedure = Procedure(
                procedure_id=procedure_id,
                name=name,
                description=description,
                steps=steps,
                category=category,
                tags=tags or [],
                metadata=metadata or {},
            )

            self._procedures[procedure_id] = procedure

            # Persist to disk
            self._persist_procedure(procedure)

            logger.info(f"Procedure stored: {procedure_id}")
            return procedure

    def retrieve_procedure(self, procedure_id: str) -> Optional[Procedure]:
        """Retrieve a procedure by ID."""
        with self._lock:
            return self._procedures.get(procedure_id)

    def search_procedures(
        self,
        query: str,
        category: Optional[str] = None,
        min_success_rate: float = 0.0,
    ) -> list[Procedure]:
        """Search procedures by query."""
        with self._lock:
            results = []
            for procedure in self._procedures.values():
                if category and procedure.category != category:
                    continue
                if procedure.success_rate < min_success_rate:
                    continue
                if (query.lower() in procedure.name.lower() or
                    query.lower() in procedure.description.lower() or
                    any(query.lower() in tag.lower() for tag in procedure.tags)):
                    results.append(procedure)
            return results

    def get_procedures_by_category(self, category: str) -> list[Procedure]:
        """Get all procedures in a category."""
        with self._lock:
            return [
                p for p in self._procedures.values()
                if p.category == category
            ]

    def start_execution(
        self,
        procedure_id: str,
        agent_id: str,
        engagement_id: int,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[ProcedureExecution]:
        """Start executing a procedure."""
        with self._lock:
            if procedure_id not in self._procedures:
                return None

            self._execution_counter += 1
            execution = ProcedureExecution(
                execution_id=f"exec_{self._execution_counter}",
                procedure_id=procedure_id,
                agent_id=agent_id,
                engagement_id=engagement_id,
                start_time=time.time(),
                total_steps=len(self._procedures[procedure_id].steps),
                metadata=metadata or {},
            )

            if engagement_id not in self._executions:
                self._executions[engagement_id] = []
            self._executions[engagement_id].append(execution)

            logger.info(f"Procedure execution started: {execution.execution_id}")
            return execution

    def update_execution(
        self,
        execution_id: str,
        steps_completed: Optional[int] = None,
        outcome: Optional[str] = None,
        errors: Optional[list[str]] = None,
    ) -> Optional[ProcedureExecution]:
        """Update a procedure execution."""
        with self._lock:
            for executions in self._executions.values():
                for execution in executions:
                    if execution.execution_id == execution_id:
                        if steps_completed is not None:
                            execution.steps_completed = steps_completed
                        if outcome:
                            execution.outcome = outcome
                            execution.end_time = time.time()
                        if errors:
                            execution.errors.extend(errors)

                        # Update procedure success rate
                        if execution.outcome in ("success", "failure"):
                            self._update_procedure_stats(execution)

                        return execution
            return None

    def _update_procedure_stats(self, execution: ProcedureExecution) -> None:
        """Update procedure statistics based on execution."""
        if execution.procedure_id not in self._procedures:
            return

        procedure = self._procedures[execution.procedure_id]
        procedure.usage_count += 1
        procedure.last_used = execution.start_time

        # Update success rate with exponential moving average
        alpha = 0.1
        success = 1.0 if execution.outcome == "success" else 0.0
        procedure.success_rate = (1 - alpha) * procedure.success_rate + alpha * success

        # Update average duration
        if execution.end_time:
            duration = execution.end_time - execution.start_time
            procedure.avg_duration = (
                (procedure.avg_duration * (procedure.usage_count - 1) + duration)
                / procedure.usage_count
            )

    def get_executions(
        self,
        engagement_id: int,
        agent_id: Optional[str] = None,
        procedure_id: Optional[str] = None,
    ) -> list[ProcedureExecution]:
        """Get executions for an engagement."""
        with self._lock:
            if engagement_id not in self._executions:
                return []

            executions = self._executions[engagement_id]

            if agent_id:
                executions = [e for e in executions if e.agent_id == agent_id]
            if procedure_id:
                executions = [e for e in executions if e.procedure_id == procedure_id]

            return executions

    def get_statistics(self) -> dict[str, Any]:
        """Get procedural memory statistics."""
        with self._lock:
            stats = {
                "total_procedures": len(self._procedures),
                "total_executions": sum(
                    len(execs) for execs in self._executions.values()
                ),
                "by_category": {},
                "top_procedures": [],
            }

            # Count by category
            for procedure in self._procedures.values():
                category = procedure.category
                stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

            # Get top procedures by usage
            sorted_procedures = sorted(
                self._procedures.values(),
                key=lambda p: p.usage_count,
                reverse=True,
            )
            stats["top_procedures"] = [
                {
                    "name": p.name,
                    "usage_count": p.usage_count,
                    "success_rate": p.success_rate,
                }
                for p in sorted_procedures[:10]
            ]

            return stats

    def _persist_procedure(self, procedure: Procedure) -> None:
        """Persist procedure to disk."""
        try:
            cat_dir = self._storage_dir / procedure.category
            cat_dir.mkdir(exist_ok=True)

            proc_file = cat_dir / f"{procedure.procedure_id}.json"
            data = {
                "procedure_id": procedure.procedure_id,
                "name": procedure.name,
                "description": procedure.description,
                "steps": procedure.steps,
                "category": procedure.category,
                "success_rate": procedure.success_rate,
                "usage_count": procedure.usage_count,
                "last_used": procedure.last_used,
                "avg_duration": procedure.avg_duration,
                "tags": procedure.tags,
                "metadata": procedure.metadata,
            }
            proc_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Procedure persisted to {proc_file}")
        except Exception as e:
            logger.error(f"Failed to persist procedure: {e}")


# Global instance
_procedural_memory: Optional[ProceduralMemory] = None


def get_procedural_memory() -> ProceduralMemory:
    """Get the global procedural memory instance."""
    global _procedural_memory
    if _procedural_memory is None:
        _procedural_memory = ProceduralMemory()
    return _procedural_memory
