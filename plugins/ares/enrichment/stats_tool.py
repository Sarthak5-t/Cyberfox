from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from cyberfox_constants import get_cyberfox_home as get_cf_home

from plugins.ares.tools.base import json_result

TOOLSET = "ares_utility"

SCHEMA = {
    "name": "enrichment_stats",
    "description": "Show CVE enrichment cache statistics and top prioritized vulnerabilities.",
    "parameters": {
        "type": "object",
        "properties": {
            "top_n": {
                "type": "integer",
                "default": 10,
                "description": "Number of top-priority CVEs to show",
            },
        },
    },
}


def _handle(args: dict, **kw) -> str:
    db_path = get_cf_home() / "ares" / "enrichment_cache.db"
    if not db_path.exists():
        return json_result(True, data={"total": 0, "message": "No enrichment cache found"})

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    top_n = args.get("top_n", 10)

    total = conn.execute("SELECT COUNT(*) FROM cve_enrichment").fetchone()[0]
    kev_count = conn.execute(
        "SELECT COUNT(*) FROM cve_enrichment WHERE kev = 1"
    ).fetchone()[0]

    top = conn.execute(
        "SELECT cve_id, priority_tier, priority_score, kev "
        "FROM cve_enrichment ORDER BY priority_score ASC LIMIT ?",
        (top_n,),
    ).fetchall()

    tiers = conn.execute(
        "SELECT priority_tier, COUNT(*) as count "
        "FROM cve_enrichment GROUP BY priority_tier"
    ).fetchall()

    conn.close()

    return json_result(True, data={
        "total_enriched": total,
        "kev_count": kev_count,
        "tier_distribution": {r["priority_tier"]: r["count"] for r in tiers},
        "top_priority": [
            {
                "cve_id": r["cve_id"],
                "tier": r["priority_tier"],
                "score": r["priority_score"],
                "kev": bool(r["kev"]),
            }
            for r in top
        ],
    })


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="enrichment_stats",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="📊",
    )
