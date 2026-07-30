from __future__ import annotations

import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"

CMS_TYPES = ["auto", "wordpress", "joomla", "drupal", "moodle", "silverstripe"]


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    cms_type = args.get("cms_type", "auto")
    verbose = args.get("verbose", False)
    timeout_val = args.get("timeout", 300)

    if not check_binary("cmsmap"):
        return json_result(False, error="cmsmap not found on PATH")

    if not target:
        return json_result(False, error="'target' parameter is required")

    try:
        argv = ["cmsmap", "-t", target, "-q"]
        if cms_type and cms_type != "auto":
            argv.extend(["-c", cms_type])
        if verbose:
            argv.append("-v")

        result = run_command_argv(argv, timeout=timeout_val)

        output_text = result.stdout.strip()
        stderr_out = result.stderr.strip()

        cms_detected = ""
        version = ""
        users = []
        plugins = []
        vulnerabilities = []

        for line in (output_text + "\n" + stderr_out).split("\n"):
            if "CMS" in line and ":" in line and not cms_detected:
                cms_detected = line.strip()
            elif "version" in line.lower() and ":" in line:
                version = line.strip()
            elif "user" in line.lower() and ":" in line:
                users.append(line.strip())
            elif "plugin" in line.lower() or "theme" in line.lower():
                plugins.append(line.strip())
            elif "vuln" in line.lower() or "CVE" in line or "issue" in line.lower():
                vulnerabilities.append(line.strip())

        return json_result(True, data={
            "target": target,
            "cms_detected": cms_detected or None,
            "version": version or None,
            "users_found": len(users),
            "users": users[:50],
            "plugins_themes": plugins[:50],
            "vulnerabilities": vulnerabilities[:50],
            "output": output_text[:20000],
        })

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "cmsmap_scan",
    "description": "CMS detection and vulnerability scanner. Detects WordPress, Joomla, Drupal, Moodle, and SilverStripe with version, users, plugins, and known CVEs.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target URL (e.g. 'https://example.com')",
            },
            "cms_type": {
                "type": "string",
                "enum": CMS_TYPES,
                "default": "auto",
                "description": "CMS type hint (auto = detect automatically)",
            },
            "verbose": {
                "type": "boolean",
                "default": False,
                "description": "Verbose output",
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
        name="cmsmap_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🌍",
    )
