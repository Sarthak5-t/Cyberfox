from __future__ import annotations

import json

from plugins.ares.tools.base import json_result
from plugins.ares.findings_db import (
    add_finding,
    query_findings,
    update_finding_status,
    get_finding,
    get_stats,
    init_db,
)

TOOLSET = "ares_utility"


def _handle_save(args: dict, **kw) -> str:
    fid = add_finding(
        title=args.get("title", ""),
        severity=args.get("severity", "info"),
        description=args.get("description", ""),
        category=args.get("category", "general"),
        target=args.get("target"),
        port=args.get("port"),
        protocol=args.get("protocol"),
        evidence=args.get("evidence", ""),
        remediation=args.get("remediation", ""),
        tool=args.get("tool"),
        cve=args.get("cve"),
        cvss=args.get("cvss"),
        tags=args.get("tags"),
    )
    return json_result(True, data={"finding_id": fid})


def _handle_query(args: dict, **kw) -> str:
    results = query_findings(
        severity=args.get("severity"),
        status=args.get("status"),
        category=args.get("category"),
        target=args.get("target"),
        limit=args.get("limit", 50),
    )
    return json_result(True, data={"count": len(results), "findings": results})


def _handle_update(args: dict, **kw) -> str:
    ok = update_finding_status(
        finding_id=args["finding_id"],
        status=args["status"],
    )
    return json_result(ok, error="Finding not found" if not ok else None)


def _handle_stats(args: dict, **kw) -> str:
    stats = get_stats()
    return json_result(True, data=stats)


_SAVE_SCHEMA = {
    "name": "findings_save",
    "description": "Save a security finding to the persistent findings database. Call this each time you discover something — do NOT wait until the end of the engagement.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short finding title (e.g. 'Open SMB port on DC01')"},
            "severity": {
                "type": "string",
                "enum": ["critical", "high", "medium", "low", "info"],
                "description": "Severity level",
            },
            "description": {"type": "string", "description": "Detailed description of the finding"},
            "category": {
                "type": "string",
                "enum": ["recon", "scanning", "exploit", "ad", "general"],
                "description": "Phase category",
            },
            "target": {"type": "string", "description": "Target IP or hostname"},
            "port": {"type": "integer", "description": "Port number"},
            "protocol": {"type": "string", "description": "Protocol (tcp, udp, http, smb, ...)"},
            "evidence": {"type": "string", "description": "Command output, proof, or excerpt"},
            "remediation": {"type": "string", "description": "Recommended fix"},
            "tool": {"type": "string", "description": "Tool that discovered this finding"},
            "cve": {"type": "string", "description": "CVE identifier if applicable"},
            "cvss": {"type": "number", "description": "CVSS 3.1 score"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for categorization",
            },
        },
        "required": ["title", "severity"],
    },
}

_QUERY_SCHEMA = {
    "name": "findings_query",
    "description": "Query the findings database. Filter by severity, status, category, or target. Returns recent findings sorted by date.",
    "parameters": {
        "type": "object",
        "properties": {
            "severity": {
                "type": "string",
                "description": "Filter by severity (comma-separated: critical,high,medium,low,info)",
            },
            "status": {
                "type": "string",
                "enum": ["open", "confirmed", "in_progress", "resolved", "false_positive"],
                "description": "Filter by status",
            },
            "category": {
                "type": "string",
                "enum": ["recon", "scanning", "exploit", "ad", "general"],
                "description": "Filter by phase category",
            },
            "target": {"type": "string", "description": "Filter by target IP/hostname (partial match)"},
            "limit": {"type": "integer", "description": "Max results (default 50)"},
        },
    },
}

_UPDATE_SCHEMA = {
    "name": "findings_update",
    "description": "Update a finding's status (e.g. mark as resolved or false_positive).",
    "parameters": {
        "type": "object",
        "properties": {
            "finding_id": {"type": "integer", "description": "Finding ID from findings_save or findings_query"},
            "status": {
                "type": "string",
                "enum": ["open", "confirmed", "in_progress", "resolved", "false_positive", "wont_fix"],
                "description": "New status",
            },
        },
        "required": ["finding_id", "status"],
    },
}

_STATS_SCHEMA = {
    "name": "findings_stats",
    "description": "Get aggregate statistics from the findings database (counts by severity and status).",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


def register_tools(ctx) -> None:
    init_db()
    ctx.register_tool(
        name="findings_save",
        toolset=TOOLSET,
        schema=_SAVE_SCHEMA,
        handler=lambda args, **kw: _handle_save(args, **kw),
        emoji="💾",
    )
    ctx.register_tool(
        name="findings_query",
        toolset=TOOLSET,
        schema=_QUERY_SCHEMA,
        handler=lambda args, **kw: _handle_query(args, **kw),
        emoji="🔍",
    )
    ctx.register_tool(
        name="findings_update",
        toolset=TOOLSET,
        schema=_UPDATE_SCHEMA,
        handler=lambda args, **kw: _handle_update(args, **kw),
        emoji="📝",
    )
    ctx.register_tool(
        name="findings_stats",
        toolset=TOOLSET,
        schema=_STATS_SCHEMA,
        handler=lambda args, **kw: _handle_stats(args, **kw),
        emoji="📊",
    )
