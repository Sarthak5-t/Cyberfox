from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cyberfox_constants import get_cyberfox_home as get_cf_home

from plugins.ares.enrichment.nvd_client import NVDClient
from plugins.ares.enrichment.epss_client import EPSSClient
from plugins.ares.enrichment.kev_client import KEVClient
from plugins.ares.enrichment.attack_mapper import map_cwe_to_attack
from plugins.ares.enrichment.priority import calculate_priority

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_CACHE_TTL = 86400

_CACHE_SCHEMA = """
CREATE TABLE IF NOT EXISTS cve_enrichment (
    cve_id          TEXT PRIMARY KEY,
    nvd_data        TEXT NOT NULL DEFAULT '{}',
    epss_score      REAL,
    epss_percentile REAL,
    epss_date       TEXT,
    kev             INTEGER NOT NULL DEFAULT 0,
    kev_data        TEXT NOT NULL DEFAULT '{}',
    attack_mapping  TEXT NOT NULL DEFAULT '[]',
    priority_score  REAL,
    priority_tier   TEXT,
    enriched_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cve_enriched ON cve_enrichment(enriched_at);
"""


def _db_path() -> Path:
    return get_cf_home() / "ares" / "enrichment_cache.db"


def _connect() -> sqlite3.Connection:
    p = _db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_cache_db() -> None:
    with _LOCK:
        conn = _connect()
        try:
            conn.executescript(_CACHE_SCHEMA)
            conn.commit()
        finally:
            conn.close()


def _get_cached(cve_id: str) -> Optional[dict]:
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM cve_enrichment WHERE cve_id = ?", (cve_id,)
            ).fetchone()
            if not row:
                return None
            enriched_at = row["enriched_at"]
            try:
                dt = datetime.fromisoformat(enriched_at)
                age = (datetime.now(timezone.utc) - dt).total_seconds()
                if age > _CACHE_TTL:
                    return None
            except Exception:
                return None
            return {
                "cve_id": row["cve_id"],
                "nvd_data": json.loads(row["nvd_data"]),
                "epss_score": row["epss_score"],
                "epss_percentile": row["epss_percentile"],
                "epss_date": row["epss_date"],
                "kev": bool(row["kev"]),
                "kev_data": json.loads(row["kev_data"]),
                "attack_mapping": json.loads(row["attack_mapping"]),
                "priority_score": row["priority_score"],
                "priority_tier": row["priority_tier"],
                "cached": True,
            }
        finally:
            conn.close()


def _save_cache(cve_id: str, data: dict) -> None:
    with _LOCK:
        conn = _connect()
        try:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """INSERT INTO cve_enrichment
                   (cve_id, nvd_data, epss_score, epss_percentile, epss_date,
                    kev, kev_data, attack_mapping, priority_score, priority_tier, enriched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(cve_id) DO UPDATE SET
                     nvd_data = excluded.nvd_data,
                     epss_score = excluded.epss_score,
                     epss_percentile = excluded.epss_percentile,
                     epss_date = excluded.epss_date,
                     kev = excluded.kev,
                     kev_data = excluded.kev_data,
                     attack_mapping = excluded.attack_mapping,
                     priority_score = excluded.priority_score,
                     priority_tier = excluded.priority_tier,
                     enriched_at = excluded.enriched_at""",
                (
                    cve_id,
                    json.dumps(data.get("nvd_data", {})),
                    data.get("epss_score"),
                    data.get("epss_percentile"),
                    data.get("epss_date"),
                    int(data.get("kev", False)),
                    json.dumps(data.get("kev_data", {})),
                    json.dumps(data.get("attack_mapping", [])),
                    data.get("priority_score"),
                    data.get("priority_tier"),
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def enrich_cve(
    cve_id: str,
    nvd_client: NVDClient,
    epss_client: EPSSClient,
    kev_client: KEVClient,
    has_exploit: bool = False,
) -> dict:
    cached = _get_cached(cve_id)
    if cached:
        return cached

    enriched: dict = {"cve_id": cve_id, "cached": False}

    try:
        nvd_data = nvd_client.get_cve(cve_id)
        if nvd_data:
            enriched["nvd_data"] = nvd_data
        else:
            enriched["nvd_data"] = {}
    except Exception as e:
        logger.warning("NVD lookup failed for %s: %s", cve_id, e)
        enriched["nvd_data"] = {}

    try:
        epss_data = epss_client.get_epss(cve_id)
        if epss_data:
            enriched.update(epss_data)
    except Exception as e:
        logger.warning("EPSS lookup failed for %s: %s", cve_id, e)

    try:
        kev_data = kev_client.is_in_kev(cve_id)
        if kev_data:
            enriched["kev"] = True
            enriched["kev_data"] = kev_data
        else:
            enriched["kev"] = False
            enriched["kev_data"] = {}
    except Exception as e:
        logger.warning("KEV lookup failed for %s: %s", cve_id, e)
        enriched["kev"] = False
        enriched.setdefault("kev_data", {})

    cwe_list = enriched.get("nvd_data", {}).get("cwe", [])
    enriched["attack_mapping"] = map_cwe_to_attack(cwe_list)

    cvss = enriched.get("nvd_data", {}).get("cvss_score")
    epss = enriched.get("epss_score")
    in_kev = enriched.get("kev", False)
    priority = calculate_priority(cvss, epss, in_kev, has_exploit)
    enriched["priority_score"] = priority["priority_score"]
    enriched["priority_tier"] = priority["priority_tier"]

    _save_cache(cve_id, enriched)
    return enriched


def enrich_cves_batch(
    cve_ids: list[str],
    nvd_client: NVDClient,
    epss_client: EPSSClient,
    kev_client: KEVClient,
) -> dict[str, dict]:
    results: dict[str, dict] = {}
    uncached: list[str] = []

    for cve_id in cve_ids:
        cached = _get_cached(cve_id)
        if cached:
            results[cve_id] = cached
        else:
            uncached.append(cve_id)

    if not uncached:
        return results

    epss_batch: dict[str, dict] = {}
    try:
        epss_batch = epss_client.get_epss_batch(uncached)
    except Exception as e:
        logger.warning("EPSS batch lookup failed: %s", e)

    for cve_id in uncached:
        enriched: dict = {"cve_id": cve_id, "cached": False}

        try:
            nvd_data = nvd_client.get_cve(cve_id)
            if nvd_data:
                enriched["nvd_data"] = nvd_data
            else:
                enriched["nvd_data"] = {}
        except Exception:
            enriched["nvd_data"] = {}

        if cve_id in epss_batch:
            enriched.update(epss_batch[cve_id])

        try:
            kev_data = kev_client.is_in_kev(cve_id)
            if kev_data:
                enriched["kev"] = True
                enriched["kev_data"] = kev_data
            else:
                enriched["kev"] = False
                enriched["kev_data"] = {}
        except Exception:
            enriched["kev"] = False
            enriched.setdefault("kev_data", {})

        cwe_list = enriched.get("nvd_data", {}).get("cwe", [])
        enriched["attack_mapping"] = map_cwe_to_attack(cwe_list)

        cvss = enriched.get("nvd_data", {}).get("cvss_score")
        epss = enriched.get("epss_score")
        priority = calculate_priority(cvss, epss, enriched.get("kev", False), False)
        enriched["priority_score"] = priority["priority_score"]
        enriched["priority_tier"] = priority["priority_tier"]

        _save_cache(cve_id, enriched)
        results[cve_id] = enriched

    return results
