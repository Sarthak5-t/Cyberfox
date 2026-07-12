from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    enumerate_opt = args.get("enumerate", "vp,vt,u")
    api_token = args.get("api_token", "")
    if not target:
        return json_result(False, error="target is required")
    if not check_binary("wpscan"):
        return json_result(False, error="wpscan not found on PATH")
    try:
        argv = [
            "wpscan", "--url", target,
            "--enumerate", enumerate_opt,
            "--no-banner", "--random-user-agent",
        ]
        if api_token:
            argv.extend(["--api-token", api_token])
        result = run_command_argv(argv, timeout=300, shell=False)
        output = result.stdout.strip()[:50000]
        if result.returncode != 0 and not output:
            return json_result(False, error=result.stderr.strip() or f"wpscan exited {result.returncode}")
        return json_result(True, data={
            "target": target,
            "enumerate": enumerate_opt,
            "output": output,
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "wpscan_scan",
    "description": "WordPress vulnerability scanner — enumerates plugins, themes, users, and checks for known vulnerabilities.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "WordPress site URL (e.g. 'http://example.com')",
            },
            "enumerate": {
                "type": "string",
                "default": "vp,vt,u",
                "description": "What to enumerate: vp=plugins, vt=themes, u=users, tt=timthumbs, etc.",
            },
            "api_token": {
                "type": "string",
                "default": "",
                "description": "WPVulnDB API token for vulnerability checks (optional but recommended)",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="wpscan_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="📝",
    )
