from __future__ import annotations

import json as json_lib
import logging
import os

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"


def _handle(args: dict, **kw) -> str:
    username = args.get("username", "")
    output_dir = args.get("output_dir", "")
    output_format = args.get("output_format", "json")
    timeout = args.get("timeout", 120)
    all_sites = args.get("all_sites", False)
    csv = args.get("csv", False)
    tor = args.get("tor", False)

    if not check_binary("sherlock"):
        return json_result(False, error="sherlock not found on PATH")

    if not username:
        return json_result(False, error="'username' parameter is required")

    try:
        argv = ["sherlock", username]

        if all_sites:
            argv.append("--all")
        if csv:
            argv.append("--csv")
        if tor:
            argv.append("--tor")
        if output_dir:
            argv.extend(["--output", output_dir])
            os.makedirs(output_dir, exist_ok=True)

        try:
            timeout = max(10, min(600, int(timeout)))
        except (TypeError, ValueError):
            timeout = 120

        result = run_command_argv(argv, timeout=timeout)

        output_text = result.stdout.strip()
        stderr_out = result.stderr.strip()

        sites_found = []
        lines = output_text.split("\n") if output_text else []
        for line in lines:
            if "[+]" in line:
                sites_found.append(line.replace("[+]", "").strip())
            elif "http" in line.lower() and username.lower() in line.lower():
                sites_found.append(line.strip())

        parsed = {}
        output_path = os.path.join(output_dir, f"{username}.json") if output_dir else ""
        if output_path and os.path.exists(output_path):
            try:
                with open(output_path) as f:
                    parsed = json_lib.load(f)
            except Exception:
                pass

        return json_result(True, data={
            "username": username,
            "sites_checked": len(lines),
            "sites_found": len(sites_found),
            "results": sites_found[:200],
            "output_file": output_path or None,
            "raw_lines": output_text[:10000],
            "stderr": stderr_out[:2000],
        })

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "sherlock_search",
    "description": "Search for a username across 400+ social networks and websites using Sherlock. Finds accounts linked to a username for OSINT recon.",
    "parameters": {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "description": "Username to search for across social networks",
            },
            "output_dir": {
                "type": "string",
                "default": "",
                "description": "Directory to save output files (saves JSON per username)",
            },
            "output_format": {
                "type": "string",
                "enum": ["json", "txt"],
                "default": "json",
                "description": "Output format",
            },
            "timeout": {
                "type": "integer",
                "default": 120,
                "minimum": 10,
                "maximum": 600,
                "description": "Timeout in seconds",
            },
            "all_sites": {
                "type": "boolean",
                "default": False,
                "description": "Check ALL sites (including ones that may timeout)",
            },
            "csv": {
                "type": "boolean",
                "default": False,
                "description": "Output results as CSV as well",
            },
            "tor": {
                "type": "boolean",
                "default": False,
                "description": "Route traffic through Tor",
            },
        },
        "required": ["username"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="sherlock_search",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🔎",
    )
