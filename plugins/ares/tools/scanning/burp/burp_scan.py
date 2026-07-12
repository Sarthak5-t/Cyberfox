from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    scan_type = args.get("scan_type", "active")
    scope = args.get("scope", "base")
    
    if not target:
        return json_result(False, error="target is required")
    
    if check_binary("burpsuite"):
        return _burp_scan(target, scan_type, scope)
    else:
        return _fallback_scan(target, scan_type)


def _burp_scan(target: str, scan_type: str, scope: str) -> str:
    """Use Burp Suite headless for scanning."""
    try:
        argv = [
            "timeout", "600",
            "burpsuite", "headless",
            "--project-file", "/tmp/burp_project.burp",
            "--config-file", "/dev/null",
            "--scan-target", target,
            "--scan-type", scan_type,
            "--scan-scope", scope,
        ]
        result = run_command_argv(argv, timeout=600, shell=False)
        
        findings = []
        for line in result.stdout.split("\n"):
            if "Vulnerability" in line or "Issue" in line:
                findings.append({"type": "burp_finding", "detail": line.strip()})
        
        return json_result(True, data={
            "target": target,
            "scan_type": scan_type,
            "scope": scope,
            "findings_count": len(findings),
            "findings": findings[:100],
            "raw_output": result.stdout[:5000],
        })
    except Exception as e:
        return json_result(False, error=f"Burp scan failed: {str(e)}")


def _fallback_scan(target: str, scan_type: str) -> str:
    """Fallback to curl-based scanning when Burp is not available."""
    findings = []
    
    try:
        argv = ["curl", "-sI", target, "--max-time", "10"]
        result = run_command_argv(argv, timeout=15, shell=False)
        
        headers = result.stdout.lower()
        
        security_headers = {
            "strict-transport-security": "Missing HSTS header",
            "x-content-type-options": "Missing X-Content-Type-Options header",
            "x-frame-options": "Missing X-Frame-Options header",
            "x-xss-protection": "Missing X-XSS-Protection header",
            "content-security-policy": "Missing Content-Security-Policy header",
        }
        
        for header, issue in security_headers.items():
            if header not in headers:
                findings.append({
                    "type": "missing_header",
                    "severity": "medium",
                    "detail": issue,
                })
        
        if "server:" in headers:
            for line in result.stdout.split("\n"):
                if line.lower().startswith("server:"):
                    findings.append({
                        "type": "info_disclosure",
                        "severity": "low",
                        "detail": f"Server header disclosed: {line.strip()}",
                    })
    except Exception as e:
        logger.warning(f"Header check failed: {e}")
    
    return json_result(True, data={
        "target": target,
        "scan_type": scan_type,
        "scanner": "fallback_headers",
        "findings_count": len(findings),
        "findings": findings,
    })


SCHEMA = {
    "name": "burp_scan",
    "description": "Web vulnerability scanning using Burp Suite or fallback header analysis. Checks for security misconfigurations, missing headers, and common web vulnerabilities.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Target URL (e.g. 'https://example.com')"},
            "scan_type": {"type": "string", "enum": ["active", "passive"], "default": "active", "description": "Scan type: active (injects payloads) or passive (analyzes traffic)"},
            "scope": {"type": "string", "enum": ["base", "host", "domain"], "default": "base", "description": "Scan scope level"},
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="burp_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🔍",
    )
