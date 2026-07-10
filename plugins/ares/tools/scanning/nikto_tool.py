from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"



def _parse_nikto_json(text: str) -> list:
    findings = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("{"):
            try:
                findings.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return findings


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    ssl = args.get("ssl", False)
    timeout_s = args.get("timeout", 30)
    if not check_binary("nikto"):
        return json_result(False, error="nikto not found on PATH")
    try:
        ssl_flag = "-ssl" if ssl else ""
        cmd = f"nikto -h {shlex.quote(target)} {ssl_flag} -timeout {timeout_s} -format json"
        result = run_command(cmd, timeout=600)
        if result.returncode not in (0, 1):
            return json_result(False, error=result.stderr.strip() or f"nikto exited {result.returncode}")
        headers = []
        findings = _parse_nikto_json(result.stdout)
        for line in result.stdout.strip().split("\n"):
            if line.strip() and not line.startswith("{"):
                headers.append(line.strip())
        return json_result(True, data={
            "target": target,
            "ssl": ssl,
            "findings_count": len(findings),
            "findings": findings[:200],
            "scan_headers": headers[:50],
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "nikto_scan",
    "description": "Web server vulnerability scanning using nikto. Checks for outdated versions, misconfigurations, and known vulnerabilities.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Target URL or IP (e.g. 'http://example.com' or '10.10.10.10')"},
            "ssl": {"type": "boolean", "default": False, "description": "Force SSL mode"},
            "timeout": {"type": "integer", "default": 30, "minimum": 5, "maximum": 120, "description": "Request timeout in seconds"},
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="nikto_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🌐",
    )
