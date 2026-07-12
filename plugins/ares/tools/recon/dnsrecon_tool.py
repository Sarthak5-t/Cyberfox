from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"


def _handle(args: dict, **kw) -> str:
    target = args.get("domain", "")
    scan_type = args.get("type", "std")
    if not check_binary("dnsrecon"):
        return json_result(False, error="dnsrecon not found on PATH")
    try:
        argv = ["dnsrecon", "-d", target, "-t", scan_type, "-j", "/dev/stdout"]
        result = run_command_argv(argv, timeout=120)
        if result.returncode != 0:
            return json_result(False, error=result.stderr.strip() or f"dnsrecon exited {result.returncode}")
        return json_result(True, data={
            "domain": target,
            "type": scan_type,
            "records": _parse_json_lines(result.stdout),
        })
    except Exception as e:
        return json_result(False, error=str(e))


def _parse_json_lines(text: str) -> list:
    records = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("{"):
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


SCHEMA = {
    "name": "dns_recon",
    "description": "DNS reconnaissance and enumeration using dnsrecon.",
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "Target domain"},
            "type": {"type": "string", "enum": ["std", "brt", "srv", "axfr", "zonewalk"], "default": "std"},
        },
        "required": ["domain"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="dns_recon",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🌐",
    )
