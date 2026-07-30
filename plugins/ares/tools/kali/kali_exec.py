from __future__ import annotations

import logging
import os
import shlex
import shutil

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_exploit"

BLOCKLIST = {
    "rm", "dd", "fdisk", "mkfs", "mkfs.ext4", "mkfs.btrfs",
    "halt", "reboot", "poweroff", "shutdown", "init",
    "kill", "killall", "pkill", "passwd", "chmod", "chown",
    "sudo", "su", "mount", "umount", "modprobe",
    "insmod", "rmmod", "iwconfig", "ifconfig",
    "ip", "iptables", "systemctl", "service",
    "dpkg", "apt", "apt-get", "pacman", "dnf", "yum", "rpm",
    "pip", "pip3", "npm", "npx", "make", "cmake", "gcc", "g++",
    "wget", "curl", "nc", "ncat", "socat",
}

SYSTEM_PATHS = ["/usr/bin", "/usr/sbin", "/usr/share", "/usr/lib", "/opt", "/snap/bin"]


def _is_safe_path(bin_path: str) -> bool:
    resolved = os.path.realpath(bin_path)
    for p in SYSTEM_PATHS:
        if resolved.startswith(p):
            return True
    return False


def _handle(args: dict, **kw) -> str:
    tool = args.get("tool", "").strip()
    raw_args = args.get("args", "").strip()
    stdin_data = args.get("stdin", "")
    timeout = args.get("timeout", 300)

    if not tool:
        return json_result(False, error="'tool' parameter is required")

    tool_basename = os.path.basename(tool)
    if tool_basename in BLOCKLIST:
        return json_result(False, error=f"'{tool_basename}' is blocked for safety")

    bin_path = shutil.which(tool)
    if not bin_path:
        return json_result(False, error=f"'{tool}' not found on PATH — is it installed?")

    if not _is_safe_path(bin_path):
        return json_result(False, error=f"'{bin_path}' is not in a system binary path")

    try:
        argv = [bin_path] + shlex.split(raw_args)
    except ValueError as e:
        return json_result(False, error=f"Failed to parse args: {e}")

    try:
        timeout = max(1, min(3600, int(timeout)))
    except (TypeError, ValueError):
        timeout = 300

    try:
        result = run_command_argv(argv, timeout=timeout)
        output = result.stdout.strip()
        err = result.stderr.strip()

        data = {
            "tool": tool,
            "command": " ".join(argv),
            "returncode": result.returncode,
            "stdout": output[:50000],
            "stderr": err[:10000],
        }

        if result.returncode == 0:
            return json_result(True, data=data)
        else:
            data["stderr"] = err or "tool returned non-zero exit code"
            return json_result(False, error=err or f"{tool} exited {result.returncode}")

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "kali_exec",
    "description": "Run ANY Kali Linux or security tool with custom arguments. Use when no dedicated wrapper exists for the tool. Safely constrained to system binary paths with dangerous commands blocked.",
    "parameters": {
        "type": "object",
        "properties": {
            "tool": {
                "type": "string",
                "description": "Tool binary name (e.g. 'sherlock', 'aircrack-ng', 'proxychains4', 'tshark', 'volatility3')",
            },
            "args": {
                "type": "string",
                "description": "CLI arguments as a single string (e.g. '--help' or 'target.com -o output.txt')",
            },
            "stdin": {
                "type": "string",
                "description": "Optional stdin to pipe to the tool",
            },
            "timeout": {
                "type": "integer",
                "default": 300,
                "description": "Timeout in seconds (1-3600)",
            },
        },
        "required": ["tool", "args"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="kali_exec",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="⚡",
    )
