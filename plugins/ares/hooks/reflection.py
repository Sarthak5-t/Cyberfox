from __future__ import annotations

import re
from typing import Callable

from plugins.ares.state import engagement_store as store


class EventBus:
    """Simple in-process publish/subscribe event bus."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, callback: Callable) -> None:
        self._subscribers.setdefault(event, []).append(callback)

    def unsubscribe(self, event: str, callback: Callable) -> None:
        if event in self._subscribers:
            self._subscribers[event] = [c for c in self._subscribers[event] if c != callback]

    def emit(self, event: str, data: dict | None = None) -> list:
        results = []
        for callback in self._subscribers.get(event, []):
            try:
                result = callback(data or {})
                results.append(result)
            except Exception:
                pass
        return results

    def events(self) -> list[str]:
        return list(self._subscribers.keys())


event_bus = EventBus()


# ── Event types ───────────────────────────────────────────────────────────

PORT_FOUND = "port_found"
HTTP_DETECTED = "http_detected"
SMB_DETECTED = "smb_detected"
VULNERABILITY_FOUND = "vulnerability_found"
CREDENTIAL_FOUND = "credential_found"
SERVICE_FINGERPRINTED = "service_fingerprinted"
WAF_DETECTED = "waf_detected"
WORDPRESS_DETECTED = "wordpress_detected"
TECHNOLOGY_DETECTED = "technology_detected"
SUBDOMAIN_FOUND = "subdomain_found"


# ── Entity extractors (per tool) ──────────────────────────────────────────

def _extract_nmap(result: str, args: dict) -> list[dict]:
    """Extract hosts, ports, services from nmap output."""
    entities = []
    target = args.get("target", "")

    # Match open ports: "22/tcp open ssh OpenSSH 8.9"
    port_pattern = re.compile(
        r"(\d+)/(tcp|udp)\s+open\s+(\S+)\s*(.*)", re.MULTILINE
    )
    for m in port_pattern.finditer(result):
        port_num, proto, service, version = m.groups()
        version = version.strip()
        entities.append({
            "type": "port",
            "name": f"{port_num}/{proto}",
            "data": {
                "port": int(port_num),
                "protocol": proto,
                "service": service,
                "version": version,
                "host": target,
            },
        })
        if version:
            entities.append({
                "type": "service",
                "name": f"{service}/{version}" if service else version,
                "data": {"port": int(port_num), "protocol": proto, "service": service, "version": version, "host": target},
            })

    # Match IP addresses
    ip_pattern = re.compile(r"Nmap scan report for (\S+)")
    for m in ip_pattern.finditer(result):
        host = m.group(1)
        entities.append({"type": "host", "name": host, "data": {"source": "nmap"}})

    return entities


def _extract_whatweb(result: str, args: dict) -> list[dict]:
    """Extract technologies from whatweb output (JSON or plain text)."""
    entities = []
    # Try JSON first (whatweb -j)
    try:
        import json as _json
        data = _json.loads(result)
        # WhatWeb outputs an array; handle both array and single object
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        for item in items:
                plugins = item.get("plugins", {})
                for tech_name, tech_data in plugins.items():
                    if tech_name in ("HTTPServer", "Title", "Country", "IP", "UncommonHeaders"):
                        continue
                    version = None
                    if isinstance(tech_data, dict):
                        v = tech_data.get("version")
                        if v and isinstance(v, list) and v:
                            version = v[0]
                    entities.append({
                        "type": "technology",
                        "name": tech_name,
                        "data": {"version": version, "source": "whatweb", "url": item.get("target", "")},
                    })
        if entities:
            return entities
    except (ValueError, TypeError):
        pass
    # Fallback: plain text regex
    tech_pattern = re.compile(r"(\w[\w\s]*?)(?:\[([^\]]*)\])?(?:,|\]|$)")
    for m in tech_pattern.finditer(result):
        name = m.group(1).strip()
        version = m.group(2)
        if name and name not in ("OK", "HTTP", "Title", "Country", "IP"):
            data = {"source": "whatweb"}
            if version:
                data["version"] = version
            entities.append({"type": "technology", "name": name, "data": data})
    return entities


def _extract_nuclei(result: str, args: dict) -> list[dict]:
    """Extract vulnerabilities from nuclei output."""
    entities = []
    # Nuclei: "[critical] [CVE-2024-xxxx] http://target/path"
    cve_pattern = re.compile(r"\[(\w+)\]\s+\[(CVE-[\d-]+)\]\s+(\S+)")
    for m in cve_pattern.finditer(result):
        severity, cve, url = m.groups()
        entities.append({
            "type": "vulnerability",
            "name": cve,
            "data": {"severity": severity, "url": url, "source": "nuclei"},
        })
    # Also match non-CVE findings
    finding_pattern = re.compile(r"\[(\w+)\]\s+\[([^\]]+)\]\s+(\S+)")
    for m in finding_pattern.finditer(result):
        severity, finding_name, url = m.groups()
        if not finding_name.startswith("CVE-"):
            entities.append({
                "type": "finding",
                "name": finding_name,
                "data": {"severity": severity, "url": url, "source": "nuclei"},
            })
    return entities


def _extract_searchsploit(result: str, args: dict) -> list[dict]:
    """Extract CVEs from searchsploit output."""
    entities = []
    # searchsploit: "Apache httpd 2.4.57 | exploits/linux/.../CVE-2024-xxxx.py"
    cve_pattern = re.compile(r"(CVE-[\d-]+)")
    for m in cve_pattern.finditer(result):
        entities.append({
            "type": "vulnerability",
            "name": m.group(1),
            "data": {"source": "searchsploit", "query": args.get("query", "")},
        })
    return entities


def _extract_subfinder(result: str, args: dict) -> list[dict]:
    """Extract subdomains from subfinder output."""
    entities = []
    for line in result.splitlines():
        line = line.strip()
        if line and "." in line and not line.startswith("[") and not " " in line:
            entities.append({
                "type": "subdomain",
                "name": line,
                "data": {"source": "subfinder", "domain": args.get("domain", "")},
            })
    return entities


def _extract_hydra(result: str, args: dict) -> list[dict]:
    """Extract credentials from hydra output."""
    entities = []
    # Hydra: "[80][http-post-form] host: 10.10.10.10   login: admin   password: admin123"
    cred_pattern = re.compile(
        r"\[\d+\]\[([^\]]+)\]\s+host:\s+(\S+)\s+login:\s+(\S+)\s+password:\s+(\S+)"
    )
    for m in cred_pattern.finditer(result):
        service, host, login, password = m.groups()
        entities.append({
            "type": "credential",
            "name": f"{login}:{password}@{host}",
            "data": {
                "username": login, "password": password,
                "host": host, "service": service, "source": "hydra",
            },
        })
    return entities


def _extract_sqlmap(result: str, args: dict) -> list[dict]:
    """Extract SQL injection findings from sqlmap output."""
    entities = []
    if "sqlmap identified the following injection point" in result.lower() or "type:" in result.lower():
        entities.append({
            "type": "finding",
            "name": "SQL Injection",
            "data": {
                "severity": "critical",
                "url": args.get("url", ""),
                "technique": args.get("technique", ""),
                "source": "sqlmap",
            },
        })
    return entities


def _extract_whatweb_tech(result: str, args: dict) -> list[dict]:
    """Extract technologies from whatweb JSON output. Kept for backward compat."""
    return _extract_whatweb(result, args)


# ── Tool → extractor mapping ──────────────────────────────────────────────

_EXTRACTORS: dict[str, Callable] = {
    "nmap_scan": _extract_nmap,
    "whatweb_scan": _extract_whatweb,
    "nuclei_scan": _extract_nuclei,
    "searchsploit_tool": _extract_searchsploit,
    "subdomain_enum": _extract_subfinder,
    "hydra_brute": _extract_hydra,
    "sqlmap_scan": _extract_sqlmap,
}


# ── Event mappings ────────────────────────────────────────────────────────

def _emit_events_for_entities(entities: list[dict]) -> None:
    """Emit bus events based on extracted entities."""
    for e in entities:
        etype = e["type"]
        data = e.get("data", {})
        if etype == "port":
            event_bus.emit(PORT_FOUND, data)
            port = data.get("port", 0)
            if port in (80, 443, 8080, 8443):
                event_bus.emit(HTTP_DETECTED, data)
            elif port in (139, 445):
                event_bus.emit(SMB_DETECTED, data)
        elif etype == "vulnerability":
            event_bus.emit(VULNERABILITY_FOUND, {**e, **data})
        elif etype == "credential":
            event_bus.emit(CREDENTIAL_FOUND, {**e, **data})
        elif etype == "service":
            event_bus.emit(SERVICE_FINGERPRINTED, data)
        elif etype == "technology":
            event_bus.emit(TECHNOLOGY_DETECTED, data)
            name_lower = e["name"].lower()
            if "waf" in name_lower or "cloudflare" in name_lower:
                event_bus.emit(WAF_DETECTED, data)
            if "wordpress" in name_lower:
                event_bus.emit(WORDPRESS_DETECTED, data)
        elif etype == "subdomain":
            event_bus.emit(SUBDOMAIN_FOUND, data)


# ── Hook entry point ──────────────────────────────────────────────────────

def post_tool_call(
    tool_name: str,
    args: dict = None,
    result: str = None,
    task_id: str = None,
    session_id: str = None,
    tool_call_id: str = None,
    turn_id: str = None,
    **kwargs,
):
    """Post-tool reflection hook.

    1. Check if we have an active engagement
    2. Extract entities from tool output
    3. Save entities to the knowledge graph
    4. Log the tool event
    5. Emit events on the bus
    """
    if args is None:
        args = {}
    if result is None:
        return

    # Only process ares tools
    extractor = _EXTRACTORS.get(tool_name)
    if not extractor:
        return

    eng = store.get_engagement()
    if not eng:
        return

    # Extract entities from output
    try:
        extracted = extractor(result, args)
    except Exception:
        extracted = []

    if not extracted:
        # Still log the event even if no entities extracted
        store.log_event(
            engagement_id=eng.id,
            tool_name=tool_name,
            args=args,
            result_summary=result[:200] if result else None,
            status="ok",
            turn_id=turn_id,
        )
        return

    # Save entities and collect IDs
    entity_ids = []
    for e in extracted:
        try:
            eid = store.save_entity(
                engagement_id=eng.id,
                entity_type=e["type"],
                name=e["name"],
                data=e.get("data", {}),
            )
            entity_ids.append(eid)
        except Exception:
            pass

    # Log the tool event
    store.log_event(
        engagement_id=eng.id,
        tool_name=tool_name,
        args=args,
        result_summary=f"Extracted {len(extracted)} entities: {', '.join(e['type'] for e in extracted)}",
        status="ok",
        entities_created=entity_ids,
        turn_id=turn_id,
    )

    # Emit events on the bus
    _emit_events_for_entities(extracted)
