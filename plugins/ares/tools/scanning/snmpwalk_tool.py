from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

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
        cmd = f"snmpwalk -v{shlex.quote(str(version))} -c {shlex.quote(community)} {shlex.quote(target)} {shlex.quote(oid)}"
        result = run_command(cmd, timeout=120)
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
