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
    extensions = args.get("extensions", "")
    threads = args.get("threads", 40)
    if not check_binary("ffuf"):
        return json_result(False, error="ffuf not found on PATH")
    try:
        cmd = f"ffuf -u {shlex.quote(target)} -w {shlex.quote(wordlist)} -json -t {threads}"
        if extensions:
            cmd += f" -e {shlex.quote(extensions)}"
        result = run_command(cmd, timeout=300)
        if result.returncode != 0:
            return json_result(False, error=result.stderr.strip() or f"ffuf exited {result.returncode}")
        findings = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    findings.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return json_result(True, data={
            "target": target,
            "results_count": len(findings),
            "results": findings[:500],
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "ffuf_scan",
    "description": "Web fuzzing using ffuf. Fast web fuzzer for discovering paths, parameters, and vhosts.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Target URL with FUZZ keyword (e.g. 'http://example.com/FUZZ')"},
            "wordlist": {
                "type": "string",
                "default": "/usr/share/wordlists/dirb/common.txt",
                "description": "Path to wordlist file",
            },
            "extensions": {
                "type": "string",
                "default": "",
                "description": "File extensions (e.g. '.php,.txt,.html')",
            },
            "threads": {
                "type": "integer",
                "default": 40,
                "minimum": 1,
                "maximum": 200,
                "description": "Number of concurrent threads",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="ffuf_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🎯",
    )
