from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".cyberfox" / "ares" / "platforms"


@dataclass
class PlatformReport:
    title: str
    vulnerability_type: str
    severity: str
    summary: str
    steps_to_reproduce: list[str] = field(default_factory=list)
    impact: str = ""
    remediation: str = ""
    affected_urls: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    cve: str = ""
    cvss: float = 0.0
    weakness: str = ""


class HackerOneAPI:
    """HackerOne API client for report submission."""

    BASE_URL = "https://api.hackerone.com/v1"

    def __init__(self, username: str = "", api_token: str = ""):
        self._username = username
        self._api_token = api_token
        self._authenticated = False
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Try loading from env
        if not username:
            self._username = os.environ.get("H1_USERNAME", "")
        if not api_token:
            self._api_token = os.environ.get("H1_API_TOKEN", "")

        # Try loading from config file
        config_file = CONFIG_DIR / "hackerone.json"
        if config_file.exists():
            try:
                cfg = json.loads(config_file.read_text())
                if not self._username:
                    self._username = cfg.get("username", "")
                if not self._api_token:
                    self._api_token = cfg.get("api_token", "")
            except Exception:
                pass

    def authenticate(self) -> bool:
        """Verify API credentials."""
        if not self._username or not self._api_token:
            logger.warning("HackerOne credentials not configured. "
                           "Set H1_USERNAME and H1_API_TOKEN env vars, "
                           "or save to ~/.cyberfox/ares/platforms/hackerone.json")
            return False

        result = self._api_request("GET", "/me")
        if result is not None:
            self._authenticated = True
            logger.info("HackerOne authentication successful")
            return True
        return False

    def save_credentials(self, username: str, api_token: str) -> None:
        """Save credentials to config file."""
        self._username = username
        self._api_token = api_token
        config_file = CONFIG_DIR / "hackerone.json"
        config_file.write_text(json.dumps({
            "username": username,
            "api_token": api_token,
        }, indent=2))
        os.chmod(config_file, 0o600)
        logger.info("HackerOne credentials saved")

    def list_programs(self) -> list[dict]:
        """List programs you can submit to."""
        result = self._api_request("GET", "/hackers/programs")
        if result and "data" in result:
            programs = []
            for item in result["data"]:
                attrs = item.get("attributes", {})
                programs.append({
                    "handle": attrs.get("handle", ""),
                    "name": attrs.get("name", ""),
                    "offers_bounties": attrs.get("offers_bounties", False),
                    "state": attrs.get("state", ""),
                })
            return programs
        return []

    def get_program_scope(self, handle: str) -> list[dict]:
        """Get in-scope assets for a program."""
        result = self._api_request("GET", f"/hackers/programs/{handle}")
        if result and "data" in result:
            attrs = result["data"].get("attributes", {})
            structured_scope = attrs.get("structured_scope", [])
            return [
                {
                    "asset_type": s.get("asset_type", ""),
                    "asset_identifier": s.get("asset_identifier", ""),
                    "instruction": s.get("instruction", ""),
                    "eligible_for_bounty": s.get("eligible_for_bounty", True),
                    "max_severity": s.get("max_severity", ""),
                }
                for s in structured_scope
            ]
        return []

    def create_report(self, handle: str, report: PlatformReport,
                      team_handle: str = "") -> Optional[dict]:
        """Submit a report to a HackerOne program."""
        if not self._authenticated:
            if not self.authenticate():
                return None

        payload = {
            "data": {
                "type": "report",
                "attributes": {
                    "team_handle": handle,
                    "vulnerability_information": self._format_report_body(report),
                },
                "relationships": {},
            }
        }

        result = self._api_request("POST", "/reports", json_data=payload)
        if result and "data" in result:
            report_id = result["data"].get("id", "")
            logger.info(f"Report submitted: {report_id}")
            return {
                "report_id": report_id,
                "url": f"https://hackerone.com/reports/{report_id}",
                "state": result["data"].get("attributes", {}).get("state", ""),
            }
        return None

    def upload_attachment(self, report_id: str, filepath: str,
                          filename: str = "") -> bool:
        """Upload a file attachment to a report."""
        if not self._authenticated:
            return False

        path = Path(filepath)
        if not path.exists():
            logger.error(f"File not found: {filepath}")
            return False

        fname = filename or path.name
        file_b64 = base64.b64encode(path.read_bytes()).decode()

        payload = {
            "data": {
                "type": "report-attachment",
                "attributes": {
                    "filename": fname,
                    "content_type": "application/octet-stream",
                    "content": file_b64,
                },
                "relationships": {
                    "report": {
                        "data": {
                            "type": "report",
                            "id": report_id,
                        }
                    }
                }
            }
        }

        result = self._api_request("POST", "/reports/attachments", json_data=payload)
        return result is not None

    def get_report(self, report_id: str) -> Optional[dict]:
        """Get report details."""
        result = self._api_request("GET", f"/reports/{report_id}")
        if result and "data" in result:
            attrs = result["data"].get("attributes", {})
            return {
                "id": result["data"].get("id", ""),
                "title": attrs.get("title", ""),
                "state": attrs.get("state", ""),
                "substate": attrs.get("substate", ""),
                "created_at": attrs.get("created_at", ""),
                "triaged_at": attrs.get("triaged_at", ""),
            }
        return None

    def add_comment(self, report_id: str, message: str) -> bool:
        """Add a comment to a report."""
        payload = {
            "data": {
                "type": "comment",
                "attributes": {
                    "message": message,
                },
                "relationships": {
                    "report": {
                        "data": {
                            "type": "report",
                            "id": report_id,
                        }
                    }
                }
            }
        }
        result = self._api_request("POST", "/comments", json_data=payload)
        return result is not None

    def _format_report_body(self, report: PlatformReport) -> str:
        """Format a PlatformReport into HackerOne's markdown report body."""
        lines = [
            f"# {report.title}",
            "",
            "## Summary",
            report.summary,
            "",
            "## Vulnerability Type",
            report.vulnerability_type,
            "",
        ]

        if report.cve:
            lines.extend(["## CVE", report.cve, ""])
        if report.cvss:
            lines.extend(["## CVSS", str(report.cvss), ""])

        if report.affected_urls:
            lines.append("## Affected URLs")
            for url in report.affected_urls:
                lines.append(f"- {url}")
            lines.append("")

        if report.steps_to_reproduce:
            lines.append("## Steps to Reproduce")
            for i, step in enumerate(report.steps_to_reproduce, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        if report.evidence:
            lines.append("## Evidence")
            for ev in report.evidence:
                lines.append(f"```\n{ev}\n```")
            lines.append("")

        if report.impact:
            lines.extend(["## Impact", report.impact, ""])

        if report.remediation:
            lines.extend(["## Remediation", report.remediation, ""])

        return "\n".join(lines)

    def _api_request(self, method: str, endpoint: str,
                     json_data: Optional[dict] = None) -> Optional[dict]:
        """Make authenticated API request using curl."""
        url = f"{self.BASE_URL}{endpoint}"
        cmd = [
            "curl", "-sS", "-X", method, url,
            "-H", "Content-Type: application/json",
        ]

        if self._username and self._api_token:
            auth_str = base64.b64encode(f"{self._username}:{self._api_token}".encode()).decode()
            cmd.extend(["-H", f"Authorization: Basic {auth_str}"])

        if json_data:
            cmd.extend(["-d", json.dumps(json_data)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"API request failed: {result.stderr}")
                return None

            response = json.loads(result.stdout)
            return response
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"API request error: {e}")
            return None


_hackerone: Optional[HackerOneAPI] = None


def get_hackerone(username: str = "", api_token: str = "") -> HackerOneAPI:
    global _hackerone
    if _hackerone is None:
        _hackerone = HackerOneAPI(username=username, api_token=api_token)
    return _hackerone
