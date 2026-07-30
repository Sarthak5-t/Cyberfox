from __future__ import annotations

import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    dns_server = args.get("dns_server", "")
    subfile = args.get("subfile", "")
    threads = args.get("threads", 10)
    page_size = args.get("page_size", 10)
    timeout_val = args.get("timeout", 300)

    if not check_binary("dnsenum"):
        return json_result(False, error="dnsenum not found on PATH")

    if not target:
        return json_result(False, error="'target' parameter is required")

    try:
        argv = ["dnsenum", "--enum"]

        try:
            threads = max(1, min(50, int(threads)))
            argv.extend(["--threads", str(threads)])
        except (TypeError, ValueError):
            pass

        try:
            page_size = max(1, min(100, int(page_size)))
            argv.extend(["--pages", str(page_size)])
        except (TypeError, ValueError):
            pass

        if dns_server:
            argv.extend(["--dnsserver", dns_server])
        if subfile:
            argv.extend(["--subfile", subfile])

        argv.append(target)

        result = run_command_argv(argv, timeout=timeout_val)

        output_text = result.stdout.strip()
        stderr_out = result.stderr.strip()

        hosts = []
        nameservers = []
        mx_records = []
        zone_transfer = None
        for line in output_text.split("\n") if output_text else []:
            if "Name Server" in line or "nameserver" in line.lower():
                nameservers.append(line.strip())
            elif "MX" in line or "mail" in line.lower():
                mx_records.append(line.strip())
            elif "Zone Transfer" in line:
                zone_transfer = line.strip()
            elif "host" in line.lower() and "." in line and len(line) > 10:
                hosts.append(line.strip())

        return json_result(True, data={
            "target": target,
            "hosts_found": len(hosts),
            "hosts": hosts[:200],
            "nameservers": nameservers,
            "mx_records": mx_records,
            "zone_transfer": zone_transfer,
            "output": output_text[:20000],
            "stderr": stderr_out[:2000],
        })

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "dnsenum_scan",
    "description": "DNS enumeration tool — performs subdomain brute-force, reverse DNS lookups, zone transfer checks, and MX/NS record discovery.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target domain (e.g. 'example.com')",
            },
            "dns_server": {
                "type": "string",
                "default": "",
                "description": "Custom DNS server to query",
            },
            "subfile": {
                "type": "string",
                "default": "",
                "description": "Custom subdomain wordlist file",
            },
            "threads": {
                "type": "integer",
                "default": 10,
                "minimum": 1,
                "maximum": 50,
                "description": "Number of threads",
            },
            "page_size": {
                "type": "integer",
                "default": 10,
                "minimum": 1,
                "maximum": 100,
                "description": "Page size for subdomain queries",
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
        name="dnsenum_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🌐",
    )
