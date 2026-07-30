from __future__ import annotations

import logging
import os

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"

SCAN_TYPES = {
    "spider": ["-t", "spider"],
    "active": ["-t", "active"],
    "full": [],
    "ajax": ["-t", "ajax"],
}


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    scan_type = args.get("scan_type", "full")
    ajax_spider = args.get("ajax_spider", False)
    api_key = args.get("api_key", "")
    zap_host = args.get("zap_host", "localhost")
    zap_port = args.get("zap_port", 8080)

    if not api_key:
        for env_key in ("ZAP_API_KEY", "ZAP_KEY", "OWASP_ZAP_API_KEY"):
            val = os.environ.get(env_key)
            if val:
                api_key = val
                break

    if not check_binary("zap-cli") and not check_binary("zap.sh"):
        return json_result(False, error="zap-cli or zap.sh not found on PATH. Install: pip install zap-cli")

    if not target:
        return json_result(False, error="'target' parameter is required")

    try:
        zap_cli_cmd = "zap-cli"

        if not check_binary(zap_cli_cmd):
            if check_binary("zap.sh"):
                zap_cli_cmd = None

        if not zap_cli_cmd:
            return json_result(False, error="zap-cli not found. Install with: pip install zap-cli")

        env = os.environ.copy()
        if api_key:
            env["ZAP_API_KEY"] = api_key

        argv = [zap_cli_cmd, "--host", zap_host, "--port", str(zap_port)]

        if scan_type == "ajax" or ajax_spider:
            argv.extend(["ajax-spider", target])
        elif scan_type == "active":
            argv.extend(["active-scan", target])
        elif scan_type == "spider":
            argv.extend(["spider", target])
        else:
            argv.extend(["quick-scan", target])

        if api_key:
            argv.extend(["--api-key", api_key])

        result = run_command_argv(argv, timeout=600, env=env)

        output_text = result.stdout.strip()
        stderr_out = result.stderr.strip()

        alerts = []
        if result.returncode == 0:
            for line in output_text.split("\n"):
                if any(w in line.lower() for w in ["alert", "risk", "vuln", "high", "medium"]):
                    alerts.append(line.strip())

        return json_result(True, data={
            "target": target,
            "scan_type": scan_type,
            "alerts_found": len(alerts),
            "alerts": alerts[:100],
            "output": output_text[:20000],
            "stderr": stderr_out[:3000],
        })

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "zap_scan",
    "description": "OWASP ZAP web application security scanner. Runs spider, active scan, AJAX spider, or full quick scan against a target URL.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target URL to scan (e.g. 'https://example.com')",
            },
            "scan_type": {
                "type": "string",
                "enum": list(SCAN_TYPES.keys()),
                "default": "full",
                "description": "spider=URL crawl, active=inject payloads, full=spider+active, ajax=AJAX-aware spider",
            },
            "ajax_spider": {
                "type": "boolean",
                "default": False,
                "description": "Use AJAX spider (handles JS-rendered content)",
            },
            "api_key": {
                "type": "string",
                "default": "",
                "description": "ZAP API key (falls back to ZAP_API_KEY env var)",
            },
            "zap_host": {
                "type": "string",
                "default": "localhost",
                "description": "ZAP daemon host",
            },
            "zap_port": {
                "type": "integer",
                "default": 8080,
                "description": "ZAP daemon port",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="zap_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🕷️",
    )
