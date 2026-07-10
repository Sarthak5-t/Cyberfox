from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

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
        if mode == "passive":
            cmd = f"amass enum -passive -d {shlex.quote(domain)}"
        else:
            cmd = f"amass enum -d {shlex.quote(domain)}"
        result = run_command(cmd, timeout=600)
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
    "description": "Deep subdomain enumeration — combines multiple OSINT sources for comprehensive subdomain discovery.",
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Target domain (e.g. 'example.com')",
            },
            "mode": {
                "type": "string",
                "enum": ["enum", "passive"],
                "default": "enum",
                "description": "enum = active + passive (slower, more results), passive = OSINT only (faster, less noisy)",
            },
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
