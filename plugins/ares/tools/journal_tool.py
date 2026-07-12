from __future__ import annotations

from plugins.ares.tools.base import json_result
from plugins.ares.journal_store import (
    init_journal,
    append_entry,
    read_journal,
    read_recent,
    search_journal,
    journal_exists,
)

TOOLSET = "ares_utility"


def _handle_init(args: dict, **kw) -> str:
    engagement = args.get("engagement_name", "engagement")
    targets = args.get("targets", "")
    init_journal(engagement, targets)
    return json_result(True, data={"message": f"Journal initialized for '{engagement}'", "path": str("journal.md")})


def _handle_write(args: dict, **kw) -> str:
    category = args.get("category", "general")
    content = args.get("content", "")
    target = args.get("target")
    if not content.strip():
        return json_result(False, error="content is required")
    ok = append_entry(category, content, target)
    return json_result(ok, data={"status": "entry added"}, error="Failed to write entry" if not ok else None)


def _handle_read(args: dict, **kw) -> str:
    if not journal_exists():
        return json_result(True, data={"journal": "", "message": "No journal exists yet. Use journal_init to create one."})
    search = args.get("search")
    last_n = args.get("last_n")
    if search:
        content = search_journal(search)
    elif last_n:
        content = read_recent(last_n)
    else:
        content = read_journal()
    # Truncate for display
    if len(content) > 4000:
        content = content[:2000] + "\n\n[... truncated ...]\n\n" + content[-2000:]
    return json_result(True, data={"journal": content, "length": len(content)})


_INIT_SCHEMA = {
    "name": "journal_init",
    "description": "Initialize the engagement journal. Call this at the start of every new engagement or CTF challenge. Creates a fresh journal file to track all discoveries, decisions, and actions.",
    "parameters": {
        "type": "object",
        "properties": {
            "engagement_name": {
                "type": "string",
                "description": "Name of the engagement (e.g. 'CTF Challenge 1', 'Target 192.168.1.0/24')",
            },
            "targets": {
                "type": "string",
                "description": "Comma-separated list of targets (e.g. '192.168.1.1, 192.168.1.10')",
            },
        },
        "required": ["engagement_name"],
    },
}

_WRITE_SCHEMA = {
    "name": "journal_write",
    "description": "Write an entry to the engagement journal. Use this EVERY TIME you discover something significant — new service, CVE, credential, vulnerability, decision, or action. This is your persistent memory across turns.",
    "parameters": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["recon", "scanning", "exploit", "ad", "credential", "decision", "finding", "general"],
                "description": "Category of the entry",
            },
            "content": {
                "type": "string",
                "description": "What you discovered, decided, or did. Be specific — include service names, versions, CVEs, IPs, ports, credentials, exploit commands, etc.",
            },
            "target": {
                "type": "string",
                "description": "Target this entry relates to (IP, hostname, URL)",
            },
        },
        "required": ["category", "content"],
    },
}

_READ_SCHEMA = {
    "name": "journal_read",
    "description": "Read the engagement journal. Use this to recall what you've discovered so far, review your progress, or check what's been done.",
    "parameters": {
        "type": "object",
        "properties": {
            "last_n": {
                "type": "integer",
                "description": "Read only the last N entries (optional)",
            },
            "search": {
                "type": "string",
                "description": "Search the journal for entries matching this query",
            },
        },
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="journal_init",
        toolset=TOOLSET,
        schema=_INIT_SCHEMA,
        handler=lambda args, **kw: _handle_init(args, **kw),
        emoji="📓",
    )
    ctx.register_tool(
        name="journal_write",
        toolset=TOOLSET,
        schema=_WRITE_SCHEMA,
        handler=lambda args, **kw: _handle_write(args, **kw),
        emoji="📝",
    )
    ctx.register_tool(
        name="journal_read",
        toolset=TOOLSET,
        schema=_READ_SCHEMA,
        handler=lambda args, **kw: _handle_read(args, **kw),
        emoji="📖",
    )
