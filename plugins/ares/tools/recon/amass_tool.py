from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"


def _handle(args: dict, **kw) -> str:
    domain = args.get("domain", "")
    mode = args.get("mode", "enum")
    if not domain:
        return json_result(False, error="domain is required")
    if not check_binary("amass"):
        return json_result(False, error="amass not found on PATH")
    try:
        argv = ["amass", "enum", "-d", domain]
        if mode == "passive":
            argv.append("-passive")
        result = run_command_argv(argv, timeout=600)
        output = result.stdout.strip()[:50000]
        if result.returncode != 0 and not output:
            return json_result(False, error=result.stderr.strip() or f"amass exited {result.returncode}")
        return json_result(True, data={
            "domain": domain,
            "mode": mode,
            "output": output,
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "amass_scan",
    "description": "Deep subdomain enumeration using multiple OSINT sources.",
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "Target domain"},
            "mode": {"type": "string", "enum": ["enum", "passive"], "default": "enum"},
        },
        "required": ["domain"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="amass_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🔎",
    )
