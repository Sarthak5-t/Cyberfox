from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cyberfox_constants import get_cyberfox_home as get_cf_home

from plugins.ares.state.models import (
    ENGAGEMENT_STATES,
    ENTITY_TYPES,
    RELATION_TYPES,
    TASK_STATUSES,
    TASK_PHASES,
    Engagement,
    Entity,
    Relationship,
    PlanTask,
    Decision,
    ToolEvent,
    GraphView,
)

_LOCK = threading.Lock()

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS engagements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    scope       TEXT NOT NULL DEFAULT '[]',
    goals       TEXT NOT NULL DEFAULT '',
    state       TEXT NOT NULL DEFAULT 'planning',
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS entities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement  INTEGER NOT NULL REFERENCES engagements(id),
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    data        TEXT NOT NULL DEFAULT '{}',
    confidence  REAL NOT NULL DEFAULT 1.0,
    verified    INTEGER NOT NULL DEFAULT 0,
    parent_id   INTEGER REFERENCES entities(id),
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(engagement, type, name)
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(engagement, type);
CREATE INDEX IF NOT EXISTS idx_entities_parent ON entities(parent_id);

CREATE TABLE IF NOT EXISTS relationships (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement  INTEGER NOT NULL REFERENCES engagements(id),
    source_id   INTEGER NOT NULL REFERENCES entities(id),
    target_id   INTEGER NOT NULL REFERENCES entities(id),
    relation    TEXT NOT NULL,
    data        TEXT NOT NULL DEFAULT '{}',
    confidence  REAL NOT NULL DEFAULT 1.0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(engagement, source_id, target_id, relation)
);

CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id);

CREATE TABLE IF NOT EXISTS plan_tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement  INTEGER NOT NULL REFERENCES engagements(id),
    phase       TEXT NOT NULL,
    step        INTEGER NOT NULL,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    tool        TEXT,
    entity_id   INTEGER REFERENCES entities(id),
    depends_on  INTEGER REFERENCES plan_tasks(id),
    status      TEXT NOT NULL DEFAULT 'pending',
    result      TEXT,
    confidence  REAL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_plan_status ON plan_tasks(engagement, status);

CREATE TABLE IF NOT EXISTS decisions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement  INTEGER NOT NULL REFERENCES engagements(id),
    reasoning   TEXT NOT NULL,
    action      TEXT NOT NULL,
    context     TEXT,
    tool_call_id TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tool_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement  INTEGER NOT NULL REFERENCES engagements(id),
    tool_name   TEXT NOT NULL,
    args        TEXT NOT NULL DEFAULT '{}',
    result_summary TEXT,
    status      TEXT,
    duration_ms INTEGER,
    entities_created TEXT DEFAULT '[]',
    turn_id     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_tool ON tool_events(engagement, tool_name);
"""


def _db_path() -> Path:
    return get_cf_home() / "ares" / "engagement.db"


def _connect() -> sqlite3.Connection:
    p = _db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    with _LOCK:
        conn = _connect()
        try:
            conn.executescript(_SCHEMA_SQL)
            _run_migrations(conn)
            conn.commit()
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass
        finally:
            conn.close()


def _run_migrations(conn: sqlite3.Connection) -> None:
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    if current < 1:
        conn.execute("PRAGMA user_version = 1")


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


# ═══════════════════════════════════════════════════════════════════════════
# Engagement CRUD
# ═══════════════════════════════════════════════════════════════════════════

def create_engagement(name: str, scope: list[str] | None = None, goals: str = "") -> int:
    now = _now()
    with _LOCK:
        conn = _connect()
        try:
            cur = conn.execute(
                "INSERT INTO engagements (name, scope, goals, state, started_at, updated_at) "
                "VALUES (?, ?, ?, 'planning', ?, ?)",
                (name, json.dumps(scope or []), goals, now, now),
            )
            conn.commit()
            return cur.lastrowid or 0
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
            return 0
        finally:
            conn.close()


def get_engagement(name: str | None = None, engagement_id: int | None = None) -> Optional[Engagement]:
    with _LOCK:
        conn = _connect()
        try:
            if engagement_id:
                row = conn.execute("SELECT * FROM engagements WHERE id = ?", (engagement_id,)).fetchone()
            elif name:
                row = conn.execute("SELECT * FROM engagements WHERE name = ?", (name,)).fetchone()
            else:
                row = conn.execute("SELECT * FROM engagements ORDER BY id DESC LIMIT 1").fetchone()
            if not row:
                return None
            d = _row_to_dict(row)
            return Engagement(
                id=d["id"], name=d["name"],
                scope=json.loads(d["scope"]), goals=d["goals"],
                state=d["state"], started_at=d["started_at"],
                updated_at=d["updated_at"],
            )
        except (sqlite3.OperationalError, sqlite3.DatabaseError, json.JSONDecodeError, OverflowError):
            return None
        finally:
            conn.close()


def list_engagements() -> list[dict]:
    with _LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT id, name, state, started_at FROM engagements ORDER BY id DESC LIMIT 20"
            ).fetchall()
            return [_row_to_dict(r) for r in rows]
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            return []
        finally:
            conn.close()


def transition_state(engagement_id: int, new_state: str) -> bool:
    if new_state not in ENGAGEMENT_STATES:
        return False
    now = _now()
    with _LOCK:
        conn = _connect()
        try:
            cur = conn.execute(
                "UPDATE engagements SET state = ?, updated_at = ? WHERE id = ?",
                (new_state, now, engagement_id),
            )
            conn.commit()
            return cur.rowcount > 0
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            return False
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# Entity CRUD
# ═══════════════════════════════════════════════════════════════════════════

def save_entity(
    engagement_id: int,
    entity_type: str,
    name: str,
    data: dict | None = None,
    confidence: float = 1.0,
    verified: bool = False,
    parent_id: int | None = None,
) -> int:
    now = _now()
    with _LOCK:
        conn = _connect()
        try:
            cur = conn.execute(
                """INSERT INTO entities (engagement, type, name, data, confidence, verified, parent_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(engagement, type, name) DO UPDATE SET
                     data = excluded.data,
                     confidence = excluded.confidence,
                     verified = excluded.verified,
                     parent_id = COALESCE(excluded.parent_id, entities.parent_id)""",
                (engagement_id, entity_type, name, json.dumps(data or {}),
                 confidence, int(verified), parent_id, now),
            )
            conn.commit()
            return cur.lastrowid or 0
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            return 0
        finally:
            conn.close()


def get_entity(entity_id: int) -> Optional[Entity]:
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
            if not row:
                return None
            d = _row_to_dict(row)
            return Entity(
                id=d["id"], engagement=d["engagement"], type=d["type"],
                name=d["name"], data=json.loads(d["data"]),
                confidence=d["confidence"], verified=bool(d["verified"]),
                parent_id=d["parent_id"], created_at=d["created_at"],
            )
        except (sqlite3.OperationalError, sqlite3.DatabaseError, json.JSONDecodeError, OverflowError):
            return None
        finally:
            conn.close()


def query_entities(
    engagement_id: int,
    entity_type: str | None = None,
    name_pattern: str | None = None,
    limit: int = 100,
) -> list[Entity]:
    clauses = ["engagement = ?"]
    params: list = [engagement_id]
    if entity_type:
        clauses.append("type = ?")
        params.append(entity_type)
    if name_pattern:
        clauses.append("name LIKE ?")
        params.append(f"%{name_pattern}%")
    where = " AND ".join(clauses)
    with _LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                f"SELECT * FROM entities WHERE {where} ORDER BY created_at DESC LIMIT ?",
                params + [limit],
            ).fetchall()
            return [
                Entity(
                    id=r["id"], engagement=r["engagement"], type=r["type"],
                    name=r["name"], data=json.loads(r["data"]),
                    confidence=r["confidence"], verified=bool(r["verified"]),
                    parent_id=r["parent_id"], created_at=r["created_at"],
                )
                for r in rows
            ]
        except (sqlite3.OperationalError, sqlite3.DatabaseError, json.JSONDecodeError, OverflowError):
            return []
        finally:
            conn.close()


def get_entity_by_name(engagement_id: int, entity_type: str, name: str) -> Optional[Entity]:
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM entities WHERE engagement = ? AND type = ? AND name = ?",
                (engagement_id, entity_type, name),
            ).fetchone()
            if not row:
                return None
            d = _row_to_dict(row)
            return Entity(
                id=d["id"], engagement=d["engagement"], type=d["type"],
                name=d["name"], data=json.loads(d["data"]),
                confidence=d["confidence"], verified=bool(d["verified"]),
                parent_id=d["parent_id"], created_at=d["created_at"],
            )
        except (sqlite3.OperationalError, sqlite3.DatabaseError, json.JSONDecodeError, OverflowError):
            return None
        finally:
            conn.close()


def count_entities(engagement_id: int) -> dict[str, int]:
    with _LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT type, COUNT(*) as cnt FROM entities WHERE engagement = ? GROUP BY type",
                (engagement_id,),
            ).fetchall()
            return {r["type"]: r["cnt"] for r in rows}
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            return {}
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# Relationship CRUD
# ═══════════════════════════════════════════════════════════════════════════

def add_relationship(
    engagement_id: int,
    source_id: int,
    target_id: int,
    relation: str,
    data: dict | None = None,
    confidence: float = 1.0,
) -> int:
    now = _now()
    with _LOCK:
        conn = _connect()
        try:
            cur = conn.execute(
                """INSERT INTO relationships (engagement, source_id, target_id, relation, data, confidence, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(engagement, source_id, target_id, relation) DO UPDATE SET
                     data = excluded.data,
                     confidence = excluded.confidence""",
                (engagement_id, source_id, target_id, relation,
                 json.dumps(data or {}), confidence, now),
            )
            conn.commit()
            return cur.lastrowid or 0
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            return 0
        finally:
            conn.close()


def get_neighbors(
    entity_id: int,
    direction: str = "both",
    relation: str | None = None,
) -> list[dict]:
    """Get entities connected to the given entity.

    direction: 'outgoing' (source), 'incoming' (target), or 'both'
    """
    with _LOCK:
        conn = _connect()
        try:
            results = []
            if direction in ("outgoing", "both"):
                clauses = ["r.source_id = ?"]
                params: list = [entity_id]
                if relation:
                    clauses.append("r.relation = ?")
                    params.append(relation)
                where = " AND ".join(clauses)
                rows = conn.execute(
                    f"""SELECT r.*, e.type as target_type, e.name as target_name, e.data as target_data
                        FROM relationships r
                        JOIN entities e ON e.id = r.target_id
                        WHERE {where}""",
                    params,
                ).fetchall()
                for r in rows:
                    d = _row_to_dict(r)
                    d["target_data"] = json.loads(d["target_data"])
                    d["direction"] = "outgoing"
                    results.append(d)

            if direction in ("incoming", "both"):
                clauses = ["r.target_id = ?"]
                params = [entity_id]
                if relation:
                    clauses.append("r.relation = ?")
                    params.append(relation)
                where = " AND ".join(clauses)
                rows = conn.execute(
                    f"""SELECT r.*, e.type as source_type, e.name as source_name, e.data as source_data
                        FROM relationships r
                        JOIN entities e ON e.id = r.source_id
                        WHERE {where}""",
                    params,
                ).fetchall()
                for r in rows:
                    d = _row_to_dict(r)
                    d["source_data"] = json.loads(d["source_data"])
                    d["direction"] = "incoming"
                    results.append(d)

            return results
        except (sqlite3.OperationalError, sqlite3.DatabaseError, json.JSONDecodeError, OverflowError):
            return []
        finally:
            conn.close()


def get_full_graph(engagement_id: int) -> GraphView:
    with _LOCK:
        conn = _connect()
        try:
            e_rows = conn.execute(
                "SELECT * FROM entities WHERE engagement = ? ORDER BY id",
                (engagement_id,),
            ).fetchall()
            r_rows = conn.execute(
                "SELECT * FROM relationships WHERE engagement = ? ORDER BY id",
                (engagement_id,),
            ).fetchall()
            entities = [
                Entity(
                    id=r["id"], engagement=r["engagement"], type=r["type"],
                    name=r["name"], data=json.loads(r["data"]),
                    confidence=r["confidence"], verified=bool(r["verified"]),
                    parent_id=r["parent_id"], created_at=r["created_at"],
                )
                for r in e_rows
            ]
            relationships = [
                Relationship(
                    id=r["id"], engagement=r["engagement"],
                    source_id=r["source_id"], target_id=r["target_id"],
                    relation=r["relation"], data=json.loads(r["data"]),
                    confidence=r["confidence"], created_at=r["created_at"],
                )
                for r in r_rows
            ]
            return GraphView(entities=entities, relationships=relationships)
        except (sqlite3.OperationalError, sqlite3.DatabaseError, json.JSONDecodeError, OverflowError):
            return []
        finally:
            conn.close()


def get_context_summary(engagement_id: int, max_chars: int = 2000) -> str:
    """Return a bounded text summary of the knowledge graph for LLM context injection."""
    priority_types = ["host", "credential", "vulnerability", "finding", "port", "service", "technology", "subdomain", "user", "group"]
    with _LOCK:
        conn = _connect()
        try:
            lines = []
            lines.append(f"=== Knowledge Graph ({max_chars} char budget) ===")
            for etype in priority_types:
                rows = conn.execute(
                    "SELECT name, data FROM entities WHERE engagement = ? AND type = ? ORDER BY created_at DESC LIMIT 20",
                    (engagement_id, etype),
                ).fetchall()
                if rows:
                    entries = []
                    for r in rows:
                        d = json.loads(r["data"])
                        detail = d.get("version") or d.get("severity") or d.get("service") or ""
                        entries.append(f"{r['name']}" + (f" ({detail})" if detail else ""))
                    lines.append(f"{etype}: {', '.join(entries)}")
            summary = "\n".join(lines)
            if len(summary) > max_chars:
                summary = summary[:max_chars - 3] + "..."
            return summary
        except (sqlite3.OperationalError, sqlite3.DatabaseError, json.JSONDecodeError, OverflowError):
            return ""
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# Plan Task CRUD
# ═══════════════════════════════════════════════════════════════════════════

def create_task(
    engagement_id: int,
    phase: str,
    step: int,
    title: str,
    description: str = "",
    tool: str | None = None,
    entity_id: int | None = None,
    depends_on: int | None = None,
) -> int:
    now = _now()
    with _LOCK:
        conn = _connect()
        try:
            cur = conn.execute(
                """INSERT INTO plan_tasks
                   (engagement, phase, step, title, description, tool, entity_id, depends_on, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
                (engagement_id, phase, step, title, description,
                 tool, entity_id, depends_on, now, now),
            )
            conn.commit()
            return cur.lastrowid or 0
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            return 0
        finally:
            conn.close()


def update_task(
    task_id: int,
    status: str | None = None,
    result: str | None = None,
    confidence: float | None = None,
) -> bool:
    if status and status not in TASK_STATUSES:
        return False
    now = _now()
    with _LOCK:
        conn = _connect()
        try:
            sets = ["updated_at = ?"]
            params: list = [now]
            if status:
                sets.append("status = ?")
                params.append(status)
            if result is not None:
                sets.append("result = ?")
                params.append(result)
            if confidence is not None:
                sets.append("confidence = ?")
                params.append(confidence)
            params.append(task_id)
            cur = conn.execute(
                f"UPDATE plan_tasks SET {', '.join(sets)} WHERE id = ?",
                params,
            )
            conn.commit()
            return cur.rowcount > 0
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            return False
        finally:
            conn.close()


def get_next_task(engagement_id: int) -> Optional[PlanTask]:
    """Get the next pending task whose dependencies are all completed."""
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute(
                """SELECT t.* FROM plan_tasks t
                   WHERE t.engagement = ?
                     AND t.status = 'pending'
                     AND (t.depends_on IS NULL OR t.depends_on IN (
                       SELECT id FROM plan_tasks WHERE status = 'completed' AND engagement = ?
                     ))
                   ORDER BY t.phase, t.step
                   LIMIT 1""",
                (engagement_id, engagement_id),
            ).fetchone()
            if not row:
                return None
            d = _row_to_dict(row)
            return PlanTask(
                id=d["id"], engagement=d["engagement"], phase=d["phase"],
                step=d["step"], title=d["title"], description=d["description"],
                tool=d["tool"], entity_id=d["entity_id"],
                depends_on=d["depends_on"], status=d["status"],
                result=d["result"], confidence=d["confidence"],
                created_at=d["created_at"], updated_at=d["updated_at"],
            )
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            return None
        finally:
            conn.close()


def get_tasks(
    engagement_id: int,
    phase: str | None = None,
    status: str | None = None,
) -> list[PlanTask]:
    clauses = ["engagement = ?"]
    params: list = [engagement_id]
    if phase:
        clauses.append("phase = ?")
        params.append(phase)
    if status:
        clauses.append("status = ?")
        params.append(status)
    where = " AND ".join(clauses)
    with _LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                f"SELECT * FROM plan_tasks WHERE {where} ORDER BY phase, step",
                params,
            ).fetchall()
            return [
                PlanTask(
                    id=r["id"], engagement=r["engagement"], phase=r["phase"],
                    step=r["step"], title=r["title"], description=r["description"],
                    tool=r["tool"], entity_id=r["entity_id"],
                    depends_on=r["depends_on"], status=r["status"],
                    result=r["result"], confidence=r["confidence"],
                    created_at=r["created_at"], updated_at=r["updated_at"],
                )
                for r in rows
            ]
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            return []
        finally:
            conn.close()


def get_plan_summary(engagement_id: int) -> dict:
    with _LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                """SELECT status, COUNT(*) as cnt FROM plan_tasks
                   WHERE engagement = ? GROUP BY status""",
                (engagement_id,),
            ).fetchall()
            counts = {r["status"]: r["cnt"] for r in rows}
            total = sum(counts.values())
            return {
                "total": total,
                "completed": counts.get("completed", 0),
                "pending": counts.get("pending", 0),
                "in_progress": counts.get("in_progress", 0),
                "failed": counts.get("failed", 0),
                "skipped": counts.get("skipped", 0),
                "percent": round(counts.get("completed", 0) / max(total, 1) * 100),
            }
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            return {"total": 0, "completed": 0, "pending": 0, "in_progress": 0, "failed": 0, "skipped": 0, "percent": 0}
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# Decisions
# ═══════════════════════════════════════════════════════════════════════════

def add_decision(
    engagement_id: int,
    reasoning: str,
    action: str,
    context: str | None = None,
    tool_call_id: str | None = None,
) -> int:
    now = _now()
    with _LOCK:
        conn = _connect()
        try:
            cur = conn.execute(
                """INSERT INTO decisions (engagement, reasoning, action, context, tool_call_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (engagement_id, reasoning, action, context, tool_call_id, now),
            )
            conn.commit()
            return cur.lastrowid or 0
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            return 0
        finally:
            conn.close()


def get_decisions(engagement_id: int, limit: int = 20) -> list[Decision]:
    with _LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT * FROM decisions WHERE engagement = ? ORDER BY created_at DESC LIMIT ?",
                (engagement_id, limit),
            ).fetchall()
            return [
                Decision(
                    id=r["id"], engagement=r["engagement"],
                    reasoning=r["reasoning"], action=r["action"],
                    context=r["context"], tool_call_id=r["tool_call_id"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            return []
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# Tool Events
# ═══════════════════════════════════════════════════════════════════════════

def log_event(
    engagement_id: int,
    tool_name: str,
    args: dict | None = None,
    result_summary: str | None = None,
    status: str | None = None,
    duration_ms: int | None = None,
    entities_created: list[int] | None = None,
    turn_id: str | None = None,
) -> int:
    now = _now()
    with _LOCK:
        conn = _connect()
        try:
            cur = conn.execute(
                """INSERT INTO tool_events
                   (engagement, tool_name, args, result_summary, status, duration_ms, entities_created, turn_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (engagement_id, tool_name, json.dumps(args or {}),
                 result_summary, status, duration_ms,
                 json.dumps(entities_created or []), turn_id, now),
            )
            conn.commit()
            return cur.lastrowid or 0
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            return 0
        finally:
            conn.close()


def get_events(
    engagement_id: int,
    tool_name: str | None = None,
    limit: int = 50,
) -> list[ToolEvent]:
    clauses = ["engagement = ?"]
    params: list = [engagement_id]
    if tool_name:
        clauses.append("tool_name = ?")
        params.append(tool_name)
    where = " AND ".join(clauses)
    with _LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                f"SELECT * FROM tool_events WHERE {where} ORDER BY created_at DESC LIMIT ?",
                params + [limit],
            ).fetchall()
            return [
                ToolEvent(
                    id=r["id"], engagement=r["engagement"],
                    tool_name=r["tool_name"], args=json.loads(r["args"]),
                    result_summary=r["result_summary"], status=r["status"],
                    duration_ms=r["duration_ms"],
                    entities_created=json.loads(r["entities_created"]),
                    turn_id=r["turn_id"], created_at=r["created_at"],
                )
                for r in rows
            ]
        except (sqlite3.OperationalError, sqlite3.DatabaseError, json.JSONDecodeError, OverflowError):
            return []
        finally:
            conn.close()
