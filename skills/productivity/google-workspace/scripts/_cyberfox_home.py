"""Resolve CYBERFOX_HOME for standalone skill scripts.

Skill scripts may run outside the Cyberfox process (e.g. system Python,
nix env, CI) where ``cyberfox_constants`` is not importable.  This module
provides the same ``get_cyberfox_home()`` and ``display_cyberfox_home()``
contracts as ``cyberfox_constants`` without requiring it on ``sys.path``.

When ``cyberfox_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``cyberfox_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``CYBERFOX_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from cyberfox_constants import display_cyberfox_home as display_cyberfox_home
    from cyberfox_constants import get_cyberfox_home as get_cyberfox_home
except (ModuleNotFoundError, ImportError):

    def get_cyberfox_home() -> Path:
        """Return the Cyberfox home directory (default: ~/.cyberfox).

        Mirrors ``cyberfox_constants.get_cyberfox_home()``."""
        val = os.environ.get("CYBERFOX_HOME", "").strip()
        return Path(val) if val else Path.home() / ".cyberfox"

    def display_cyberfox_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``cyberfox_constants.display_cyberfox_home()``."""
        home = get_cyberfox_home()
        try:
            return "~/" + str(home.relative_to(Path.home()))
        except ValueError:
            return str(home)
