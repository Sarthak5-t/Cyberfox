from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    template_type = args.get("template_type", "cve")
    severity = args.get("severity", "critical,high")
    
    if not target:
        return json_result(False, error="target is required")
    
    if not check_binary("nuclei"):
        return json_result(False, error="nuclei not found on PATH")
    
    return _run_nuclei_templates(target, template_type, severity)


def _run_nuclei_templates(target: str, template_type: str, severity: str) -> str:
    """Run nuclei with specific template categories."""
    try:
        template_map = {
            "cve": "cves",
            "misconfiguration": "misconfigurations",
            "exposure": "exposures",
            "technologies": "technologies",
            "default": "default-logins",
        }
        
        template_dir = template_map.get(template_type, "cves")
        
        argv = [
            "nuclei", "-u", target,
            "-severity", severity,
            "-t", f"nuclei-templates/{template_dir}/",
            "-json",
        ]
        result = run_command_argv(argv, timeout=600, shell=False)
        
        findings = []
        for line in result.stdout.split("\n"):
            if line.strip():
                try:
                    finding = json.loads(line)
                    findings.append(finding)
                except json.JSONDecodeError:
                    pass
        
        return json_result(True, data={
            "target": target,
            "template_type": template_type,
            "severity": severity,
            "findings_count": len(findings),
            "findings": findings[:100],
        })
    except Exception as e:
        return json_result(False, error=f"Nuclei templates scan failed: {str(e)}")


SCHEMA = {
    "name": "nuclei_templates",
    "description": "Run nuclei with specific template categories (CVEs, misconfigurations, exposures).",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Target URL or IP"},
            "template_type": {"type": "string", "enum": ["cve", "misconfiguration", "exposure", "technologies", "default"], "default": "cve", "description": "Template category"},
            "severity": {"type": "string", "default": "critical,high", "description": "Severity filter (comma-separated)"},
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="nuclei_templates",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🔎",
    )
