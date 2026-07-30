from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from plugins.ares.cve_kb import db

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com/repos/{full_name}"
_USER_AGENT = "Cyberfox-Ares-CVE-KB"
_CACHE_TTL_HOURS = 24


def _fetch_repo_info(full_name: str, token: str | None = None) -> dict | None:
    url = _GITHUB_API.format(full_name=full_name)
    headers = {"User-Agent": _USER_AGENT, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "stars": data.get("stargazers_count", 0),
                "description": (data.get("description") or "")[:500],
                "language": data.get("language") or "",
            }
    except HTTPError as e:
        if e.code == 403:
            logger.warning("GitHub API rate limited for %s", full_name)
            return None
        if e.code == 404:
            logger.debug("Repo not found: %s", full_name)
            return {"stars": 0, "description": "", "language": ""}
        logger.warning("GitHub API error %s for %s: %s", e.code, full_name, e)
        return None
    except Exception as e:
        logger.debug("Failed to fetch %s: %s", full_name, e)
        return None


def enrich_stale_pocs(
    token: str | None = None,
    max_per_run: int = 50,
    hours: int = _CACHE_TTL_HOURS,
) -> dict:
    stale = db.get_poc_repos_stale(hours=hours, limit=max_per_run)
    if not stale:
        return {"enriched": 0, "remaining": 0, "errors": 0}

    enriched = 0
    errors = 0
    rate_limited = False

    for item in stale:
        if rate_limited:
            break

        url = item["url"]
        full_name = url.replace("https://github.com/", "").rstrip("/")
        if not full_name or "/" not in full_name:
            continue

        info = _fetch_repo_info(full_name, token)
        if info is None:
            if _was_rate_limited(token):
                rate_limited = True
            errors += 1
            continue

        db.update_poc_metadata(
            url=url,
            stars=info["stars"],
            description=info["description"],
            language=info["language"],
        )
        enriched += 1

    return {
        "enriched": enriched,
        "remaining": max(0, len(stale) - enriched - errors),
        "errors": errors,
        "rate_limited": rate_limited,
    }


def _was_rate_limited(token: str | None) -> bool:
    headers = {"User-Agent": _USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = Request("https://api.github.com/rate_limit", headers=headers)
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            core = data.get("resources", {}).get("core", {})
            remaining = core.get("remaining", 0)
            return remaining == 0
    except Exception:
        return False


def get_remaining_requests(token: str | None = None) -> int:
    headers = {"User-Agent": _USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = Request("https://api.github.com/rate_limit", headers=headers)
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("resources", {}).get("core", {}).get("remaining", 0)
    except Exception:
        return 0
