from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class NVDClient:
    """NVD REST API 2.0 client with rate limiting."""

    BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._last_request = 0.0
        self._lock = threading.Lock()
        self._min_interval = 0.6

    def get_cve(self, cve_id: str) -> Optional[dict]:
        self._rate_limit()
        try:
            headers = {"apiKey": self.api_key}
            params = {"cveId": cve_id}
            resp = requests.get(
                self.BASE_URL, params=params, headers=headers, timeout=10
            )
            if resp.status_code == 403:
                logger.warning("NVD rate limit hit for %s", cve_id)
                return None
            resp.raise_for_status()
            data = resp.json()
            vulns = data.get("vulnerabilities", [])
            if not vulns:
                return None
            cve = vulns[0]["cve"]
            return self._parse_cve(cve)
        except requests.RequestException as e:
            logger.warning("NVD request failed for %s: %s", cve_id, e)
            return None
        except (KeyError, IndexError) as e:
            logger.warning("NVD parse error for %s: %s", cve_id, e)
            return None

    def _parse_cve(self, cve: dict) -> dict:
        cvss_score = None
        cvss_vector = None
        cvss_severity = None

        metrics = cve.get("metrics", {})
        for version_key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if version_key in metrics and metrics[version_key]:
                try:
                    m = metrics[version_key][0]["cvssData"]
                    cvss_score = m.get("baseScore")
                    cvss_vector = m.get("vectorString")
                    cvss_severity = m.get("baseSeverity")
                except (KeyError, IndexError):
                    pass
                break

        cwe_list = []
        for weakness in cve.get("weaknesses", []):
            for desc in weakness.get("description", []):
                val = desc.get("value", "")
                if val.startswith("CWE-"):
                    cwe_list.append(val)

        cpe_list = []
        for config in cve.get("configurations", []):
            for node in config.get("nodes", []):
                for match in node.get("cpeMatch", []):
                    criteria = match.get("criteria", "")
                    if criteria:
                        cpe_list.append(criteria)

        description = ""
        for desc in cve.get("descriptions", []):
            if desc.get("lang") == "en":
                description = desc.get("value", "")
                break

        references = [r.get("url", "") for r in cve.get("references", [])]

        return {
            "cve_id": cve["id"],
            "cvss_score": cvss_score,
            "cvss_vector": cvss_vector,
            "cvss_severity": cvss_severity,
            "cwe": cwe_list,
            "cpe": cpe_list[:10],
            "description": description[:500],
            "published": cve.get("published"),
            "last_modified": cve.get("lastModified"),
            "vuln_status": cve.get("vulnStatus"),
            "references": references[:5],
            "source": "nvd",
        }

    def _rate_limit(self):
        with self._lock:
            elapsed = time.time() - self._last_request
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_request = time.time()
