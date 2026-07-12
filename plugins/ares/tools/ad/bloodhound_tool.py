from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_ad"



def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    domain = args.get("domain", "")
    username = args.get("username", "")
    password = args.get("password", "")
    hashes = args.get("hashes", "")
    methods = args.get("collection_method", "All")
    if not check_binary("bloodhound-python"):
        return json_result(False, error="bloodhound-python not found on PATH")
    try:
        argv = [
            "bloodhound-python",
            "-d", domain,
            "-u", username,
            "-c", methods,
        ]
        if password:
            argv.extend(["-p", password])
        if hashes:
            argv.extend(["--hashes", hashes])
        if target:
            argv.extend(["-dc", target])
        result = run_command_argv(argv, timeout=300, shell=False)
        if result.returncode != 0:
            return json_result(False, error=result.stderr.strip() or f"bloodhound-python exited {result.returncode}")
        return json_result(True, data={
            "domain": domain,
            "target": target,
            "collection_method": methods,
            "output": result.stdout.strip()[:50000],
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "bloodhound_ingest",
    "description": "Run BloodHound ingestor (bloodhound-python) to collect Active Directory data. Collects users, groups, computers, GPOs, and trust relationships.",
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "Target domain (e.g. 'domain.local')"},
            "username": {"type": "string", "description": "Domain username (e.g. 'domain\\\\user' or 'user@domain.local')"},
            "password": {"type": "string", "default": "", "description": "Password for authentication"},
            "hashes": {"type": "string", "default": "", "description": "NTLM hashes for pass-the-hash (format: LMHASH:NTHASH)"},
            "target": {"type": "string", "description": "Target domain controller IP/hostname (optional)"},
            "collection_method": {
                "type": "string",
                "enum": ["All", "Default", "Group", "LocalAdmin", "Session", "Trusts", "ACL", "ObjectProps", "Container", "DCOM", "RDP", "PSRemote"],
                "default": "All",
                "description": "Collection methods (comma-separated or single method)",
            },
        },
        "required": ["domain", "username"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="bloodhound_ingest",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🐾",
    )
