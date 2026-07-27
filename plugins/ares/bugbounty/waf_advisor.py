from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

WAF_SIGNATURES = {
    "Cloudflare": {"headers": ["cf-ray", "cf-cache-status"], "body": ["cloudflare", "attention required"]},
    "AWS WAF": {"headers": ["x-amzn-waf"], "body": ["x-amzn-waf", "aws"]},
    "Akamai": {"headers": ["x-akamai-transformed"], "body": ["akamai", "reference #"]},
    "Imperva": {"headers": ["x-iinfo"], "body": ["imperva", "incapsula"]},
    "Sucuri": {"headers": ["x-sucuri-id"], "body": ["sucuri", "access denied"]},
    "ModSecurity": {"headers": [], "body": ["mod_security", "modsecurity", "rules engine"]},
    "Barracuda": {"headers": [], "body": ["barracuda", "bac_defender"]},
    "FortiWeb": {"headers": [], "body": ["fortiweb", "fortiguard"]},
    "F5 BIG-IP ASM": {"headers": ["x-wa-info"], "body": ["bigip", "f5 networks"]},
    "DDoS-Guard": {"headers": ["x-ddos-guard"], "body": ["ddos-guard"]},
    "RackCDN": {"headers": ["x-rackcdn"], "body": ["rackcdn"]},
    "Fastly": {"headers": ["x-served-by", "x-cache"], "body": ["fastly"]},
    "Vercel": {"headers": ["x-vercel-id"], "body": ["vercel"]},
}

WAF_BLOCK_PATTERNS = {
    "Cloudflare": {"status": [403, 503], "captcha": True},
    "AWS WAF": {"status": [403], "captcha": False},
    "Akamai": {"status": [403, 406], "captcha": False},
    "Imperva": {"status": [403], "captcha": True},
    "Sucuri": {"status": [403], "captcha": False},
    "ModSecurity": {"status": [403, 501], "captcha": False},
}


@dataclass
class WAFResult:
    name: str = "none"
    detected: bool = False
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)


@dataclass
class ScanStrategy:
    rate_limit: float = 10.0
    burst: int = 20
    use_proxy: bool = False
    use_tamper: bool = False
    concurrent_threads: int = 10
    user_agent_rotation: bool = True
    jitter: tuple[float, float] = (0.5, 2.0)
    encoding: list[str] = field(default_factory=list)
    delay_between_requests: float = 0.0
    notes: list[str] = field(default_factory=list)


class WAFAdvisor:
    """WAF detection + automatic scan strategy adjustment."""

    def __init__(self):
        self._waf_result: Optional[WAFResult] = None
        self._strategy: Optional[ScanStrategy] = None

    def detect(self, target: str, use_wafw00f: bool = True) -> WAFResult:
        """Detect WAF on target. Uses wafw00f if available, falls back to heuristic."""
        if use_wafw00f:
            result = self._detect_wafw00f(target)
            if result.detected:
                self._waf_result = result
                return result

        result = self._detect_heuristic(target)
        self._waf_result = result
        return result

    def _detect_wafw00f(self, target: str) -> WAFResult:
        """Run wafw00f binary for detection."""
        try:
            from plugins.ares.tools.base import check_binary
            if not check_binary("wafw00f"):
                return WAFResult()

            url = target if target.startswith("http") else f"http://{target}"
            cmd = ["wafw00f", url, "-o", "-", "-f", "json"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if proc.returncode in (0, 1):
                try:
                    data = json.loads(proc.stdout)
                    if isinstance(data, list) and data:
                        waf_info = data[0]
                        firewall = waf_info.get("firewall", "unknown")
                        if firewall and firewall != "None":
                            return WAFResult(
                                name=firewall,
                                detected=True,
                                confidence=0.9,
                                evidence=[f"wafw00f detected: {firewall}"]
                            )
                except json.JSONDecodeError:
                    pass

            if "No WAF" in proc.stdout or proc.returncode == 1:
                return WAFResult(name="none", detected=False, confidence=0.8,
                                 evidence=["wafw00f: no WAF detected"])

        except Exception as e:
            logger.debug(f"wafw00f detection failed: {e}")

        return WAFResult()

    def _detect_heuristic(self, target: str) -> WAFResult:
        """Heuristic WAF detection via headers and response body."""
        try:
            import urllib.request
            url = target if target.startswith("http") else f"http://{target}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                headers = {k.lower(): v for k, v in resp.headers.items()}
                body = resp.read(4096).decode("utf-8", errors="ignore").lower()

                for waf_name, sigs in WAF_SIGNATURES.items():
                    matches = []
                    for h in sigs["headers"]:
                        if h.lower() in headers:
                            matches.append(f"header:{h}")
                    for b in sigs["body"]:
                        if b.lower() in body:
                            matches.append(f"body:{b}")

                    if matches:
                        confidence = min(1.0, 0.6 + 0.15 * len(matches))
                        return WAFResult(
                            name=waf_name, detected=True, confidence=confidence,
                            evidence=matches
                        )
        except Exception as e:
            logger.debug(f"Heuristic WAF detection failed: {e}")

        return WAFResult()

    def get_strategy(self, waf_result: Optional[WAFResult] = None) -> ScanStrategy:
        """Return optimal scan strategy based on detected WAF."""
        result = waf_result or self._waf_result or WAFResult()

        if not result.detected:
            return ScanStrategy(rate_limit=20.0, burst=40, concurrent_threads=20,
                                notes=["No WAF detected, full speed"])

        waf_strategies = {
            "Cloudflare": ScanStrategy(
                rate_limit=5.0, burst=10, use_proxy=True, use_tamper=True,
                concurrent_threads=5, jitter=(1.0, 4.0),
                notes=["Cloudflare: slow down, rotate IPs, use tamper"]
            ),
            "AWS WAF": ScanStrategy(
                rate_limit=3.0, burst=5, use_proxy=True, use_tamper=True,
                concurrent_threads=3, jitter=(2.0, 6.0),
                notes=["AWS WAF: very slow, IP rotation essential, avoid patterns"]
            ),
            "Akamai": ScanStrategy(
                rate_limit=8.0, burst=15, use_proxy=False, use_tamper=True,
                concurrent_threads=8, jitter=(0.5, 2.0),
                notes=["Akamai: moderate speed, tamper payloads"]
            ),
            "Imperva": ScanStrategy(
                rate_limit=2.0, burst=3, use_proxy=True, use_tamper=True,
                concurrent_threads=2, jitter=(3.0, 8.0),
                notes=["Imperva: very aggressive bot detection, use real browser patterns"]
            ),
            "Sucuri": ScanStrategy(
                rate_limit=10.0, burst=20, concurrent_threads=10, jitter=(0.5, 2.0),
                notes=["Sucuri: moderate, mostly blocks known bad IPs"]
            ),
            "ModSecurity": ScanStrategy(
                rate_limit=5.0, burst=10, use_tamper=True,
                concurrent_threads=5, jitter=(1.0, 3.0),
                encoding=["url", "double_url", "html"],
                notes=["ModSecurity: rule-based, encoding bypass helps"]
            ),
        }

        strategy = waf_strategies.get(result.name, ScanStrategy(
            rate_limit=5.0, burst=10, concurrent_threads=5, use_proxy=True,
            jitter=(1.0, 3.0), notes=[f"Unknown WAF '{result.name}', using conservative settings"]
        ))

        self._strategy = strategy
        return strategy

    def get_current(self) -> dict[str, Any]:
        return {
            "waf": self._waf_result.__dict__ if self._waf_result else None,
            "strategy": self._strategy.__dict__ if self._strategy else None,
        }


_waf_advisor: Optional[WAFAdvisor] = None


def get_waf_advisor() -> WAFAdvisor:
    global _waf_advisor
    if _waf_advisor is None:
        _waf_advisor = WAFAdvisor()
    return _waf_advisor
