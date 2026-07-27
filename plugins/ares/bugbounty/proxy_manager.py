from __future__ import annotations

import logging
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProxyInfo:
    url: str
    proxy_type: str = "http"  # http, socks5, https
    username: str = ""
    password: str = ""
    is_healthy: bool = True
    failures: int = 0
    success_count: int = 0
    last_used: float = 0.0
    last_check: float = 0.0
    avg_latency: float = 0.0
    total_latency: float = 0.0


class ProxyManager:
    """Proxy rotation with health tracking. Supports HTTP/HTTPS/SOCKS5."""

    def __init__(self):
        self._proxies: dict[str, ProxyInfo] = {}
        self._current_index = 0
        self._lock = threading.Lock()
        self._max_failures = 3
        self._use_tor = False
        self._stats = {"requests_routed": 0, "failures": 0}

    def add_proxy(self, url: str, proxy_type: str = "http",
                  username: str = "", password: str = "") -> None:
        """Register a proxy."""
        proxy_id = self._proxy_id(url)
        self._proxies[proxy_id] = ProxyInfo(
            url=url, proxy_type=proxy_type,
            username=username, password=password
        )
        logger.info(f"Proxy added: {proxy_type}://{url}")

    def add_tor_proxy(self, control_port: int = 9051, socks_port: int = 9050) -> None:
        """Configure Tor SOCKS5 proxy."""
        self.add_proxy(f"127.0.0.1:{socks_port}", "socks5")
        self._use_tor = True
        logger.info(f"Tor proxy added on port {socks_port}")

    def remove_proxy(self, url: str) -> None:
        proxy_id = self._proxy_id(url)
        self._proxies.pop(proxy_id, None)

    def get_proxy(self) -> Optional[ProxyInfo]:
        """Get next healthy proxy via round-robin. Returns None if no healthy proxies."""
        with self._lock:
            healthy = [p for p in self._proxies.values() if p.is_healthy]
            if not healthy:
                return None
            # Round-robin
            proxy = healthy[self._current_index % len(healthy)]
            self._current_index += 1
            proxy.last_used = time.time()
            return proxy

    def get_proxy_for_tool(self) -> list[str]:
        """Return command-line proxy args for tools like nuclei/nuclei."""
        proxy = self.get_proxy()
        if not proxy:
            return []
        return ["-proxy", f"{proxy.proxy_type}://{proxy.url}"]

    def get_curl_proxy(self) -> Optional[str]:
        """Return proxy string for curl."""
        proxy = self.get_proxy()
        if not proxy:
            return None
        return f"{proxy.proxy_type}://{proxy.url}"

    def report_success(self, url: str, latency: float = 0.0) -> None:
        """Report successful request through proxy."""
        proxy_id = self._proxy_id(url)
        if proxy_id in self._proxies:
            p = self._proxies[proxy_id]
            p.failures = max(0, p.failures - 1)
            p.success_count += 1
            p.is_healthy = True
            if latency > 0:
                p.total_latency += latency
                p.avg_latency = p.total_latency / p.success_count

    def report_failure(self, url: str) -> bool:
        """Report failed request. Returns True if proxy was disabled."""
        proxy_id = self._proxy_id(url)
        if proxy_id in self._proxies:
            p = self._proxies[proxy_id]
            p.failures += 1
            self._stats["failures"] += 1
            if p.failures >= self._max_failures:
                p.is_healthy = False
                logger.warning(f"Proxy {url} DISABLED after {p.failures} failures")
                return True
        return False

    def rotate_tor(self) -> Optional[str]:
        """Request new Tor circuit (requires tor control port)."""
        if not self._use_tor:
            return None
        try:
            from stem import Signal
            from stem.control import Controller
            with Controller.from_port(port=9051) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)
                logger.info("Tor: new circuit requested")
                time.sleep(2)
                return "Tor circuit rotated"
        except Exception as e:
            logger.debug(f"Tor rotation failed: {e}")
            return None

    def get_all(self) -> list[dict[str, Any]]:
        return [
            {
                "url": p.url, "type": p.proxy_type,
                "healthy": p.is_healthy, "failures": p.failures,
                "successes": p.success_count,
                "avg_latency": round(p.avg_latency * 1000, 1),
            }
            for p in self._proxies.values()
        ]

    def get_healthy_count(self) -> int:
        return sum(1 for p in self._proxies.values() if p.is_healthy)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_proxies": len(self._proxies),
            "healthy": self.get_healthy_count(),
            "requests_routed": self._stats["requests_routed"],
            "failures": self._stats["failures"],
            "tor_enabled": self._use_tor,
        }

    @staticmethod
    def _proxy_id(url: str) -> str:
        return url.lower().strip()


_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager() -> ProxyManager:
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager
