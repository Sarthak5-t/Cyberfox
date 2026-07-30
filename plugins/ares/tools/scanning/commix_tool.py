from __future__ import annotations

import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"


def _handle(args: dict, **kw) -> str:
    url = args.get("url", "")
    method = args.get("method", "GET")
    data = args.get("data", "")
    cookies = args.get("cookies", "")
    user_agent = args.get("user_agent", "")
    level = args.get("level", 1)
    skip_detection = args.get("skip_detection", False)
    batch = args.get("batch", False)
    tamper = args.get("tamper", "")
    output_dir = args.get("output_dir", "")
    proxy = args.get("proxy", "")

    if not check_binary("commix"):
        return json_result(False, error="commix not found on PATH")

    if not url:
        return json_result(False, error="'url' parameter is required")

    try:
        argv = ["commix", "--url", url]

        try:
            level = max(1, min(3, int(level)))
            if level > 1:
                argv.append("--level=" + str(level))
        except (TypeError, ValueError):
            pass

        if method and method.upper() != "GET":
            argv.extend(["--data", data]) if method.upper() == "POST" else None
        if data and method.upper() == "POST":
            argv.extend(["--data", data])
        if cookies:
            argv.extend(["--cookie", cookies])
        if user_agent:
            argv.extend(["--user-agent", user_agent])
        if skip_detection:
            argv.append("--skip-detection")
        if batch:
            argv.append("--batch")
        if tamper:
            argv.extend(["--tamper", tamper])
        if output_dir:
            argv.extend(["--output-dir", output_dir])
        if proxy:
            argv.extend(["--proxy", proxy])

        result = run_command_argv(argv, timeout=600)

        output_text = result.stdout.strip()
        stderr_out = result.stderr.strip()

        vuln_found = False
        vuln_type = ""
        payloads = []
        for line in (output_text + "\n" + stderr_out).split("\n"):
            if "vulnerable" in line.lower() or "injection" in line.lower():
                vuln_found = True
                vuln_type = line.strip()
            if "payload" in line.lower():
                payloads.append(line.strip())

        return json_result(True, data={
            "url": url,
            "method": method,
            "vulnerable": vuln_found,
            "vulnerability_type": vuln_type or None,
            "payloads": payloads[:50],
            "output": output_text[:30000],
            "stderr": stderr_out[:3000],
        })

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "commix_scan",
    "description": "Command injection finder (commix). Tests URL parameters, POST data, headers, and cookies for OS command injection vulnerabilities.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Target URL with test parameters (e.g. 'http://target.com/page.php?cmd=test')",
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST"],
                "default": "GET",
                "description": "HTTP method",
            },
            "data": {
                "type": "string",
                "default": "",
                "description": "POST body data for injection testing",
            },
            "cookies": {
                "type": "string",
                "default": "",
                "description": "Cookie string for authenticated testing",
            },
            "user_agent": {
                "type": "string",
                "default": "",
                "description": "Custom User-Agent header",
            },
            "level": {
                "type": "integer",
                "enum": [1, 2, 3],
                "default": 1,
                "description": "Test level (1=basic, 2=medium, 3=extensive)",
            },
            "skip_detection": {
                "type": "boolean",
                "default": False,
                "description": "Skip detection phase, go straight to exploitation",
            },
            "batch": {
                "type": "boolean",
                "default": False,
                "description": "Non-interactive mode (answer defaults)",
            },
            "tamper": {
                "type": "string",
                "default": "",
                "description": "Tamper script for WAF bypass",
            },
            "output_dir": {
                "type": "string",
                "default": "",
                "description": "Directory to save output files",
            },
            "proxy": {
                "type": "string",
                "default": "",
                "description": "Proxy for requests (e.g. 'http://127.0.0.1:8080')",
            },
        },
        "required": ["url"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="commix_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="💉",
    )
