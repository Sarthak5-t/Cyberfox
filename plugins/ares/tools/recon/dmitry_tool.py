from __future__ import annotations

import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    modules = args.get("modules", "whois,subdomains,ports,email")
    output = args.get("output", "")

    if not check_binary("dmitry"):
        return json_result(False, error="dmitry not found on PATH")

    if not target:
        return json_result(False, error="'target' parameter is required")

    try:
        argv = ["dmitry"]

        mods = modules.lower().replace(" ", "").split(",")
        if "whois" in mods:
            argv.append("-w")
        if "subdomains" in mods:
            argv.append("-s")
        if "ports" in mods:
            argv.append("-p")
        if "email" in mods:
            argv.append("-e")
        if "banners" in mods:
            argv.append("-b")
        if "redirect" in mods:
            argv.append("-r")
        if "tcp" in mods:
            argv.extend(["-t", "100"])
        if len(argv) == 1:
            argv.extend(["-w", "-s", "-p", "-e"])

        if output:
            argv.extend(["-o", output])

        argv.append(target)

        result = run_command_argv(argv, timeout=300)

        output_text = result.stdout.strip()
        stderr_out = result.stderr.strip()

        whois_info = []
        subdomains = []
        ports_found = []
        emails = []

        for line in output_text.split("\n") if output_text else []:
            if "@" in line:
                emails.append(line.strip())
            elif ":" in line and any(c.isdigit() for c in line.split(":")[0]):
                ports_found.append(line.strip())
            elif "." in line and target.split(".")[0] in line:
                subdomains.append(line.strip())
            elif line.strip():
                whois_info.append(line.strip())

        return json_result(True, data={
            "target": target,
            "modules_used": mods,
            "whois_lines": len(whois_info),
            "subdomains_found": len(subdomains),
            "subdomains": subdomains[:100],
            "ports_found": ports_found[:100],
            "emails_found": len(emails),
            "emails": emails[:50],
            "output": output_text[:20000],
        })

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "dmitry_scan",
    "description": "Deepmagic Information Gathering Tool — performs WHOIS lookups, subdomain discovery, open port scanning, email harvesting, and banner grabbing.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target domain or IP address",
            },
            "modules": {
                "type": "string",
                "default": "whois,subdomains,ports,email",
                "description": "Comma-separated modules: whois, subdomains, ports, email, banners, redirect, tcp",
            },
            "output": {
                "type": "string",
                "default": "",
                "description": "Output file prefix",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="dmitry_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🔍",
    )
