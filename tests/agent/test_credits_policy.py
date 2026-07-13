"""Tests for agent.credits_tracker — inert stub policy surface.

The credits feature is disabled in this build. ``evaluate_credits_notices`` is a
no-op, ``is_free_tier_model`` always returns ``False``, and ``CreditsState`` is a
thin placeholder whose properties degrade safely. These tests assert that
fail-open behaviour.
"""

from __future__ import annotations

import pytest

from agent.credits_tracker import (
    AgentNotice,
    CreditsState,
    evaluate_credits_notices,
    is_free_tier_model,
    seed_credits_at_session_start,
)


def fresh_latch() -> dict:
    return {"active": set(), "seen_below_90": False, "usage_band": None}


class TestCreditsPolicyStub:
    def test_evaluate_returns_empty_noop(self):
        latch = fresh_latch()
        state = CreditsState()
        to_show, to_clear = evaluate_credits_notices(state, latch)
        assert to_show == []
        assert to_clear == []

    def test_evaluate_never_mutates_latch(self):
        latch = fresh_latch()
        evaluate_credits_notices(CreditsState(), latch)
        assert latch == fresh_latch()

    def test_agent_notice_dataclass_exists(self):
        notice = AgentNotice(text="hi")
        assert notice.text == "hi"
        assert notice.level == "info"
        assert notice.kind == "sticky"

    def test_is_free_tier_model_always_false(self):
        assert is_free_tier_model("any-model") is False
        assert is_free_tier_model("") is False

    def test_seed_returns_false(self):
        class _FakeAgent:
            pass

        assert seed_credits_at_session_start(_FakeAgent()) is False
