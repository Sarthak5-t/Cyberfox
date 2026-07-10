"""Tests for the Nous-Cyberfox-3/4 non-agentic warning detector.

Prior to this check, the warning fired on any model whose name contained
``"cyberfox"`` anywhere (case-insensitive). That false-positived on unrelated
local Modelfiles such as ``cyberfox-brain:qwen3-14b-ctx16k`` — a tool-capable
Qwen3 wrapper that happens to live under the "cyberfox" tag namespace.

``is_nous_cyberfox_non_agentic`` should only match the actual Nous Research
Cyberfox-3 / Cyberfox-4 chat family.
"""

from __future__ import annotations

import pytest

from cyberfox_cli.model_switch import (
    _CYBERFOX_MODEL_WARNING,
    _check_cyberfox_model_warning,
    is_nous_cyberfox_non_agentic,
)


@pytest.mark.parametrize(
    "model_name",
    [
        "NousResearch/Cyberfox-3-Llama-3.1-70B",
        "NousResearch/Cyberfox-3-Llama-3.1-405B",
        "cyberfox-3",
        "Cyberfox-3",
        "cyberfox-4",
        "cyberfox-4-405b",
        "cyberfox_4_70b",
        "openrouter/cyberfox3:70b",
        "openrouter/nousresearch/cyberfox-4-405b",
        "NousResearch/Cyberfox3",
        "cyberfox-3.1",
    ],
)
def test_matches_real_nous_cyberfox_chat_models(model_name: str) -> None:
    assert is_nous_cyberfox_non_agentic(model_name), (
        f"expected {model_name!r} to be flagged as Nous Cyberfox 3/4"
    )
    assert _check_cyberfox_model_warning(model_name) == _CYBERFOX_MODEL_WARNING


@pytest.mark.parametrize(
    "model_name",
    [
        # Kyle's local Modelfile — qwen3:14b under a custom tag
        "cyberfox-brain:qwen3-14b-ctx16k",
        "cyberfox-brain:qwen3-14b-ctx32k",
        "cyberfox-honcho:qwen3-8b-ctx8k",
        # Plain unrelated models
        "qwen3:14b",
        "qwen3-coder:30b",
        "qwen2.5:14b",
        "claude-opus-4-6",
        "anthropic/claude-sonnet-4.5",
        "gpt-5",
        "openai/gpt-4o",
        "google/gemini-2.5-flash",
        "deepseek-chat",
        # Non-chat Cyberfox models we don't warn about
        "cyberfox-llm-2",
        "cyberfox2-pro",
        "nous-cyberfox-2-mistral",
        # Edge cases
        "",
        "cyberfox",  # bare "cyberfox" isn't the 3/4 family
        "cyberfox-brain",
        "brain-cyberfox-3-impostor",  # "3" not preceded by /: boundary
    ],
)
def test_does_not_match_unrelated_models(model_name: str) -> None:
    assert not is_nous_cyberfox_non_agentic(model_name), (
        f"expected {model_name!r} NOT to be flagged as Nous Cyberfox 3/4"
    )
    assert _check_cyberfox_model_warning(model_name) == ""


def test_none_like_inputs_are_safe() -> None:
    assert is_nous_cyberfox_non_agentic("") is False
    # Defensive: the helper shouldn't crash on None-ish falsy input either.
    assert _check_cyberfox_model_warning("") == ""
