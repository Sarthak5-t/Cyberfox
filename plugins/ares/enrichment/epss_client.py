from __future__ import annotations

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class EPSSClient:
    """FIRST.org EPSS API client."""

    BASE_URL = "https://api.first.org/data/v1/epss"

    def get_epss(self, cve_id: str) -> Optional[dict]:
        try:
            resp = requests.get(
                self.BASE_URL, params={"cve": cve_id}, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", [])
            if not items:
                return None
            item = items[0]
            return {
                "epss_score": float(item.get("epss", 0)),
                "epss_percentile": float(item.get("percentile", 0)),
                "epss_date": item.get("date"),
            }
        except requests.RequestException as e:
            logger.warning("EPSS request failed for %s: %s", cve_id, e)
            return None
        except (ValueError, KeyError) as e:
            logger.warning("EPSS parse error for %s: %s", cve_id, e)
            return None

    def get_epss_batch(self, cve_ids: list[str]) -> dict[str, dict]:
        results = {}
        batch_size = 50
        for i in range(0, len(cve_ids), batch_size):
            batch = cve_ids[i : i + batch_size]
            cve_param = ",".join(batch)
            try:
                resp = requests.get(
                    self.BASE_URL, params={"cve": cve_param}, timeout=15
                )
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("data", []):
                    results[item["cve"]] = {
                        "epss_score": float(item.get("epss", 0)),
                        "epss_percentile": float(item.get("percentile", 0)),
                        "epss_date": item.get("date"),
                    }
            except requests.RequestException as e:
                logger.warning("EPSS batch request failed: %s", e)
            except (ValueError, KeyError) as e:
                logger.warning("EPSS batch parse error: %s", e)
        return results
