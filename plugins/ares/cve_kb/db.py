from __future__ import annotations

import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cyberfox_constants import get_cyberfox_home as get_cf_home

import logging

logger = logging.getLogger(__name__)

_LOCK = threading.RLock()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cve_entries (
    cve_id      TEXT PRIMARY KEY,
    description TEXT NOT NULL DEFAULT '',
    product     TEXT NOT NULL DEFAULT '',
    version     TEXT NOT NULL DEFAULT '',
    cwe         TEXT NOT NULL DEFAULT '',
    published   TEXT NOT NULL DEFAULT '',
    cvss        REAL,
    cvss_vector TEXT NOT NULL DEFAULT '',
    severity    TEXT NOT NULL DEFAULT '',
    source      TEXT NOT NULL DEFAULT 'repo'
);

CREATE TABLE IF NOT EXISTS cve_pocs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    cve_id       TEXT NOT NULL REFERENCES cve_entries(cve_id),
    url          TEXT NOT NULL,
    repo_name    TEXT NOT NULL DEFAULT '',
    stars        INTEGER DEFAULT 0,
    description  TEXT NOT NULL DEFAULT '',
    language     TEXT NOT NULL DEFAULT '',
    last_checked TEXT,
    UNIQUE(cve_id, url)
);

CREATE TABLE IF NOT EXISTS cve_references (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    cve_id TEXT NOT NULL REFERENCES cve_entries(cve_id),
    url    TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    UNIQUE(cve_id, url)
);

CREATE TABLE IF NOT EXISTS kb_metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS cve_searches USING fts5(
    cve_id,
    description,
    product,
    content='cve_entries',
    content_rowid='rowid'
);

CREATE INDEX IF NOT EXISTS idx_pocs_cve ON cve_pocs(cve_id);
CREATE INDEX IF NOT EXISTS idx_refs_cve ON cve_references(cve_id);
CREATE INDEX IF NOT EXISTS idx_entries_published ON cve_entries(published);
CREATE INDEX IF NOT EXISTS idx_entries_severity ON cve_entries(severity);
CREATE INDEX IF NOT EXISTS idx_entries_cvss ON cve_entries(cvss);
"""


def db_path() -> Path:
    return get_cf_home() / "ares" / "cve_kb.db"


def _connect() -> sqlite3.Connection:
    p = db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with _LOCK:
        conn = _connect()
        try:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()


def get_metadata(key: str) -> str | None:
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT value FROM kb_metadata WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else None
        finally:
            conn.close()


def set_metadata(key: str, value: str) -> None:
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO kb_metadata (key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()
        finally:
            conn.close()


def bulk_insert_entries(entries: list[dict]) -> int:
    with _LOCK:
        conn = _connect()
        try:
            count = 0
            for e in entries:
                existing = conn.execute(
                    "SELECT description, product, version, cwe FROM cve_entries WHERE cve_id = ?",
                    (e["cve_id"],),
                ).fetchone()
                if existing:
                    conn.execute(
                        """UPDATE cve_entries SET
                           description = CASE WHEN ? != '' THEN ? ELSE description END,
                           product     = CASE WHEN ? != '' THEN ? ELSE product END,
                           version     = CASE WHEN ? != '' THEN ? ELSE version END,
                           cwe         = CASE WHEN ? != '' THEN ? ELSE cwe END,
                           published   = CASE WHEN ? != '' THEN ? ELSE published END,
                           cvss        = CASE WHEN ? IS NOT NULL THEN ? ELSE cvss END,
                           cvss_vector = CASE WHEN ? != '' THEN ? ELSE cvss_vector END,
                           severity    = CASE WHEN ? != '' THEN ? ELSE severity END
                           WHERE cve_id = ?""",
                        (
                            e.get("description", ""), e.get("description", ""),
                            e.get("product", ""), e.get("product", ""),
                            e.get("version", ""), e.get("version", ""),
                            e.get("cwe", ""), e.get("cwe", ""),
                            e.get("published", ""), e.get("published", ""),
                            e.get("cvss"), e.get("cvss"),
                            e.get("cvss_vector", ""), e.get("cvss_vector", ""),
                            e.get("severity", ""), e.get("severity", ""),
                            e["cve_id"],
                        ),
                    )
                    count += 1
                else:
                    conn.execute(
                        """INSERT INTO cve_entries
                           (cve_id, description, product, version, cwe, published, cvss, cvss_vector, severity, source)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            e["cve_id"],
                            e.get("description", ""),
                            e.get("product", ""),
                            e.get("version", ""),
                            e.get("cwe", ""),
                            e.get("published", ""),
                            e.get("cvss"),
                            e.get("cvss_vector", ""),
                            e.get("severity", ""),
                            e.get("source", "repo"),
                        ),
                    )
                    count += 1
            conn.commit()
            return count
        finally:
            conn.close()


def bulk_insert_pocs(pocs: list[dict]) -> int:
    if not pocs:
        return 0
    with _LOCK:
        conn = _connect()
        try:
            known = set(
                row["cve_id"]
                for row in conn.execute(
                    "SELECT cve_id FROM cve_entries"
                ).fetchall()
            )
            count = 0
            for p in pocs:
                if p["cve_id"] not in known:
                    conn.execute(
                        "INSERT OR IGNORE INTO cve_entries (cve_id, description, source) VALUES (?, ?, ?)",
                        (p["cve_id"], "", "auto_created"),
                    )
                    known.add(p["cve_id"])
                conn.execute(
                    """INSERT OR IGNORE INTO cve_pocs
                       (cve_id, url, repo_name, stars, description, language, last_checked)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        p["cve_id"],
                        p["url"],
                        p.get("repo_name", ""),
                        p.get("stars", 0),
                        p.get("description", ""),
                        p.get("language", ""),
                        p.get("last_checked"),
                    ),
                )
                count += conn.total_changes
            conn.commit()
            return count
        finally:
            conn.close()


def bulk_insert_references(refs: list[dict]) -> int:
    if not refs:
        return 0
    with _LOCK:
        conn = _connect()
        try:
            known = set(
                row["cve_id"]
                for row in conn.execute(
                    "SELECT cve_id FROM cve_entries"
                ).fetchall()
            )
            count = 0
            for r in refs:
                if r["cve_id"] not in known:
                    conn.execute(
                        "INSERT OR IGNORE INTO cve_entries (cve_id, description, source) VALUES (?, ?, ?)",
                        (r["cve_id"], "", "auto_created"),
                    )
                    known.add(r["cve_id"])
                conn.execute(
                    """INSERT OR IGNORE INTO cve_references (cve_id, url, source)
                       VALUES (?, ?, ?)""",
                    (r["cve_id"], r["url"], r.get("source", "")),
                )
                count += conn.total_changes
            conn.commit()
            return count
        finally:
            conn.close()


def rebuild_fts() -> None:
    with _LOCK:
        conn = _connect()
        try:
            conn.executescript(
                "INSERT INTO cve_searches(cve_searches) VALUES('rebuild')"
            )
            conn.commit()
        finally:
            conn.close()


def search_cves(
    query: str, limit: int = 20, year: str | None = None
) -> list[dict]:
    with _LOCK:
        conn = _connect()
        try:
            if year:
                rows = conn.execute(
                    """SELECT e.*, (SELECT COUNT(*) FROM cve_pocs p WHERE p.cve_id = e.cve_id) as poc_count
                       FROM cve_entries e
                       WHERE e.cve_id LIKE ?
                       ORDER BY e.published DESC LIMIT ?""",
                    (f"CVE-{year}-%", limit),
                ).fetchall()
            else:
                sanitized = " ".join(
                    f'"{t}"' if re.search(r"[^a-zA-Z0-9*]", t) else t
                    for t in query.split()
                )
                rows = conn.execute(
                    """SELECT e.*, (SELECT COUNT(*) FROM cve_pocs p WHERE p.cve_id = e.cve_id) as poc_count
                       FROM cve_searches s
                       JOIN cve_entries e ON e.rowid = s.rowid
                       WHERE s.cve_searches MATCH ?
                       ORDER BY rank
                       LIMIT ?""",
                    (sanitized, limit),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def lookup_cve(cve_id: str) -> dict | None:
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM cve_entries WHERE cve_id = ?", (cve_id,)
            ).fetchone()
            if not row:
                return None
            entry = dict(row)
            entry["pocs"] = [
                dict(p)
                for p in conn.execute(
                    "SELECT * FROM cve_pocs WHERE cve_id = ? ORDER BY stars DESC",
                    (cve_id,),
                ).fetchall()
            ]
            entry["references"] = [
                dict(r)
                for r in conn.execute(
                    "SELECT url, source FROM cve_references WHERE cve_id = ?",
                    (cve_id,),
                ).fetchall()
            ]
            return entry
        finally:
            conn.close()


def get_pocs_for_cve(cve_id: str) -> list[dict]:
    with _LOCK:
        conn = _connect()
        try:
            return [
                dict(p)
                for p in conn.execute(
                    "SELECT * FROM cve_pocs WHERE cve_id = ? ORDER BY stars DESC",
                    (cve_id,),
                ).fetchall()
            ]
        finally:
            conn.close()


def get_stats() -> dict:
    with _LOCK:
        conn = _connect()
        try:
            total = conn.execute("SELECT COUNT(*) as c FROM cve_entries").fetchone()["c"]
            with_pocs = conn.execute(
                "SELECT COUNT(DISTINCT cve_id) as c FROM cve_pocs"
            ).fetchone()["c"]
            total_pocs = conn.execute("SELECT COUNT(*) as c FROM cve_pocs").fetchone()["c"]
            total_refs = conn.execute(
                "SELECT COUNT(*) as c FROM cve_references"
            ).fetchone()["c"]
            newest = [
                dict(r)
                for r in conn.execute(
                    "SELECT cve_id, description FROM cve_entries ORDER BY published DESC LIMIT 5"
                ).fetchall()
            ]
            by_severity = {
                r["severity"]: r["c"]
                for r in conn.execute(
                    "SELECT severity, COUNT(*) as c FROM cve_entries WHERE severity != '' GROUP BY severity"
                ).fetchall()
            }
            last_synced = get_metadata("last_synced")
            return {
                "total_cves": total,
                "cves_with_pocs": with_pocs,
                "total_poc_links": total_pocs,
                "total_references": total_refs,
                "pct_with_pocs": round(with_pocs / total * 100, 1) if total else 0,
                "newest_cves": newest,
                "by_severity": by_severity,
                "last_synced": last_synced or "never",
            }
        finally:
            conn.close()


def get_poc_repos_stale(hours: int = 24, limit: int = 50) -> list[dict]:
    with _LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                """SELECT DISTINCT url FROM cve_pocs
                   WHERE last_checked IS NULL
                      OR datetime(last_checked) < datetime('now', ?)
                   ORDER BY last_checked ASC NULLS FIRST
                   LIMIT ?""",
                (f"-{hours} hours", limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def update_poc_metadata(url: str, stars: int, description: str, language: str) -> None:
    with _LOCK:
        conn = _connect()
        try:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """UPDATE cve_pocs SET stars = ?, description = ?, language = ?, last_checked = ?
                   WHERE url = ?""",
                (stars, description, language, now, url),
            )
            conn.commit()
        finally:
            conn.close()
