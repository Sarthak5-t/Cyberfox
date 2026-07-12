from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    if not target:
        return json_result(False, error="target is required")
    if not check_binary("wafw00f"):
        return json_result(False, error="wafw00f not found on PATH")
    try:
        argv = ["wafw00f", target, "-a"]
        result = run_command_argv(argv, timeout=120, shell=False)
        output = result.stdout.strip()[:50000]
        if result.returncode != 0 and not output:
            return json_result(False, error=result.stderr.strip() or f"wafw00f exited {result.returncode}")
        return json_result(True, data={
            "target": target,
            "output": output,
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "wafw00f_scan",
    "description": "Web Application Firewall detection — identifies WAF vendor and version to plan evasion strategy.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target URL (e.g. 'http://example.com')",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="wafw00f_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🛡️",
    )
