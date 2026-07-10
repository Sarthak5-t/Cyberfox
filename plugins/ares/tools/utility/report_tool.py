from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from plugins.ares.tools.base import json_result, _cyberfox_home

logger = logging.getLogger(__name__)

TOOLSET = "ares_utility"



def _handle(args: dict, **kw) -> str:
    title = args.get("title", "Security Assessment Report")
    target = args.get("target", "Unknown")
    findings = args.get("findings", [])
    severity = args.get("severity", "info")
    try:
        reports_dir = _cyberfox_home() / "ares" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in target)
        report_file = reports_dir / f"report_{safe_name}_{ts}.json"

        doc = {
            "title": title,
            "target": target,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            "findings": findings if isinstance(findings, list) else [findings],
        }
        report_file.write_text(json.dumps(doc, indent=2))
        return json_result(True, data={"path": str(report_file), "finding_count": len(doc["findings"])})
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "report_save",
    "description": "Save a structured findings report to the ares/reports directory. Stores findings with severity, target metadata, and timestamp.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "default": "Security Assessment Report", "description": "Report title"},
            "target": {"type": "string", "description": "Target host, domain, or scope identifier"},
            "findings": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of finding objects, each with 'type', 'severity', 'description', 'evidence' fields",
            },
            "severity": {
                "type": "string",
                "enum": ["critical", "high", "medium", "low", "info"],
                "default": "info",
                "description": "Overall report severity",
            },
        },
        "required": ["target", "findings"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="report_save",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="📋",
    )
