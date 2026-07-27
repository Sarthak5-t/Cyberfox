from __future__ import annotations

from plugins.ares.tools.base import json_result, tool_error

TOOLSET = "ares_utility"

SCHEMA = {
    "name": "cve_enrich",
    "description": "Enrich a CVE with NVD, EPSS, CISA KEV, and MITRE ATT&CK data. Returns CVSS, CWE, exploitation probability, and priority score.",
    "parameters": {
        "type": "object",
        "properties": {
            "cve_id": {
                "type": "string",
                "description": "CVE identifier (e.g., CVE-2024-1234)",
            },
        },
        "required": ["cve_id"],
    },
}


def _handle(args: dict, **kw) -> str:
    from plugins.ares.config import get_config
    from plugins.ares.enrichment.pipeline import enrich_cve, init_cache_db
    from plugins.ares.enrichment.nvd_client import NVDClient
    from plugins.ares.enrichment.epss_client import EPSSClient
    from plugins.ares.enrichment.kev_client import KEVClient

    cve_id = args.get("cve_id", "").strip().upper()
    if not cve_id.startswith("CVE-"):
        return tool_error(f"Invalid CVE format: {cve_id}")

    cfg = get_config()
    if not cfg.nvd_api_key:
        return tool_error(
            "NVD API key required. Set nvd_api_key in ares config.yaml"
        )

    init_cache_db()
    nvd = NVDClient(cfg.nvd_api_key)
    epss = EPSSClient()
    kev = KEVClient()

    enriched = enrich_cve(cve_id, nvd, epss, kev)
    return json_result(True, data=enriched)


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="cve_enrich",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🔍",
    )
