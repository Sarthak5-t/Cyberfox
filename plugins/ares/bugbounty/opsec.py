from __future__ import annotations

import logging
import random
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,fr;q=0.8",
    "en-US,en;q=0.9,es;q=0.8",
    "de-DE,de;q=0.9,en;q=0.8",
    "ja-JP,ja;q=0.9,en;q=0.8",
    "pt-BR,pt;q=0.9,en;q=0.8",
    "en-CA,en;q=0.9,fr;q=0.8",
    "en-AU,en;q=0.9",
    "en-US,en;q=0.9,hi;q=0.8",
]

ACCEPT_HEADERS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,application/signed-exchange;v=b3;q=0.7",
]


class OPSEC:
    """Operational security layer: header randomization, timing jitter, fingerprinting."""

    def __init__(self):
        self._ua_index = random.randint(0, len(USER_AGENTS) - 1)
        self._jitter_min = 0.5
        self._jitter_max = 3.0
        self._stats = {"requests": 0, "headers_rotated": 0}

    def randomize_headers(self) -> dict[str, str]:
        """Generate randomized HTTP headers for a request."""
        self._stats["headers_rotated"] += 1
        ua = random.choice(USER_AGENTS)
        return {
            "User-Agent": ua,
            "Accept": random.choice(ACCEPT_HEADERS),
            "Accept-Language": random.choice(ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": random.choice(["max-age=0", "no-cache"]),
        }

    def randomize_tool_headers(self) -> dict[str, str]:
        """Generate headers that look like a real browser for tool requests."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": random.choice(ACCEPT_HEADERS),
            "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        }

    def jitter_delay(self) -> float:
        """Sleep a random amount between min and max seconds."""
        delay = random.uniform(self._jitter_min, self._jitter_max)
        time.sleep(delay)
        return delay

    def get_delay(self) -> float:
        """Get next delay without sleeping."""
        return random.uniform(self._jitter_min, self._jitter_max)

    def set_jitter(self, min_sec: float, max_sec: float) -> None:
        self._jitter_min = min_sec
        self._jitter_max = max_sec

    def get_fingerprint(self) -> dict[str, Any]:
        return {
            "user_agent": random.choice(USER_AGENTS),
            "platform": random.choice(["Win32", "MacIntel", "Linux x86_64"]),
            "language": random.choice(["en-US", "en-GB", "de-DE", "fr-FR"]),
            "screen_resolution": random.choice([
                "1920x1080", "2560x1440", "1366x768", "1536x864",
                "1440x900", "1280x720", "3840x2160"
            ]),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "requests": self._stats["requests"],
            "headers_rotated": self._stats["headers_rotated"],
            "jitter_range": f"{self._jitter_min}-{self._jitter_max}s",
        }


_opsec: Optional[OPSEC] = None


def get_opsec() -> OPSEC:
    global _opsec
    if _opsec is None:
        _opsec = OPSEC()
    return _opsec
