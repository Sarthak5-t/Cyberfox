from __future__ import annotations

import json
import logging

import re

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

_DANGEROUS_FILENAME_RE = re.compile(r"[;|`\n\r\x00]")

TOOLSET = "ares_scanning"


def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    share = args.get("share", "")
    username = args.get("username", "")
    password = args.get("password", "")
    action = args.get("action", "list")
    if not target:
        return json_result(False, error="target is required")
    if not check_binary("smbclient"):
        return json_result(False, error="smbclient not found on PATH")
    try:
        argv = ["smbclient"]
        if share:
            argv.append(f"//{target}/{share}")
        else:
            argv.extend(["-L", f"//{target}"])
        if username:
            auth = username
            if password:
                auth += f"%{password}"
            argv.extend(["-U", auth])
        if share:
            if action == "list":
                argv.extend(["-c", "ls"])
            elif action == "get":
                remote_file = args.get("remote_file", "")
                local_file = args.get("local_file", "/tmp/smb_loot")
                if _DANGEROUS_FILENAME_RE.search(remote_file) or _DANGEROUS_FILENAME_RE.search(local_file):
                    return json_result(False, error="Filename contains dangerous characters")
                argv.extend(["-c", f"get {remote_file} {local_file}"])
            elif action == "put":
                local_file = args.get("local_file", "")
                remote_file = args.get("remote_file", "uploaded")
                if _DANGEROUS_FILENAME_RE.search(local_file) or _DANGEROUS_FILENAME_RE.search(remote_file):
                    return json_result(False, error="Filename contains dangerous characters")
                argv.extend(["-c", f"put {local_file} {remote_file}"])
            elif action == "enum":
                argv.extend(["-c", "recurse; ls"])
            else:
                return json_result(False, error=f"Unknown action: {action}")
        result = run_command_argv(argv, timeout=60)
        output = result.stdout.strip()[:50000]
        if result.returncode != 0 and not output:
            return json_result(False, error=result.stderr.strip() or f"smbclient exited {result.returncode}")
        return json_result(True, data={
            "target": target,
            "share": share,
            "action": action,
            "output": output,
        })
    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "smbclient_tool",
    "description": "SMB client — list shares, browse files, upload/download via SMB.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Target IP"},
            "share": {"type": "string", "default": "", "description": "Share name (empty = list shares)"},
            "username": {"type": "string", "default": ""},
            "password": {"type": "string", "default": ""},
            "action": {"type": "string", "enum": ["list", "get", "put", "enum"], "default": "list"},
            "remote_file": {"type": "string", "default": ""},
            "local_file": {"type": "string", "default": "/tmp/smb_loot"},
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="smbclient_tool",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="📂",
    )
