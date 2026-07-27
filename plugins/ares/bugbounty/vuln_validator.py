from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Finding:
    title: str
    severity: str  # critical, high, medium, low, info
    target: str
    url: str = ""
    vulnerability_type: str = ""
    evidence: str = ""
    request: str = ""
    response: str = ""
    payload: str = ""
    tool: str = ""
    cve: str = ""
    cvss: float = 0.0
    confidence: float = 0.0


@dataclass
class ValidationResult:
    finding: Finding
    confirmed: bool = False
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    is_false_positive: bool = False
    fp_reason: str = ""
    retested: bool = False
    validated_at: float = field(default_factory=time.time)


# False positive indicators
FP_PATTERNS = {
    "reflected_xss": [
        "User-Agent:", "Referer:", "X-Forwarded",
        "input was reflected in error message",
        "the string you submitted was not",
    ],
    "sql_injection": [
        "You have an error in your SQL syntax",
        "MySQL server version",
        "ORA-01756",
        "Microsoft OLE DB Provider",
        "SQLite3::",
        "valid MySQL result",
        "pg_query", "PSQLException",
    ],
    "cmd_injection": [
        "uid=", "root:",  # Linux
        "Directory of C:\\", "Volume Serial",  # Windows
    ],
    "open_redirect": [
        "document.referrer",
        "window.location.href",
        "history.back",
    ],
    "lfi": [
        "root:x:0:0",  # /etc/passwd
        "[boot loader]",
        "Microsoft Windows [Version",
    ],
}

SEVERITY_MAP = {
    "critical": 10.0,
    "high": 8.0,
    "medium": 5.0,
    "low": 2.0,
    "info": 0.0,
}


class VulnValidator:
    """Validate and confirm vulnerability findings, filter false positives."""

    def __init__(self):
        self._results: list[ValidationResult] = []

    def validate(self, finding: Finding) -> ValidationResult:
        """Validate a single finding by replaying the exploit."""
        result = ValidationResult(finding=finding)

        # Step 1: Check for false positive patterns
        if self._check_false_positive(finding):
            result.is_false_positive = True
            result.confirmed = False
            result.confidence = 0.9
            self._results.append(result)
            return result

        # Step 2: Replay the request
        if finding.request:
            replay_result = self._replay_request(finding)
            if replay_result:
                result.confirmed = True
                result.confidence = replay_result.get("confidence", 0.7)
                result.evidence.append(replay_result.get("evidence", ""))
            else:
                result.confirmed = False
                result.confidence = 0.3
                result.evidence.append("Replay failed or no evidence found")
        else:
            # No request to replay — rely on evidence from original scan
            result.confirmed = self._evaluate_evidence(finding)
            result.confidence = 0.6 if result.confirmed else 0.2

        self._results.append(result)
        return result

    def validate_batch(self, findings: list[Finding]) -> list[ValidationResult]:
        """Validate multiple findings."""
        results = []
        for finding in findings:
            result = self.validate(finding)
            results.append(result)
            if result.is_false_positive:
                logger.info(f"FALSE POSITIVE filtered: {finding.title}")
            elif result.confirmed:
                logger.info(f"CONFIRMED: {finding.title} (confidence={result.confidence:.0%})")
        return results

    def retest(self, finding: Finding, payloads: list[str]) -> ValidationResult:
        """Retest with alternative payloads."""
        result = ValidationResult(finding=finding, retested=True)
        for payload in payloads:
            try:
                import urllib.request
                url = finding.url.replace(finding.payload, payload) if finding.payload else finding.url
                if url != finding.url:
                    req = urllib.request.Request(url)
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        body = resp.read(1024).decode("utf-8", errors="ignore")
                        if self._check_payload_reflected(payload, body, finding):
                            result.confirmed = True
                            result.confidence = 0.85
                            result.evidence.append(f"Payload reflected: {payload}")
                            break
            except Exception as e:
                logger.debug(f"Retest failed for payload '{payload}': {e}")

        self._results.append(result)
        return result

    def _check_false_positive(self, finding: Finding) -> bool:
        """Check if finding matches known false positive patterns."""
        evidence_lower = (finding.evidence + " " + finding.response).lower()
        vuln_type = finding.vulnerability_type.lower().replace(" ", "_")

        # Check generic FP patterns
        for ftype, patterns in FP_PATTERNS.items():
            if ftype in vuln_type or vuln_type in ftype:
                matches = sum(1 for p in patterns if p.lower() in evidence_lower)
                if matches >= 2:
                    logger.info(f"False positive detected: {finding.title} "
                                f"(matched {matches} FP patterns for {ftype})")
                    return True

        # Check for common FP in XSS: reflection only in headers/error messages
        if "xss" in vuln_type.lower():
            if any(p.lower() in evidence_lower for p in FP_PATTERNS["reflected_xss"]):
                return True

        return False

    def _replay_request(self, finding: Finding) -> Optional[dict[str, Any]]:
        """Replay the HTTP request and analyze response."""
        try:
            cmd = ["curl", "-sS", "-o", "-", "-D", "-",
                    "-X", "GET", finding.url, "--max-time", "10"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            response = result.stdout

            # Check if the vulnerability is still present
            if finding.payload and finding.payload in response:
                return {
                    "confirmed": True,
                    "confidence": 0.8,
                    "evidence": f"Payload '{finding.payload}' found in replay response",
                }

            # Check for SQL error indicators
            if "sql" in finding.vulnerability_type.lower():
                error_indicators = [
                    "you have an error in your sql syntax",
                    "mysql", "ora-", "postgresql", "sqlite",
                    "microsoft ole db provider",
                ]
                for indicator in error_indicators:
                    if indicator in response.lower():
                        return {
                            "confirmed": True,
                            "confidence": 0.75,
                            "evidence": f"SQL error indicator found: {indicator}",
                        }

        except Exception as e:
            logger.debug(f"Replay failed: {e}")

        return None

    def _evaluate_evidence(self, finding: Finding) -> bool:
        """Evaluate if evidence suggests a real vulnerability."""
        evidence = (finding.evidence + " " + finding.response).lower()
        positive_indicators = [
            "uid=", "root:x:0:0",  # command injection / LFI
            "sql syntax", "mysql", "ora-",  # SQLi
            "alert(", "onerror=", "onload=",  # XSS
            "<script>", "javascript:",  # XSS
            "admin:", "password:", "secret",  # info disclosure
        ]
        return any(ind in evidence for ind in positive_indicators)

    def _check_payload_reflected(self, payload: str, body: str, finding: Finding) -> bool:
        """Check if a payload is reflected in the response body."""
        if payload in body:
            return True
        import html
        decoded = html.unescape(body)
        if payload in decoded:
            return True
        return False

    def get_fp_rate(self) -> float:
        if not self._results:
            return 0.0
        fps = sum(1 for r in self._results if r.is_false_positive)
        return fps / len(self._results)

    def get_confirmation_rate(self) -> float:
        confirmed = [r for r in self._results if r.confirmed and not r.is_false_positive]
        return len(confirmed) / len(self._results) if self._results else 0.0

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_validated": len(self._results),
            "confirmed": sum(1 for r in self._results if r.confirmed),
            "false_positives": sum(1 for r in self._results if r.is_false_positive),
            "fp_rate": f"{self.get_fp_rate():.1%}",
            "confirmation_rate": f"{self.get_confirmation_rate():.1%}",
        }


_vuln_validator: Optional[VulnValidator] = None


def get_vuln_validator() -> VulnValidator:
    global _vuln_validator
    if _vuln_validator is None:
        _vuln_validator = VulnValidator()
    return _vuln_validator
