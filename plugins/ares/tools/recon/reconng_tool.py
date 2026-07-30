from __future__ import annotations

import json
import logging
import os
import tempfile

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"

RECON_MODULES = {
    "dns/hosts": "recon/domains-hosts/hackertarget",
    "dns/subdomains": "recon/domains-hosts/brute_hosts",
    "dns/zones": "recon/domains-hosts/zonetransfer",
    "dns/reverse": "recon/hosts-domains/reverse_resolve",
    "contacts/creds": "recon/contacts-creds/hibp",
    "contacts/social": "recon/contacts-creds/scythe",
    "ports/banner": "recon/hosts-ports/banner_http",
    "geoip": "recon/hosts-hosts/ip_geoip",
    "whois": "recon/domains-hosts/whois_pocs",
    "shodan": "recon/domains-hosts/shodan_search",
    "censys": "recon/domains-hosts/census_2019_censys",
}


def _handle(args: dict, **kw) -> str:
    workspace = args.get("workspace", "ares_workspace")
    module = args.get("module", "")
    source = args.get("source", "")
    options = args.get("options", {})
    resource_file = args.get("resource_file", "")

    if not check_binary("recon-ng"):
        return json_result(False, error="recon-ng not found on PATH")

    try:
        script_lines = [
            f"workspaces create {workspace}" if workspace != "ares_workspace" else f"workspaces select {workspace}",
        ]

        if resource_file:
            script_lines.append(f"resource {resource_file}")
        elif module:
            full_module = RECON_MODULES.get(module, module)
            script_lines.append(f"modules load {full_module}")
            if source:
                script_lines.append(f"set SOURCE {source}")
            for key, val in options.items():
                script_lines.append(f"set {key} {val}")
            script_lines.append("run")
        else:
            script_lines.append("show modules")

        script_lines.append("exit")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".rc", delete=False) as f:
            f.write("\n".join(script_lines))
            rc_path = f.name

        argv = ["recon-ng", "-r", rc_path]

        if options.get("no_color"):
            argv.append("--no-color")

        result = run_command_argv(argv, timeout=300)

        os.unlink(rc_path)

        output_text = result.stdout.strip()
        stderr_out = result.stderr.strip()

        return json_result(True, data={
            "workspace": workspace,
            "module": module or "none",
            "source": source or None,
            "output": output_text[:30000],
            "stderr": stderr_out[:3000],
        })

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "reconng_scan",
    "description": "Recon-ng recon framework. Runs module-based workflows for DNS enumeration, contact discovery, port banner grabbing, and more. Use the module name key for common modules, or pass a full module path in options.",
    "parameters": {
        "type": "object",
        "properties": {
            "workspace": {
                "type": "string",
                "default": "ares_workspace",
                "description": "Recon-ng workspace name",
            },
            "module": {
                "type": "string",
                "enum": list(RECON_MODULES.keys()),
                "description": "Module key from the preset list (e.g. 'dns/hosts', 'dns/subdomains', 'whois', 'shodan'). Leave empty to list modules.",
            },
            "source": {
                "type": "string",
                "default": "",
                "description": "SOURCE value for the module (domain, host, IP, etc.)",
            },
            "options": {
                "type": "object",
                "default": {},
                "description": "Additional module options as key=value pairs",
            },
            "resource_file": {
                "type": "string",
                "default": "",
                "description": "Path to a resource script file (overrides module/source)",
            },
        },
        "required": [],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="reconng_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🔎",
    )
