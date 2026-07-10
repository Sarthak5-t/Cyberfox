from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"


def _handle(args: dict, **kw) -> str:
    domain = args.get("domain", "")
    wordlist = args.get("wordlist", "/usr/share/wordlists/subdomains.txt")
    threads = args.get("threads", 10)
    
    if not domain:
        return json_result(False, error="domain is required")
    
    if not check_binary("subjack"):
        return json_result(False, error="subjack not found on PATH")
    
    return _scan_subdomains(domain, wordlist, threads)


def _scan_subdomains(domain: str, wordlist: str, threads: int) -> str:
    """Scan for subdomain takeover vulnerabilities."""
    try:
        cmd = f"subjack -w {shlex.quote(wordlist)} -t {threads} -timeout 30 -ssl -c fingerprints.json -v {shlex.quote(domain)}"
        result = run_command(cmd, timeout=600)
        
        findings = []
        for line in result.stdout.split("\n"):
            if "vulnerable" in line.lower() or "takeover" in line.lower():
                findings.append({"type": "subdomain_takeover", "detail": line.strip()})
        
        return json_result(True, data={
            "domain": domain,
            "findings_count": len(findings),
            "findings": findings[:100],
            "raw_output": result.stdout[:5000],
        })
    except Exception as e:
        return json_result(False, error=f"Subjack scan failed: {str(e)}")


SCHEMA = {
    "name": "subjack",
    "description": "Scan for subdomain takeover vulnerabilities using subjack.",
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "Target domain (e.g. 'example.com')"},
            "wordlist": {"type": "string", "default": "/usr/share/wordlists/subdomains.txt", "description": "Subdomain wordlist path"},
            "threads": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50, "description": "Number of threads"},
        },
        "required": ["domain"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="subjack",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🎯",
    )
