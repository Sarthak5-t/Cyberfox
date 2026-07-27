from __future__ import annotations

import logging
import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TargetRateState:
    """Rate tracking state for a single target."""
    requests_made: int = 0
    consecutive_403: int = 0
    consecutive_429: int = 0
    last_429_time: float = 0.0
    backoff_until: float = 0.0
    is_banned: bool = False
    ban_time: float = 0.0
    response_times: list[float] = field(default_factory=list)


class TokenBucket:
    """Thread-safe token bucket rate limiter."""

    def __init__(self, rate: float = 10.0, burst: int = 20):
        self._rate = rate
        self._burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    @property
    def rate(self) -> float:
        return self._rate

    @rate.setter
    def rate(self, value: float) -> None:
        with self._lock:
            self._rate = max(0.1, value)
            self._tokens = min(self._tokens, self._burst)

    def consume(self, tokens: int = 1, blocking: bool = True) -> bool:
        """Consume tokens. Returns True if successful."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            if not blocking:
                return False

        # Block until tokens available
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
            wait = (tokens - self._tokens) / self._rate
            time.sleep(min(wait, 0.5))

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
        self._last_refill = now

    def available(self) -> int:
        with self._lock:
            self._refill()
            return int(self._tokens)


class RateLimiter:
    """Rate limiter with per-target tracking, ban detection, and backoff."""

    def __init__(self, rate: float = 10.0, burst: int = 20):
        self._bucket = TokenBucket(rate=rate, burst=burst)
        self._targets: dict[str, TargetRateState] = {}
        self._lock = threading.Lock()
        self._global_ban_detected = False
        self._stats = defaultdict(int)

    @property
    def rate(self) -> float:
        return self._bucket.rate

    @rate.setter
    def rate(self, value: float) -> None:
        self._bucket.rate = value

    def get_target_state(self, target: str) -> TargetRateState:
        with self._lock:
            if target not in self._targets:
                self._targets[target] = TargetRateState()
            return self._targets[target]

    def wait_if_needed(self, target: str) -> None:
        """Block if rate limited or backed off for this target."""
        state = self.get_target_state(target)
        now = time.time()

        # Check if banned
        if state.is_banned:
            wait_time = state.ban_time + 3600 - now  # 1hr ban
            if wait_time > 0:
                raise RateLimitError(
                    f"Target {target} is BANNED. Wait {wait_time:.0f}s or reset manually."
                )
            state.is_banned = False
            state.consecutive_403 = 0
            state.consecutive_429 = 0
            logger.info(f"Ban expired for {target}, resuming")

        # Check backoff
        if state.backoff_until > now:
            wait = state.backoff_until - now
            logger.info(f"Backing off {target} for {wait:.1f}s")
            time.sleep(wait)

        # Consume token
        self._bucket.consume(blocking=True)
        self._stats["total_requests"] += 1

    def report_response(self, target: str, status_code: int, response_time: float = 0.0) -> None:
        """Report HTTP response code for rate/ban tracking."""
        state = self.get_target_state(target)
        state.requests_made += 1
        if response_time > 0:
            state.response_times.append(response_time)
            if len(state.response_times) > 100:
                state.response_times = state.response_times[-50:]

        if status_code == 429:
            state.consecutive_429 += 1
            state.last_429_time = time.time()
            # Exponential backoff: 2s, 4s, 8s, 16s... max 1hr
            backoff = min(2 ** state.consecutive_429, 3600)
            state.backoff_until = time.time() + backoff
            self._stats["rate_limited"] += 1
            logger.warning(f"Rate limited on {target} (429 x{state.consecutive_429}), "
                           f"backing off {backoff}s")

        elif status_code in (403, 503, 406):
            state.consecutive_403 += 1
            if state.consecutive_403 >= 5:
                state.is_banned = True
                state.ban_time = time.time()
                self._global_ban_detected = True
                self._stats["bans"] += 1
                logger.critical(f"BAN DETECTED on {target} after {state.consecutive_403} "
                                f"consecutive blocks. HALTING.")
                raise RateLimitError(f"BANNED on {target}! Too many blocks.")
        else:
            state.consecutive_403 = max(0, state.consecutive_403 - 1)
            state.consecutive_429 = max(0, state.consecutive_429 - 1)

    def is_banned(self, target: str) -> bool:
        state = self.get_target_state(target)
        return state.is_banned

    def is_rate_limited(self, target: str) -> bool:
        state = self.get_target_state(target)
        return state.backoff_until > time.time()

    def reset_target(self, target: str) -> None:
        with self._lock:
            self._targets[target] = TargetRateState()

    def get_stats(self) -> dict:
        return {
            "total_requests": self._stats["total_requests"],
            "rate_limited": self._stats["rate_limited"],
            "bans": self._stats["bans"],
            "targets_tracked": len(self._targets),
            "bucket_available": self._bucket.available(),
        }

    def configure_for_program(self, max_rps: float, burst: int = 0) -> None:
        """Configure rate limiter for a bug bounty program's rules."""
        self._bucket.rate = max_rps
        if burst > 0:
            self._bucket._burst = burst
        logger.info(f"Rate limiter configured: {max_rps} req/s, burst={burst or int(max_rps * 2)}")


class RateLimitError(Exception):
    pass


_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
