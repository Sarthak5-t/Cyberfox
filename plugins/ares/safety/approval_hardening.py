from __future__ import annotations

import logging
from typing import Any

from plugins.ares.config import get_config
from plugins.ares.tools.permission import (
    PermissionLevel,
    get_tool_permission,
)

logger = logging.getLogger(__name__)


def pre_tool_call(
    tool_name: str,
    args: dict | None = None,
    task_id: str | None = None,
    session_id: str | None = None,
    tool_call_id: str | None = None,
    turn_id: str | None = None,
    api_request_id: str | None = None,
    **kwargs: Any,
) -> dict | None:
    """Check whether a tool call is allowed under the permission system.

    Returns None if allowed, or a dict with action + message if blocked.
    Uses the new PermissionLevel system from permission.py, falling back
    to the legacy hardcoded set for backward compatibility.
    """
    cfg = get_config()

    perm_level, external_effect, _category, _timeout = get_tool_permission(tool_name)

    if cfg.safety_require_exploit_approval and perm_level >= PermissionLevel.DANGEROUS:
        logger.warning(
            "Dangerous tool requires approval: %s session=%s turn=%s",
            tool_name, session_id, turn_id,
        )
        return {
            "action": "block",
            "message": (
                f"Tool `{tool_name}` requires explicit approval "
                f"(permission level: {perm_level.name}). "
                f"Disable via `ares.safety.require_exploit_approval: false`."
            ),
        }

    if cfg.requires_approval and tool_name in cfg.requires_approval:
        logger.warning(
            "Tool in approval list: %s session=%s turn=%s",
            tool_name, session_id, turn_id,
        )
        return {
            "action": "block",
            "message": f"Tool `{tool_name}` is in the approval-required list.",
        }

    return None


def check_permission(tool_name: str, max_level: PermissionLevel = PermissionLevel.DANGEROUS) -> tuple[bool, str]:
    """Check if a tool is within the allowed permission level.

    Returns (allowed, reason).
    """
    perm_level, _external, _cat, _timeout = get_tool_permission(tool_name)
    if perm_level > max_level:
        return False, (
            f"Tool `{tool_name}` requires {perm_level.name} but max allowed is {max_level.name}"
        )
    return True, ""


def requires_exploit_approval(tool_name: str) -> bool:
    """Check if a tool requires exploit-level approval."""
    cfg = get_config()
    if not cfg.safety_require_exploit_approval:
        return False
    perm_level, _external, _cat, _timeout = get_tool_permission(tool_name)
    return perm_level >= PermissionLevel.DANGEROUS
