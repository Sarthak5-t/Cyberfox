from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_ad"



def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    protocol = args.get("protocol", "smb")
    module = args.get("module", "")
    username = args.get("username", "")
    password = args.get("password", "")
    hashes = args.get("hashes", "")
    domain = args.get("domain", "")
    if not check_binary("netexec") and not check_binary("crackmapexec"):
        return json_result(False, error="neither netexec nor crackmapexec found on PATH")
    try:
        binary = "netexec" if check_binary("netexec") else "crackmapexec"
        cmd = f"{binary} {shlex.quote(protocol)} {shlex.quote(target)}"
        if username:
            cmd += f" -u {shlex.quote(username)}"
        if password:
            cmd += f" -p {shlex.quote(password)}"
        if hashes:
            cmd += f" -H {shlex.quote(hashes)}"
        if domain:
            cmd += f" -d {shlex.quote(domain)}"
        if module:
            cmd += f" -M {shlex.quote(module)}"
        result = run_command(cmd, timeout=120)
        if result.returncode != 0:
            return json_result(False, error=result.stderr.strip() or f"{binary} exited {result.returncode}")
        return json_result(True, data={
            "target": target,
            "protocol": protocol,
            "module": module,
            "output": result.stdout.strip()[:50000],
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "crackmapexec",
    "description": "Remote Windows/AD enumeration using CrackMapExec or NetExec. Enumerate SMB, SSH, WinRM, LDAP, RDP, and MSSQL with authentication.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Target IP or CIDR range"},
            "protocol": {
                "type": "string",
                "enum": ["smb", "ssh", "winrm", "ldap", "rdp", "mssql"],
                "default": "smb",
                "description": "Protocol to use",
            },
            "username": {"type": "string", "default": "", "description": "Username for authentication"},
            "password": {"type": "string", "default": "", "description": "Password for authentication"},
            "hashes": {"type": "string", "default": "", "description": "NTLM hashes for pass-the-hash (format: LMHASH:NTHASH)"},
            "domain": {"type": "string", "default": "", "description": "Domain for authentication"},
            "module": {"type": "string", "default": "", "description": "Module to run (e.g. 'lsassy', 'slinky', 'get_netconnections')"},
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="crackmapexec",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="⚡",
    )
