"""Linux-only subprocess compatibility stubs.

All functions are no-ops on Linux — Cyberfox is Kali Linux only.
"""

from __future__ import annotations

IS_WINDOWS = False


def windows_hide_flags() -> int:
    return 0


def windows_detach_flags() -> int:
    return 0


def windows_detach_flags_without_breakaway() -> int:
    return 0


def windows_detach_popen_kwargs() -> dict:
    return {}
