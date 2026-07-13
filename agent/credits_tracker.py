"""Credits tracking — stub.

The subscription-credits tracking feature is disabled in this build. The entry
points below are inert stubs that return empty / false so callers degrade
gracefully (fail-open) without per-call credits logic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Mapping, Optional

logger = logging.getLogger(__name__)


@dataclass
class CreditsState:
    """Placeholder credits state.

    The credits feature is disabled, so no real credits state is produced.
    All fields default to empty / false and the properties degrade safely.
    """

    captured_at: float = 0.0
    from_header: bool = False

    @property
    def has_data(self) -> bool:
        return False

    @property
    def age_seconds(self) -> float:
        return float("inf")

    @property
    def depleted(self) -> bool:
        return False

    @property
    def used_fraction(self) -> Optional[float]:
        return None


@dataclass
class AgentNotice:
    """A structured, driver-agnostic out-of-band notice (unused stub)."""

    text: str
    level: str = "info"
    kind: str = "sticky"
    ttl_ms: Optional[int] = None
    key: Optional[str] = None
    id: Optional[str] = None


def is_free_tier_model(model: str, base_url: str = "") -> bool:
    """The credits feature is disabled; no model is a free-tier model here."""
    return False


def evaluate_credits_notices(state, latch, *, model_is_free: bool = False):
    """No-op: the credits feature is disabled, so no notices are produced."""
    return ([], [])


def parse_credits_headers(
    headers: Mapping[str, str],
    provider: str = "",
) -> Optional[CreditsState]:
    """No-op: the credits feature is disabled, so no credits headers exist."""
    return None


def dev_fixture_credits_state() -> Optional[CreditsState]:
    """No-op: the credits feature is disabled, so no dev fixtures exist."""
    return None


def seed_credits_at_session_start(agent) -> bool:
    """No-op: the credits feature is disabled, so nothing is seeded.

    Returns False (not seeded). Never raises — credits must never block session
    startup.
    """
    return False
