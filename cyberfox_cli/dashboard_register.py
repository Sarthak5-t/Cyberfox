"""``cyberfox dashboard register`` — stub.

This command previously registered a self-hosted dashboard OAuth client, but
that flow depended on a provider that has been removed from this build. Every
entry point below is an inert stub that returns empty / false so callers degrade
gracefully (fail-open).
"""

from __future__ import annotations


def cmd_dashboard_register(args) -> None:
    """No-op.

    The self-hosted dashboard OAuth client registration that this command
    performed is no longer available. We degrade gracefully (print a notice and
    exit cleanly) rather than attempting a request against a removed backend.

    Never raises — dashboard registration must never block the CLI.
    """
    print(
        "`cyberfox dashboard register` is no longer available."
    )
