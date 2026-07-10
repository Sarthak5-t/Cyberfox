from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"



def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    mode = args.get("mode", "dir")
    wordlist = args.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
    extensions = args.get("extensions", "")
    threads = args.get("threads", 10)
    if not check_binary("gobuster"):
        return json_result(False, error="gobuster not found on PATH")
    try:
        cmd = f"gobuster {shlex.quote(mode)} -u {shlex.quote(target)} -w {shlex.quote(wordlist)} -q -t {threads}"
        if extensions:
            cmd += f" -x {shlex.quote(extensions)}"
        result = run_command(cmd, timeout=300)
        if result.returncode != 0:
            return json_result(False, error=result.stderr.strip() or f"gobuster exited {result.returncode}")
        lines = [line for line in result.stdout.strip().split("\n") if line.strip()]
        return json_result(True, data={
            "target": target,
            "mode": mode,
            "results_count": len(lines),
            "results": lines[:1000],
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "gobuster_scan",
    "description": "Directory/file brute-forcing using gobuster. Discovers hidden paths, DNS subdomains, or vhosts.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Target URL (e.g. 'http://example.com')"},
            "mode": {
                "type": "string",
                "enum": ["dir", "dns", "vhost"],
                "default": "dir",
                "description": "Scan mode: dir (directories/files), dns (subdomains), vhost (virtual hosts)",
            },
            "wordlist": {
                "type": "string",
                "default": "/usr/share/wordlists/dirb/common.txt",
                "description": "Path to wordlist file",
            },
            "extensions": {
                "type": "string",
                "description": "File extensions to append (e.g. 'php,txt,html')",
            },
            "threads": {
                "type": "integer",
                "default": 10,
                "minimum": 1,
                "maximum": 100,
                "description": "Number of concurrent threads",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="gobuster_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="📂",
    )
