"""Tests for agent.credits_tracker — inert stub.

The credits-tracking feature is disabled in this build. ``parse_credits_headers``
returns ``None`` unconditionally (it does not parse any ``x-credits-*`` headers),
and ``CreditsState`` is a thin placeholder whose properties degrade safely.
These tests assert the stub's fail-open behaviour.
"""

from __future__ import annotations

import time

import pytest

from agent.credits_tracker import (
    CreditsState,
    evaluate_credits_notices,
    is_free_tier_model,
    parse_credits_headers,
    seed_credits_at_session_start,
)


def _sample_headers() -> dict:
    """A dictionary shaped like the old credits response, used only to prove
    the stub ignores it entirely."""
    return {
        "x-credits-version": "1",
        "x-credits-remaining-micros": "30340000",
        "x-credits-remaining-usd": "30.34",
        "x-credits-subscription-micros": "18000000",
        "x-credits-subscription-usd": "18.00",
        "x-credits-purchased-micros": "12340000",
        "x-credits-purchased-usd": "12.34",
        "x-credits-paid-access": "true",
    }


class TestParseCreditsHeadersStub:
    def test_returns_none_for_old_credits_headers(self):
        # The legacy credits header family is no longer parsed.
        assert parse_credits_headers(_sample_headers()) is None

    def test_returns_none_for_empty_headers(self):
        assert parse_credits_headers({}) is None

    def test_returns_none_for_irrelevant_headers(self):
        headers = {
            "content-type": "application/json",
            "x-request-id": "abc123",
            "server": "nginx",
        }
        assert parse_credits_headers(headers) is None

    def test_returns_none_for_api_key_path(self):
        headers = {
            "content-type": "application/json",
            "authorization": "Bearer sk-test",
        }
        assert parse_credits_headers(headers) is None


class TestCreditsStateDefaults:
    def test_default_state(self):
        state = CreditsState()
        assert state.captured_at == 0.0
        assert state.from_header is False

    def test_has_data_is_false(self):
        assert CreditsState().has_data is False

    def test_age_seconds_is_inf(self):
        assert CreditsState().age_seconds == float("inf")

    def test_depleted_is_false(self):
        assert CreditsState().depleted is False

    def test_used_fraction_is_none(self):
        assert CreditsState().used_fraction is None

    def test_explicit_from_header_flag(self):
        state = CreditsState(from_header=True, captured_at=time.time())
        assert state.from_header is True


class TestCreditsFeatureDisabled:
    def test_is_free_tier_model_always_false(self):
        assert is_free_tier_model("any-model") is False
        assert is_free_tier_model("another-model", base_url="https://example.com") is False

    def test_evaluate_credits_notices_is_noop(self):
        notices, latched = evaluate_credits_notices(None, None)
        assert notices == []
        assert latched == []

    def test_seed_credits_at_session_start_returns_false(self):
        class _FakeAgent:
            pass

        assert seed_credits_at_session_start(_FakeAgent()) is False
