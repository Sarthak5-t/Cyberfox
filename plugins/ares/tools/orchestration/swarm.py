from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import json_result, tool_error
from plugins.ares.state import engagement_store as store
from plugins.ares.tools.orchestration.swarm_helpers import (
    AgentSpec,
    SwarmState,
    build_phase2_tasks,
    build_stealth_tasks,
    build_aggressive_tasks,
)

logger = logging.getLogger(__name__)

TOOLSET = "ares_utility"

SCHEMA = {
    "name": "swarm_dispatch",
    "description": "Dispatch parallel specialist agents for concurrent recon, scanning, and exploitation. Supports multiple strategies for different engagement scenarios.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target IP, range, or domain",
            },
            "strategy": {
                "type": "string",
                "enum": ["recon_first", "parallel_full", "stealth", "aggressive"],
                "default": "recon_first",
                "description": "Execution strategy",
            },
            "max_agents": {
                "type": "integer",
                "default": 3,
                "minimum": 1,
                "maximum": 5,
                "description": "Max parallel agents",
            },
            "focus": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["recon", "web", "network", "ad", "exploit"],
                },
                "description": "Focus areas (default: all applicable)",
            },
        },
        "required": ["target"],
    },
}


def _handle(args: dict, **kw) -> str:
    parent_agent = kw.get("parent_agent")
    target = args.get("target", "")
    strategy = args.get("strategy", "recon_first")
    max_agents = min(args.get("max_agents", 3), 5)
    focus = args.get("focus", ["recon", "web", "network", "exploit"])

    if not target:
        return tool_error("target is required")

    eng = store.get_engagement()
    if not eng:
        eng_id = store.create_engagement(name=f"swarm-{target}", scope=[target])
    else:
        eng_id = eng.id

    swarm_state = SwarmState(
        engagement_id=eng_id,
        target=target,
        max_agents=max_agents,
    )

    try:
        from tools.delegate_tool import delegate_task as _delegate_task
    except ImportError:
        return tool_error("delegate_task not available — cannot dispatch swarm agents")

    results = []

    if strategy == "recon_first":
        recon_goal = (
            f"Reconnaissance on {target}. "
            f"Run nmap_scan(quick), subdomain_enum, dnsrecon_scan, whatweb_scan. "
            f"Save all discovered hosts, ports, services with findings_save. "
            f"Save entities with entity_save."
        )
        recon_result = _delegate_task(
            goal=recon_goal,
            context=f"Target: {target}. Phase 1 of swarm: reconnaissance.",
            role="leaf",
            max_iterations=50,
            background=False,
            parent_agent=parent_agent,
        )
        results.append({"phase": "recon", "result": recon_result})

        eng = store.get_engagement()
        if eng:
            findings = store.query_entities(eng.id, entity_type="service")
            findings_dicts = [f.to_dict() for f in findings]
        else:
            findings_dicts = []

        phase2 = build_phase2_tasks(findings_dicts, focus, target)
        if phase2:
            batch_result = _delegate_task(
                tasks=phase2,
                role="leaf",
                max_iterations=50,
                background=False,
                parent_agent=parent_agent,
            )
            results.append({"phase": "scan_exploit", "result": batch_result})

    elif strategy == "parallel_full":
        all_tasks = _build_all_tasks(target, focus)
        batch_result = _delegate_task(
            tasks=all_tasks,
            role="leaf",
            max_iterations=50,
            background=False,
            parent_agent=parent_agent,
        )
        results.append({"phase": "parallel", "result": batch_result})

    elif strategy == "stealth":
        stealth_tasks = build_stealth_tasks(target)
        recon_result = _delegate_task(
            tasks=stealth_tasks,
            role="leaf",
            max_iterations=50,
            background=False,
            parent_agent=parent_agent,
        )
        results.append({"phase": "stealth_recon", "result": recon_result})

        eng = store.get_engagement()
        if eng:
            findings = store.query_entities(eng.id, entity_type="service")
            findings_dicts = [f.to_dict() for f in findings]
        else:
            findings_dicts = []

        if findings_dicts:
            targeted = _build_targeted_tasks(findings_dicts, target)
            if targeted:
                targeted_result = _delegate_task(
                    tasks=targeted,
                    role="leaf",
                    max_iterations=50,
                    background=False,
                    parent_agent=parent_agent,
                )
                results.append({"phase": "targeted_exploit", "result": targeted_result})

    elif strategy == "aggressive":
        aggressive_tasks = build_aggressive_tasks(target, focus)
        batch_result = _delegate_task(
            tasks=aggressive_tasks,
            role="leaf",
            max_iterations=50,
            background=False,
            parent_agent=parent_agent,
        )
        results.append({"phase": "aggressive", "result": batch_result})

    eng = store.get_engagement()
    stats = store.count_entities(eng.id) if eng else {}

    return json_result(True, data={
        "strategy": strategy,
        "target": target,
        "max_agents": max_agents,
        "phases_completed": len(results),
        "entities_discovered": stats,
        "engagement_id": eng_id,
        "results": results,
    })


def _build_all_tasks(target: str, focus: list[str]) -> list[dict]:
    tasks = []
    if "recon" in focus:
        tasks.append({
            "goal": (
                f"Recon on {target}. Run nmap_scan(quick), subdomain_enum, "
                f"dnsrecon_scan, whatweb_scan. Save all findings."
            ),
            "context": f"Target: {target}",
        })
    if "web" in focus:
        tasks.append({
            "goal": (
                f"Web scan on {target}. Run nuclei_scan, gobuster_scan, "
                f"nikto_scan, wafw00f_scan. Save all findings."
            ),
            "context": f"Target: {target}",
        })
    if "network" in focus:
        tasks.append({
            "goal": (
                f"Network scan on {target}. Run enum4linux_scan, "
                f"smbclient_tool, snmpwalk_tool. Save all findings."
            ),
            "context": f"Target: {target}",
        })
    if "exploit" in focus:
        tasks.append({
            "goal": (
                f"Exploit on {target}. Searchsploit for each service, "
                f"attempt critical/high vulns. Save all results."
            ),
            "context": f"Target: {target}",
        })
    return tasks


def _build_targeted_tasks(findings: list[dict], target: str) -> list[dict]:
    tasks = []
    services = [f for f in findings if f.get("type") == "service"]
    http_services = [
        s for s in services
        if "http" in s.get("data", {}).get("service", "").lower()
    ]
    if http_services:
        host = http_services[0].get("data", {}).get("host", target)
        tasks.append({
            "goal": (
                f"Targeted web scan on {host}. "
                f"Run nuclei_scan, nikto_scan. Save findings."
            ),
            "context": json.dumps(http_services[:5]),
        })
    return tasks


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="swarm_dispatch",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🐝",
    )
