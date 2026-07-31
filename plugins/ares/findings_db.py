from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cyberfox_constants import get_cyberfox_home as get_cf_home

_LOCK = threading.Lock()

_SEVERITIES = ("critical", "high", "medium", "low", "info")

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS findings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    severity    TEXT NOT NULL CHECK(severity IN ('critical','high','medium','low','info')),
    category    TEXT NOT NULL DEFAULT 'general',
    target      TEXT,
    port        INTEGER,
    protocol    TEXT,
    description TEXT NOT NULL DEFAULT '',
    evidence    TEXT NOT NULL DEFAULT '',
    remediation TEXT NOT NULL DEFAULT '',
    tool        TEXT,
    cve         TEXT,
    cvss        REAL,
    status      TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','confirmed','in_progress','resolved','false_positive','wont_fix')),
    tags        TEXT NOT NULL DEFAULT '[]',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_status   ON findings(status);
CREATE INDEX IF NOT EXISTS idx_findings_target   ON findings(target);
CREATE INDEX IF NOT EXISTS idx_findings_category ON findings(category);
"""


def _db_path() -> Path:
    return get_cf_home() / "ares" / "findings.db"


def _connect() -> sqlite3.Connection:
    p = _db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _run_migrations(conn):
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    if current < 2:
        try:
            conn.execute("ALTER TABLE findings ADD COLUMN cwe TEXT DEFAULT ''")
            conn.execute("ALTER TABLE findings ADD COLUMN epss REAL")
            conn.execute("ALTER TABLE findings ADD COLUMN kev INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE findings ADD COLUMN attack_techniques TEXT DEFAULT '[]'")
            conn.execute("ALTER TABLE findings ADD COLUMN priority_score REAL")
            conn.execute("ALTER TABLE findings ADD COLUMN priority_tier TEXT DEFAULT ''")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_findings_cve ON findings(cve)")
        except sqlite3.OperationalError:
            pass
        conn.execute("PRAGMA user_version = 2")


def init_db() -> None:
    with _LOCK:
        conn = _connect()
        try:
            conn.executescript(_SCHEMA_SQL)
            _run_migrations(conn)
            conn.commit()
        finally:
            conn.close()


def add_finding(
    title: str,
    severity: str,
    description: str = "",
    category: str = "general",
    target: Optional[str] = None,
    port: Optional[int] = None,
    protocol: Optional[str] = None,
    evidence: str = "",
    remediation: str = "",
    tool: Optional[str] = None,
    cve: Optional[str] = None,
    cvss: Optional[float] = None,
    cwe: Optional[list[str]] = None,
    epss: Optional[float] = None,
    kev: bool = False,
    attack_techniques: Optional[list[str]] = None,
    priority_score: Optional[float] = None,
    priority_tier: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> int:
    severity = severity.lower().strip()
    if severity not in _SEVERITIES:
        severity = "info"

    with _LOCK:
        conn = _connect()
        try:
            now = datetime.now(timezone.utc).isoformat()
            # ponytail: dedup on title+target+severity; NULL target never matches
            row = conn.execute(
                "SELECT id FROM findings WHERE title=? AND target=? AND severity=? LIMIT 1",
                (title, target, severity),
            ).fetchone()
            if row:
                return row[0]
            cur = conn.execute(
                """INSERT INTO findings
                   (title, severity, category, target, port, protocol,
                    description, evidence, remediation, tool, cve, cvss,
                    cwe, epss, kev, attack_techniques, priority_score, priority_tier,
                    tags, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    title, severity, category, target, port, protocol,
                    description, evidence, remediation, tool, cve, cvss,
                    json.dumps(cwe or []), epss, int(kev),
                    json.dumps(attack_techniques or []),
                    priority_score, priority_tier or "",
                    json.dumps(tags or []), now, now,
                ),
            )
            conn.commit()
            return cur.lastrowid or 0
        finally:
            conn.close()


def query_findings(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    target: Optional[str] = None,
    cve: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    clauses = []
    params = []

    if severity:
        parts = [s.strip().lower() for s in severity.split(",")]
        placeholders = ",".join("?" for _ in parts)
        clauses.append(f"severity IN ({placeholders})")
        params.extend(parts)
    if status:
        clauses.append("status = ?")
        params.append(status)
    if category:
        clauses.append("category = ?")
        params.append(category)
    if target:
        clauses.append("target LIKE ?")
        params.append(f"%{target}%")
    if cve:
        clauses.append("cve = ?")
        params.append(cve)

    where = "WHERE " + " AND ".join(clauses) if clauses else ""

    with _LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                f"SELECT * FROM findings {where} ORDER BY created_at DESC LIMIT ?",
                params + [limit],
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def update_finding_status(finding_id: int, status: str) -> bool:
    valid = ("open", "confirmed", "in_progress", "resolved", "false_positive", "wont_fix")
    if status not in valid:
        return False
    with _LOCK:
        conn = _connect()
        try:
            now = datetime.now(timezone.utc).isoformat()
            cur = conn.execute(
                "UPDATE findings SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, finding_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def get_finding(finding_id: int) -> Optional[dict]:
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM findings WHERE id = ?", (finding_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def get_stats() -> dict:
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute(
                """SELECT severity, status, COUNT(*) as count
                   FROM findings GROUP BY severity, status"""
            ).fetchall()
        finally:
            conn.close()

    stats: dict = {}
    for r in row:
        key = f"{r['severity']}_{r['status']}"
        stats[key] = r["count"]
    return stats


if __name__ == "__main__":
    import os
    import tempfile

    os.environ["CYBERFOX_HOME"] = tempfile.mkdtemp()
    init_db()
    a = add_finding("Dup test", "high", target="10.0.0.1")
    b = add_finding("Dup test", "high", target="10.0.0.1")
    c = add_finding("Dup test", "high", target="10.0.0.2")
    assert a == b, "duplicate insert returned different ids"
    assert c != a, "distinct target wrongly deduped"
    assert get_stats().get("high_open", 0) == 2, "row count wrong"
    print("findings dedup OK")
