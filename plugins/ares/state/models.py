from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Engagement ────────────────────────────────────────────────────────────

ENGAGEMENT_STATES = (
    "planning",
    "recon",
    "scanning",
    "enumeration",
    "validation",
    "exploitation",
    "reporting",
    "completed",
)


@dataclass
class Engagement:
    id: int = 0
    name: str = ""
    scope: list[str] = field(default_factory=list)
    goals: str = ""
    state: str = "planning"
    started_at: str = ""
    updated_at: str = ""


# ── Entities ──────────────────────────────────────────────────────────────

ENTITY_TYPES = (
    "host",
    "domain",
    "subdomain",
    "port",
    "service",
    "technology",
    "credential",
    "user",
    "group",
    "finding",
    "vulnerability",
)


@dataclass
class Entity:
    id: int = 0
    engagement: int = 0
    type: str = ""
    name: str = ""
    data: dict = field(default_factory=dict)
    confidence: float = 1.0
    verified: bool = False
    parent_id: Optional[int] = None
    created_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["data"] = self.data
        return d


# ── Relationships ─────────────────────────────────────────────────────────

RELATION_TYPES = (
    "runs_on",
    "has_port",
    "has_service",
    "uses_tech",
    "has_vulnerability",
    "discovered_by",
    "authenticated_with",
    "references_cve",
    "exploits",
    "depends_on",
    "member_of",
    "connected_to",
    "resolves_to",
    "hosted_on",
    "subdomain_of",
)


@dataclass
class Relationship:
    id: int = 0
    engagement: int = 0
    source_id: int = 0
    target_id: int = 0
    relation: str = ""
    data: dict = field(default_factory=dict)
    confidence: float = 1.0
    created_at: str = ""


# ── Plan Tasks ────────────────────────────────────────────────────────────

TASK_STATUSES = ("pending", "in_progress", "completed", "failed", "skipped")

TASK_PHASES = (
    "recon",
    "scanning",
    "enumeration",
    "validation",
    "exploitation",
    "reporting",
)


@dataclass
class PlanTask:
    id: int = 0
    engagement: int = 0
    phase: str = ""
    step: int = 0
    title: str = ""
    description: str = ""
    tool: Optional[str] = None
    entity_id: Optional[int] = None
    depends_on: Optional[int] = None
    status: str = "pending"
    result: Optional[str] = None
    confidence: Optional[float] = None
    created_at: str = ""
    updated_at: str = ""


# ── Decisions ─────────────────────────────────────────────────────────────

@dataclass
class Decision:
    id: int = 0
    engagement: int = 0
    reasoning: str = ""
    action: str = ""
    context: Optional[str] = None
    tool_call_id: Optional[str] = None
    created_at: str = ""


# ── Tool Events ───────────────────────────────────────────────────────────

@dataclass
class ToolEvent:
    id: int = 0
    engagement: int = 0
    tool_name: str = ""
    args: dict = field(default_factory=dict)
    result_summary: Optional[str] = None
    status: Optional[str] = None
    duration_ms: Optional[int] = None
    entities_created: list[int] = field(default_factory=list)
    turn_id: Optional[str] = None
    created_at: str = ""


# ── Graph View ────────────────────────────────────────────────────────────

@dataclass
class GraphView:
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [asdict(r) for r in self.relationships],
        }
