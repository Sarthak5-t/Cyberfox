from __future__ import annotations

import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"


def _handle(args: dict, **kw) -> str:
    url = args.get("url", "")
    params = args.get("params", "")
    crawl = args.get("crawl", False)
    crawl_depth = args.get("crawl_depth", 2)
    skip_dom = args.get("skip_dom_check", False)
    blind_xss = args.get("blind_xss", False)
    timeout_val = args.get("timeout", 300)
    headers = args.get("headers", "")
    proxy = args.get("proxy", "")

    if not check_binary("xsstrike"):
        return json_result(False, error="xsstrike not found on PATH")

    if not url:
        return json_result(False, error="'url' parameter is required")

    try:
        argv = ["xsstrike", "-u", url]

        if params:
            argv.extend(["--data", params])
        if crawl:
            argv.append("--crawl")
            try:
                argv.extend(["--crawl-depth", str(max(1, min(5, int(crawl_depth))))])
            except (TypeError, ValueError):
                argv.extend(["--crawl-depth", "2"])
        if skip_dom:
            argv.append("--skip-dom")
        if blind_xss:
            argv.append("--blind")
        if headers:
            argv.extend(["--headers", headers])
        if proxy:
            argv.extend(["--proxy", proxy])

        argv.extend(["--timeout", "30"])

        result = run_command_argv(argv, timeout=timeout_val)

        output_text = result.stdout.strip()
        stderr_out = result.stderr.strip()

        vulnerable = False
        vuln_params = []
        payloads = []
        for line in output_text.split("\n") if output_text else []:
            if "Vulnerable" in line or "XSS" in line:
                vulnerable = True
            if "param" in line.lower() and ":" in line:
                vuln_params.append(line.strip())
            if "payload" in line.lower():
                payloads.append(line.strip())

        return json_result(True, data={
            "url": url,
            "vulnerable": vulnerable,
            "vulnerable_params": vuln_params,
            "payloads": payloads[:50],
            "output": output_text[:30000],
            "stderr": stderr_out[:3000],
            "crawl_used": crawl,
        })

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "xsstrike_scan",
    "description": "Advanced XSS detection with XSStrike. Tests for reflected, stored, DOM-based XSS with context-aware payload generation.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Target URL to test for XSS",
            },
            "params": {
                "type": "string",
                "default": "",
                "description": "POST data parameters if testing POST endpoint",
            },
            "crawl": {
                "type": "boolean",
                "default": False,
                "description": "Crawl the target before testing",
            },
            "crawl_depth": {
                "type": "integer",
                "default": 2,
                "minimum": 1,
                "maximum": 5,
                "description": "Crawl depth (if crawl is enabled)",
            },
            "skip_dom_check": {
                "type": "boolean",
                "default": False,
                "description": "Skip DOM XSS scanning",
            },
            "blind_xss": {
                "type": "boolean",
                "default": False,
                "description": "Enable blind XSS payload injection",
            },
            "headers": {
                "type": "string",
                "default": "",
                "description": "Custom headers for requests",
            },
            "proxy": {
                "type": "string",
                "default": "",
                "description": "Proxy for requests (e.g. 'http://127.0.0.1:8080')",
            },
            "timeout": {
                "type": "integer",
                "default": 300,
                "description": "Timeout in seconds",
            },
        },
        "required": ["url"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="xsstrike_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="⚡",
    )
