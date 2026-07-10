"""Tests for is_provider_explicitly_configured()."""

import json
import pytest


def _write_config(tmp_path, config: dict) -> None:
    cyberfox_home = tmp_path / "cyberfox"
    cyberfox_home.mkdir(parents=True, exist_ok=True)
    import yaml
    (cyberfox_home / "config.yaml").write_text(yaml.dump(config))


def _write_auth_store(tmp_path, payload: dict) -> None:
    cyberfox_home = tmp_path / "cyberfox"
    cyberfox_home.mkdir(parents=True, exist_ok=True)
    (cyberfox_home / "auth.json").write_text(json.dumps(payload, indent=2))


@pytest.fixture(autouse=True)
def _clean_anthropic_env(monkeypatch):
    """Strip Anthropic env vars so CI secrets don't leak into tests."""
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN"):
        monkeypatch.delenv(key, raising=False)


def test_returns_false_when_no_config(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERFOX_HOME", str(tmp_path / "cyberfox"))
    (tmp_path / "cyberfox").mkdir(parents=True, exist_ok=True)

    from cyberfox_cli.auth import is_provider_explicitly_configured
    assert is_provider_explicitly_configured("anthropic") is False


def test_returns_true_when_active_provider_matches(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERFOX_HOME", str(tmp_path / "cyberfox"))
    _write_auth_store(tmp_path, {
        "version": 1,
        "providers": {},
        "active_provider": "anthropic",
    })

    from cyberfox_cli.auth import is_provider_explicitly_configured
    assert is_provider_explicitly_configured("anthropic") is True


def test_returns_true_when_config_provider_matches(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERFOX_HOME", str(tmp_path / "cyberfox"))
    _write_config(tmp_path, {"model": {"provider": "anthropic", "default": "claude-sonnet-4-6"}})

    from cyberfox_cli.auth import is_provider_explicitly_configured
    assert is_provider_explicitly_configured("anthropic") is True


def test_returns_false_when_config_provider_is_different(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERFOX_HOME", str(tmp_path / "cyberfox"))
    _write_config(tmp_path, {"model": {"provider": "kimi-coding", "default": "kimi-k2"}})
    _write_auth_store(tmp_path, {
        "version": 1,
        "providers": {},
        "active_provider": None,
    })

    from cyberfox_cli.auth import is_provider_explicitly_configured
    assert is_provider_explicitly_configured("anthropic") is False


def test_returns_true_when_anthropic_env_var_set(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERFOX_HOME", str(tmp_path / "cyberfox"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-realkey")
    (tmp_path / "cyberfox").mkdir(parents=True, exist_ok=True)

    from cyberfox_cli.auth import is_provider_explicitly_configured
    assert is_provider_explicitly_configured("anthropic") is True


def test_claude_code_oauth_token_does_not_count_as_explicit(tmp_path, monkeypatch):
    """CLAUDE_CODE_OAUTH_TOKEN is set by Claude Code, not the user — must not gate."""
    monkeypatch.setenv("CYBERFOX_HOME", str(tmp_path / "cyberfox"))
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-auto-token")
    (tmp_path / "cyberfox").mkdir(parents=True, exist_ok=True)

    from cyberfox_cli.auth import is_provider_explicitly_configured
    assert is_provider_explicitly_configured("anthropic") is False
