from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    method = args.get("method", "GET")
    headers = args.get("headers", {})
    data = args.get("data", "")
    
    if not target:
        return json_result(False, error="target is required")
    
    return _send_request(target, method, headers, data)


def _send_request(target: str, method: str, headers: dict, data: str) -> str:
    """Send HTTP request and analyze response."""
    try:
        cmd_parts = ["curl", "-s", "-i", "-X", method, "--max-time", "15"]
        
        # Add headers
        for key, value in headers.items():
            cmd_parts.extend(["-H", f"{key}: {value}"])
        
        # Add data if present
        if data:
            cmd_parts.extend(["-d", data])
        
        cmd_parts.append(target)
        
        cmd = " ".join(cmd_parts)
        result = run_command(cmd, timeout=20)
        
        # Parse response
        response = {
            "status_code": 0,
            "headers": {},
            "body": "",
            "security_headers": [],
        }
        
        lines = result.stdout.split("\n")
        in_body = False
        body_lines = []
        
        for line in lines:
            if in_body:
                body_lines.append(line)
            elif line.strip() == "":
                in_body = True
            elif ":" in line:
                key, _, value = line.partition(":")
                response["headers"][key.strip()] = value.strip()
        
        response["body"] = "\n".join(body_lines)[:5000]
        
        # Check status code
        status_line = lines[0] if lines else ""
        if "HTTP/" in status_line:
            parts = status_line.split()
            if len(parts) >= 2:
                response["status_code"] = int(parts[1])
        
        # Check security headers
        security_headers = [
            "strict-transport-security",
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection",
            "content-security-policy",
            "x-permitted-cross-domain-policies",
            "referrer-policy",
            "permissions-policy",
        ]
        
        for header in security_headers:
            if header.lower() not in [k.lower() for k in response["headers"]]:
                response["security_headers"].append(header)
        
        return json_result(True, data={
            "target": target,
            "method": method,
            "response": response,
        })
    except Exception as e:
        return json_result(False, error=f"Request failed: {str(e)}")


SCHEMA = {
    "name": "burp_repeater",
    "description": "Manual HTTP request crafting and analysis. Send custom requests and inspect responses for security testing.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Target URL (e.g. 'https://example.com/api')"},
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"], "default": "GET", "description": "HTTP method"},
            "headers": {"type": "object", "default": {}, "description": "Custom headers as key-value pairs"},
            "data": {"type": "string", "default": "", "description": "Request body data"},
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="burp_repeater",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="📤",
    )
