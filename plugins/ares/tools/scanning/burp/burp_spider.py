from __future__ import annotations

import json
import logging
import shlex
import time

from plugins.ares.tools.base import check_binary, run_command, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_scanning"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    max_depth = args.get("max_depth", 3)
    max_urls = args.get("max_urls", 500)
    
    if not target:
        return json_result(False, error="target is required")
    
    if check_binary("gobuster"):
        return _gobuster_spider(target, max_depth, max_urls)
    else:
        return _fallback_spider(target, max_depth)


def _gobuster_spider(target: str, max_depth: int, max_urls: int) -> str:
    """Use gobuster for web crawling."""
    try:
        cmd = f"gobuster dir -u {shlex.quote(target)} -w /usr/share/wordlists/dirb/common.txt -t 10 --no-error -q"
        result = run_command(cmd, timeout=300)
        
        urls = []
        for line in result.stdout.split("\n"):
            if line.startswith("/") or target in line:
                urls.append(line.strip())
        
        return json_result(True, data={
            "target": target,
            "max_depth": max_depth,
            "urls_found": len(urls),
            "urls": urls[:max_urls],
        })
    except Exception as e:
        return json_result(False, error=f"Spider failed: {str(e)}")


def _fallback_spider(target: str, max_depth: int) -> str:
    """Fallback to curl-based spider."""
    urls = []
    
    try:
        cmd = f"curl -sL {shlex.quote(target)} --max-time 10 | grep -oP 'href=\"\\K[^\"]+' | head -50"
        result = run_command(cmd, timeout=15)
        
        for line in result.stdout.split("\n"):
            if line.strip():
                urls.append(line.strip())
    except Exception as e:
        logger.warning(f"Spider failed: {e}")
    
    return json_result(True, data={
        "target": target,
        "max_depth": max_depth,
        "scanner": "fallback_grep",
        "urls_found": len(urls),
        "urls": urls[:100],
    })


SCHEMA = {
    "name": "burp_spider",
    "description": "Web application crawling and discovery. Maps out site structure, forms, and endpoints.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Target URL to spider (e.g. 'https://example.com')"},
            "max_depth": {"type": "integer", "default": 3, "minimum": 1, "maximum": 10, "description": "Maximum crawl depth"},
            "max_urls": {"type": "integer", "default": 500, "minimum": 10, "maximum": 5000, "description": "Maximum URLs to discover"},
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="burp_spider",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🕷️",
    )
