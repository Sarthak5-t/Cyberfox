from __future__ import annotations

import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    checks = args.get("checks", "dynamic")
    proxy = args.get("proxy", "")
    timeout_val = args.get("timeout", 300)

    if not check_binary("uniscan"):
        return json_result(False, error="uniscan not found on PATH")

    if not target:
        return json_result(False, error="'target' parameter is required")

    try:
        argv = ["uniscan", "-u", target, "-q"]

        check_opts = checks.lower().replace(" ", "").split(",")
        for c in check_opts:
            if c == "dynamic":
                argv.append("-d")
            elif c == "static":
                argv.append("-s")
            elif c in ("dirs", "directories"):
                argv.append("-w")
        if proxy:
            argv.extend(["-p", proxy])

        result = run_command_argv(argv, timeout=timeout_val)

        output_text = result.stdout.strip()
        stderr_out = result.stderr.strip()

        dirs_found = []
        files_found = []
        dynamic_issues = []

        for line in output_text.split("\n") if output_text else []:
            if "/" in line and ("200" in line or "301" in line or "403" in line):
                if "." in line.split("/")[-1] if "/" in line else False:
                    files_found.append(line.strip())
                else:
                    dirs_found.append(line.strip())
            elif "vuln" in line.lower() or "issue" in line.lower():
                dynamic_issues.append(line.strip())

        return json_result(True, data={
            "target": target,
            "checks": checks,
            "directories_found": len(dirs_found),
            "directories": dirs_found[:200],
            "files_found": len(files_found),
            "files": files_found[:100],
            "dynamic_issues": dynamic_issues[:50] or None,
            "output": output_text[:20000],
        })

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "uniscan_scan",
    "description": "Web security scanner combining directory enumeration, static file checks, and dynamic vulnerability testing.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target URL (e.g. 'https://example.com')",
            },
            "checks": {
                "type": "string",
                "default": "dynamic",
                "description": "Comma-separated checks: dynamic, static, dirs (e.g. 'dynamic,static,dirs')",
            },
            "proxy": {
                "type": "string",
                "default": "",
                "description": "Proxy for requests (e.g. 'http://127.0.0.1:8080')",
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
        name="uniscan_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🔍",
    )
