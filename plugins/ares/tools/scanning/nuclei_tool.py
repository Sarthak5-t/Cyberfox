from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"



def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    templates = args.get("templates", "cves")
    severity = args.get("severity", "")
    if not check_binary("nuclei"):
        return json_result(False, error="nuclei not found on PATH")
    try:
        argv = ["nuclei", "-target", target, "-json"]
        if templates and templates != "all":
            argv.extend(["-tags", templates])
        if severity:
            argv.extend(["-severity", severity])
        result = run_command_argv(argv, timeout=600, shell=False)
        if result.returncode != 0:
            return json_result(False, error=result.stderr.strip() or f"nuclei exited {result.returncode}")
        findings = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    findings.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return json_result(True, data={
            "target": target,
            "findings_count": len(findings),
            "findings": findings[:500],
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "nuclei_scan",
    "description": "Template-based vulnerability scanning using nuclei. Scans targets against hundreds of vulnerability templates.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Target URL or IP"},
            "templates": {
                "type": "string",
                "default": "cves",
                "description": "Template tags (e.g. 'cves', 'tech', 'os', 'exposures', or 'all')",
            },
            "severity": {
                "type": "string",
                "enum": ["", "info", "low", "medium", "high", "critical"],
                "default": "",
                "description": "Minimum severity filter",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="nuclei_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🛡️",
    )
