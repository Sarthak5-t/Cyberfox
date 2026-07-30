from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"


def _handle(args: dict, **kw) -> str:
    email = args.get("email", "")
    output_only_used = args.get("only_used", True)
    no_analysis = args.get("no_analysis", False)
    timeout_val = args.get("timeout", 120)

    if not check_binary("holehe"):
        return json_result(False, error="holehe not found on PATH")

    if not email:
        return json_result(False, error="'email' parameter is required")

    try:
        argv = ["holehe", email]

        if output_only_used:
            argv.append("--only-used")
        if no_analysis:
            argv.append("--no-analysis")

        result = run_command_argv(argv, timeout=timeout_val)

        output_text = result.stdout.strip()
        stderr_out = result.stderr.strip()

        services_used = []
        services_not_used = []
        rate_limited = False

        for line in output_text.split("\n") if output_text else []:
            if "[+]" in line:
                services_used.append(line.replace("[+]", "").strip())
            elif "[-]" in line:
                services_not_used.append(line.replace("[-]", "").strip())
            elif "rate" in line.lower() or "limit" in line.lower():
                rate_limited = True

        return json_result(True, data={
            "email": email,
            "services_found": len(services_used),
            "services_used": services_used,
            "services_not_used_count": len(services_not_used),
            "rate_limited": rate_limited,
            "raw_output": output_text[:10000],
        })

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "holehe_check",
    "description": "Check if an email address is registered on various online services (social media, forums, etc.) using holehe. Useful for OSINT email enumeration.",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "Email address to check (e.g. 'target@example.com')",
            },
            "only_used": {
                "type": "boolean",
                "default": True,
                "description": "Only show services where the email is registered",
            },
            "no_analysis": {
                "type": "boolean",
                "default": False,
                "description": "Skip analysis of results (faster for bulk checks)",
            },
            "timeout": {
                "type": "integer",
                "default": 120,
                "description": "Timeout in seconds",
            },
        },
        "required": ["email"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="holehe_check",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="📧",
    )
