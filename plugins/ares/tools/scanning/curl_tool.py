from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"


def _handle(args: dict, **kw) -> str:
    if not check_binary("curl"):
        return json_result(False, error="curl not found on PATH (install with: apt install curl)")
    url = args.get("url", "")
    method = args.get("method", "GET")
    headers = args.get("headers", "")
    data = args.get("data", "")
    follow = args.get("follow_redirects", False)
    insecure = args.get("insecure", False)
    return_body = args.get("return_body", True)
    if not url:
        return json_result(False, error="url is required")
    try:
        argv = ["curl", "-sS", "--max-time", "30"]
        if return_body:
            argv.append("-D-")
        else:
            argv.extend(["-D-", "-o", "/dev/null"])
        if follow:
            argv.append("-L")
        if insecure:
            argv.append("-k")
        argv.extend(["-X", method])
        if headers:
            for h in headers.split("\n"):
                h = h.strip()
                if h:
                    argv.extend(["-H", h])
        if data:
            argv.extend(["-d", data])
        argv.append(url)
        result = run_command_argv(argv, timeout=60)
        output = result.stdout.strip()[:80000]
        return json_result(True, data={
            "url": url,
            "method": method,
            "output": output,
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "curl_tool",
    "description": "HTTP request tool — test endpoints, check headers, probe for vulnerabilities.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Target URL"},
            "method": {"type": "string", "default": "GET", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]},
            "headers": {"type": "string", "default": "", "description": "Newline-separated headers"},
            "data": {"type": "string", "default": "", "description": "POST data"},
            "follow_redirects": {"type": "boolean", "default": False, "description": "Follow HTTP redirects"},
            "insecure": {"type": "boolean", "default": False, "description": "Skip SSL verification"},
            "return_body": {"type": "boolean", "default": True, "description": "Include response body"},
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
