from __future__ import annotations

import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    wordlist = args.get("wordlist", "")
    delay = args.get("delay", 0)
    ips = args.get("ips", False)
    resolver = args.get("resolver", "")
    timeout_val = args.get("timeout", 300)

    if not check_binary("dnsmap"):
        return json_result(False, error="dnsmap not found on PATH")

    if not target:
        return json_result(False, error="'target' parameter is required")

    try:
        argv = ["dnsmap", target]

        if wordlist:
            argv.extend(["-w", wordlist])
        try:
            d = max(0, min(60, int(delay)))
            if d > 0:
                argv.extend(["-d", str(d)])
        except (TypeError, ValueError):
            pass
        if ips:
            argv.append("-i")
        if resolver:
            argv.extend(["-r", resolver])

        argv.extend(["-q"])

        result = run_command_argv(argv, timeout=timeout_val)

        output_text = result.stdout.strip()
        stderr_out = result.stderr.strip()

        subdomains = []
        for line in output_text.split("\n") if output_text else []:
            if "IP" in line or "." in line:
                parts = line.split()
                if len(parts) >= 1:
                    subdomains.append(line.strip())

        return json_result(True, data={
            "target": target,
            "subdomains_found": len(subdomains),
            "subdomains": subdomains[:200],
            "output": output_text[:20000],
        })

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "dnsmap_scan",
    "description": "DNS subdomain brute-force discovery. Tests common subdomain names against a target domain to find hidden hosts.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target domain (e.g. 'example.com')",
            },
            "wordlist": {
                "type": "string",
                "default": "",
                "description": "Path to custom subdomain wordlist",
            },
            "delay": {
                "type": "integer",
                "default": 0,
                "description": "Milliseconds delay between queries",
            },
            "ips": {
                "type": "boolean",
                "default": False,
                "description": "Show IP addresses for discovered subdomains",
            },
            "resolver": {
                "type": "string",
                "default": "",
                "description": "Custom DNS resolver IP",
            },
            "timeout": {
                "type": "integer",
                "default": 300,
                "description": "Timeout in seconds",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="dnsmap_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🌐",
    )
