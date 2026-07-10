from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    aggression = args.get("aggression", 3)
    if not target:
        return json_result(False, error="target is required")
    if not check_binary("whatweb"):
        return json_result(False, error="whatweb not found on PATH")
    try:
        cmd = f"whatweb -a {int(aggression)} --color=never {shlex.quote(target)}"
        result = run_command(cmd, timeout=120)
        output = result.stdout.strip()[:50000]
        if result.returncode != 0 and not output:
            return json_result(False, error=result.stderr.strip() or f"whatweb exited {result.returncode}")
        return json_result(True, data={
            "target": target,
            "aggression": aggression,
            "output": output,
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "whatweb_scan",
    "description": "Web fingerprinting — detects technologies, CMS, frameworks, server version, headers, and more.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target URL or IP (e.g. 'http://example.com', '10.10.10.1')",
            },
            "aggression": {
                "type": "integer",
                "default": 3,
                "minimum": 1,
                "maximum": 4,
                "description": "Detection level (1=passive, 4=aggressive). Higher = more thorough but noisier.",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="whatweb_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🌐",
    )
