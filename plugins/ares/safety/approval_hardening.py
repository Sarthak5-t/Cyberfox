from __future__ import annotations

import logging

from plugins.ares.config import get_config

logger = logging.getLogger(__name__)

_EXPLOIT_TOOLS = frozenset({
    "sqlmap_scan", "hydra_brute", "msf_exec", "responder_listener",
    "impacket_exec", "bloodhound_ingest", "certipy_tool", "crackmapexec",
    "metasploit_tool", "ares_delegate",
})


def pre_tool_call(
    tool_name: str,
    args: dict = None,
    task_id: str = None,
    session_id: str = None,
    tool_call_id: str = None,
    turn_id: str = None,
    api_request_id: str = None,
    **kwargs,
):
    cfg = get_config()
    if not cfg.safety_require_exploit_approval:
        return None
    if tool_name not in _EXPLOIT_TOOLS:
        return None
    logger.warning(
        "Exploit tool requires approval: %s session=%s turn=%s",
        tool_name, session_id, turn_id,
    )
    return {
        "action": "block",
        "message": (
            f"Tool `{tool_name}` is an exploitation tool requiring explicit "
            f"approval. Disable via `ares.safety.require_exploit_approval: false`."
        ),
    }
