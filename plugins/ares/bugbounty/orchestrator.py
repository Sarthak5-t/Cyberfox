from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from plugins.ares.bugbounty.rate_limiter import RateLimiter, RateLimitError, get_rate_limiter
from plugins.ares.bugbounty.scope_enforcer import ScopeEnforcer, ScopeError, get_scope_enforcer
from plugins.ares.bugbounty.opsec import OPSEC, get_opsec
from plugins.ares.bugbounty.waf_advisor import WAFAdvisor, get_waf_advisor
from plugins.ares.bugbounty.proxy_manager import ProxyManager, get_proxy_manager
from plugins.ares.bugbounty.auth_handler import AuthHandler, get_auth_handler
from plugins.ares.bugbounty.vuln_validator import VulnValidator, Finding, get_vuln_validator

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    PASSIVE_RECON = "passive_recon"
    LIVE_PROBE = "live_probe"
    PORT_SCAN = "port_scan"
    WAF_DETECT = "waf_detect"
    VULN_SCAN = "vuln_scan"
    CRAWL = "crawl"
    INJECT = "inject"
    VALIDATE = "validate"
    REPORT = "report"


@dataclass
class StageResult:
    stage: PipelineStage
    success: bool = True
    findings: list[Finding] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    duration_sec: float = 0.0
    error: str = ""


@dataclass
class PipelineState:
    target: str
    stages_completed: list[str] = field(default_factory=list)
    stage_results: dict[str, dict] = field(default_factory=dict)
    findings: list[dict] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0


class BugBountyOrchestrator:
    """Full kill-chain pipeline orchestrator with all safety layers."""

    def __init__(self):
        self.rate_limiter: RateLimiter = get_rate_limiter()
        self.scope: ScopeEnforcer = get_scope_enforcer()
        self.opsec: OPSEC = get_opsec()
        self.waf: WAFAdvisor = get_waf_advisor()
        self.proxy: ProxyManager = get_proxy_manager()
        self.auth: AuthHandler = get_auth_handler()
        self.validator: VulnValidator = get_vuln_validator()

        self._state: Optional[PipelineState] = None
        self._findings: list[Finding] = []
        self._stage_handlers: dict[PipelineStage, Callable] = {
            PipelineStage.PASSIVE_RECON: self._stage_passive_recon,
            PipelineStage.LIVE_PROBE: self._stage_live_probe,
            PipelineStage.PORT_SCAN: self._stage_port_scan,
            PipelineStage.WAF_DETECT: self._stage_waf_detect,
            PipelineStage.VULN_SCAN: self._stage_vuln_scan,
            PipelineStage.CRAWL: self._stage_crawl,
            PipelineStage.INJECT: self._stage_inject,
            PipelineStage.VALIDATE: self._stage_validate,
            PipelineStage.REPORT: self._stage_report,
        }
        self._on_progress: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable) -> None:
        self._on_progress = callback

    def _notify(self, stage: str, message: str, **kwargs) -> None:
        if self._on_progress:
            self._on_progress(stage=stage, message=message, **kwargs)
        logger.info(f"[{stage}] {message}")

    def run(self, target: str, stages: Optional[list[PipelineStage]] = None,
            scope_file: Optional[str] = None,
            authenticated: bool = False,
            max_rps: float = 10.0) -> dict[str, Any]:
        """Run the full bug bounty pipeline."""
        self._state = PipelineState(target=target, start_time=time.time())
        self._findings = []

        # Load scope
        if scope_file:
            self.scope.load_from_file(scope_file)

        # Scope check
        try:
            self.scope.enforce(target)
        except ScopeError as e:
            return {"success": False, "error": str(e), "target": target}

        # Configure rate limiter
        self.rate_limiter.configure_for_program(max_rps)

        pipeline = stages or list(PipelineStage)

        self._notify("pipeline", f"Starting pipeline for {target} "
                      f"({len(pipeline)} stages)")

        for stage in pipeline:
            if stage.value in self._state.stages_completed:
                continue

            self._notify(stage.value, f"Starting {stage.value}")
            stage_start = time.time()

            try:
                handler = self._stage_handlers[stage]
                result = handler(target)
                result.duration_sec = time.time() - stage_start
                self._state.stage_results[stage.value] = {
                    "success": result.success,
                    "findings_count": len(result.findings),
                    "duration": result.duration_sec,
                    "data": result.data,
                }
                self._state.stages_completed.append(stage.value)

                if result.findings:
                    self._findings.extend(result.findings)
                    self._notify(stage.value, f"Found {len(result.findings)} issues")

            except RateLimitError as e:
                self._notify(stage.value, f"BANNED: {e}", error=True)
                break
            except Exception as e:
                self._notify(stage.value, f"Error: {e}", error=True)
                self._state.stage_results[stage.value] = {
                    "success": False, "error": str(e),
                    "duration": time.time() - stage_start
                }

        self._state.end_time = time.time()
        self._state.findings = [f.__dict__ for f in self._findings]

        total_duration = self._state.end_time - self._state.start_time
        self._notify("pipeline", f"Pipeline complete: {len(self._findings)} findings "
                      f"in {total_duration:.1f}s")

        return {
            "success": True,
            "target": target,
            "findings_count": len(self._findings),
            "findings": [f.__dict__ for f in self._findings],
            "stages_completed": self._state.stages_completed,
            "duration_sec": total_duration,
            "stats": {
                "rate_limiter": self.rate_limiter.get_stats(),
                "proxy": self.proxy.get_stats(),
                "validator": self.validator.get_stats(),
            },
        }

    def _safe_execute(self, target: str, stage: PipelineStage,
                      command: list[str], label: str) -> dict[str, Any]:
        """Execute a tool command with safety layers."""
        # Scope check
        self.scope.enforce(target)
        # Rate limit
        self.rate_limiter.wait_if_needed(target)
        # Jitter
        self.opsec.jitter_delay()
        # Proxy injection
        proxy_args = self.proxy.get_proxy_for_tool()
        # Opsec headers
        headers = self.opsec.randomize_tool_headers()

        full_cmd = command + proxy_args
        self._notify(stage.value, f"Running: {label}")

        start = time.time()
        try:
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=120)
            latency = time.time() - start
            self.rate_limiter.report_response(target, 200, latency)
            return {"success": True, "stdout": result.stdout,
                    "stderr": result.stderr, "latency": latency}
        except subprocess.TimeoutExpired:
            self._notify(stage.value, f"Timeout: {label}")
            return {"success": False, "error": "timeout"}
        except Exception as e:
            self._notify(stage.value, f"Error: {e}")
            return {"success": False, "error": str(e)}

    def _stage_passive_recon(self, target: str) -> StageResult:
        """Passive reconnaissance: subdomains, DNS, WHOIS."""
        result = StageResult(stage=PipelineStage.PASSIVE_RECON)
        findings = []

        # Subdomain enumeration
        subdomain_result = self._safe_execute(
            target, PipelineStage.PASSIVE_RECON,
            ["subfinder", "-d", target, "-json"],
            "subfinder subdomain enum"
        )
        if subdomain_result.get("success"):
            subs = []
            for line in subdomain_result["stdout"].strip().split("\n"):
                if line:
                    try:
                        data = json.loads(line)
                        subs.append(data.get("host", data.get("input", "")))
                    except json.JSONDecodeError:
                        subs.append(line.strip())
            result.data["subdomains"] = subs
            result.data["subdomains_count"] = len(subs)

        # DNS recon
        dns_result = self._safe_execute(
            target, PipelineStage.PASSIVE_RECON,
            ["dig", "+short", "ANY", target],
            "DNS records"
        )
        if dns_result.get("success"):
            result.data["dns"] = dns_result["stdout"].strip()

        # HTTP probe (basic liveness)
        url = target if target.startswith("http") else f"http://{target}"
        probe_result = self._safe_execute(
            target, PipelineStage.PASSIVE_RECON,
            ["curl", "-sS", "-o", "/dev/null", "-w",
             "%{http_code}|%{content_type}|%{size_download}|%{time_total}",
             url, "--max-time", "10"],
            "HTTP probe"
        )
        if probe_result.get("success"):
            parts = probe_result["stdout"].strip().split("|")
            if len(parts) >= 4:
                result.data["http_probe"] = {
                    "status_code": int(parts[0]) if parts[0].isdigit() else 0,
                    "content_type": parts[1],
                    "size": int(parts[2]) if parts[2].isdigit() else 0,
                    "time": float(parts[3]) if parts[3].replace(".", "").isdigit() else 0,
                }
                status = int(parts[0]) if parts[0].isdigit() else 0
                if status:
                    result.data["live"] = True
                    result.data["status_code"] = status

        return result

    def _stage_live_probe(self, target: str) -> StageResult:
        """Probe live hosts for common services."""
        result = StageResult(stage=PipelineStage.LIVE_PROBE)

        # Nmap quick service scan
        probe = self._safe_execute(
            target, PipelineStage.LIVE_PROBE,
            ["nmap", "-sV", "-sC", "-T4", "--top-ports", "100", "-oX", "-", target],
            "nmap quick service scan"
        )
        if probe.get("success"):
            result.data["nmap"] = probe["stdout"]

            # Parse open ports
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(probe["stdout"])
                for port in root.findall(".//port"):
                    portid = port.get("portid", "")
                    protocol = port.get("protocol", "")
                    state_el = port.find("state")
                    service_el = port.find("service")
                    state = state_el.get("state", "") if state_el is not None else ""
                    service = service_el.get("name", "") if service_el is not None else ""
                    version = service_el.get("product", "") if service_el is not None else ""

                    if state == "open":
                        result.data.setdefault("open_ports", []).append({
                            "port": portid, "protocol": protocol,
                            "service": service, "version": version,
                        })
            except ET.ParseError:
                pass

        return result

    def _stage_port_scan(self, target: str) -> StageResult:
        """Detailed port scan on discovered open ports."""
        result = StageResult(stage=PipelineStage.PORT_SCAN)

        # Full port scan with version detection
        scan = self._safe_execute(
            target, PipelineStage.PORT_SCAN,
            ["nmap", "-sV", "-sC", "-T4", "-p-", "--open", "-oX", "-", target],
            "nmap full port scan"
        )
        if scan.get("success"):
            result.data["full_scan"] = scan["stdout"]
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(scan["stdout"])
                for port in root.findall(".//port"):
                    portid = port.get("portid", "")
                    protocol = port.get("protocol", "")
                    state_el = port.find("state")
                    service_el = port.find("service")
                    state = state_el.get("state", "") if state_el is not None else ""
                    service = service_el.get("name", "") if service_el is not None else ""

                    if state == "open":
                        result.data.setdefault("ports", []).append({
                            "port": portid, "protocol": protocol, "service": service,
                        })
            except ET.ParseError:
                pass

        return result

    def _stage_waf_detect(self, target: str) -> StageResult:
        """Detect WAF and configure scan strategy."""
        result = StageResult(stage=PipelineStage.WAF_DETECT)

        url = target if target.startswith("http") else f"http://{target}"
        waf_result = self.waf.detect(url)
        strategy = self.waf.get_strategy(waf_result)

        result.data["waf"] = waf_result.__dict__
        result.data["strategy"] = {
            "rate_limit": strategy.rate_limit,
            "burst": strategy.burst,
            "use_proxy": strategy.use_proxy,
            "use_tamper": strategy.use_tamper,
            "concurrent_threads": strategy.concurrent_threads,
            "notes": strategy.notes,
        }

        # Apply strategy
        self.rate_limiter.rate = strategy.rate_limit
        if strategy.use_proxy and self.proxy.get_healthy_count() > 0:
            result.data["proxy_active"] = True

        return result

    def _stage_vuln_scan(self, target: str) -> StageResult:
        """Vulnerability scanning with nuclei."""
        result = StageResult(stage=PipelineStage.VULN_SCAN)
        url = target if target.startswith("http") else f"http://{target}"

        strategy = self.waf.get_strategy() or self.waf.get_strategy()

        nuclei_cmd = ["nuclei", "-u", url, "-jsonl", "-silent",
                       "-severity", "critical,high,medium"]

        if strategy.use_tamper:
            nuclei_cmd.extend(["-rate-limit", str(int(strategy.rate_limit))])
        else:
            nuclei_cmd.extend(["-rate-limit", "50"])

        scan = self._safe_execute(
            target, PipelineStage.VULN_SCAN,
            nuclei_cmd, "nuclei vulnerability scan"
        )

        if scan.get("success"):
            for line in scan["stdout"].strip().split("\n"):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    finding = Finding(
                        title=data.get("info", {}).get("name", "Unknown"),
                        severity=data.get("info", {}).get("severity", "info"),
                        target=target,
                        url=url,
                        vulnerability_type=data.get("info", {}).get("classification", {}).get("cwe", [""])[0] if data.get("info", {}).get("classification", {}).get("cwe") else "",
                        evidence=data.get("info", {}).get("description", ""),
                        payload=data.get("matched-at", data.get("matched", "")),
                        tool="nuclei",
                        cve=data.get("info", {}).get("classification", {}).get("cve-id", [""])[0] if data.get("info", {}).get("classification", {}).get("cve-id") else "",
                    )
                    result.findings.append(finding)
                except json.JSONDecodeError:
                    pass

        return result

    def _stage_crawl(self, target: str) -> StageResult:
        """Crawl the target for hidden paths, forms, parameters."""
        result = StageResult(stage=PipelineStage.CRAWL)
        url = target if target.startswith("http") else f"http://{target}"

        # Directory brute-force with feroxbuster
        scan = self._safe_execute(
            target, PipelineStage.CRAWL,
            ["feroxbuster", "-u", url, "--json", "-q",
             "-w", "/usr/share/wordlists/dirb/common.txt", "-t", "20"],
            "feroxbuster directory scan"
        )

        if scan.get("success"):
            paths = []
            for line in scan["stdout"].strip().split("\n"):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "url" in data:
                        paths.append(data["url"])
                except json.JSONDecodeError:
                    pass
            result.data["paths"] = paths
            result.data["paths_count"] = len(paths)

        return result

    def _stage_inject(self, target: str) -> StageResult:
        """Injection testing: SQLi, XSS, CMDi."""
        result = StageResult(stage=PipelineStage.INJECT)
        url = target if target.startswith("http") else f"http://{target}"

        # SQLi testing with sqlmap
        sqli = self._safe_execute(
            target, PipelineStage.INJECT,
            ["sqlmap", "-u", url, "--batch", "--level=2", "--risk=1",
             "--output-dir=/tmp/sqlmap_out", "--forms", "--crawl=2"],
            "sqlmap injection test"
        )
        if sqli.get("success") and "is vulnerable" in sqli.get("stdout", "").lower():
            result.findings.append(Finding(
                title="SQL Injection",
                severity="critical",
                target=target, url=url,
                vulnerability_type="sqli",
                evidence=sqli["stdout"][:2000],
                tool="sqlmap"
            ))

        # XSS detection via nuclei (already covered in vuln_scan, but
        # add custom XSS payloads)
        xss_payloads = [
            '<script>alert(1)</script>',
            '"><img src=x onerror=alert(1)>',
            "'-alert(1)-'",
        ]
        for payload in xss_payloads:
            import urllib.parse
            test_url = f"{url}?q={urllib.parse.quote(payload)}"
            probe = self._safe_execute(
                target, PipelineStage.INJECT,
                ["curl", "-sS", test_url, "--max-time", "5"],
                f"XSS probe: {payload[:30]}"
            )
            if probe.get("success") and payload in probe.get("stdout", ""):
                result.findings.append(Finding(
                    title="Reflected XSS",
                    severity="high",
                    target=target, url=test_url,
                    vulnerability_type="reflected_xss",
                    payload=payload,
                    evidence=f"Payload reflected in response",
                    tool="curl"
                ))
                break

        # Command injection
        cmdi_payloads = ["; id", "| id", "$(id)", "`id`"]
        for payload in cmdi_payloads:
            import urllib.parse
            test_url = f"{url}?cmd={urllib.parse.quote(payload.strip())}"
            probe = self._safe_execute(
                target, PipelineStage.INJECT,
                ["curl", "-sS", test_url, "--max-time", "5"],
                f"CMDi probe: {payload.strip()}"
            )
            if probe.get("success") and "uid=" in probe.get("stdout", ""):
                result.findings.append(Finding(
                    title="Command Injection",
                    severity="critical",
                    target=target, url=test_url,
                    vulnerability_type="command_injection",
                    payload=payload.strip(),
                    evidence=probe["stdout"][:1000],
                    tool="curl"
                ))
                break

        return result

    def _stage_validate(self, target: str) -> StageResult:
        """Validate all findings to filter false positives."""
        result = StageResult(stage=PipelineStage.VALIDATE)
        validated = self.validator.validate_batch(self._findings)

        for vr in validated:
            if vr.is_false_positive:
                logger.info(f"FP removed: {vr.finding.title}")
            elif vr.confirmed:
                result.findings.append(vr.finding)

        result.data["validation_stats"] = self.validator.get_stats()
        return result

    def _stage_report(self, target: str) -> StageResult:
        """Generate report."""
        result = StageResult(stage=PipelineStage.REPORT)

        severity_counts = {}
        for f in self._findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

        report_lines = [
            f"# Bug Bounty Report: {target}",
            f"",
            f"## Summary",
            f"- Total findings: {len(self._findings)}",
            f"- Critical: {severity_counts.get('critical', 0)}",
            f"- High: {severity_counts.get('high', 0)}",
            f"- Medium: {severity_counts.get('medium', 0)}",
            f"- Low: {severity_counts.get('low', 0)}",
            f"- Info: {severity_counts.get('info', 0)}",
            f"",
            f"## Findings",
            f"",
        ]

        for i, f in enumerate(self._findings, 1):
            report_lines.extend([
                f"### {i}. {f.title}",
                f"- **Severity:** {f.severity}",
                f"- **Target:** {f.target}",
                f"- **URL:** {f.url}",
                f"- **Type:** {f.vulnerability_type}",
                f"- **Tool:** {f.tool}",
                f"- **Evidence:** {f.evidence[:200]}",
                f"",
            ])

        result.data["report"] = "\n".join(report_lines)
        return result

    def get_findings(self) -> list[Finding]:
        return list(self._findings)

    def get_state(self) -> Optional[dict]:
        if not self._state:
            return None
        return {
            "target": self._state.target,
            "stages_completed": self._state.stages_completed,
            "findings_count": len(self._state.findings),
            "duration": self._state.end_time - self._state.start_time if self._state.end_time else 0,
        }


_orchestrator: Optional[BugBountyOrchestrator] = None


def get_orchestrator() -> BugBountyOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = BugBountyOrchestrator()
    return _orchestrator
