from __future__ import annotations

import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_exploit"


def _handle(args: dict, **kw) -> str:
    image_file = args.get("image_file", "")
    plugin = args.get("plugin", "windows.info")
    output_dir = args.get("output_dir", "")
    timeout_val = args.get("timeout", 300)

    if not check_binary("volatility3") and not check_binary("vol"):
        return json_result(False, error="volatility3 or vol not found on PATH")

    if not image_file:
        return json_result(False, error="'image_file' parameter is required")

    try:
        if check_binary("volatility3"):
            vol_cmd = "volatility3"
            argv = [vol_cmd, "-f", image_file, plugin]
        else:
            vol_cmd = "vol"
            argv = [vol_cmd, "-f", image_file, plugin]

        if output_dir:
            argv.extend(["--output-dir", output_dir])

        result = run_command_argv(argv, timeout=timeout_val)

        output_text = result.stdout.strip()
        stderr_out = result.stderr.strip()

        lines = output_text.split("\n") if output_text else []

        return json_result(True, data={
            "image_file": image_file,
            "plugin": plugin,
            "output_lines": len(lines),
            "output": output_text[:30000],
            "stderr": stderr_out[:3000],
        })

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "volatility_memdump",
    "description": "Memory forensics analysis using Volatility 3. Analyze memory dumps for processes, network connections, registry hives, dumped passwords, and kernel objects.",
    "parameters": {
        "type": "object",
        "properties": {
            "image_file": {
                "type": "string",
                "description": "Path to memory dump image file",
            },
            "plugin": {
                "type": "string",
                "default": "windows.info",
                "description": "Volatility plugin: windows.info, windows.pslist, windows.netscan, windows.filescan, windows.cmdline, windows.registry, windows.dumpfiles, linux.bash, etc.",
            },
            "output_dir": {
                "type": "string",
                "default": "",
                "description": "Directory to save plugin output files (if plugin supports it)",
            },
            "timeout": {
                "type": "integer",
                "default": 300,
                "description": "Timeout in seconds",
            },
        },
        "required": ["image_file"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="volatility_memdump",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🧠",
    )
