from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    wordlist = args.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
    threads = args.get("threads", 30)
    extensions = args.get("extensions", "")
    if not target:
        return json_result(False, error="target is required")
    if not check_binary("wfuzz"):
        return json_result(False, error="wfuzz not found on PATH")
    try:
        cmd = f"wfuzz -c -w {shlex.quote(wordlist)} -t {int(threads)}"
        if extensions:
            cmd += f" -e {shlex.quote(extensions)}"
        cmd += f" {shlex.quote(target)}"
        result = run_command(cmd, timeout=600)
        output = result.stdout.strip()[:50000]
        if result.returncode != 0 and not output:
            return json_result(False, error=result.stderr.strip() or f"wfuzz exited {result.returncode}")
        return json_result(True, data={
            "target": target,
            "wordlist": wordlist,
            "output": output,
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "wfuzz_scan",
    "description": "Web application fuzzer — brute-force parameters, paths, POST data, and headers with payload-based attacks.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target URL with FUZZ keyword (e.g. 'http://target.com/FUZZ')",
            },
            "wordlist": {
                "type": "string",
                "default": "/usr/share/wordlists/dirb/common.txt",
                "description": "Path to wordlist file",
            },
            "threads": {
                "type": "integer",
                "default": 30,
                "description": "Number of concurrent threads",
            },
            "extensions": {
                "type": "string",
                "default": "",
                "description": "File extensions to append (e.g. '.php,.html,.txt')",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="wfuzz_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="💥",
    )
