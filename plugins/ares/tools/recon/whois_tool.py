from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    if not target:
        return json_result(False, error="target is required")
    if not check_binary("whois"):
        return json_result(False, error="whois not found on PATH")
    try:
        result = run_command(f"whois {shlex.quote(target)}", timeout=60)
        if result.returncode != 0:
            return json_result(False, error=result.stderr.strip() or f"whois exited {result.returncode}")
        return json_result(True, data={
            "target": target,
            "output": result.stdout.strip()[:50000],
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "whois_scan",
    "description": "WHOIS lookup for domain/IP registration information. Returns registrant, name servers, creation/expiry dates, ASN, and related infrastructure.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Domain name, IP address, or ASN (e.g. 'example.com', '10.10.10.0', 'AS15169')",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="whois_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🌐",
    )
