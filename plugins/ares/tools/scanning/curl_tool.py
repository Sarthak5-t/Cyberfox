from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"


def _handle(args: dict, **kw) -> str:
    url = args.get("url", "")
    method = args.get("method", "GET")
    headers = args.get("headers", "")
    data = args.get("data", "")
    follow = args.get("follow_redirects", True)
    insecure = args.get("insecure", True)
    if not url:
        return json_result(False, error="url is required")
    try:
        cmd = f"curl -sS -D- -o /dev/null --max-time 30"
        if follow:
            cmd += " -L"
        if insecure:
            cmd += " -k"
        cmd += f" -X {shlex.quote(method)}"
        if headers:
            for h in headers.split("\n"):
                h = h.strip()
                if h:
                    cmd += f" -H {shlex.quote(h)}"
        if data:
            cmd += f" -d {shlex.quote(data)}"
        cmd += f" {shlex.quote(url)}"
        result = run_command(cmd, timeout=60)
        output = result.stdout.strip()[:50000]
        return json_result(True, data={
            "url": url,
            "method": method,
            "output": output,
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "curl_tool",
    "description": "HTTP request tool — test endpoints, check headers, probe for vulnerabilities, test auth, and verify findings.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Target URL (e.g. 'http://10.10.10.1/robots.txt')",
            },
            "method": {
                "type": "string",
                "default": "GET",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                "description": "HTTP method",
            },
            "headers": {
                "type": "string",
                "default": "",
                "description": "Headers (newline-separated, e.g. 'X-Forwarded-For: 127.0.0.1\\nHost: internal.local')",
            },
            "data": {
                "type": "string",
                "default": "",
                "description": "POST data (e.g. 'user=admin&pass=test')",
            },
            "follow_redirects": {
                "type": "boolean",
                "default": True,
                "description": "Follow HTTP redirects",
            },
            "insecure": {
                "type": "boolean",
                "default": True,
                "description": "Skip SSL/TLS verification",
            },
        },
        "required": ["url"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="curl_tool",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🔗",
    )
