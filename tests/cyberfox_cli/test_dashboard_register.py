"""Tests for ``cyberfox dashboard register``.

The self-hosted dashboard OAuth client registration flow has been removed from
this build. ``cmd_dashboard_register`` is an inert stub that prints a notice and
returns cleanly (never raises, never blocks the CLI). These tests assert that
graceful no-op behaviour.
"""

from __future__ import annotations

import argparse

import pytest

import cyberfox_cli.dashboard_register as dr


def _ns(**kw):
    defaults = dict(name=None, redirect_uri=None, portal_url=None)
    defaults.update(kw)
    return argparse.Namespace(**defaults)


class TestDashboardRegisterStub:
    def test_prints_unavailable_notice_and_returns(self, capsys):
        # The stub must degrade gracefully: print a notice and return without
        # raising or attempting any network call.
        result = dr.cmd_dashboard_register(_ns())
        out = capsys.readouterr().out
        assert result is None
        assert "no longer available" in out

    def test_does_not_raise_with_explicit_args(self, capsys):
        dr.cmd_dashboard_register(
            _ns(name="my_box", redirect_uri="https://example.com/auth/callback")
        )
        out = capsys.readouterr().out
        assert "no longer available" in out
