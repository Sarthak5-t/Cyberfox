from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

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
        cmd = f"theHarvester -d {shlex.quote(domain)} -b {shlex.quote(source)} -l {int(limit)}"
        result = run_command(cmd, timeout=300)
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
    "description": "OSINT email and subdomain enumeration using theHarvester. Gathers emails, subdomains, IPs, and hosts from public sources.",
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Target domain to harvest (e.g. 'example.com')",
            },
            "source": {
                "type": "string",
                "default": "all",
                "description": "Data source: all, bing, google, linkedin, twitter, dnsdumpster, crtsh, etc.",
            },
            "limit": {
                "type": "integer",
                "default": 500,
                "description": "Maximum results per source",
            },
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
