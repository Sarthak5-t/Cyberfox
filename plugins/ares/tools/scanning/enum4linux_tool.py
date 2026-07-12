from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"



def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    username = args.get("username", "")
    password = args.get("password", "")
    if not check_binary("enum4linux"):
        return json_result(False, error="enum4linux not found on PATH")
    try:
        argv = ["enum4linux", "-a"]
        if username and password:
            argv.extend(["-u", username, "-p", password])
        argv.append(target)
        result = run_command_argv(argv, timeout=300, shell=False)
        if result.returncode != 0:
            return json_result(False, error=result.stderr.strip() or f"enum4linux exited {result.returncode}")
        return json_result(True, data={
            "target": target,
            "output": result.stdout.strip()[:50000],
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "enum4linux_scan",
    "description": "SMB/CIFS enumeration using enum4linux. Gathers users, shares, groups, and policy information from Windows/Samba hosts.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Target IP address"},
            "username": {"type": "string", "default": "", "description": "Username for authenticated enumeration (optional)"},
            "password": {"type": "string", "default": "", "description": "Password for authenticated enumeration (optional)"},
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="enum4linux_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🖥️",
    )
