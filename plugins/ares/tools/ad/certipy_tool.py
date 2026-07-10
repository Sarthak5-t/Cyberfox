from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_ad"



def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    action = args.get("action", "find")
    username = args.get("username", "")
    password = args.get("password", "")
    hashes = args.get("hashes", "")
    dc_ip = args.get("dc_ip", "")
    ca = args.get("ca", "")
    if not check_binary("certipy-ad"):
        return json_result(False, error="certipy-ad not found on PATH (install with: pip install certipy-ad)")
    try:
        cmd = f"certipy-ad {shlex.quote(action)} -target {shlex.quote(target)}"
        if username:
            cmd += f" -u {shlex.quote(username)}"
        if password:
            cmd += f" -p {shlex.quote(password)}"
        if hashes:
            cmd += f" -hashes {shlex.quote(hashes)}"
        if dc_ip:
            cmd += f" -dc-ip {shlex.quote(dc_ip)}"
        if ca:
            cmd += f" -ca {shlex.quote(ca)}"
        result = run_command(cmd, timeout=300)
        if result.returncode != 0:
            return json_result(False, error=result.stderr.strip() or f"certipy-ad exited {result.returncode}")
        return json_result(True, data={
            "action": action,
            "target": target,
            "output": result.stdout.strip()[:50000],
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "certipy_tool",
    "description": "Active Directory Certificate Services exploitation using certipy. Find misconfigured CA templates, request certificates, and authenticate.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Target domain controller IP or hostname"},
            "action": {
                "type": "string",
                "enum": ["find", "req", "auth", "forge"],
                "default": "find",
                "description": "Action: find (enum templates), req (request cert), auth (authenticate with cert), forge (forge cert)",
            },
            "username": {"type": "string", "description": "Domain username (e.g. 'domain\\\\user' or 'user@domain.local')"},
            "password": {"type": "string", "default": "", "description": "Password for authentication"},
            "hashes": {"type": "string", "default": "", "description": "NTLM hashes for pass-the-hash (format: LMHASH:NTHASH)"},
            "dc_ip": {"type": "string", "default": "", "description": "Domain controller IP address (optional)"},
            "ca": {"type": "string", "default": "", "description": "Certificate Authority name (optional)"},
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="certipy_tool",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="📜",
    )
