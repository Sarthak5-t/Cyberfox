from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

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
        argv = ["masscan", target, "-p", str(ports), f"--rate={int(rate)}", "--open", "-oJ", "/dev/stdout"]
        result = run_command_argv(argv, timeout=600)
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
    "description": "Ultra-fast port scanner — scans all 65535 ports in seconds.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Target IP or CIDR"},
            "ports": {"type": "string", "default": "-", "description": "Port range"},
            "rate": {"type": "integer", "default": 1000, "description": "Packets per second"},
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
