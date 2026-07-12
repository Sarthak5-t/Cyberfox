from __future__ import annotations

import json as _json
import logging
import re
from typing import Callable

from plugins.ares.state import engagement_store as store

logger = logging.getLogger(__name__)


class EventBus:
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
            except Exception as e:
                logger.error("EventBus subscriber %s failed: %s", event, e, exc_info=True)
        return results

    def events(self) -> list[str]:
        return list(self._subscribers.keys())


event_bus = EventBus()

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


def _on_http_detected(data: dict) -> None:
    try:
        eng = store.get_engagement()
        if not eng:
            return
        host = data.get("host", "")
        port = data.get("port", 80)
        url = f"{host}:{port}" if host else str(port)
        existing = store.get_tasks(eng.id, phase="scanning")
        if any("vulnerability scan" in t.title.lower() for t in existing):
            return
        store.create_task(eng.id, "scanning", len(existing) + 1,
                          f"Vulnerability scan on {url}", f"Nuclei for known CVEs on {url}", "nuclei_scan")
        store.create_task(eng.id, "scanning", len(existing) + 2,
                          f"Directory enumeration on {url}", f"Hidden paths on {url}", "gobuster_scan")
    except Exception as e:
        logger.error("HTTP subscriber failed: %s", e, exc_info=True)


def _on_smb_detected(data: dict) -> None:
    try:
        eng = store.get_engagement()
        if not eng:
            return
        host = data.get("host", "")
        existing = store.get_tasks(eng.id, phase="scanning")
        if any("smb" in t.title.lower() for t in existing):
            return
        store.create_task(eng.id, "scanning", len(existing) + 1,
                          f"SMB enumeration on {host}", f"enum4linux on {host}", "enum4linux_scan")
    except Exception as e:
        logger.error("SMB subscriber failed: %s", e, exc_info=True)


def _on_wordpress_detected(data: dict) -> None:
    try:
        eng = store.get_engagement()
        if not eng:
            return
        url = data.get("url", "")
        existing = store.get_tasks(eng.id, phase="scanning")
        if any("wpscan" in t.title.lower() for t in existing):
            return
        store.create_task(eng.id, "scanning", len(existing) + 1,
                          f"WPScan on {url}", f"WP plugin/theme vulns on {url}", "wpscan_scan")
    except Exception as e:
        logger.error("WordPress subscriber failed: %s", e, exc_info=True)


def _on_vuln_found(data: dict) -> None:
    try:
        eng = store.get_engagement()
        if not eng:
            return
        name = data.get("name", data.get("cve", "unknown"))
        existing = store.get_tasks(eng.id, phase="exploitation")
        if any("exploit research" in t.title.lower() for t in existing):
            return
        store.create_task(eng.id, "exploitation", 1,
                          f"Exploit research for {name}", f"Search PoCs for {name}", "searchsploit_tool")
    except Exception as e:
        logger.error("Vuln subscriber failed: %s", e, exc_info=True)

event_bus.subscribe(HTTP_DETECTED, _on_http_detected)
event_bus.subscribe(SMB_DETECTED, _on_smb_detected)
event_bus.subscribe(WORDPRESS_DETECTED, _on_wordpress_detected)
event_bus.subscribe(VULNERABILITY_FOUND, _on_vuln_found)


def _parse_envelope(result: str) -> dict | None:
    try:
        obj = _json.loads(result)
        if isinstance(obj, dict) and "success" in obj:
            return obj
    except (ValueError, TypeError):
        pass
    return None


def _extract_nmap(result: str, args: dict) -> list[dict]:
    entities = []
    target = args.get("target", "")
    env = _parse_envelope(result)
    if env and isinstance(env.get("data"), dict):
        for port_info in env["data"].get("results", []):
            port_num = port_info.get("port", 0)
            proto = port_info.get("protocol", "tcp")
            service = port_info.get("service", "")
            version = port_info.get("version", "")
            entities.append({
                "type": "port", "name": f"{port_num}/{proto}",
                "data": {"port": port_num, "protocol": proto, "service": service, "version": version, "host": target},
            })
            if version:
                entities.append({
                    "type": "service", "name": f"{service}/{version}" if service else version,
                    "data": {"port": port_num, "protocol": proto, "service": service, "version": version, "host": target},
                })
        for h in env["data"].get("hosts", []):
            entities.append({"type": "host", "name": h, "data": {"source": "nmap"}})
    if not entities:
        port_pattern = re.compile(r"(\d+)/(tcp|udp)\s+open\s+(\S+)\s*(.*)", re.MULTILINE)
        for m in port_pattern.finditer(result):
            port_num, proto, service, version = m.groups()
            version = version.strip()
            entities.append({
                "type": "port", "name": f"{port_num}/{proto}",
                "data": {"port": int(port_num), "protocol": proto, "service": service, "version": version, "host": target},
            })
            if version:
                entities.append({
                    "type": "service", "name": f"{service}/{version}" if service else version,
                    "data": {"port": int(port_num), "protocol": proto, "service": service, "version": version, "host": target},
                })
        ip_pattern = re.compile(r"Nmap scan report for (\S+)")
        for m in ip_pattern.finditer(result):
            entities.append({"type": "host", "name": m.group(1), "data": {"source": "nmap"}})
    return entities


def _extract_whatweb(result: str, args: dict) -> list[dict]:
    entities = []
    env = _parse_envelope(result)
    raw = result
    if env and isinstance(env.get("data"), dict):
        raw = env["data"].get("output", result)
    try:
        data = _json.loads(raw)
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
                    "type": "technology", "name": tech_name,
                    "data": {"version": version, "source": "whatweb", "url": item.get("target", "")},
                })
        if entities:
            return entities
    except (ValueError, TypeError):
        pass
    tech_pattern = re.compile(r"(\w[\w\s]*?)(?:\[([^\]]*)\])?(?:,|\]|$)")
    for m in tech_pattern.finditer(raw):
        name = m.group(1).strip()
        version = m.group(2)
        if name and name not in ("OK", "HTTP", "Title", "Country", "IP"):
            d = {"source": "whatweb"}
            if version:
                d["version"] = version
            entities.append({"type": "technology", "name": name, "data": d})
    return entities


def _extract_nuclei(result: str, args: dict) -> list[dict]:
    entities = []
    env = _parse_envelope(result)
    if env and isinstance(env.get("data"), dict):
        for f in env["data"].get("findings", []):
            severity = f.get("severity", "")
            cve = f.get("cve", f.get("template_id", ""))
            url = f.get("url", "")
            if cve.startswith("CVE-"):
                entities.append({"type": "vulnerability", "name": cve,
                                 "data": {"severity": severity, "url": url, "source": "nuclei"}})
            else:
                entities.append({"type": "finding", "name": cve,
                                 "data": {"severity": severity, "url": url, "source": "nuclei"}})
    if not entities:
        cve_pattern = re.compile(r"\[(\w+)\]\s+\[(CVE-[\d-]+)\]\s+(\S+)")
        for m in cve_pattern.finditer(result):
            severity, cve, url = m.groups()
            entities.append({"type": "vulnerability", "name": cve,
                             "data": {"severity": severity, "url": url, "source": "nuclei"}})
        finding_pattern = re.compile(r"\[(\w+)\]\s+\[([^\]]+)\]\s+(\S+)")
        for m in finding_pattern.finditer(result):
            severity, name, url = m.groups()
            if not name.startswith("CVE-"):
                entities.append({"type": "finding", "name": name,
                                 "data": {"severity": severity, "url": url, "source": "nuclei"}})
    return entities


def _extract_searchsploit(result: str, args: dict) -> list[dict]:
    entities = []
    env = _parse_envelope(result)
    raw = result
    if env and isinstance(env.get("data"), dict):
        for mod in env["data"].get("results", []):
            name = mod.get("name", mod.get("path", ""))
            if "CVE-" in name:
                for cve_match in re.finditer(r"(CVE-[\d-]+)", name):
                    entities.append({"type": "vulnerability", "name": cve_match.group(1),
                                     "data": {"source": "searchsploit", "query": args.get("query", "")}})
        if entities:
            return entities
    for m in re.finditer(r"(CVE-[\d-]+)", raw):
        entities.append({"type": "vulnerability", "name": m.group(1),
                         "data": {"source": "searchsploit", "query": args.get("query", "")}})
    return entities


def _extract_subfinder(result: str, args: dict) -> list[dict]:
    entities = []
    env = _parse_envelope(result)
    if env and isinstance(env.get("data"), dict):
        for sub in env["data"].get("subdomains", []):
            if isinstance(sub, str) and "." in sub:
                entities.append({"type": "subdomain", "name": sub,
                                 "data": {"source": "subfinder", "domain": args.get("domain", "")}})
        if entities:
            return entities
    for line in result.splitlines():
        line = line.strip()
        if line and "." in line and not line.startswith("[") and " " not in line:
            entities.append({"type": "subdomain", "name": line,
                             "data": {"source": "subfinder", "domain": args.get("domain", "")}})
    return entities


def _extract_hydra(result: str, args: dict) -> list[dict]:
    entities = []
    env = _parse_envelope(result)
    if env and isinstance(env.get("data"), dict):
        for r in env["data"].get("results", []):
            if isinstance(r, dict):
                login = r.get("login", "")
                password = r.get("password", "")
                host = r.get("host", args.get("target", ""))
                service = r.get("service", "")
                if login and password:
                    entities.append({"type": "credential", "name": f"{login}:{password}@{host}",
                                     "data": {"username": login, "password": password,
                                              "host": host, "service": service, "source": "hydra"}})
        if entities:
            return entities
    cred_pattern = re.compile(
        r"\[\d+\]\[([^\]]+)\]\s+host:\s+(\S+)\s+login:\s+(\S+)\s+password:\s+(\S+)")
    for m in cred_pattern.finditer(result):
        service, host, login, password = m.groups()
        entities.append({"type": "credential", "name": f"{login}:{password}@{host}",
                         "data": {"username": login, "password": password,
                                  "host": host, "service": service, "source": "hydra"}})
    return entities


def _extract_sqlmap(result: str, args: dict) -> list[dict]:
    entities = []
    env = _parse_envelope(result)
    raw = result
    if env and isinstance(env.get("data"), dict):
        raw = env["data"].get("raw_output", result)
    if "sqlmap identified the following injection point" in raw.lower() or "type:" in raw.lower():
        entities.append({"type": "finding", "name": "SQL Injection",
                         "data": {"severity": "critical", "url": args.get("url", ""),
                                  "technique": args.get("technique", ""), "source": "sqlmap"}})
    return entities


_EXTRACTORS: dict[str, Callable] = {
    "nmap_scan": _extract_nmap,
    "whatweb_scan": _extract_whatweb,
    "nuclei_scan": _extract_nuclei,
    "searchsploit_tool": _extract_searchsploit,
    "subdomain_enum": _extract_subfinder,
    "hydra_brute": _extract_hydra,
    "sqlmap_scan": _extract_sqlmap,
}


def _emit_events_for_entities(entities: list[dict]) -> None:
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
    if args is None:
        args = {}
    if result is None:
        return
    extractor = _EXTRACTORS.get(tool_name)
    if not extractor:
        return
    eng = store.get_engagement()
    if not eng:
        return
    try:
        extracted = extractor(result, args)
    except Exception:
        extracted = []
    if not extracted:
        store.log_event(eng.id, tool_name, args,
                        result_summary=result[:200] if result else None,
                        status="ok", turn_id=turn_id)
        return
    entity_ids = []
    for e in extracted:
        try:
            eid = store.save_entity(eng.id, e["type"], e["name"], e.get("data", {}))
            entity_ids.append(eid)
        except Exception:
            pass
    store.log_event(eng.id, tool_name, args,
                    result_summary=f"Extracted {len(extracted)} entities: {', '.join(e['type'] for e in extracted)}",
                    status="ok", entities_created=entity_ids, turn_id=turn_id)
    _emit_events_for_entities(extracted)
