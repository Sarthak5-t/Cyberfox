from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"


def _handle(args: dict, **kw) -> str:
    domain = args.get("domain", "")
    source = args.get("source", "all")
    limit = args.get("limit", 500)
    if not domain:
        return json_result(False, error="domain is required")
    if not check_binary("theHarvester"):
        return json_result(False, error="theHarvester not found on PATH")
    try:
        argv = ["theHarvester", "-d", domain, "-b", source, "-l", str(int(limit))]
        result = run_command_argv(argv, timeout=300)
        output = result.stdout.strip()[:50000]
        if result.returncode != 0 and not output:
            return json_result(False, error=result.stderr.strip() or f"theHarvester exited {result.returncode}")
        return json_result(True, data={
            "domain": domain,
            "source": source,
            "output": output,
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "theharvester_scan",
    "description": "OSINT email and subdomain enumeration using theHarvester.",
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "Target domain"},
            "source": {"type": "string", "default": "all", "description": "Data source"},
            "limit": {"type": "integer", "default": 500, "description": "Max results per source"},
        },
        "required": ["domain"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="theharvester_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🔍",
    )
