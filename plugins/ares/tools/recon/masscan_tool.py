from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    ports = args.get("ports", "-")
    rate = args.get("rate", 1000)
    if not target:
        return json_result(False, error="target is required")
    if not check_binary("masscan"):
        return json_result(False, error="masscan not found on PATH")
    try:
        cmd = f"masscan {shlex.quote(target)} -p {shlex.quote(str(ports))} --rate={int(rate)} --open -oJ /dev/stdout"
        result = run_command(cmd, timeout=600)
        output = result.stdout.strip()[:50000]
        if result.returncode != 0 and not output:
            return json_result(False, error=result.stderr.strip() or f"masscan exited {result.returncode}")
        return json_result(True, data={
            "target": target,
            "ports": str(ports),
            "rate": rate,
            "output": output,
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "masscan_scan",
    "description": "Ultra-fast port scanner — scans all 65535 ports in seconds. Use for initial sweep, then nmap on discovered ports.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target IP or CIDR (e.g. '10.10.10.0/24')",
            },
            "ports": {
                "type": "string",
                "default": "-",
                "description": "Port range (e.g. '1-65535', '80,443', '21-25,80,443,3389'). Default: all ports.",
            },
            "rate": {
                "type": "integer",
                "default": 1000,
                "description": "Packets per second (1000 is stealthy, 10000 is fast, 50000 is aggressive)",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="masscan_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="⚡",
    )
