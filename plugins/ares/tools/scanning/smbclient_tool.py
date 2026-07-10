from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

logger = logging.getLogger(__name__)

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
        auth = ""
        if username:
            auth = f"-U {shlex.quote(username)}"
            if password:
                auth += f"%{shlex.quote(password)}"
        if share:
            if action == "list":
                cmd = f"smbclient {shlex.quote(f'//{target}/{share}')} {auth} -c 'ls'"
            elif action == "get":
                remote_file = args.get("remote_file", "")
                local_file = args.get("local_file", "/tmp/smb_loot")
                cmd = f"smbclient {shlex.quote(f'//{target}/{share}')} {auth} -c 'get {shlex.quote(remote_file)} {shlex.quote(local_file)}'"
            elif action == "put":
                local_file = args.get("local_file", "")
                remote_file = args.get("remote_file", "uploaded")
                cmd = f"smbclient {shlex.quote(f'//{target}/{share}')} {auth} -c 'put {shlex.quote(local_file)} {shlex.quote(remote_file)}'"
            elif action == "enum":
                cmd = f"smbclient {shlex.quote(f'//{target}/{share}')} {auth} -c 'recurse; ls'"
            else:
                return json_result(False, error=f"Unknown action: {action}")
        else:
            cmd = f"smbclient -L {shlex.quote(f'//{target}')} {auth}"
        result = run_command(cmd, timeout=60)
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
    "description": "SMB client — list shares, browse files, upload/download files via SMB. Supports null sessions and authenticated access.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target IP (e.g. '10.10.10.1')",
            },
            "share": {
                "type": "string",
                "default": "",
                "description": "Share name (e.g. 'IPC$', 'ADMIN$', 'C$', 'Users'). Empty = list shares.",
            },
            "username": {
                "type": "string",
                "default": "",
                "description": "Username (empty for null session)",
            },
            "password": {
                "type": "string",
                "default": "",
                "description": "Password",
            },
            "action": {
                "type": "string",
                "enum": ["list", "get", "put", "enum"],
                "default": "list",
                "description": "Action: list (files), get (download), put (upload), enum (recursive list)",
            },
            "remote_file": {
                "type": "string",
                "default": "",
                "description": "Remote file path for get/put",
            },
            "local_file": {
                "type": "string",
                "default": "/tmp/smb_loot",
                "description": "Local file path for get/put",
            },
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
