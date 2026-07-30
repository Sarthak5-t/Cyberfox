from __future__ import annotations

import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"

WAPITI_MODULES = [
    "all", "sql", "xss", "backup", "htaccess", "blindsql",
    "file", "crlf", "exec", "methods", "nikto",
    "shellshock", "htp", "drupal", "magento", "wp",
]


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    modules = args.get("modules", "all")
    scope = args.get("scope", "folder")
    proxy = args.get("proxy", "")
    auth_creds = args.get("auth_credentials", "")
    timeout_val = args.get("timeout", 600)

    if not check_binary("wapiti"):
        return json_result(False, error="wapiti not found on PATH")

    if not target:
        return json_result(False, error="'target' parameter is required")

    try:
        argv = ["wapiti", "-u", target, "--color", "off"]

        if modules != "all":
            argv.extend(["-m", modules])
        if scope and scope != "folder":
            argv.extend(["--scope", scope])
        if proxy:
            argv.extend(["-p", proxy])
        if auth_creds:
            user, pwd = auth_creds.split(":", 1) if ":" in auth_creds else (auth_creds, "")
            argv.extend(["--auth-user", user, "--auth-password", pwd])

        result = run_command_argv(argv, timeout=timeout_val)

        output_text = result.stdout.strip()
        stderr_out = result.stderr.strip()

        vulnerabilities = []
        vuln_count = {"high": 0, "medium": 0, "low": 0, "info": 0}

        for line in output_text.split("\n") if output_text else []:
            for severity in vuln_count:
                if severity in line.lower():
                    vuln_count[severity] += 1
                    if severity in ("high", "medium"):
                        vulnerabilities.append(line.strip())

        return json_result(True, data={
            "target": target,
            "modules_used": modules,
            "vulnerabilities_found": vuln_count,
            "vulnerability_list": vulnerabilities[:100],
            "output": output_text[:30000],
            "stderr": stderr_out[:3000],
        })

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "wapiti_scan",
    "description": "Web application vulnerability scanner. Tests for SQL injection, XSS, file disclosure, command execution, CRLF injection, backup files, and CMS-specific vulnerabilities.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target URL to scan (e.g. 'https://example.com')",
            },
            "modules": {
                "type": "string",
                "enum": WAPITI_MODULES,
                "default": "all",
                "description": "Vulnerability modules to enable (comma-separated or 'all')",
            },
            "scope": {
                "type": "string",
                "enum": ["folder", "domain", "url"],
                "default": "folder",
                "description": "Scan scope: folder, domain, or url",
            },
            "proxy": {
                "type": "string",
                "default": "",
                "description": "Proxy for requests (e.g. 'http://127.0.0.1:8080')",
            },
            "auth_credentials": {
                "type": "string",
                "default": "",
                "description": "Authentication credentials (format: 'username:password')",
            },
            "timeout": {
                "type": "integer",
                "default": 600,
                "description": "Timeout in seconds",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="wapiti_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🕷️",
    )
