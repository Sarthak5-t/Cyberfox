from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    community = args.get("community", "public")
    oid = args.get("oid", "1")
    version = args.get("version", "2c")
    if not target:
        return json_result(False, error="target is required")
    if not check_binary("snmpwalk"):
        return json_result(False, error="snmpwalk not found on PATH")
    try:
        argv = [
            "snmpwalk", f"-v{version}",
            "-c", community,
            target, oid,
        ]
        result = run_command_argv(argv, timeout=120, shell=False)
        output = result.stdout.strip()[:50000]
        if result.returncode != 0 and not output:
            return json_result(False, error=result.stderr.strip() or f"snmpwalk exited {result.returncode}")
        return json_result(True, data={
            "target": target,
            "community": community,
            "oid": oid,
            "output": output,
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "snmpwalk_tool",
    "description": "SNMP MIB walk — enumerate system info, network config, processes, users via SNMP. Requires valid community string.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target IP (e.g. '10.10.10.1')",
            },
            "community": {
                "type": "string",
                "default": "public",
                "description": "SNMP community string",
            },
            "oid": {
                "type": "string",
                "default": "1",
                "description": "OID to walk (default: .1 = full MIB tree)",
            },
            "version": {
                "type": "string",
                "default": "2c",
                "enum": ["1", "2c", "3"],
                "description": "SNMP version",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="snmpwalk_tool",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="📡",
    )
