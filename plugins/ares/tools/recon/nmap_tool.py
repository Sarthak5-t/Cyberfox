from __future__ import annotations

import json
import logging
import shlex

from plugins.ares.tools.base import check_binary, run_command, json_result

logger = logging.getLogger(__name__)

TOOLSET = "ares_recon"

SCAN_TYPES = {
    "quick": "-T4 -F",
    "full": "-T4 -p- -A",
    "vuln": "-T4 --script vuln",
    "udp": "-T4 -sU --top-ports 100",
    "stealth": "-T2 -sS -F",
}



def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    scan_type = args.get("scan_type", "quick")
    ports = args.get("ports", "")
    if not check_binary("nmap"):
        return json_result(False, error="nmap not found on PATH")
    flags = SCAN_TYPES.get(scan_type, "-T4 -F")
    if ports:
        flags = f"{flags} -p {shlex.quote(ports)}"
    try:
        result = run_command(f"nmap {flags} -oX - {shlex.quote(target)}", timeout=600)
        if result.returncode != 0:
            return json_result(False, error=result.stderr.strip() or f"nmap exited {result.returncode}")
        parsed = _parse_nmap_xml(result.stdout)
        return json_result(True, data={
            "scan_type": scan_type,
            "target": target,
            "results": parsed,
        })
    except Exception as e:
        return json_result(False, error=str(e))


def _parse_nmap_xml(xml: str) -> list:
    import xml.etree.ElementTree as ET
    hosts = []
    try:
        root = ET.fromstring(xml)
        for host in root.findall(".//host"):
            addr = host.find(".//address")
            ip = addr.get("addr", "") if addr is not None else ""
            ports_info = []
            for port in host.findall(".//port"):
                port_id = port.get("portid", "")
                protocol = port.get("protocol", "")
                state = port.find("state")
                svc = port.find("service")
                ports_info.append({
                    "port": port_id,
                    "protocol": protocol,
                    "state": state.get("state", "") if state is not None else "",
                    "service": svc.get("name", "") if svc is not None else "",
                    "product": svc.get("product", "") if svc is not None else "",
                    "version": svc.get("version", "") if svc is not None else "",
                })
            os_elem = host.find(".//osmatch")
            os_name = os_elem.get("name", "") if os_elem is not None else ""
            hosts.append({"ip": ip, "ports": ports_info, "os": os_name})
    except ET.ParseError:
        return []
    return hosts


SCHEMA = {
    "name": "nmap_scan",
    "description": "Run nmap port scan against a target. Returns structured JSON with open ports, services, and OS detection.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target IP address, hostname, or CIDR range (e.g. '10.10.10.10' or '192.168.1.0/24')",
            },
            "scan_type": {
                "type": "string",
                "enum": list(SCAN_TYPES.keys()),
                "default": "quick",
                "description": "Scan intensity: quick (-T4 -F), full (-T4 -p- -A), vuln (--script vuln), udp (-sU), stealth (-T2 -sS)",
            },
            "ports": {
                "type": "string",
                "default": "",
                "description": "Port specification override (e.g. '80,443' or '1-1000'). Adds to the scan_type's default flags.",
            },
        },
        "required": ["target"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="nmap_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🔍",
    )
