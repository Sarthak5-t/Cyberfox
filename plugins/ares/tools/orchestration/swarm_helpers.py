from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class AgentSpec:
    role: str
    goal: str
    context: str = ""
    toolsets: list[str] = field(default_factory=list)
    max_iterations: int = 50
    model: str | None = None


@dataclass
class SwarmState:
    engagement_id: int
    target: str
    max_agents: int
    phase: str = "recon"
    agents_dispatched: int = 0
    agents_completed: int = 0
    findings_queue: list[dict] = field(default_factory=list)


def build_phase2_tasks(findings: list[dict], focus: list[str], target: str) -> list[dict]:
    tasks = []
    services = [f for f in findings if f.get("type") == "service"]
    http_targets = [
        f for f in services
        if "http" in f.get("data", {}).get("service", "").lower()
    ]

    if "web" in focus and http_targets:
        host = http_targets[0].get("data", {}).get("host", target)
        ports = [str(t.get("data", {}).get("port", "")) for t in http_targets[:5]]
        tasks.append({
            "goal": (
                f"Web vulnerability scan on {host} ports {','.join(ports)}. "
                f"Run nuclei_scan, nikto_scan, gobuster_scan. "
                f"Save all findings with findings_save."
            ),
            "context": json.dumps(http_targets[:10]),
        })
    if "network" in focus and services:
        host = services[0].get("data", {}).get("host", target)
        tasks.append({
            "goal": (
                f"Network-level scan on {host}. "
                f"Run enum4linux_scan, snmpwalk_tool if SNMP open, smbclient_tool. "
                f"Save all findings with findings_save."
            ),
            "context": json.dumps(services[:20]),
        })
    if "exploit" in focus and services:
        tasks.append({
            "goal": (
                f"Exploitation phase for {target}. "
                f"Search for exploits with searchsploit_tool for each discovered service. "
                f"Attempt exploitation of critical/high findings. "
                f"Save results with findings_save."
            ),
            "context": json.dumps(services[:10]),
        })
    return tasks


def build_stealth_tasks(target: str) -> list[dict]:
    return [{
        "goal": (
            f"Stealth reconnaissance on {target}. "
            f"Use nmap_scan with stealth mode (SYN scan, low timing). "
            f"Run dnsrecon_scan for DNS enumeration. "
            f"Use whatweb_scan for web fingerprinting. "
            f"Save all findings with findings_save."
        ),
        "context": f"Target: {target}. Stealth mode: minimize noise and detection.",
    }]


def build_aggressive_tasks(target: str, focus: list[str]) -> list[dict]:
    tasks = []
    if "recon" in focus:
        tasks.append({
            "goal": (
                f"Aggressive recon on {target}. "
                f"Run nmap_scan full, subdomain_enum, masscan_scan, dnsrecon_scan. "
                f"Save all hosts, ports, services with findings_save."
            ),
            "context": f"Target: {target}. Maximum coverage.",
        })
    if "web" in focus:
        tasks.append({
            "goal": (
                f"Aggressive web scan on {target}. "
                f"Run nuclei_scan critical+high, gobuster_scan, nikto_scan, "
                f"wafw00f_scan, ffuf_scan. Save all findings."
            ),
            "context": f"Target: {target}. Maximum web coverage.",
        })
    if "network" in focus:
        tasks.append({
            "goal": (
                f"Aggressive network scan on {target}. "
                f"Run enum4linux_scan, smbclient_tool, snmpwalk_tool. "
                f"Save all findings."
            ),
            "context": f"Target: {target}. Maximum network coverage.",
        })
    if "exploit" in focus:
        tasks.append({
            "goal": (
                f"Aggressive exploitation on {target}. "
                f"Search all services for exploits. Attempt critical and high vulns. "
                f"Save all results with findings_save."
            ),
            "context": f"Target: {target}. Maximum exploitation.",
        })
    return tasks
