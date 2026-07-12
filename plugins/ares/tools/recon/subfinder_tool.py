from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"


def _handle(args: dict, **kw) -> str:
    domain = args.get("domain", "")
    sources = args.get("sources", "all")
    if not check_binary("subfinder"):
        return json_result(False, error="subfinder not found on PATH")
    try:
        argv = ["subfinder", "-d", domain, "-oJ"]
        if sources and sources != "all":
            argv.extend(["-sources", sources])
        result = run_command_argv(argv, timeout=180)
        if result.returncode != 0:
            return json_result(False, error=result.stderr.strip() or f"subfinder exited {result.returncode}")
        subdomains = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    subdomains.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return json_result(True, data={
            "domain": domain,
            "subdomains_found": len(subdomains),
            "subdomains": subdomains,
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "subdomain_enum",
    "description": "Passive subdomain enumeration using subfinder.",
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "Target domain"},
            "sources": {"type": "string", "default": "all", "description": "Comma-separated sources or 'all'"},
        },
        "required": ["domain"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="subdomain_enum",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🔎",
    )
