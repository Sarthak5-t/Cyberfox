from __future__ import annotations

import json

from plugins.ares.tools.base import json_result
from plugins.ares.state import engagement_store as store

TOOLSET = "ares_utility"

_KILL_CHAIN_TEMPLATE = [
    # Recon phase
    {"phase": "recon", "step": 1, "title": "Port discovery scan", "tool": "nmap_scan",
     "description": "Fast full-range port scan to identify live hosts and open ports"},
    {"phase": "recon", "step": 2, "title": "Service fingerprinting", "tool": "nmap_scan",
     "description": "Identify services and versions on discovered ports"},
    {"phase": "recon", "step": 3, "title": "Technology detection", "tool": "whatweb_scan",
     "description": "Fingerprint web technologies on HTTP services",
     "condition": "http_found"},
    {"phase": "recon", "step": 4, "title": "DNS reconnaissance", "tool": "dnsrecon_scan",
     "description": "DNS records, zone transfer, SRV records",
     "condition": "domain_in_scope"},
    # Scanning phase
    {"phase": "scanning", "step": 1, "title": "Vulnerability template scan", "tool": "nuclei_scan",
     "description": "Run Nuclei templates for known CVEs on discovered services"},
    {"phase": "scanning", "step": 2, "title": "Web directory enumeration", "tool": "gobuster_scan",
     "description": "Discover hidden paths and files on web servers",
     "condition": "http_found"},
    {"phase": "scanning", "step": 3, "title": "Web vulnerability scan", "tool": "nikto_scan",
     "description": "Web server misconfigurations and known vulnerabilities",
     "condition": "http_found"},
    {"phase": "scanning", "step": 4, "title": "Exploit research", "tool": "searchsploit_tool",
     "description": "Search for public exploits for discovered service versions"},
    # Validation phase
    {"phase": "validation", "step": 1, "title": "Validate findings", "tool": None,
     "description": "Verify discovered vulnerabilities with targeted testing"},
    # Reporting phase
    {"phase": "reporting", "step": 1, "title": "Generate report", "tool": None,
     "description": "Compile findings into structured report with CVSS scores"},
]


def _handle_init(args: dict, **kw) -> str:
    name = args.get("name", "engagement")
    scope_raw = args.get("scope", "")
    goals = args.get("goals", "")
    if isinstance(scope_raw, str):
        scope = [t.strip() for t in scope_raw.split(",") if t.strip()]
    else:
        scope = scope_raw or []
    eid = store.create_engagement(name, scope, goals)
    return json_result(True, data={
        "engagement_id": eid,
        "name": name,
        "scope": scope,
        "goals": goals,
        "state": "planning",
        "message": f"Engagement '{name}' created. Use plan_create to generate your attack plan.",
    })


def _handle_resume(args: dict, **kw) -> str:
    name = args.get("name")
    eid = args.get("engagement_id")
    eng = store.get_engagement(name=name, engagement_id=eid)
    if not eng:
        return json_result(False, error="Engagement not found. Use engage_init to create one.")
    counts = store.count_entities(eng.id)
    plan = store.get_plan_summary(eng.id)
    return json_result(True, data={
        "engagement_id": eng.id,
        "name": eng.name,
        "state": eng.state,
        "scope": eng.scope,
        "goals": eng.goals,
        "entities": counts,
        "plan": plan,
    })


def _handle_status(args: dict, **kw) -> str:
    eng = store.get_engagement()
    if not eng:
        return json_result(False, error="No active engagement. Use engage_init to start one.")
    counts = store.count_entities(eng.id)
    plan = store.get_plan_summary(eng.id)
    recent_decisions = store.get_decisions(eng.id, limit=5)
    return json_result(True, data={
        "engagement_id": eng.id,
        "name": eng.name,
        "state": eng.state,
        "scope": eng.scope,
        "entities": counts,
        "plan": plan,
        "recent_decisions": [
            {"reasoning": d.reasoning, "action": d.action, "at": d.created_at}
            for d in recent_decisions
        ],
    })


_INIT_SCHEMA = {
    "name": "engage_init",
    "description": "Initialize a new engagement. Call this FIRST at the start of any pentest, CTF, or security assessment. Creates the engagement database and sets up structured state tracking.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Engagement name (e.g. 'CTF Challenge 1', 'Corporate Pentest')"},
            "scope": {"type": "string", "description": "Comma-separated targets (e.g. '10.10.10.0/24, example.com')"},
            "goals": {"type": "string", "description": "Engagement goals (e.g. 'Find RCE on web app', 'Escalate to Domain Admin')"},
        },
        "required": ["name"],
    },
}

_RESUME_SCHEMA = {
    "name": "engage_resume",
    "description": "Resume a previous engagement by name or ID. Loads all saved state, entities, and plan progress.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Engagement name to resume"},
            "engagement_id": {"type": "integer", "description": "Engagement ID to resume"},
        },
    },
}

_STATUS_SCHEMA = {
    "name": "engage_status",
    "description": "Get current engagement status: state, entity counts, plan progress, and recent decisions.",
    "parameters": {"type": "object", "properties": {}},
}


def register_tools(ctx) -> None:
    store.init_db()
    ctx.register_tool(
        name="engage_init",
        toolset=TOOLSET,
        schema=_INIT_SCHEMA,
        handler=lambda args, **kw: _handle_init(args, **kw),
        emoji="🎯",
    )
    ctx.register_tool(
        name="engage_resume",
        toolset=TOOLSET,
        schema=_RESUME_SCHEMA,
        handler=lambda args, **kw: _handle_resume(args, **kw),
        emoji="🔄",
    )
    ctx.register_tool(
        name="engage_status",
        toolset=TOOLSET,
        schema=_STATUS_SCHEMA,
        handler=lambda args, **kw: _handle_status(args, **kw),
        emoji="📊",
    )
