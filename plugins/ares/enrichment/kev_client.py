from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Optional

import requests

from cyberfox_constants import get_cyberfox_home as get_cf_home

logger = logging.getLogger(__name__)


class KEVClient:
    """CISA Known Exploited Vulnerabilities catalog client."""

    CATALOG_URL = (
        "https://www.cisa.gov/sites/default/files/feeds/"
        "known_exploited_vulnerabilities.json"
    )
    CACHE_TTL = 86400

    def __init__(self):
        self._cache: dict[str, dict] = {}
        self._cache_time: float = 0.0
        self._lock = threading.Lock()

    def _cache_path(self) -> Path:
        return get_cf_home() / "ares" / "cache" / "kev_catalog.json"

    def _load_cache(self) -> bool:
        with self._lock:
            if self._cache and (time.time() - self._cache_time) < self.CACHE_TTL:
                return True

            cache_file = self._cache_path()
            if cache_file.exists():
                try:
                    age = time.time() - cache_file.stat().st_mtime
                    if age < self.CACHE_TTL:
                        data = json.loads(cache_file.read_text())
                        self._cache = {
                            v["cveID"]: v
                            for v in data.get("vulnerabilities", [])
                        }
                        self._cache_time = time.time()
                        return True
                except Exception:
                    pass

            try:
                resp = requests.get(self.CATALOG_URL, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                self._cache = {
                    v["cveID"]: v for v in data.get("vulnerabilities", [])
                }
                self._cache_time = time.time()
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps(data, indent=None))
                return True
            except Exception as e:
                logger.error("Failed to download KEV catalog: %s", e)
                return False

    def is_in_kev(self, cve_id: str) -> Optional[dict]:
        self._load_cache()
        entry = self._cache.get(cve_id)
        if not entry:
            return None
        return {
            "kev": True,
            "kev_vendor": entry.get("vendorProject"),
            "kev_product": entry.get("product"),
            "kev_date_added": entry.get("dateAdded"),
            "kev_due_date": entry.get("dueDate"),
            "kev_ransomware": entry.get("knownRansomwareCampaignUse") == "Known",
            "kev_description": entry.get("shortDescription", "")[:200],
        }

    def get_stats(self) -> dict:
        self._load_cache()
        return {"total_kev": len(self._cache)}
