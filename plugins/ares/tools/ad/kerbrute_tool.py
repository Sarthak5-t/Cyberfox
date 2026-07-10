from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_ad"



def _handle(args: dict, **kw) -> str:
    domain = args.get("domain", "")
    userlist = args.get("userlist", "/usr/share/wordlists/metasploit/namelist.txt")
    target = args.get("target", "")
    threads = args.get("threads", 10)
    mode = args.get("mode", "userenum")
    if not check_binary("kerbrute"):
        return json_result(False, error="kerbrute not found on PATH")
    try:
        cmd = f"kerbrute {shlex.quote(mode)} -d {shlex.quote(domain)} --threads {threads}"
        if target:
            cmd += f" --dc {shlex.quote(target)}"
        cmd += f" {shlex.quote(userlist)}"
        result = run_command(cmd, timeout=120)
        if result.returncode != 0:
            return json_result(False, error=result.stderr.strip() or f"kerbrute exited {result.returncode}")
        lines = [line for line in result.stdout.strip().split("\n") if line.strip()]
        return json_result(True, data={
            "domain": domain,
            "mode": mode,
            "results_count": len(lines),
            "results": lines[:500],
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "kerbrute_enum",
    "description": "Kerberos user enumeration using kerbrute. Enumerates valid domain users by attempting Kerberos pre-authentication.",
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "Target domain (e.g. 'domain.local')"},
            "userlist": {
                "type": "string",
                "default": "/usr/share/wordlists/metasploit/namelist.txt",
                "description": "Path to username wordlist",
            },
            "target": {
                "type": "string",
                "default": "",
                "description": "Domain controller IP/hostname (optional, uses DNS SRV lookup if empty)",
            },
            "threads": {
                "type": "integer",
                "default": 10,
                "minimum": 1,
                "maximum": 100,
                "description": "Number of concurrent threads",
            },
            "mode": {
                "type": "string",
                "enum": ["userenum", "bruteforce", "passwordspray"],
                "default": "userenum",
                "description": "Attack mode: userenum (find users), bruteforce (user+pass), passwordspray (one pass, many users)",
            },
        },
        "required": ["domain"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="kerbrute_enum",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="👤",
    )
