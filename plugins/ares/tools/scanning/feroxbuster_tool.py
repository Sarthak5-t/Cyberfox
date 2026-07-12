from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    wordlist = args.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
    threads = args.get("threads", 50)
    extensions = args.get("extensions", "")
    if not target:
        return json_result(False, error="target is required")
    if not check_binary("feroxbuster"):
        return json_result(False, error="feroxbuster not found on PATH")
    try:
        argv = [
            "feroxbuster", "-u", target, "-w", wordlist,
            "-t", str(int(threads)), "--silent", "--no-progress",
        ]
        if extensions:
            argv.extend(["-x", extensions])
        result = run_command_argv(argv, timeout=600, shell=False)
        output = result.stdout.strip()[:50000]
        if result.returncode != 0 and not output:
            return json_result(False, error=result.stderr.strip() or f"feroxbuster exited {result.returncode}")
        return json_result(True, data={
            "target": target,
            "wordlist": wordlist,
            "output": output,
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "feroxbuster_scan",
    "description": "Fast recursive directory brute-force with automatic filtering. Faster than gobuster for large scans.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target URL (e.g. 'http://10.10.10.1')",
            },
            "wordlist": {
                "type": "string",
                "default": "/usr/share/wordlists/dirb/common.txt",
                "description": "Path to wordlist",
            },
            "threads": {
                "type": "integer",
                "default": 50,
                "description": "Concurrent threads",
            },
            "extensions": {
                "type": "string",
                "default": "",
                "description": "File extensions (e.g. 'php,html,js')",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="feroxbuster_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="📁",
    )
