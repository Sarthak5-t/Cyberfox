"""Tests for get_cyberfox_home() profile-mode fallback warning.

Regression test for https://github.com/NousResearch/cyberfox-agent/issues/18594.

When CYBERFOX_HOME is unset but an active_profile file indicates a non-default
profile is active, get_cyberfox_home() should:
  1. STILL return ~/.cyberfox (raising would brick 30+ module-level callers)
  2. Emit a loud one-shot warning to stderr so operators can diagnose
     cross-profile data contamination after the fact.

The warning goes to stderr directly (not through logging) because this
function is called at module-import time from 30+ sites, often before the
logging subsystem has been configured.
"""

from pathlib import Path

import pytest


@pytest.fixture
def fresh_constants(monkeypatch, tmp_path):
    """Import cyberfox_constants fresh and reset the one-shot warn flag."""
    import importlib
    import cyberfox_constants
    importlib.reload(cyberfox_constants)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("CYBERFOX_HOME", raising=False)
    return cyberfox_constants


class TestGetCyberfoxHomeProfileWarning:
    def test_classic_mode_no_active_profile_no_warning(
        self, fresh_constants, tmp_path, capsys
    ):
        """Classic mode: no active_profile file → silent, returns ~/.cyberfox."""
        result = fresh_constants.get_cyberfox_home()
        assert result == tmp_path / ".cyberfox"
        assert "CYBERFOX_HOME fallback" not in capsys.readouterr().err

    def test_default_active_profile_no_warning(
        self, fresh_constants, tmp_path, capsys
    ):
        """active_profile=default → still no warning, returns ~/.cyberfox."""
        cyberfox_dir = tmp_path / ".cyberfox"
        cyberfox_dir.mkdir()
        (cyberfox_dir / "active_profile").write_text("default\n")
        result = fresh_constants.get_cyberfox_home()
        assert result == tmp_path / ".cyberfox"
        assert "CYBERFOX_HOME fallback" not in capsys.readouterr().err

    def test_named_profile_unset_home_warns_once(
        self, fresh_constants, tmp_path, capsys
    ):
        """active_profile=coder + CYBERFOX_HOME unset → warn loudly, still return fallback."""
        cyberfox_dir = tmp_path / ".cyberfox"
        cyberfox_dir.mkdir()
        (cyberfox_dir / "active_profile").write_text("coder\n")

        result = fresh_constants.get_cyberfox_home()

        # 1. Still returns the fallback — no import-time crash
        assert result == tmp_path / ".cyberfox"
        # 2. Stderr got the warning exactly once
        err = capsys.readouterr().err
        assert err.count("CYBERFOX_HOME fallback") == 1
        assert "'coder'" in err
        assert "#18594" in err

        # 3. One-shot: second and third calls don't re-warn
        fresh_constants.get_cyberfox_home()
        fresh_constants.get_cyberfox_home()
        err2 = capsys.readouterr().err
        assert "CYBERFOX_HOME fallback" not in err2

    def test_cyberfox_home_set_suppresses_warning(
        self, fresh_constants, tmp_path, capsys, monkeypatch
    ):
        """Even if active_profile is 'coder', setting CYBERFOX_HOME suppresses warning."""
        profile_dir = tmp_path / ".cyberfox" / "profiles" / "coder"
        profile_dir.mkdir(parents=True)
        (tmp_path / ".cyberfox" / "active_profile").write_text("coder\n")
        monkeypatch.setenv("CYBERFOX_HOME", str(profile_dir))

        result = fresh_constants.get_cyberfox_home()

        assert result == profile_dir
        assert "CYBERFOX_HOME fallback" not in capsys.readouterr().err

    def test_unreadable_active_profile_no_crash(
        self, fresh_constants, tmp_path, capsys
    ):
        """active_profile that can't be decoded → fall through silently."""
        cyberfox_dir = tmp_path / ".cyberfox"
        cyberfox_dir.mkdir()
        # Write bytes that aren't valid utf-8
        (cyberfox_dir / "active_profile").write_bytes(b"\xff\xfe\x00\x00")

        result = fresh_constants.get_cyberfox_home()

        assert result == tmp_path / ".cyberfox"
        # Shouldn't crash; shouldn't warn either (can't tell what profile was intended)
        assert "CYBERFOX_HOME fallback" not in capsys.readouterr().err

    def test_empty_active_profile_no_warning(
        self, fresh_constants, tmp_path, capsys
    ):
        """Empty active_profile file → treated as default, no warning."""
        cyberfox_dir = tmp_path / ".cyberfox"
        cyberfox_dir.mkdir()
        (cyberfox_dir / "active_profile").write_text("")

        result = fresh_constants.get_cyberfox_home()

        assert result == tmp_path / ".cyberfox"
        assert "CYBERFOX_HOME fallback" not in capsys.readouterr().err
