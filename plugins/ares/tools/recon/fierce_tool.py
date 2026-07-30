from __future__ import annotations

import logging
import re

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"


def _handle(args: dict, **kw) -> str:
    domain = args.get("domain", "")
    dns_server = args.get("dns_server", "")
    wordlist = args.get("wordlist", "")
    threads = args.get("threads", 10)
    delay = args.get("delay", 0)
    zone_transfer = args.get("zone_transfer", False)
    timeout_val = args.get("timeout", 300)

    if not check_binary("fierce"):
        return json_result(False, error="fierce not found on PATH")

    if not domain:
        return json_result(False, error="'domain' parameter is required")

    try:
        argv = ["fierce", "--domain", domain]

        if dns_server:
            argv.extend(["--dns-server", dns_server])
        if wordlist:
            argv.extend(["--wordlist", wordlist])
        try:
            t = max(1, min(50, int(threads)))
            if t > 1:
                argv.extend(["--threads", str(t)])
        except (TypeError, ValueError):
            pass
        try:
            d = max(0, min(60, int(delay)))
            if d > 0:
                argv.extend(["--delay", str(d)])
        except (TypeError, ValueError):
            pass
        if zone_transfer:
            argv.append("--zonetransfer")

        result = run_command_argv(argv, timeout=timeout_val)

        output_text = result.stdout.strip()
        stderr_out = result.stderr.strip()

        subdomains = []
        nameservers = []
        zone_transfer_result = None
        ips = []

        for line in output_text.split("\n") if output_text else []:
            if "found" in line.lower() and "." in line:
                subdomains.append(line.strip())
            elif "nameserver" in line.lower() or "NS:" in line:
                nameservers.append(line.strip())
            elif "Zone Transfer" in line or "zone" in line.lower():
                zone_transfer_result = line.strip()
            elif "ip" in line.lower() or re.search(r'\d+\.\d+\.\d+\.\d+', line):
                ips.append(line.strip())

        return json_result(True, data={
            "domain": domain,
            "subdomains_found": len(subdomains),
            "subdomains": subdomains[:200],
            "nameservers": nameservers,
            "zone_transfer": zone_transfer_result,
            "output": output_text[:20000],
        })

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "fierce_scan",
    "description": "DNS reconnaissance tool for locating non-contiguous IP space and subdomains. Uses DNS brute-force, zone transfer checks, and reverse lookups.",
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Target domain to scan",
            },
            "dns_server": {
                "type": "string",
                "default": "",
                "description": "Specific DNS server to query",
            },
            "wordlist": {
                "type": "string",
                "default": "",
                "description": "Custom subdomain wordlist path",
            },
            "threads": {
                "type": "integer",
                "default": 10,
                "minimum": 1,
                "maximum": 50,
                "description": "Number of scan threads",
            },
            "delay": {
                "type": "integer",
                "default": 0,
                "description": "Delay between queries (seconds, for stealth)",
            },
            "zone_transfer": {
                "type": "boolean",
                "default": False,
                "description": "Attempt DNS zone transfer",
            },
            "timeout": {
                "type": "integer",
                "default": 300,
                "description": "Timeout in seconds",
            },
        },
        "required": ["domain"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="fierce_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🌐",
    )
